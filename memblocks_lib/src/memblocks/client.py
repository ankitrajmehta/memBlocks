"""MemBlocksClient — single entry-point for the memBlocks library.

Users interact with the library exclusively through this class.
All dependencies are wired here via constructor injection; no singletons or
globals escape this module.

Usage (minimal):

    from memblocks import MemBlocksClient, MemBlocksConfig

    config = MemBlocksConfig()           # reads from .env
    client = MemBlocksClient(config)

    # User + block management
    user = await client.users.get_or_create("alice")
    block = await client.blocks.create_block("alice", "Work Memory")

    # Get a chat engine scoped to a block
    engine = client.get_chat_engine(block)
    session_id = await engine.sessions.create_session("alice", block.meta_data.id)
    result = await engine.chat.send_message(session_id, "Hello!")
    print(result["response"])

Usage (custom providers):

    from memblocks import MemBlocksClient, MemBlocksConfig
    from memblocks.llm.groq_provider import GroqLLMProvider

    config = MemBlocksConfig(groq_api_key="gsk_…")
    my_llm = GroqLLMProvider(config)
    client = MemBlocksClient(config, llm_provider=my_llm)
"""

from typing import Any, Optional, TYPE_CHECKING

from memblocks.config import MemBlocksConfig
from memblocks.llm.groq_provider import GroqLLMProvider
from memblocks.storage.embeddings import EmbeddingProvider
from memblocks.storage.mongo import MongoDBAdapter
from memblocks.storage.qdrant import QdrantAdapter
from memblocks.services.block_manager import BlockManager
from memblocks.services.core_memory import CoreMemoryService
from memblocks.services.memory_pipeline import MemoryPipeline
from memblocks.services.semantic_memory import SemanticMemoryService
from memblocks.services.session_manager import SessionManager
from memblocks.services.transparency import (
    EventBus,
    OperationLog,
    ProcessingHistory,
    RetrievalLog,
)
from memblocks.services.user_manager import UserManager

if TYPE_CHECKING:
    from memblocks.llm.base import LLMProvider
    from memblocks.models.block import MemoryBlock


class _BlockChatEngine:
    """
    A chat engine scoped to a single memory block.

    Returned by ``MemBlocksClient.get_chat_engine(block)``.

    Attributes:
        chat:     ChatEngine — send_message, get_chat_history.
        sessions: SessionManager — create/get/list sessions.
    """

    def __init__(
        self,
        chat_engine: Any,
        session_manager: "SessionManager",
    ) -> None:
        self.chat = chat_engine
        self.sessions = session_manager


class MemBlocksClient:
    """
    Top-level client for the memBlocks library.

    Wires all infrastructure adapters, transparency objects, and service
    classes together with full constructor injection.  Nothing in the library
    uses global state after this class is constructed.

    Attributes (infrastructure):
        mongo:      MongoDBAdapter
        qdrant:     QdrantAdapter
        embeddings: EmbeddingProvider
        llm:        LLMProvider

    Attributes (transparency — Phase 9 stubs, always present):
        event_bus:          EventBus
        operation_log:      OperationLog
        retrieval_log:      RetrievalLog
        processing_history: ProcessingHistory

    Attributes (services):
        users:    UserManager   — create / get / list users
        blocks:   BlockManager  — create / get / list / delete blocks
        sessions: SessionManager — create / get / manage sessions (global)
        core:     CoreMemoryService — read / update core memory
    """

    def __init__(
        self,
        config: MemBlocksConfig,
        *,
        mongo_adapter: Optional[MongoDBAdapter] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
        qdrant_adapter: Optional[QdrantAdapter] = None,
        llm_provider: Optional["LLMProvider"] = None,
    ) -> None:
        """
        Initialise the client, wiring all dependencies.

        Args:
            config: Library configuration (MemBlocksConfig instance).
            mongo_adapter: Optional pre-built MongoDBAdapter (for testing /
                custom connections).  Defaults to a new MongoDBAdapter(config).
            embedding_provider: Optional pre-built EmbeddingProvider.
                Defaults to a new EmbeddingProvider(config).
            qdrant_adapter: Optional pre-built QdrantAdapter.
                Defaults to a new QdrantAdapter(config, embeddings).
            llm_provider: Optional LLMProvider implementation.
                Defaults to GroqLLMProvider(config).
        """
        self.config = config

        # ------------------------------------------------------------------ #
        # 1. Infrastructure adapters
        # ------------------------------------------------------------------ #
        self.mongo: MongoDBAdapter = mongo_adapter or MongoDBAdapter(config)
        self.embeddings: EmbeddingProvider = embedding_provider or EmbeddingProvider(
            config
        )
        self.qdrant: QdrantAdapter = qdrant_adapter or QdrantAdapter(
            config, self.embeddings
        )
        self.llm: "LLMProvider" = llm_provider or GroqLLMProvider(config)

        # ------------------------------------------------------------------ #
        # 2. Transparency layer (Phase-9 stubs — always present)
        # ------------------------------------------------------------------ #
        self.event_bus: EventBus = EventBus()
        self.operation_log: OperationLog = OperationLog()
        self.retrieval_log: RetrievalLog = RetrievalLog()
        self.processing_history: ProcessingHistory = ProcessingHistory()

        # ------------------------------------------------------------------ #
        # 3. Services
        # ------------------------------------------------------------------ #
        self.users: UserManager = UserManager(self.mongo)

        self.blocks: BlockManager = BlockManager(
            mongo_adapter=self.mongo,
            qdrant_adapter=self.qdrant,
            embedding_provider=self.embeddings,
            operation_log=self.operation_log,
        )

        # Global session manager (not scoped to a block)
        self.sessions: SessionManager = SessionManager(self.mongo)

        self.core: CoreMemoryService = CoreMemoryService(
            llm_provider=self.llm,
            mongo_adapter=self.mongo,
            config=self.config,
            operation_log=self.operation_log,
            event_bus=self.event_bus,
        )

    # ---------------------------------------------------------------------- #
    # Block-scoped chat engine factory
    # ---------------------------------------------------------------------- #

    def get_chat_engine(self, block: "MemoryBlock") -> "_BlockChatEngine":
        """
        Create a ChatEngine + SessionManager pair scoped to *block*.

        Because SemanticMemoryService is constructed with a fixed
        ``collection_name``, a new instance is created per block so that
        each block operates on its own Qdrant collection.

        Args:
            block: The MemoryBlock whose semantic collection will be used.

        Returns:
            _BlockChatEngine with .chat and .sessions attributes.
        """
        from memblocks.services.chat_engine import ChatEngine

        collection_name: str = block.semantic_collection or ""

        semantic_svc = SemanticMemoryService(
            llm_provider=self.llm,
            embedding_provider=self.embeddings,
            qdrant_adapter=self.qdrant,
            collection_name=collection_name,
            config=self.config,
            operation_log=self.operation_log,
            retrieval_log=self.retrieval_log,
            event_bus=self.event_bus,
        )

        pipeline = MemoryPipeline(
            semantic_memory_service=semantic_svc,
            core_memory_service=self.core,
            llm_provider=self.llm,
            config=self.config,
            keep_last_n=self.config.keep_last_n,
            max_concurrent=self.config.max_concurrent_processing,
            processing_history=self.processing_history,
            operation_log=self.operation_log,
            event_bus=self.event_bus,
        )

        chat_engine = ChatEngine(
            session_manager=self.sessions,
            semantic_memory_service=semantic_svc,
            core_memory_service=self.core,
            memory_pipeline=pipeline,
            llm_provider=self.llm,
            config=self.config,
            memory_window=self.config.memory_window,
            retrieval_log=self.retrieval_log,
            event_bus=self.event_bus,
        )

        return _BlockChatEngine(chat_engine=chat_engine, session_manager=self.sessions)

    # ---------------------------------------------------------------------- #
    # Transparency helpers
    # ---------------------------------------------------------------------- #

    def subscribe(self, event_name: str, callback: Any) -> None:
        """
        Subscribe *callback* to an internal library event.

        Args:
            event_name: One of EventBus.VALID_EVENTS.
            callback: Callable receiving a single payload dict argument.

        Raises:
            ValueError: If *event_name* is not valid.
        """
        self.event_bus.subscribe(event_name, callback)

    def unsubscribe(self, event_name: str, callback: Any) -> None:
        """
        Remove *callback* from event subscriptions. Silent no-op if not found.

        Args:
            event_name: Event name subscribed to.
            callback: The same callable passed to subscribe().
        """
        self.event_bus.unsubscribe(event_name, callback)

    def get_operation_log(self) -> "OperationLog":
        """Return the OperationLog for inspecting database writes."""
        return self.operation_log

    def get_retrieval_log(self) -> "RetrievalLog":
        """Return the RetrievalLog for inspecting memory retrievals."""
        return self.retrieval_log

    def get_processing_history(self) -> "ProcessingHistory":
        """Return the ProcessingHistory for inspecting pipeline runs."""
        return self.processing_history

    # ---------------------------------------------------------------------- #
    # Convenience helpers
    # ---------------------------------------------------------------------- #

    async def close(self) -> None:
        """
        Gracefully close all open infrastructure connections.

        Call this when shutting down to ensure MongoDB connections are released.
        """
        await self.mongo.close()


__all__ = ["MemBlocksClient"]
