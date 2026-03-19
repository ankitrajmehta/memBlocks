"""SessionManager — creates and loads Session objects wired with pipeline."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from memblocks.logger import get_logger
from memblocks.services.session import Session

if TYPE_CHECKING:
    from memblocks.services.block_manager import BlockManager
    from memblocks.services.core_memory import CoreMemoryService
    from memblocks.services.memory_pipeline import MemoryPipeline
    from memblocks.services.semantic_memory import SemanticMemoryService
    from memblocks.services.transparency import LLMUsageTracker, OperationLog
    from memblocks.storage.mongo import MongoDBAdapter
    from memblocks.config import MemBlocksConfig
    from memblocks.llm.base import LLMProvider
    from memblocks.storage.qdrant import QdrantAdapter
    from memblocks.storage.embeddings import EmbeddingProvider

logger = get_logger(__name__)


class SessionManager:
    """
    Creates and loads Session objects.

    Each Session is wired with a MemoryPipeline scoped to the session's
    block (a new SemanticMemoryService instance per block's collection).
    """

    def __init__(
        self,
        mongo_adapter: "MongoDBAdapter",
        ps1_llm: "LLMProvider",
        qdrant_adapter: "QdrantAdapter",
        embedding_provider: "EmbeddingProvider",
        core_memory_service: "CoreMemoryService",
        config: "MemBlocksConfig",
        memory_window_limit: int = 10,
        keep_last_n: int = 5,
        operation_log: Optional["OperationLog"] = None,
        event_bus: Optional[Any] = None,
        processing_history: Optional[Any] = None,
        retrieval_log: Optional[Any] = None,
        ps2_llm: Optional["LLMProvider"] = None,
        retrieval_llm: Optional["LLMProvider"] = None,
        summary_llm: Optional["LLMProvider"] = None,
        llm_usage_tracker: Optional["LLMUsageTracker"] = None,
    ) -> None:
        self._mongo = mongo_adapter
        self._ps1_llm = ps1_llm
        self._ps2_llm = ps2_llm or ps1_llm
        self._retrieval_llm = retrieval_llm or ps1_llm
        self._summary_llm = summary_llm or ps1_llm
        self._qdrant = qdrant_adapter
        self._embeddings = embedding_provider
        self._core = core_memory_service
        self._config = config
        self._memory_window_limit = memory_window_limit
        self._keep_last_n = keep_last_n
        self._log = operation_log
        self._bus = event_bus
        self._history = processing_history
        self._retrieval_log = retrieval_log
        self._llm_usage = llm_usage_tracker

    # ------------------------------------------------------------------ #
    # Session lifecycle
    # ------------------------------------------------------------------ #

    async def create_session(
        self,
        user_id: str,
        block_id: str,
    ) -> "Session":
        """
        Create and persist a new session, returning a stateful Session object.

        Args:
            user_id: Owner of the session.
            block_id: Memory block attached to this session.

        Returns:
            Stateful Session object.
        """
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        current_time = datetime.utcnow().isoformat()
        session_data: Dict[str, Any] = {
            "session_id": session_id,
            "user_id": user_id,
            "block_id": block_id,
            "created_at": current_time,
            "messages": [],
            "recursive_summary": "",
        }
        await self._mongo.create_session(session_data)
        logger.info("Created session: %s (block: %s)", session_id, block_id)
        return self._make_session(
            session_id=session_id,
            user_id=user_id,
            block_id=block_id,
            created_at=current_time,
        )

    async def get_session(self, session_id: str) -> Optional["Session"]:
        """
        Load a session from MongoDB and return a stateful Session object.

        Args:
            session_id: Session identifier.

        Returns:
            Session object or None if not found.
        """
        doc = await self._mongo.get_session(session_id)
        if not doc:
            return None
        return self._make_session(
            session_id=doc["session_id"],
            user_id=doc.get("user_id", ""),
            block_id=doc.get("block_id", ""),
            created_at=doc.get("created_at"),
        )

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _make_pipeline(
        self, block_id: str, semantic_collection: str
    ) -> "MemoryPipeline":
        """Build a MemoryPipeline scoped to the given block's Qdrant collection."""
        from memblocks.services.memory_pipeline import MemoryPipeline
        from memblocks.services.semantic_memory import SemanticMemoryService

        semantic_svc = SemanticMemoryService(
            ps1_llm=self._ps1_llm,
            ps2_llm=self._ps2_llm,
            retrieval_llm=self._retrieval_llm,
            embedding_provider=self._embeddings,
            qdrant_adapter=self._qdrant,
            collection_name=semantic_collection,
            config=self._config,
            operation_log=self._log,
            retrieval_log=self._retrieval_log,
            event_bus=self._bus,
        )
        return MemoryPipeline(
            semantic_memory_service=semantic_svc,
            core_memory_service=self._core,
            summary_llm=self._summary_llm,
            config=self._config,
            processing_history=self._history,
            operation_log=self._log,
            event_bus=self._bus,
            llm_usage_tracker=self._llm_usage,
        )

    def _make_session(
        self,
        session_id: str,
        user_id: str,
        block_id: str,
        created_at: Optional[str] = None,
    ) -> "Session":
        """
        Build a wired Session.  We need the block's semantic_collection to
        construct the pipeline — look it up from the blocks collection.
        The lookup is deferred to pipeline construction time (lazy), so this
        method is synchronous.

        Because blocks always have the naming convention
        ``{block_id}_semantic``, we can derive the collection name without
        an extra DB round-trip.
        """
        semantic_collection = f"{block_id}_semantic"
        pipeline = self._make_pipeline(block_id, semantic_collection)
        return Session(
            session_id=session_id,
            user_id=user_id,
            block_id=block_id,
            mongo=self._mongo,
            pipeline=pipeline,
            memory_window_limit=self._memory_window_limit,
            keep_last_n=self._keep_last_n,
            created_at=created_at,
            llm_usage_tracker=self._llm_usage,
        )
