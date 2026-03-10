"""Pure data models for MemoryBlock and its metadata.

Derived from models/container.py. All DB I/O (save/load) removed —
those operations move to MongoDBAdapter in Phase 5.

Key design changes from container.py:
- Sections stored as plain string references (collection names / block IDs)
  rather than Section model instances. This removes the circular import.
- Fields renamed for clarity:
    semantic_memories  -> semantic_collection  (Qdrant collection name)
    core_memories      -> core_memory_block_id (MongoDB block ID ref)
    resource_memories  -> resource_collection  (Qdrant collection name)
- to_dict() and from_dict() kept as pure serialization helpers.
- save() and load() class methods are REMOVED (belong in MongoDBAdapter).
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class MemoryBlockMetaData(BaseModel):
    id: str = Field(..., description="Unique identifier for the memory block.")
    created_at: str = Field(
        ..., description="ISO 8601 formatted timestamp when the block was created."
    )
    updated_at: str = Field(
        ..., description="ISO 8601 formatted timestamp when the block was last updated."
    )
    usage: Optional[List[str]] = Field(
        [], description="ISO 8601 timestamps of when this block was accessed."
    )
    user_id: Optional[str] = Field(
        None, description="Identifier for the user associated with this block."
    )
    llm_usage: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Aggregated LLM token usage and timing per call type for this block. "
            "Keys are LLMCallType values; values are LLMUsageSummary dicts."
        ),
    )


class MemoryBlock(BaseModel):
    """A block of memory with section references and metadata.

    Sections are stored as lightweight string references:
    - semantic_collection: Qdrant collection name for semantic memories
    - core_memory_block_id: block_id used as key in MongoDB core_memories collection
    - resource_collection: Qdrant collection name for resource memories
    """

    meta_data: MemoryBlockMetaData = Field(
        ..., description="Metadata associated with the memory block."
    )
    name: str = Field(..., description="Human-readable name of the memory block.")
    description: str = Field(
        ...,
        description=(
            "User-given description of the block. Tells the orchestrator, retriever "
            "and other agents what this block's purpose and domain constraints are."
        ),
    )
    semantic_collection: Optional[str] = Field(
        None, description="Qdrant collection name for semantic memories."
    )
    core_memory_block_id: Optional[str] = Field(
        None, description="Block ID key for core memory in MongoDB."
    )
    resource_collection: Optional[str] = Field(
        None, description="Qdrant collection name for resource memories."
    )
    is_active: bool = Field(
        False, description="Whether this block is currently active."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "meta_data": {
                    "id": "block_12345",
                    "created_at": "2023-11-20T14:30:00",
                    "updated_at": "2023-11-21T09:15:00",
                    "usage": ["2023-11-21T10:00:00"],
                    "user_id": "user_67890",
                },
                "name": "Professional Work Block",
                "description": "Contains information about professional experiences.",
                "semantic_collection": "block_12345_semantic",
                "core_memory_block_id": "block_12345",
                "resource_collection": "block_12345_resource",
            }
        }
    }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize MemoryBlock to a MongoDB-storable dictionary."""
        return {
            "meta_data": self.meta_data.model_dump(),
            "name": self.name,
            "description": self.description,
            "semantic_collection": self.semantic_collection,
            "core_memory_block_id": self.core_memory_block_id,
            "resource_collection": self.resource_collection,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryBlock":
        """Reconstruct MemoryBlock from a MongoDB document."""
        return cls(
            meta_data=MemoryBlockMetaData(**data["meta_data"]),
            name=data["name"],
            description=data["description"],
            semantic_collection=data.get("semantic_collection"),
            core_memory_block_id=data.get("core_memory_block_id"),
            resource_collection=data.get("resource_collection"),
        )

    def touch(self) -> None:
        """Update the updated_at timestamp (call before saving)."""
        self.meta_data.updated_at = datetime.utcnow().isoformat()


__all__ = ["MemoryBlockMetaData", "MemoryBlock"]
