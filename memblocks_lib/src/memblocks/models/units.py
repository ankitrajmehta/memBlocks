"""Pure data models for memory units.

Copied from models/units.py — zero service or DB imports.
All 6 classes are plain Pydantic models.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional, List


class MemoryUnitMetaData(BaseModel):
    usage: Optional[list[str]] = Field(
        [],
        description="List of ISO 8601 formatted timestamps indicating when this memory was accessed or used.",
    )
    status: Optional[Literal["active", "archived", "deleted"]] = Field(
        "active", description="The current status of the memory unit."
    )
    message_ids: Optional[list[str]] = Field(
        [], description="List of message IDs associated with this memory unit."
    )


class SemanticMemoryUnit(BaseModel):
    """One unit of memory to be stored in the section "event_and_factual_memories"

    PS1 Enhancement: Includes keywords, context sentence, and enriched embedding text
    for better semantic retrieval.
    """

    content: str = Field(
        ...,
        description="The main content of the memory. Extracted from user input or documents in a concise form.",
    )
    type: Literal["event", "fact", "opinion"] = Field(
        ...,
        description="The type of memory: 'event' for time-specific events, 'factual' for general knowledge.",
    )

    memory_id: Optional[str] = Field(
        None,
        description="Unique identifier for the memory unit, typically the Qdrant point ID after storage. Not present before storage.",
    )

    source: Optional[str] = Field(
        None,
        description="Source of the memory information, e.g., 'user', 'document', etc.",
    )
    confidence: float = Field(
        ...,
        ge=0,
        le=1,
        description="Confidence score of the memory's accuracy or relevance, between 0 and 1.",
    )
    memory_time: Optional[str] = Field(
        ...,
        description="ISO 8601 formatted timestamp indicating when the memory event occurred. Not present for 'factual' memories.",
    )
    updated_at: str = Field(
        ...,
        description="ISO 8601 formatted timestamp indicating when the memory was last updated.",
    )
    meta_data: Optional[MemoryUnitMetaData] = Field(
        None, description="Additional metadata for the memory unit."
    )
    keywords: Optional[list[str]] = Field(
        [],
        description="PS1: Ranked keywords optimized for retrieval (most to least important).",
    )
    embedding_text: Optional[str] = Field(
        "",
        description="PS1: Concatenated text used for embedding generation.",
    )
    entities: Optional[list[str]] = Field(
        [], description="List of entities mentioned in the memory content."
    )

    # class Config:
    #     json_schema_extra = {
    #         "example": {
    #             "content": "User attended the AI conference in San Francisco.",
    #             "type": "event",
    #             "confidence": 0.95,
    #             "memory_time": "2023-11-15T10:00:00",
    #             "entities": ["AI conference", "San Francisco"],
    #             "keywords": ["AI conference", "San Francisco", "machine learning"],
    #             "updated_at": "2023-11-16T12:00:00",
    #         }
    #     }


class CoreMemoryUnit(BaseModel):
    """One unit of core memory — stable facts about user/persona."""

    persona_content: str = Field(
        ...,
        description="The persona to give to the LLM.",
    )
    human_content: str = Field(
        ...,
        description="The stable fact about the user to give to the LLM.",
    )


class ResourceMemoryUnit(BaseModel):
    """One unit of resource memory — uploaded documents, images, links."""

    content: str = Field(
        ...,
        description="The main content of the resource memory.",
    )
    resource_type: Literal[
        "document", "image", "video", "audio", "link", "extracted"
    ] = Field(..., description="Type of the resource memory.")
    resource_link: Optional[str] = Field(
        None, description="Link or path to the resource if applicable."
    )


class MemoryOperation(BaseModel):
    """Represents a single memory operation during processing."""

    operation: Literal["ADD", "UPDATE", "DELETE", "NONE"] = Field(
        ..., description="Type of operation performed"
    )
    memory_id: Optional[str] = Field(
        None, description="Qdrant point ID (if applicable)"
    )
    content: str = Field(..., description="The memory content")
    old_content: Optional[str] = Field(
        None, description="Previous content (for UPDATE operations)"
    )


class ProcessingEvent(BaseModel):
    """Represents a complete memory processing event."""

    event_id: str = Field(
        ..., description="Unique identifier for this processing event"
    )
    timestamp: str = Field(
        ..., description="ISO 8601 timestamp when processing occurred"
    )
    messages_processed: int = Field(
        ..., description="Number of messages that triggered this processing"
    )
    operations: List[MemoryOperation] = Field(
        default_factory=list, description="List of memory operations performed"
    )


__all__ = [
    "MemoryUnitMetaData",
    "SemanticMemoryUnit",
    "CoreMemoryUnit",
    "ResourceMemoryUnit",
    "MemoryOperation",
    "ProcessingEvent",
]
