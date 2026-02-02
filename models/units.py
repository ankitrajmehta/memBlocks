from pydantic import BaseModel, Field
from typing import Literal, Optional


class MemoryUnitMetaData(BaseModel):
    usage: Optional[list[str]] = Field(
        [],
        description="List of ISO 8601 formatted timestamps indicating when this memory was accessed or used.",
    )
    status: Optional[Literal["active", "archived", "deleted"]] = Field(
        "active", description="The current status of the memory unit."
    )
    Parent_Memory_ids: Optional[list[str]] = Field(
        [], description="List of IDs of parent memories related to this memory unit."
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
    type: Literal["event", "factual", "opinion"] = Field(
        ...,
        description="The type of memory: 'event' for time-specific events, 'factual' for general knowledge.",
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
    entities: Optional[list[str]] = Field(
        [], description="List of entities mentioned in the memory content."
    )
    tags: Optional[list[str]] = Field(
        [],
        description="Optional tags or keywords associated with the memory for easier retrieval.",
    )
    updated_at: str = Field(
        ...,
        description="ISO 8601 formatted timestamp indicating when the memory was last updated.",
    )
    meta_data: Optional[MemoryUnitMetaData] = Field(
        None, description="Additional metadata for the memory unit."
    )

    # PS1-specific fields
    keywords: Optional[list[str]] = Field(
        [],
        description="PS1: Ranked keywords optimized for retrieval (most to least important).",
    )
    context_sentence: Optional[str] = Field(
        "",
        description="PS1: One sentence capturing domain, intent, and knowledge type.",
    )
    embedding_text: Optional[str] = Field(
        "",
        description="PS1: Concatenated text used for embedding generation (content + keywords + tags + context).",
    )

    class Config:
        schema_extra = {
            "example": {
                "content": "User attended the AI conference in San Francisco and learned about the latest advancements in machine learning.",
                "type": "event",
                "confidence": 0.95,
                "memory_time": "2023-11-15T10:00:00",
                "entities": ["AI conference", "San Francisco", "machine learning"],
                "tags": ["conference", "AI", "ML"],
                "keywords": [
                    "AI conference",
                    "San Francisco",
                    "machine learning advancements",
                ],
                "context_sentence": "User participated in AI conference event in San Francisco focused on machine learning advancements, representing professional development activity.",
                "updated_at": "2023-11-16T12:00:00",
            }
        }


class CoreMemoryUnit(BaseModel):
    """One unit of core memory to be stored in the section "core_memories"

    Core memories are simple, stable facts about user/persona that are always injected
    into context. No PS1 needed - kept simple and direct.
    """

    persona_content: str = Field(
        ...,
        description="The persona to give to the LLM.",
    )
    human_content: str = Field(
        ...,
        description="The stable fact about the user to give to the LLM.",
    )


class ResourceMemoryUnit(BaseModel):
    """One unit of resource memory to be stored in the section "resource_memories"

    PS1 Enhancement: Includes keywords, tags, and entities for better searchability
    of uploaded documents, images, and links.
    """

    content: str = Field(
        ...,
        description="The main content of the resource memory. Usually a summary or extraction from the resource.",
    )
    resource_type: Literal[
        "document", "image", "video", "audio", "link", "extracted"
    ] = Field(..., description="Type of the resource memory.")
    resource_link: Optional[str] = Field(
        None, description="Link or path or message_ids to the resource if applicable."
    )

    # PS1-specific fields for resources
    keywords: Optional[list[str]] = Field(
        [],
        description="PS1: Key terms extracted from the resource for better retrieval.",
    )
    tags: Optional[list[str]] = Field(
        [],
        description="PS1: Categorical tags for the resource (domain, type, purpose).",
    )
    entities: Optional[list[str]] = Field(
        [], description="PS1: Named entities found in the resource."
    )
    context_sentence: Optional[str] = Field(
        "",
        description="PS1: One sentence summary of the resource's purpose and content.",
    )
    embedding_text: Optional[str] = Field(
        "",
        description="PS1: Enriched text for embedding (summary + keywords + tags + context).",
    )
