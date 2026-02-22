"""BlockManager — extracted from services/block_service.py BlockService."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from memblocks.models.block import MemoryBlock, MemoryBlockMetaData

if TYPE_CHECKING:
    from memblocks.services.transparency import OperationLog
    from memblocks.storage.embeddings import EmbeddingProvider
    from memblocks.storage.mongo import MongoDBAdapter
    from memblocks.storage.qdrant import QdrantAdapter


class BlockManager:
    """
    Creates, loads, lists, and deletes memory blocks.

    Replaces: BlockService (block_service.py:13-143).

    Key changes from BlockService:
    - All dependencies injected (no global singletons).
    - Uses MongoDBAdapter / QdrantAdapter instead of mongo_manager / VectorDBManager.
    - MemoryBlock.save() / MemoryBlock.load() removed from model; logic lives here.
    - semantic_collection / core_memory_block_id / resource_collection fields on
      MemoryBlock are now plain strings (not Section objects).
    """

    def __init__(
        self,
        mongo_adapter: "MongoDBAdapter",
        qdrant_adapter: "QdrantAdapter",
        embedding_provider: "EmbeddingProvider",
        operation_log: Optional["OperationLog"] = None,
    ) -> None:
        """
        Args:
            mongo_adapter: MongoDB persistence layer.
            qdrant_adapter: Qdrant vector DB layer.
            embedding_provider: Used to create Qdrant collections with correct dim.
            operation_log: Phase-9 transparency placeholder.
        """
        self._mongo = mongo_adapter
        self._qdrant = qdrant_adapter
        self._embeddings = embedding_provider
        self._log = operation_log

    # ------------------------------------------------------------------ #
    # Block lifecycle
    # ------------------------------------------------------------------ #

    async def create_block(
        self,
        user_id: str,
        name: str,
        description: str = "",
        create_semantic: bool = True,
        create_core: bool = True,
        create_resource: bool = False,
    ) -> MemoryBlock:
        """
        Create a new memory block with Qdrant collections and MongoDB documents.

        Mirrors BlockService.create_block() (block_service.py:16-96).

        Args:
            user_id: Owner user ID.
            name: Human-readable block name.
            description: Optional description.
            create_semantic: Whether to create a semantic Qdrant collection.
            create_core: Whether to initialise a core memory document in Mongo.
            create_resource: Whether to create a resource Qdrant collection.

        Returns:
            Created MemoryBlock instance.
        """
        block_id = f"block_{uuid.uuid4().hex[:12]}"
        current_time = datetime.utcnow().isoformat()

        metadata = MemoryBlockMetaData(
            id=block_id,
            created_at=current_time,
            updated_at=current_time,
            usage=[],
            user_id=user_id,
        )

        semantic_collection: Optional[str] = None
        resource_collection: Optional[str] = None
        core_memory_block_id: Optional[str] = None

        if create_semantic:
            semantic_collection = f"{block_id}_semantic"
            self._qdrant.create_collection(semantic_collection)
            print(f"   ✓ Created semantic collection: {semantic_collection}")

        if create_resource:
            resource_collection = f"{block_id}_resource"
            self._qdrant.create_collection(resource_collection)
            print(f"   ✓ Created resource collection: {resource_collection}")

        if create_core:
            core_memory_block_id = block_id
            await self._mongo.save_core_memory(
                block_id=block_id,
                persona_content="",
                human_content="",
            )
            print(f"   ✓ Created core memory document: {block_id}")

        block = MemoryBlock(
            meta_data=metadata,
            name=name,
            description=description,
            semantic_collection=semantic_collection,
            core_memory_block_id=core_memory_block_id,
            resource_collection=resource_collection,
        )

        # Persist the block document
        block_dict = {
            "block_id": block_id,
            "user_id": user_id,
            "name": name,
            "description": description,
            "meta_data": metadata.model_dump(),
            "semantic_collection": semantic_collection,
            "core_memory_block_id": core_memory_block_id,
            "resource_collection": resource_collection,
            "is_active": False,
            "created_at": current_time,
            "updated_at": current_time,
        }
        await self._mongo.create_memory_block(user_id, block_dict)
        await self._mongo.add_block_to_user(user_id, block_id)

        print(f"✅ Created memory block: {block_id}")
        return block

    async def get_block(self, block_id: str) -> Optional[MemoryBlock]:
        """
        Load a memory block from MongoDB.

        Mirrors BlockService.load_block() (block_service.py:98-109).

        Args:
            block_id: Block identifier.

        Returns:
            MemoryBlock instance or None.
        """
        doc = await self._mongo.get_memory_block(block_id)
        if not doc:
            return None
        return self._doc_to_block(doc)

    async def get_user_blocks(self, user_id: str) -> List[MemoryBlock]:
        """
        Return all blocks belonging to a user.

        Mirrors BlockService.list_user_blocks() (block_service.py:111-127).

        Args:
            user_id: Owner user ID.

        Returns:
            List of MemoryBlock instances.
        """
        docs = await self._mongo.list_user_blocks(user_id)
        return [self._doc_to_block(doc) for doc in docs]

    async def delete_block(self, block_id: str, user_id: str) -> bool:
        """
        Delete a memory block.

        Mirrors BlockService.delete_block() (block_service.py:129-143).

        Args:
            block_id: Block identifier.
            user_id: Owner user ID (for future auth checks).

        Returns:
            True if deletion was successful.
        """
        return await self._mongo.delete_memory_block(block_id)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _doc_to_block(self, doc: Dict[str, Any]) -> MemoryBlock:
        """Convert a raw MongoDB document to a MemoryBlock instance."""
        meta_data_raw = doc.get("meta_data", {})
        if not meta_data_raw:
            meta_data_raw = {
                "id": doc.get("block_id", ""),
                "created_at": doc.get("created_at", datetime.utcnow().isoformat()),
                "updated_at": doc.get("updated_at", datetime.utcnow().isoformat()),
                "usage": doc.get("usage", []),
                "user_id": doc.get("user_id", ""),
            }

        return MemoryBlock(
            meta_data=MemoryBlockMetaData(**meta_data_raw),
            name=doc.get("name", ""),
            description=doc.get("description", ""),
            is_active=doc.get("is_active", False),
            semantic_collection=doc.get("semantic_collection"),
            core_memory_block_id=doc.get("core_memory_block_id"),
            resource_collection=doc.get("resource_collection"),
        )
