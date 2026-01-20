from pydantic import BaseModel, Field
from typing import List, Optional
from .sections import SemanticMemoryUnit, CoreMemoryUnit, ResourceMemoryUnit

class MemoryBlockMetaData(BaseModel):
    id: str = Field(..., description="Unique identifier for the memory block.")
    created_at: str = Field(..., description="ISO 8601 formatted timestamp indicating when the memory block was created.")
    updated_at: str = Field(..., description="ISO 8601 formatted timestamp indicating when the memory block was last updated.")
    usage: Optional[List[str]] = Field([], description="List of ISO 8601 formatted timestamps indicating when this memory block was accessed or used.")
    user_id: Optional[str] = Field(None, description="Identifier for the user associated with this memory block, if applicable.")

class MemoryBlock(BaseModel):
    """ A block of memory with associated sections and metadata. """
    meta_data: MemoryBlockMetaData = Field(..., description="Metadata associated with the memory block.")
    description: str = Field(..., description=" User given description of the block. " \
        "It tells the orchastrator, retriver and other agents of what is the purpose of this blocks, " \
        "and defines the domain/constraints of the block.")
    semantic_memories = None #qDrant collection that stores SemanticMemoryUnit instances
    core_memories = None #qDrant collection that stores CoreMemoryUnit instances
    resource_memories = None #qDrant collection that stores ResourceMemoryUnit instances
    class Config:
        schema_extra = {
            "example": {
                "meta_data": {
                    "id": "block_12345",
                    "created_at": "2023-11-20T14:30:00",
                    "updated_at": "2023-11-21T09:15:00",
                    "usage": ["2023-11-21T10:00:00", "2023-11-22T11:30:00"],
                    "user_id": "user_67890"
                },
                "description": "This memory block contains information about the user's professional experiences and skills.",
                "semantic_memories": None,
                "core_memories": None #
            }
        }


