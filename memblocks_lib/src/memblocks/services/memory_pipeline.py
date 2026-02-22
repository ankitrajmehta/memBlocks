"""MemoryPipeline — background memory processing extracted from services/chat_service.py."""

import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from memblocks.models.llm_outputs import SummaryOutput
from memblocks.models.units import MemoryOperation, ProcessingEvent, SemanticMemoryUnit
from memblocks.prompts import SUMMARY_SYSTEM_PROMPT

if TYPE_CHECKING:
    from memblocks.config import MemBlocksConfig
    from memblocks.llm.base import LLMProvider
    from memblocks.services.core_memory import CoreMemoryService
    from memblocks.services.semantic_memory import SemanticMemoryService
    from memblocks.services.transparency import OperationLog, ProcessingHistory


class TaskStatus(str, Enum):
    """Background processing task status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class _TaskRecord:
    """Internal container for a single background task's state."""

    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        self.status: TaskStatus = TaskStatus.RUNNING
        self.started_at: datetime = datetime.now()
        self.completed_at: Optional[datetime] = None
        self.error: Optional[str] = None
        self.result: Optional[Dict[str, Any]] = None


class MemoryPipeline:
    """
    Orchestrates the full background memory processing pipeline:

    1. Semantic memory extraction (PS1) + conflict resolution (PS2) + storage.
    2. Core memory update.
    3. Recursive summary generation.                ← Bug Fix 4: was ``pass``
    4. Message history flush (keep last N messages).

    Extracted from:
    - ChatService._process_memory_window_task() (chat_service.py:224-292)
    - ChatService._generate_recursive_summary() (chat_service.py:366-401)
    - ChatService._process_memory_window() (chat_service.py:323-364)
    - ChatService._trigger_memory_processing() (chat_service.py:403-431)

    Bug Fix 4: ``_process_memory_window_task`` at chat_service.py:288 was
    literally ``pass`` — Step 3 (summary generation) was never executed.
    This class fully implements all pipeline steps.
    """

    def __init__(
        self,
        semantic_memory_service: "SemanticMemoryService",
        core_memory_service: "CoreMemoryService",
        llm_provider: "LLMProvider",
        config: "MemBlocksConfig",
        keep_last_n: int = 4,
        max_concurrent: int = 1,
        processing_history: Optional["ProcessingHistory"] = None,
        operation_log: Optional["OperationLog"] = None,
        event_bus: Optional[Any] = None,
    ) -> None:
        """
        Args:
            semantic_memory_service: Handles semantic extraction/storage.
            core_memory_service: Handles core memory updates.
            llm_provider: LLM for summary generation.
            config: Library configuration.
            keep_last_n: Messages to retain after a flush.
            max_concurrent: Maximum concurrent pipeline runs.
            processing_history: Phase-9 transparency placeholder.
            operation_log: Phase-9 transparency placeholder.
            event_bus: Phase-9 event publishing placeholder.
        """
        self._semantic = semantic_memory_service
        self._core = core_memory_service
        self._llm = llm_provider
        self._config = config
        self._keep_last_n = keep_last_n

        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._lock = asyncio.Lock()

        self._tasks: Dict[str, _TaskRecord] = {}
        self._history = processing_history
        self._log = operation_log
        self._bus = event_bus

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def trigger(
        self,
        user_id: str,
        block_id: str,
        messages: List[Dict[str, str]],
        current_summary: str,
        message_history_ref: List[Dict[str, str]],
        summary_ref_holder: Dict[str, str],
    ) -> str:
        """
        Fire-and-forget: schedule the pipeline as an asyncio background task.

        Args:
            user_id: Owner of the memory block.
            block_id: Active memory block ID.
            messages: Snapshot of message history to process.
            current_summary: Current recursive summary text.
            message_history_ref: The live message list — pipeline will trim it.
            summary_ref_holder: Dict with key "summary" — pipeline will update it.

        Returns:
            task_id for later status queries.
        """
        task_id = f"mem_proc_{uuid.uuid4()}"

        async def _run_with_tracking() -> None:
            record = _TaskRecord(task_id)
            self._tasks[task_id] = record
            # Transparency: record pipeline start
            if self._history:
                self._history.record_start(
                    task_id=task_id,
                    trigger_event="message_window_full",
                    message_count=len(messages),
                )
            if self._bus:
                self._bus.publish(
                    "on_pipeline_started",
                    {
                        "task_id": task_id,
                        "message_count": len(messages),
                    },
                )
            try:
                new_summary = await self._run(
                    task_id=task_id,
                    user_id=user_id,
                    block_id=block_id,
                    messages=messages,
                    current_summary=current_summary,
                )
                async with self._lock:
                    summary_ref_holder["summary"] = new_summary
                    old_len = len(message_history_ref)
                    del message_history_ref[: max(0, old_len - self._keep_last_n)]
                    print(
                        f"   ✓ Flushed history ({old_len} → {len(message_history_ref)})"
                    )
                record.status = TaskStatus.COMPLETED
                record.completed_at = datetime.now()
                # Transparency: record success
                if self._history:
                    self._history.record_complete(
                        task_id,
                        {
                            "summary_generated": bool(new_summary),
                            "core_memory_updated": True,
                        },
                    )
                if self._bus:
                    self._bus.publish("on_pipeline_completed", {"task_id": task_id})

            except Exception as exc:
                record.status = TaskStatus.FAILED
                record.error = str(exc)
                record.completed_at = datetime.now()
                # Transparency: record failure
                if self._history:
                    self._history.record_failure(task_id, str(exc))
                if self._bus:
                    self._bus.publish(
                        "on_pipeline_failed",
                        {
                            "task_id": task_id,
                            "error": str(exc),
                        },
                    )
                print(f"❌ Memory pipeline failed (Task: {task_id[:12]}...): {exc}")

        task = asyncio.create_task(_run_with_tracking())
        task.add_done_callback(
            lambda t: (
                print(f"⚠️ Uncaught error in pipeline: {t.exception()}")
                if not t.cancelled() and t.exception()
                else None
            )
        )
        return task_id

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Return the status dictionary for a task.

        Args:
            task_id: ID returned by trigger().

        Returns:
            Dict with keys: status, started_at, completed_at, error.
        """
        record = self._tasks.get(task_id)
        if not record:
            return {"status": "unknown", "task_id": task_id}
        return {
            "task_id": task_id,
            "status": record.status.value,
            "started_at": record.started_at,
            "completed_at": record.completed_at,
            "error": record.error,
        }

    async def get_all_statuses(self) -> Dict[str, Any]:
        """Return summary stats for all tracked tasks."""
        statuses = [r.status for r in self._tasks.values()]
        return {
            "total": len(statuses),
            "running": statuses.count(TaskStatus.RUNNING),
            "completed": statuses.count(TaskStatus.COMPLETED),
            "failed": statuses.count(TaskStatus.FAILED),
        }

    # ------------------------------------------------------------------ #
    # Core pipeline
    # ------------------------------------------------------------------ #

    async def _run(
        self,
        task_id: str,
        user_id: str,
        block_id: str,
        messages: List[Dict[str, str]],
        current_summary: str,
    ) -> str:
        """
        Execute the full pipeline and return the updated summary.

        Steps:
        1. Semantic extraction + PS2 conflict resolution + storage.
        2. Core memory update.
        3. Recursive summary generation.  ← Bug Fix 4

        Args:
            task_id: For logging.
            user_id: Owner user ID.
            block_id: Active memory block ID.
            messages: Message snapshot to process.
            current_summary: Current recursive summary.

        Returns:
            New recursive summary string.
        """
        async with self._semaphore:
            print(f"🔄 MEMORY PIPELINE START (Task: {task_id[:12]}...)")
            print(f"   Processing {len(messages)} messages...")

            all_operations: List[MemoryOperation] = []

            # ---- STEP 1: Semantic Memory ----
            print("   → STEP 1: Semantic Extraction...")
            semantic_memories = await self._semantic.extract(messages)
            print(f"   ✓ Extracted {len(semantic_memories)} semantic memories")

            for mem in semantic_memories:
                ops = await self._semantic.store(mem)
                all_operations.extend(ops)
            print(f"   ✓ Stored {len(semantic_memories)} memories")

            # ---- STEP 2: Core Memory ----
            print("   → STEP 2: Core Memory Update...")
            await self._core.update(block_id=block_id, messages=messages)
            print("   ✓ Updated core memory")

            # ---- STEP 3: Recursive Summary (Bug Fix 4 — was `pass`) ----
            print("   → STEP 3: Recursive Summary...")
            new_summary = await self._generate_summary(messages, current_summary)
            print("   ✓ Summary updated")

            # Record ProcessingEvent (will feed into transparency in Phase 9)
            event = ProcessingEvent(
                messages_processed=len(messages),
                operations=all_operations,
            )

            print(f"✅ MEMORY PIPELINE COMPLETE (Task: {task_id[:12]}...)")
            return new_summary

    # ------------------------------------------------------------------ #
    # Summary generation
    # ------------------------------------------------------------------ #

    async def _generate_summary(
        self,
        messages: List[Dict[str, str]],
        previous_summary: str,
    ) -> str:
        """
        Generate a recursive summary that incorporates the current window.

        Merges ChatService._generate_recursive_summary() (chat_service.py:366-401)
        and ChatService._generate_recursive_summary_bg() (chat_service.py:294-321)
        into a single async implementation.

        Args:
            messages: Message window being processed.
            previous_summary: Existing recursive summary (empty string if none).

        Returns:
            Updated summary string.
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
            chain = self._llm.create_structured_chain(
                system_prompt=SUMMARY_SYSTEM_PROMPT,
                pydantic_model=SummaryOutput,
                temperature=self._config.llm_recursive_summary_gen_temperature,
            )
            result = await chain.ainvoke({"input": user_input})
            return result.summary

        except Exception as e:
            print(f"⚠️ Failed to generate summary: {e}")
            return previous_summary
