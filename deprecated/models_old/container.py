from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from .units import SemanticMemoryUnit, CoreMemoryUnit, ResourceMemoryUnit
from .sections import SemanticMemorySection, CoreMemorySection, ResourceMemorySection
from vector_db.mongo_manager import mongo_manager

class MemoryBlockMetaData(BaseModel):
    id: str = Field(..., description="Unique identifier for the memory block.")
    created_at: str = Field(..., description="ISO 8601 formatted timestamp indicating when the memory block was created.")
    updated_at: str = Field(..., description="ISO 8601 formatted timestamp indicating when the memory block was last updated.")
    usage: Optional[List[str]] = Field([], description="List of ISO 8601 formatted timestamps indicating when this memory block was accessed or used.")
    user_id: Optional[str] = Field(None, description="Identifier for the user associated with this memory block, if applicable.")

class MemoryBlock(BaseModel):
    """ A block of memory with associated sections and metadata. """
    meta_data: MemoryBlockMetaData = Field(..., description="Metadata associated with the memory block.")
    name: str = Field(..., description=" Human-readable name of the memory block. ")
    description: str = Field(..., description=" User given description of the block. " \
        "It tells the orchastrator, retriver and other agents of what is the purpose of this blocks, " \
        "and defines the domain/constraints of the block.")
    semantic_memories: Optional[SemanticMemorySection] = Field(None)
    core_memories: Optional[CoreMemorySection] = Field(None)
    resource_memories: Optional[ResourceMemorySection] = Field(None)
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "meta_data": {
                    "id": "block_12345",
                    "created_at": "2023-11-20T14:30:00",
                    "updated_at": "2023-11-21T09:15:00",
                    "usage": ["2023-11-21T10:00:00", "2023-11-22T11:30:00"],
                    "user_id": "user_67890"
                },
                "name": "Professional Work Block",
                "description": "This memory block contains information about the user's professional experiences and skills.",
                "semantic_memories": "block_12345_semantic",
                "core_memories": "block_12345",
                "resource_memories": "block_12345_resource"
            }
        }
    }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert MemoryBlock to dictionary for MongoDB storage.
        
        Sections are stored as references:
        - semantic_memories: Qdrant collection name
        - core_memories: block_id (references MongoDB core_memories collection)
        - resource_memories: Qdrant collection name
        """
        return {
            "meta_data": self.meta_data.model_dump(),
            "name": self.name,
            "description": self.description,
            "semantic_memories": self.semantic_memories.collection_name if self.semantic_memories else None,
            "core_memories": self.core_memories.block_id if self.core_memories else None,
            "resource_memories": self.resource_memories.collection_name if self.resource_memories else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryBlock":
        """
        Reconstruct MemoryBlock from MongoDB document.
        
        Args:
            data: Dictionary from MongoDB
            
        Returns:
            MemoryBlock instance with section references
        """
        return cls(
            meta_data=MemoryBlockMetaData(**data["meta_data"]),
            name=data["name"],
            description=data["description"],
            semantic_memories=SemanticMemorySection(collection_name=data["semantic_memories"]) if data.get("semantic_memories") else None,
            core_memories=CoreMemorySection(block_id=data["core_memories"]) if data.get("core_memories") else None,
            resource_memories=ResourceMemorySection(collection_name=data["resource_memories"]) if data.get("resource_memories") else None
        )
    
    async def save(self):
        """Save this MemoryBlock to MongoDB."""
        self.meta_data.updated_at = datetime.utcnow().isoformat()
        await mongo_manager.save_block(self.to_dict())
    
    @classmethod
    async def load(cls, block_id: str) -> Optional["MemoryBlock"]:
        """
        Load a MemoryBlock from MongoDB by ID.
        
        Args:
            block_id: Block identifier
            
        Returns:
            MemoryBlock instance or None
        """
        data = await mongo_manager.load_block(block_id)
        if data:
            return cls.from_dict(data)
        return None


