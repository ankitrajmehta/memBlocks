"""ChatEngine — conversation handling extracted from services/chat_service.py."""

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from memblocks.models.units import CoreMemoryUnit, SemanticMemoryUnit
from memblocks.prompts import ASSISTANT_BASE_PROMPT

if TYPE_CHECKING:
    from memblocks.config import MemBlocksConfig
    from memblocks.llm.base import LLMProvider
    from memblocks.services.block_manager import BlockManager
    from memblocks.services.core_memory import CoreMemoryService
    from memblocks.services.memory_pipeline import MemoryPipeline
    from memblocks.services.semantic_memory import SemanticMemoryService
    from memblocks.services.session_manager import SessionManager
    from memblocks.services.transparency import RetrievalLog
    from memblocks.services.user_manager import UserManager


class ChatEngine:
    """
    Handles the conversational turn:
    1. Retrieve relevant memories (semantic + core).
    2. Assemble context (XML-tagged system prompt).
    3. Send to LLM.
    4. Persist messages via SessionManager.
    5. Trigger MemoryPipeline when window is full.

    Extracted from ChatService (chat_service.py):
    - send_message() (lines 507-565)
    - _retrieve_semantic_memories() (lines 437-447)
    - _get_core_memory() (lines 449-453)
    - _build_system_prompt() (lines 455-501)
    """

    def __init__(
        self,
        session_manager: "SessionManager",
        semantic_memory_service: "SemanticMemoryService",
        core_memory_service: "CoreMemoryService",
        memory_pipeline: "MemoryPipeline",
        llm_provider: "LLMProvider",
        config: "MemBlocksConfig",
        memory_window: int = 10,
        retrieval_top_k: int = 5,
        retrieval_log: Optional["RetrievalLog"] = None,
        event_bus: Optional[Any] = None,
    ) -> None:
        """
        Args:
            session_manager: Manages session state / message persistence.
            semantic_memory_service: Retrieves and stores semantic memories.
            core_memory_service: Retrieves core memory for context.
            memory_pipeline: Background pipeline triggered when window is full.
            llm_provider: LLM used for chat responses.
            config: Library configuration.
            memory_window: Number of messages that triggers pipeline.
            retrieval_top_k: Memories returned per query.
            retrieval_log: Phase-9 transparency placeholder.
            event_bus: Phase-9 event publishing placeholder.
        """
        self._sessions = session_manager
        self._semantic = semantic_memory_service
        self._core = core_memory_service
        self._pipeline = memory_pipeline
        self._llm = llm_provider
        self._config = config
        self._memory_window = memory_window
        self._top_k = retrieval_top_k
        self._retrieval_log = retrieval_log
        self._bus = event_bus

        # Per-engine mutable state (summary ref + message history ref)
        # These are managed externally by the session; kept here for pipeline handoff.
        self._summary_ref: Dict[str, str] = {"summary": ""}

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def send_message(
        self,
        session_id: str,
        user_message: str,
    ) -> Dict[str, Any]:
        """
        Process one user message and produce an assistant response.

        Steps:
        1. Retrieve relevant semantic + core memories.
        2. Build system prompt (XML-tagged).
        3. Add user message to session history.
        4. Call LLM.
        5. Add assistant message to session history.
        6. If window full → trigger MemoryPipeline.

        Args:
            session_id: Active session identifier.
            user_message: The user's input text.

        Returns:
            Dict with "response" and "retrieved_context" keys.
        """
        print(f"\n{'─' * 70}")
        print("💬 Processing message...")
        print(f"{'─' * 70}")

        # ---- retrieve session state ----
        session = await self._sessions.get_session(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")

        block_id: str = session.get("block_id", "")

        # ---- memory retrieval ----
        print("🔍 Retrieving memories...")
        semantic_memories = self._retrieve_semantic_memories(user_message)
        core_memory = await self._core.get(block_id)
        print(f"   📚 Semantic: {len(semantic_memories)} memories")
        print(f"   🧠 Core: {'Yes' if core_memory else 'No'}")

        # ---- assemble system prompt ----
        system_prompt = await self._build_system_prompt(
            semantic_memories=semantic_memories,
            core_memory=core_memory,
            recursive_summary=self._summary_ref["summary"],
        )

        # ---- persist user message ----
        await self._sessions.add_message(session_id, role="user", content=user_message)

        # ---- build messages list for LLM ----
        history = await self._sessions.get_messages(session_id)
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)

        # ---- call LLM ----
        try:
            assistant_response = await self._llm.chat(
                messages=messages,
                temperature=self._config.llm_convo_temperature,
            )
        except Exception as e:
            print(f"⚠️ LLM error: {e}")
            assistant_response = (
                "I apologize, but I encountered an error processing your message."
            )

        # ---- persist assistant message ----
        await self._sessions.add_message(
            session_id, role="assistant", content=assistant_response
        )

        # ---- check memory window ----
        msg_count = await self._sessions.get_message_count(session_id)
        if msg_count >= self._memory_window:
            print(
                "\n🔄 Memory window threshold reached, triggering background processing..."
            )
            all_messages = await self._sessions.get_messages(session_id)
            # Pass a mutable list; pipeline will trim it via the ref
            self._pipeline.trigger(
                user_id=session.get("user_id", ""),
                block_id=block_id,
                messages=list(all_messages),
                current_summary=self._summary_ref["summary"],
                message_history_ref=all_messages,
                summary_ref_holder=self._summary_ref,
            )

        # ---- format retrieved context for caller ----
        retrieved_context = [
            {
                "content": mem.content,
                "type": mem.type,
                "confidence": mem.confidence,
                "keywords": mem.keywords[:5] if mem.keywords else [],
            }
            for mem in semantic_memories
        ]

        return {"response": assistant_response, "retrieved_context": retrieved_context}

    async def get_chat_history(
        self,
        session_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Return recent messages for a session.

        Args:
            session_id: Active session identifier.
            limit: Maximum number of messages to return.

        Returns:
            List of message dicts with "role" and "content".
        """
        return await self._sessions.get_messages(session_id, limit=limit)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _retrieve_semantic_memories(
        self,
        query: str,
    ) -> List[SemanticMemoryUnit]:
        """
        Retrieve relevant semantic memories for a query.

        Mirrors ChatService._retrieve_semantic_memories() (chat_service.py:437-447).
        """
        results = self._semantic.retrieve([query], top_k=self._top_k)
        return results[0] if results else []

    async def _build_system_prompt(
        self,
        semantic_memories: List[SemanticMemoryUnit],
        core_memory: Optional[CoreMemoryUnit],
        recursive_summary: str,
        base_prompt: str = ASSISTANT_BASE_PROMPT,
    ) -> str:
        """
        Build the system prompt with tagged memory sections.

        Preserves XML tag format from ChatService._build_system_prompt()
        (chat_service.py:455-501):
        - <CORE_MEMORY>
        - <CONVERSATION_SUMMARY>
        - <SEMANTIC_MEMORY>

        Args:
            semantic_memories: Retrieved semantic memories.
            core_memory: Core memory (persona + human facts).
            recursive_summary: Current recursive summary.
            base_prompt: Base assistant instructions.

        Returns:
            Complete system prompt string.
        """
        parts = [base_prompt]

        # Core memory (always present if it exists)
        if core_memory and (core_memory.persona_content or core_memory.human_content):
            core_text = []
            if core_memory.persona_content:
                core_text.append(f"[PERSONA]\n{core_memory.persona_content}")
            if core_memory.human_content:
                core_text.append(f"[HUMAN]\n{core_memory.human_content}")
            parts.append(f"\n<CORE_MEMORY>\n{chr(10).join(core_text)}\n</CORE_MEMORY>")

        # Recursive summary
        if recursive_summary:
            parts.append(
                f"\n<CONVERSATION_SUMMARY>\n{recursive_summary}\n</CONVERSATION_SUMMARY>"
            )

        # Semantic memories
        if semantic_memories:
            semantic_text = "\n\n".join(
                [
                    f"[{mem.type.upper()}] {mem.content}\n"
                    f"  Keywords: {', '.join(mem.keywords[:5])}"
                    for mem in semantic_memories
                ]
            )
            parts.append(f"\n<SEMANTIC_MEMORY>\n{semantic_text}\n</SEMANTIC_MEMORY>")

        return "\n".join(parts)
