"""Pure data models for memory section state.

Derived from models/sections.py. All business logic methods
(store_memory, retrieve_memories, extract_semantic_memories, etc.)
are NOT present here — they move to the services layer in Phase 7.

Renamed models:
- SemanticMemorySection -> SemanticMemoryData
- CoreMemorySection     -> CoreMemoryData
- ResourceMemorySection -> ResourceMemoryData
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal


class SemanticMemoryData(BaseModel):
    """Pure data model representing the semantic memory section of a block.

    Holds the Qdrant collection name where SemanticMemoryUnit objects are stored.
    All retrieval and storage logic lives in SemanticMemoryService (Phase 7).
    """

    type: Literal["semantic"] = Field(
        default="semantic", description="Type discriminator for this memory section."
    )
    collection_name: str = Field(
        ..., description="Qdrant collection that stores SemanticMemoryUnit instances."
    )


class CoreMemoryData(BaseModel):
    """Pure data model representing the core memory section of a block.

    Holds the block_id used as a key in the MongoDB core_memories collection.
    All retrieval and storage logic lives in CoreMemoryService (Phase 7).
    """

    type: Literal["core"] = Field(
        default="core", description="Type discriminator for this memory section."
    )
    block_id: str = Field(
        ..., description="ID of the memory block this core memory belongs to."
    )


class ResourceMemoryData(BaseModel):
    """Pure data model representing the resource memory section of a block (stub).

    Holds the Qdrant collection name where ResourceMemoryUnit objects are stored.
    Implementation is stubbed; all logic will live in ResourceMemoryService (future).
    """

    type: Literal["resource"] = Field(
        default="resource", description="Type discriminator for this memory section."
    )
    collection_name: str = Field(
        ..., description="Qdrant collection that stores ResourceMemoryUnit instances."
    )


__all__ = [
    "SemanticMemoryData",
    "CoreMemoryData",
    "ResourceMemoryData",
]
