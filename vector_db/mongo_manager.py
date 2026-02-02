"""MongoDB integration layer for memBlocks."""

import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()


class MongoDBManager:
    """Async MongoDB manager for users, blocks, and core memories."""
    
    _instance: Optional['MongoDBManager'] = None
    _client: Optional[AsyncIOMotorClient] = None
    _db = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize MongoDB async client."""
        connection_string = os.getenv("MONGODB_CONNECTION_STRING")
        if not connection_string:
            raise ValueError("MONGODB_CONNECTION_STRING not found in environment variables")
        
        self._client = AsyncIOMotorClient(connection_string)
        self._db = self._client.memblocks
        
        # Collections
        self.users = self._db.users
        self.blocks = self._db.blocks
        self.core_memories = self._db.core_memories
    
    # ========================================================================
    # USER OPERATIONS
    # ========================================================================
    
    async def create_user(self, user_id: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a new user.
        
        Args:
            user_id: Unique user identifier
            metadata: Optional user metadata
            
        Returns:
            Created user document
        """
        user_doc = {
            "user_id": user_id,
            "block_ids": [],
            "created_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        await self.users.insert_one(user_doc)
        return user_doc
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by ID.
        
        Args:
            user_id: User identifier
            
        Returns:
            User document or None
        """
        return await self.users.find_one({"user_id": user_id})
    
    async def add_block_to_user(self, user_id: str, block_id: str) -> bool:
        """
        Add a block ID to user's block_ids list.
        
        Args:
            user_id: User identifier
            block_id: Block identifier to add
            
        Returns:
            True if successful
        """
        result = await self.users.update_one(
            {"user_id": user_id},
            {"$addToSet": {"block_ids": block_id}}
        )
        return result.modified_count > 0 or result.matched_count > 0
    
    async def list_users(self) -> List[Dict[str, Any]]:
        """Get all users."""
        cursor = self.users.find({})
        return await cursor.to_list(length=None)
    
    # ========================================================================
    # BLOCK OPERATIONS
    # ========================================================================
    
    async def save_block(self, block_data: Dict[str, Any]) -> str:
        """
        Save a memory block.
        
        Args:
            block_data: Block document with metadata, name, description, and section references
            
        Returns:
            Block ID
        """
        # Ensure updated_at is current
        block_data["meta_data"]["updated_at"] = datetime.utcnow().isoformat()
        
        # Upsert by block ID
        block_id = block_data["meta_data"]["id"]
        await self.blocks.replace_one(
            {"meta_data.id": block_id},
            block_data,
            upsert=True
        )
        
        return block_id
    
    async def load_block(self, block_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a memory block by ID.
        
        Args:
            block_id: Block identifier
            
        Returns:
            Block document or None
        """
        return await self.blocks.find_one({"meta_data.id": block_id})
    
    async def list_user_blocks(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all blocks for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of block documents
        """
        user = await self.get_user(user_id)
        if not user or not user.get("block_ids"):
            return []
        
        cursor = self.blocks.find({"meta_data.id": {"$in": user["block_ids"]}})
        return await cursor.to_list(length=None)
    
    async def delete_block(self, block_id: str) -> bool:
        """
        Delete a block.
        
        Args:
            block_id: Block identifier
            
        Returns:
            True if deleted
        """
        result = await self.blocks.delete_one({"meta_data.id": block_id})
        return result.deleted_count > 0
    
    # ========================================================================
    # CORE MEMORY OPERATIONS
    # ========================================================================
    
    async def save_core_memory(
        self, 
        block_id: str, 
        persona_content: str, 
        human_content: str
    ) -> str:
        """
        Save or update core memory for a block.
        
        Args:
            block_id: Block identifier
            persona_content: Persona paragraph
            human_content: Human facts paragraph
            
        Returns:
            Core memory document ID (MongoDB ObjectId as string)
        """
        core_memory_doc = {
            "block_id": block_id,
            "persona_content": persona_content,
            "human_content": human_content,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Upsert by block_id
        result = await self.core_memories.replace_one(
            {"block_id": block_id},
            core_memory_doc,
            upsert=True
        )
        
        if result.upserted_id:
            return str(result.upserted_id)
        else:
            # Get existing document ID
            doc = await self.core_memories.find_one({"block_id": block_id})
            return str(doc["_id"])
    
    async def get_core_memory(self, block_id: str) -> Optional[Dict[str, Any]]:
        """
        Get core memory for a block.
        
        Args:
            block_id: Block identifier
            
        Returns:
            Core memory document or None
        """
        return await self.core_memories.find_one({"block_id": block_id})
    
    async def delete_core_memory(self, block_id: str) -> bool:
        """
        Delete core memory for a block.
        
        Args:
            block_id: Block identifier
            
        Returns:
            True if deleted
        """
        result = await self.core_memories.delete_one({"block_id": block_id})
        return result.deleted_count > 0
    
    # ========================================================================
    # UTILITY
    # ========================================================================
    
    async def close(self):
        """Close MongoDB connection."""
        if self._client:
            self._client.close()


# Singleton instance
mongo_manager = MongoDBManager()
