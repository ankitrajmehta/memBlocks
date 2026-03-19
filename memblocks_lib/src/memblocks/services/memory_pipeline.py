"""MemoryPipeline — memory processing pipeline called explicitly by Session.add()."""

from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from memblocks.models.llm_outputs import SummaryOutput
from memblocks.models.units import MemoryOperation, ProcessingEvent, SemanticMemoryUnit
from memblocks.prompts import SUMMARY_SYSTEM_PROMPT
from memblocks.logger import get_logger

if TYPE_CHECKING:
    from memblocks.config import MemBlocksConfig
    from memblocks.llm.base import LLMProvider
    from memblocks.services.core_memory import CoreMemoryService
    from memblocks.services.semantic_memory import SemanticMemoryService
    from memblocks.services.transparency import (
        LLMUsageTracker,
        OperationLog,
        ProcessingHistory,
    )

logger = get_logger(__name__)


class MemoryPipeline:
    """
    Orchestrates the full memory processing pipeline.

    Called explicitly via ``await pipeline.run(...)`` from ``Session.add()``.
    The caller decides whether to await inline or schedule as a background task
    via ``asyncio.create_task(session.add(...))``.

    Pipeline steps:
    1. Semantic memory extraction (PS1) + conflict resolution (PS2) + storage.
    2. Core memory update.
    3. Recursive summary generation.

    Post-run state management (session messages + summary) is handled by the
    caller (Session.add()) after this coroutine returns, so this class has no
    knowledge of session IDs or MongoDB session documents.
    """

    def __init__(
        self,
        semantic_memory_service: "SemanticMemoryService",
        core_memory_service: "CoreMemoryService",
        summary_llm: "LLMProvider",
        config: "MemBlocksConfig",
        processing_history: Optional["ProcessingHistory"] = None,
        operation_log: Optional["OperationLog"] = None,
        event_bus: Optional[Any] = None,
        llm_usage_tracker: Optional["LLMUsageTracker"] = None,
    ) -> None:
        """
        Args:
            semantic_memory_service: Handles semantic extraction/storage.
            core_memory_service: Handles core memory updates.
            summary_llm: LLM for summary generation.
            config: Library configuration (temperatures etc.).
            processing_history: Transparency — records pipeline runs.
            operation_log: Transparency — records DB writes.
            event_bus: Transparency — publishes pipeline events.
            llm_usage_tracker: Optional tracker; when provided, a per-run
                usage snapshot is captured in the ``PipelineRunEntry``.
        """
        self._semantic = semantic_memory_service
        self._core = core_memory_service
        self._summary_llm = summary_llm
        self._config = config
        self._history = processing_history
        self._log = operation_log
        self._bus = event_bus
        self._llm_usage = llm_usage_tracker

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def run(
        self,
        user_id: str,
        block_id: str,
        messages: List[Dict[str, str]],
        current_summary: str = "",
    ) -> str:
        """
        Execute the full pipeline and return the new recursive summary.

        This is a plain coroutine — the caller (Session.add) decides whether
        to await it directly or wrap it in asyncio.create_task().

        Steps:
        1. Semantic extraction (PS1) + conflict resolution (PS2) + storage.
        2. Core memory update.
        3. Recursive summary generation.

        Args:
            user_id: Owner user ID (used for transparency logging).
            block_id: Active memory block ID.
            messages: Snapshot of the message window to process.
            current_summary: Current recursive summary (empty string if none).

        Returns:
            New recursive summary string.
        """
        run_id = f"pipeline_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
        run_start = datetime.utcnow()  # snapshot for per-run usage tracking

        if self._history:
            self._history.record_start(
                task_id=run_id,
                trigger_event="message_window_full",
                message_count=len(messages),
            )
        if self._bus:
            self._bus.publish(
                "on_pipeline_started",
                {"run_id": run_id, "message_count": len(messages)},
            )

        logger.info(
            "Memory pipeline started: %s — processing %d messages for block %s",
            run_id,
            len(messages),
            block_id,
        )
        all_operations: List[MemoryOperation] = []

        try:
            # ---- STEP 1: Semantic Memory ----
            logger.debug("Step 1: Semantic Extraction")
            semantic_memories = await self._semantic.extract(messages)
            logger.debug("Extracted %d semantic memories", len(semantic_memories))

            for mem in semantic_memories:
                ops = await self._semantic.store(mem)
                all_operations.extend(ops)
            logger.debug(
                "Stored semantic memories (%d operations)", len(all_operations)
            )

            # ---- STEP 2: Core Memory ----
            logger.debug("Step 2: Core Memory Update")
            new_core = await self._core.update(block_id=block_id, messages=messages)
            logger.debug("Core memory updated")

            # ---- STEP 3: Recursive Summary ----
            logger.debug("Step 3: Recursive Summary Generation")
            new_summary = await self._generate_summary(messages, current_summary)
            logger.debug("Summary generated")

            # Transparency
            ProcessingEvent(
                event_id=run_id,
                timestamp=datetime.utcnow().isoformat(),
                messages_processed=len(messages),
                operations=all_operations,
            )

            # Capture per-run LLM usage snapshot
            run_llm_usage: Dict[str, Any] = {}
            if self._llm_usage is not None:
                raw_summary = self._llm_usage.get_run_summary(since=run_start)
                run_llm_usage = {
                    ct: summary.model_dump() for ct, summary in raw_summary.items()
                }

            if self._history:
                self._history.record_complete(
                    run_id,
                    {
                        "summary_generated": bool(new_summary),
                        "core_memory_updated": True,
                        "semantic_ops": len(all_operations),
                        "llm_usage": run_llm_usage,
                    },
                )
            if self._bus:
                self._bus.publish("on_pipeline_completed", {"run_id": run_id})

            logger.info("Memory pipeline complete: %s", run_id)
            return new_summary

        except Exception as exc:
            if self._history:
                self._history.record_failure(run_id, str(exc))
            if self._bus:
                self._bus.publish(
                    "on_pipeline_failed",
                    {"run_id": run_id, "error": str(exc)},
                )
            logger.error("Memory pipeline failed (%s): %s", run_id, exc)
            raise

    # ------------------------------------------------------------------ #
    # Summary generation
    # ------------------------------------------------------------------ #

    async def _generate_summary(
        self,
        messages: List[Dict[str, str]],
        previous_summary: str,
    ) -> str:
        """
        Generate a recursive summary that incorporates the current message window.

        Args:
            messages: Message window being processed.
            previous_summary: Existing recursive summary (empty string if none).

        Returns:
            Updated summary string. Falls back to previous_summary on error.
        """
        conversation_text = "\n".join(
            [f"{msg['role'].upper()}: {msg['content']}\n" for msg in messages]
        )

        user_input = (
            f"Previous Summary:\n"
            f"{previous_summary if previous_summary else 'None'}\n\n"
            f"Recent Conversation:\n{conversation_text}\n\n"
            f"Generate an updated recursive summary that incorporates the new conversation."
        )

        try:
            chain = self._summary_llm.create_structured_chain(
                system_prompt=SUMMARY_SYSTEM_PROMPT,
                pydantic_model=SummaryOutput,
                temperature=self._config.llm_recursive_summary_gen_temperature,
            )
            result = await chain.ainvoke({"input": user_input})
            return result.summary

        except Exception as e:
            logger.warning("Failed to generate recursive summary: %s", e)
            return previous_summary
