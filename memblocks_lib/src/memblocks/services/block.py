"""Block — stateful object returned from client.create_block() / client.get_block().

Users interact with memory retrieval through this object:

    context = await block.retrieve(user_msg)
    context = await block.core_retrieve()
    context = await block.semantic_retrieve(user_msg)
    context = await block.resource_retrieve(user_msg)   # stub — empty for now
    prompt_str = context.to_prompt_string()
"""

from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from memblocks.models.retrieval import RetrievalResult
from memblocks.models.units import (
    CoreMemoryUnit,
    ResourceMemoryUnit,
    SemanticMemoryUnit,
)

if TYPE_CHECKING:
    from memblocks.services.core_memory import CoreMemoryService
    from memblocks.services.semantic_memory import SemanticMemoryService


class Block:
    """
    Stateful handle to a memory block with retrieval methods.

    Returned by:
        client.create_block(...)
        client.get_block(block_id)

    Holds the block's identifiers and has direct access to the underlying
    SemanticMemoryService and CoreMemoryService, so retrieval calls can be
    made without touching the client.

    Attributes:
        id:                  Block ID (e.g. "block_abc123def456").
        name:                Human-readable block name.
        description:         Block description.
        user_id:             Owner user ID.
        semantic_collection: Qdrant collection name for semantic memories.
        core_memory_block_id: Key used in MongoDB core_memories collection.
        resource_collection: Qdrant collection name for resource memories (stub).
        created_at:          ISO 8601 creation timestamp.
        updated_at:          ISO 8601 last-updated timestamp.
    """

    def __init__(
        self,
        block_id: str,
        name: str,
        description: str,
        user_id: str,
        semantic_memory_service: "SemanticMemoryService",
        core_memory_service: "CoreMemoryService",
        semantic_collection: Optional[str] = None,
        core_memory_block_id: Optional[str] = None,
        resource_collection: Optional[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        retrieval_top_k: int = 5,
    ) -> None:
        self.id = block_id
        self.name = name
        self.description = description
        self.user_id = user_id
        self.semantic_collection = semantic_collection
        self.core_memory_block_id = core_memory_block_id
        self.resource_collection = resource_collection
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.updated_at = updated_at or datetime.utcnow().isoformat()

        self._semantic = semantic_memory_service
        self._core = core_memory_service
        self._top_k = retrieval_top_k

    # ------------------------------------------------------------------ #
    # Retrieval API
    # ------------------------------------------------------------------ #

    async def retrieve(self, query: str) -> RetrievalResult:
        """
        Retrieve all available memory types relevant to *query*.

        Combines core memory (always fetched in full) with semantic memories
        (vector-searched). Resource memories are a stub and always empty.

        Args:
            query: The user's message / query string.

        Returns:
            RetrievalResult containing core, semantic, and resource fields.
            Call .to_prompt_string() for a formatted string.
        """
        core, semantic = await self._fetch_core_and_semantic(query)
        return RetrievalResult(core=core, semantic=semantic, resource=[])

    async def core_retrieve(self) -> RetrievalResult:
        """
        Retrieve only the core memory for this block.

        Core memory is always fetched in full — no query needed.

        Returns:
            RetrievalResult with only the core field populated.
        """
        core = await self._core.get(self.core_memory_block_id or self.id)
        return RetrievalResult(core=core, semantic=[], resource=[])

    async def semantic_retrieve(self, query: str) -> RetrievalResult:
        """
        Retrieve only semantic memories relevant to *query* via vector search.

        Args:
            query: The user's message / query string.

        Returns:
            RetrievalResult with only the semantic field populated.
        """
        semantic = await self._fetch_semantic(query)
        return RetrievalResult(core=None, semantic=semantic, resource=[])

    async def resource_retrieve(self, query: str) -> RetrievalResult:
        """
        Retrieve resource memories relevant to *query*.

        Resource memories (documents, links, etc.) are not yet implemented.
        This method is a stub that always returns an empty result.

        Args:
            query: The user's message / query string (reserved for future use).

        Returns:
            RetrievalResult with empty resource list.
        """
        return RetrievalResult(core=None, semantic=[], resource=[])

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    async def _fetch_core_and_semantic(
        self, query: str
    ) -> tuple[Optional[CoreMemoryUnit], List[SemanticMemoryUnit]]:
        """Fetch core and semantic memories concurrently."""
        import asyncio

        core_task = asyncio.create_task(
            self._core.get(self.core_memory_block_id or self.id)
        )
        # Semantic retrieval is now async
        semantic_task = asyncio.create_task(self._fetch_semantic(query))
        core = await core_task
        semantic = await semantic_task
        return core, semantic

    async def _fetch_semantic(self, query: str) -> List[SemanticMemoryUnit]:
        """Run semantic vector search and return flat list of memories."""
        if not self.semantic_collection:
            return []
        results = await self._semantic.retrieve([query], top_k=self._top_k)
        return results[0] if results else []

    # ------------------------------------------------------------------ #
    # Repr
    # ------------------------------------------------------------------ #

    def __repr__(self) -> str:
        return f"Block(id={self.id!r}, name={self.name!r}, user_id={self.user_id!r})"
