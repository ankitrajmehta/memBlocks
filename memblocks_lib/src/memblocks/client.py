"""MemBlocksClient — single entry-point for the memBlocks library.

This library is a **memory management** library. It does NOT run inference.
The user is responsible for calling their own LLM with the retrieved context.

Typical usage:

    import asyncio
    from memblocks import MemBlocksClient, MemBlocksConfig

    config = MemBlocksConfig()           # reads from .env
    client = MemBlocksClient(config)

    # Phase A — Initialization (once per run / user / session)
    user   = await client.get_or_create_user("alice")
    block  = await client.create_block(user_id="alice", name="Work Memory")
    session = await client.create_session(user_id="alice", block_id=block.id)

    # Phase B — Per-turn loop
    context  = await block.retrieve(user_msg)         # all memory sources
    messages = await session.get_memory_window()      # last N messages
    summary  = await session.get_recursive_summary()  # rolling summary

    # User runs their own LLM:
    system   = my_prompt + "\\n\\n" + context.to_prompt_string()
    response = my_llm.chat(system, messages + [{"role": "user", "content": user_msg}])

    # Persist the turn (user decides: await inline or asyncio.create_task)
    await session.add(user_msg=user_msg, ai_response=response)

    await client.close()
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from memblocks.config import MemBlocksConfig
from memblocks.llm.groq_provider import GroqLLMProvider
from memblocks.llm.gemini_provider import GeminiLLMProvider
from memblocks.storage.embeddings import EmbeddingProvider
from memblocks.storage.mongo import MongoDBAdapter
from memblocks.storage.qdrant import QdrantAdapter
from memblocks.services.block_manager import BlockManager
from memblocks.services.core_memory import CoreMemoryService
from memblocks.services.session_manager import SessionManager
from memblocks.services.user_manager import UserManager
from memblocks.services.transparency import (
    EventBus,
    OperationLog,
    ProcessingHistory,
    RetrievalLog,
)

if TYPE_CHECKING:
    from memblocks.llm.base import LLMProvider
    from memblocks.services.block import Block
    from memblocks.services.session import Session


class MemBlocksClient:
    """
    Top-level client for the memBlocks library.

    Wires all infrastructure adapters, transparency objects, and service
    classes together with constructor injection. No global state.

    Infrastructure (advanced / testing use):
        mongo:      MongoDBAdapter
        qdrant:     QdrantAdapter
        embeddings: EmbeddingProvider
        llm:        LLMProvider

    Transparency:
        event_bus:          EventBus
        operation_log:      OperationLog
        retrieval_log:      RetrievalLog
        processing_history: ProcessingHistory
    """

    def __init__(
        self,
        config: MemBlocksConfig,
        *,
        mongo_adapter: Optional[MongoDBAdapter] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
        qdrant_adapter: Optional[QdrantAdapter] = None,
    ) -> None:
        """
        Initialise the client, wiring all dependencies.

        Args:
            config: Library configuration (MemBlocksConfig instance).
            mongo_adapter: Optional pre-built MongoDBAdapter (for testing).
            embedding_provider: Optional pre-built EmbeddingProvider.
            qdrant_adapter: Optional pre-built QdrantAdapter.
            llm_provider: Optional LLMProvider for memory management.
                Defaults to GroqLLMProvider(config).
        """
        self.config = config

        # ---- Infrastructure adapters ----
        self.mongo: MongoDBAdapter = mongo_adapter or MongoDBAdapter(config)
        self.embeddings: EmbeddingProvider = embedding_provider or EmbeddingProvider(
            config
        )
        self.qdrant: QdrantAdapter = qdrant_adapter or QdrantAdapter(
            config, self.embeddings
        )

        if self.config.llm_provider_name == "groq":
            llm_provider = GroqLLMProvider(config)
        elif self.config.llm_provider_name == "gemini":
            llm_provider = GeminiLLMProvider(config)
        else:
            raise ValueError(
                f"Unknown LLM provider: {self.config.llm_provider_name}. "
                "Supported providers: 'groq', 'gemini'"
            )

        self.llm: "LLMProvider" = llm_provider

        # ---- Transparency layer ----
        self.event_bus: EventBus = EventBus()
        self.operation_log: OperationLog = OperationLog()
        self.retrieval_log: RetrievalLog = RetrievalLog()
        self.processing_history: ProcessingHistory = ProcessingHistory()

        # ---- Shared services ----
        self._users: UserManager = UserManager(self.mongo)

        self._core: CoreMemoryService = CoreMemoryService(
            llm_provider=self.llm,
            mongo_adapter=self.mongo,
            config=self.config,
            operation_log=self.operation_log,
            event_bus=self.event_bus,
        )

        self._blocks: BlockManager = BlockManager(
            mongo_adapter=self.mongo,
            qdrant_adapter=self.qdrant,
            embedding_provider=self.embeddings,
            llm_provider=self.llm,
            core_memory_service=self._core,
            config=self.config,
            operation_log=self.operation_log,
            retrieval_log=self.retrieval_log,
            event_bus=self.event_bus,
        )

        self._sessions: SessionManager = SessionManager(
            mongo_adapter=self.mongo,
            llm_provider=self.llm,
            qdrant_adapter=self.qdrant,
            embedding_provider=self.embeddings,
            core_memory_service=self._core,
            config=self.config,
            memory_window_limit=self.config.memory_window_limit,
            keep_last_n=self.config.keep_last_n,
            operation_log=self.operation_log,
            event_bus=self.event_bus,
            processing_history=self.processing_history,
            retrieval_log=self.retrieval_log,
        )

    # ------------------------------------------------------------------ #
    # User management
    # ------------------------------------------------------------------ #

    async def create_user(
        self,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new user.

        Args:
            user_id: Unique user identifier.
            metadata: Optional metadata dict.

        Returns:
            User document dict.
        """
        return await self._users.create_user(user_id, metadata)

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a user by ID.

        Args:
            user_id: User identifier.

        Returns:
            User document dict or None.
        """
        return await self._users.get_user(user_id)

    async def get_or_create_user(
        self,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get an existing user or create one if not found.

        Args:
            user_id: User identifier.
            metadata: Optional metadata (used only on creation).

        Returns:
            User document dict.
        """
        return await self._users.get_or_create_user(user_id, metadata)

    async def list_users(self) -> List[Dict[str, Any]]:
        """Return all user documents."""
        return await self._users.list_users()

    # ------------------------------------------------------------------ #
    # Block management
    # ------------------------------------------------------------------ #

    async def create_block(
        self,
        user_id: str,
        name: str,
        description: str = "",
        create_semantic: bool = True,
        create_core: bool = True,
        create_resource: bool = False,
    ) -> "Block":
        """
        Create a new memory block.

        Creates the Qdrant collection(s) and MongoDB documents needed for the
        block, then returns a stateful Block object ready for retrieval.

        Args:
            user_id: Owner user ID.
            name: Human-readable block name.
            description: Optional description.
            create_semantic: Create a semantic (vector) Qdrant collection.
            create_core: Initialise an empty core memory document.
            create_resource: Create a resource Qdrant collection (stub).

        Returns:
            Stateful Block with .retrieve(), .core_retrieve(),
            .semantic_retrieve(), .resource_retrieve() methods.
        """
        return await self._blocks.create_block(
            user_id=user_id,
            name=name,
            description=description,
            create_semantic=create_semantic,
            create_core=create_core,
            create_resource=create_resource,
        )

    async def get_block(self, block_id: str) -> Optional["Block"]:
        """
        Load an existing block by ID.

        Args:
            block_id: Block identifier.

        Returns:
            Stateful Block or None if not found.
        """
        return await self._blocks.get_block(block_id)

    async def get_user_blocks(self, user_id: str) -> List["Block"]:
        """
        Return all blocks belonging to a user.

        Args:
            user_id: Owner user ID.

        Returns:
            List of stateful Block objects.
        """
        return await self._blocks.get_user_blocks(user_id)

    async def delete_block(self, block_id: str, user_id: str) -> bool:
        """
        Delete a memory block.

        Args:
            block_id: Block identifier.
            user_id: Owner user ID.

        Returns:
            True if deletion succeeded.
        """
        return await self._blocks.delete_block(block_id, user_id)

    # ------------------------------------------------------------------ #
    # Session management
    # ------------------------------------------------------------------ #

    async def create_session(
        self,
        user_id: str,
        block_id: str,
    ) -> "Session":
        """
        Create a new conversation session attached to a block.

        Args:
            user_id: Owner user ID.
            block_id: Memory block to attach (must already exist).

        Returns:
            Stateful Session with .get_memory_window(), .get_recursive_summary(),
            and .add() methods.
        """
        return await self._sessions.create_session(user_id, block_id)

    async def get_session(self, session_id: str) -> Optional["Session"]:
        """
        Load an existing session by ID.

        Args:
            session_id: Session identifier.

        Returns:
            Stateful Session or None if not found.
        """
        return await self._sessions.get_session(session_id)

    # ------------------------------------------------------------------ #
    # Transparency helpers
    # ------------------------------------------------------------------ #

    def subscribe(self, event_name: str, callback: Any) -> None:
        """Subscribe *callback* to an internal library event."""
        self.event_bus.subscribe(event_name, callback)

    def unsubscribe(self, event_name: str, callback: Any) -> None:
        """Remove *callback* from event subscriptions."""
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

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    async def close(self) -> None:
        """Gracefully close all open infrastructure connections."""
        await self.mongo.close()


__all__ = ["MemBlocksClient"]
