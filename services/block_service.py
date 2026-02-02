"""Block management service."""

import uuid
from typing import Optional, List
from datetime import datetime

from models.container import MemoryBlock, MemoryBlockMetaData
from models.sections import SemanticMemorySection, CoreMemorySection, ResourceMemorySection
from vector_db.mongo_manager import mongo_manager
from vector_db.vector_db_manager import VectorDBManager


class BlockService:
    """Service for memory block operations."""
    
    @staticmethod
    async def create_block(
        user_id: str,
        name: str,
        description: str,
        create_semantic: bool = True,
        create_core: bool = True,
        create_resource: bool = False
    ) -> MemoryBlock:
        """
        Create a new memory block with Qdrant collections and MongoDB doc.
        
        Args:
            user_id: User identifier
            name: Block name
            description: Block description
            create_semantic: Whether to create semantic memory section
            create_core: Whether to create core memory section
            create_resource: Whether to create resource memory section
            
        Returns:
            Created MemoryBlock instance
        """
        # Generate block ID
        block_id = f"block_{uuid.uuid4().hex[:12]}"
        current_time = datetime.utcnow().isoformat()
        
        # Create metadata
        metadata = MemoryBlockMetaData(
            id=block_id,
            created_at=current_time,
            updated_at=current_time,
            usage=[],
            user_id=user_id
        )
        
        # Create Qdrant collections for semantic and resource memories
        semantic_section = None
        if create_semantic:
            semantic_collection = f"{block_id}_semantic"
            VectorDBManager.create_collection(semantic_collection)
            semantic_section = SemanticMemorySection(collection_name=semantic_collection)
            print(f"   ✓ Created semantic collection: {semantic_collection}")
        
        resource_section = None
        if create_resource:
            resource_collection = f"{block_id}_resource"
            VectorDBManager.create_collection(resource_collection)
            resource_section = ResourceMemorySection(collection_name=resource_collection)
            print(f"   ✓ Created resource collection: {resource_collection}")
        
        # Core memory section (MongoDB, no Qdrant needed)
        core_section = None
        if create_core:
            core_section = CoreMemorySection(block_id=block_id)
            # Initialize empty core memory
            await mongo_manager.save_core_memory(
                block_id=block_id,
                persona_content="",
                human_content=""
            )
            print(f"   ✓ Created core memory document: {block_id}")
        
        # Create MemoryBlock
        block = MemoryBlock(
            meta_data=metadata,
            name=name,
            description=description,
            semantic_memories=semantic_section,
            core_memories=core_section,
            resource_memories=resource_section
        )
        
        # Save to MongoDB
        await block.save()
        
        # Add block to user's block_ids
        await mongo_manager.add_block_to_user(user_id, block_id)
        
        print(f"✅ Created memory block: {block_id}")
        return block
    
    @staticmethod
    async def load_block(block_id: str) -> Optional[MemoryBlock]:
        """
        Load a memory block by ID.
        
        Args:
            block_id: Block identifier
            
        Returns:
            MemoryBlock instance or None
        """
        return await MemoryBlock.load(block_id)
    
    @staticmethod
    async def list_user_blocks(user_id: str) -> List[MemoryBlock]:
        """
        Get all blocks for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of MemoryBlock instances
        """
        block_docs = await mongo_manager.list_user_blocks(user_id)
        blocks = []
        for doc in block_docs:
            block = MemoryBlock.from_dict(doc)
            blocks.append(block)
        return blocks
    
    @staticmethod
    async def delete_block(block_id: str, user_id: str) -> bool:
        """
        Delete a memory block (soft delete for now - just remove from user's list).
        
        Args:
            block_id: Block identifier
            user_id: User identifier
            
        Returns:
            True if successful
        """
        # TODO: Implement full deletion (Qdrant collections + MongoDB docs)
        # For now, just soft delete
        return await mongo_manager.delete_block(block_id)


class SessionManager:
    """Manages chat session state (in-memory)."""
    
    def __init__(self):
        self.active_sessions: dict[str, dict] = {}
    
    def create_session(self, user_id: str) -> str:
        """Create a new chat session for user."""
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        self.active_sessions[session_id] = {
            "user_id": user_id,
            "attached_block_id": None,
            "created_at": datetime.utcnow().isoformat()
        }
        return session_id
    
    def attach_block(self, session_id: str, block_id: str):
        """Attach a block to a session."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["attached_block_id"] = block_id
            print(f"✅ Attached block {block_id} to session {session_id}")
    
    def detach_block(self, session_id: str):
        """Detach block from session."""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["attached_block_id"] = None
            print(f"✅ Detached block from session {session_id}")
    
    def get_attached_block(self, session_id: str) -> Optional[str]:
        """Get attached block ID for session."""
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]["attached_block_id"]
        return None
    
    def get_session(self, session_id: str) -> Optional[dict]:
        """Get session info."""
        return self.active_sessions.get(session_id)


# Singleton instances
block_service = BlockService()
session_manager = SessionManager()
