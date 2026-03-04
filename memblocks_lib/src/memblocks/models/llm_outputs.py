"""Pure data models for LLM structured outputs.

Copied from llm/output_models.py — zero service or DB imports.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class SemanticExtractionOutput(BaseModel):
    """Output model for single semantic memory extraction."""

    keywords: List[str] = Field(description="Key terms and concepts from the content")
    content: str = Field(description="The actual memory content")
    type: str = Field(description="Memory type")
    entities: List[str] = Field(
        description="Named entities (people, places, organizations)"
    )
    confidence: float = Field(description="Confidence score between 0 and 1")
    memory_time: Optional[str] = Field(
        default=None,
        description=(
            "ISO 8601 timestamp of when the event occurred. "
            "Only for type='event'. Compute from the current time provided in the input "
            "and any relative cues in the conversation (e.g. 'yesterday', 'last week'). "
            "Leave null if the memory type is not 'event' or if no temporal information is available."
        ),
    )


class SemanticMemoriesOutput(BaseModel):
    """Output model for list of semantic memories."""

    memories: List[SemanticExtractionOutput] = Field(
        description="List of extracted semantic memories"
    )


class ExistingSemanticMemoryUnitForPS2(BaseModel):
    """Input model passed to PS2 for each existing memory during conflict resolution."""

    id: str = Field(description="Qdrant point ID of the existing memory")
    memory_time: Optional[str] = Field(
        default=None,
        description="Original memory_time of the existing memory, if available",
    )
    updated_at: Optional[str] = Field(
        default=None,
        description="Original updated_at timestamp of the existing memory, if available",
    )
    keywords: List[str] = Field(
        description="Key terms and concepts from the existing memory"
    )
    content: str = Field(description="Content of the existing memory")
    type: str = Field(description="Type of the existing memory")
    entities: List[str] = Field(description="Named entities in the existing memory")
    confidence: float = Field(description="Confidence score of the existing memory")


class CoreMemoryOutput(BaseModel):
    """Output model for core memory extraction."""

    persona_content: str = Field(
        description="2-3 sentence paragraph about the AI's persona, behavior preferences, and communication style"
    )
    human_content: str = Field(
        description="5-7 sentence paragraph about the human user's identity, preferences, key facts, and context"
    )


class SummaryOutput(BaseModel):
    """Output model for recursive summary generation."""

    summary: str = Field(
        description="Concise summary of the conversation incorporating previous context"
    )


class PS2NewMemoryOperation(BaseModel):
    """Operation to perform on a new memory being added."""

    operation: Literal["ADD", "NONE"] = Field(
        description="Whether to ADD the new memory or do NOTHING"
    )
    reason: Optional[str] = Field(
        default=None, description="Explanation for the decision"
    )


class PS2ExistingMemoryOperation(BaseModel):
    """Operation to perform on an existing memory in the database."""

    id: str = Field(description="Qdrant point ID of the existing memory")
    operation: Literal["UPDATE", "DELETE", "NONE"] = Field(
        description="Operation to perform on the existing memory"
    )
    updated_memory: Optional["ExistingSemanticMemoryUnitForPS2"] = Field(
        default=None,
        description=(
            "Updated memory for UPDATE operation. Contains the same fields as the existing "
            "memory input (id, content, keywords, type, entities, confidence, memory_time, updated_at) "
            "with changes applied. Use the same simple integer ID as the input."
        ),
    )
    reason: Optional[str] = Field(
        default=None, description="Explanation for the decision"
    )


class PS2MemoryUpdateOutput(BaseModel):
    """Output model for PS2 memory conflict resolution."""

    new_memory_operation: PS2NewMemoryOperation = Field(
        description="Decision for the new memory being processed"
    )
    existing_memory_operations: List[PS2ExistingMemoryOperation] = Field(
        default_factory=list, description="Operations to perform on existing memories"
    )


class QueryExpansionOutput(BaseModel):
    """Output model for query expansion."""

    expanded_queries: List[str] = Field(
        description="List of expanded queries with additional related terms for better retrieval coverage"
    )


class HypotheticalParagraphsOutput(BaseModel):
    """Output model for hypothetical paragraph generation."""

    paragraphs: List[str] = Field(
        description="List of hypothetical answer paragraphs that could respond to the query"
    )


class QueryEnhancementOutput(BaseModel):
    """Combined output model for query expansion and hypothetical paragraph generation.
    
    This model combines both operations into a single LLM call to reduce latency.
    """

    expanded_queries: List[str] = Field(
        description="List of expanded queries with additional related terms for better retrieval coverage"
    )
    hypothetical_paragraphs: List[str] = Field(
        description="List of hypothetical answer paragraphs that could respond to the query"
    )


class RankedMemory(BaseModel):
    """Single ranked memory with relevance explanation."""

    memory_id: str = Field(description="Unique identifier of the memory")
    content: str = Field(description="Content of the memory")
    relevance_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Relevance score between 0 and 1"
    )
    relevance_reason: str = Field(
        description="Brief explanation of why this memory is relevant to the query"
    )


class ReRankingOutput(BaseModel):
    """Output model for re-ranking retrieval results."""

    ranked_memories: List[RankedMemory] = Field(
        description="List of memories ranked by relevance to the query, with explanations"
    )


__all__ = [
    "SemanticExtractionOutput",
    "SemanticMemoriesOutput",
    "ExistingSemanticMemoryUnitForPS2",
    "CoreMemoryOutput",
    "SummaryOutput",
    "PS2NewMemoryOperation",
    "PS2ExistingMemoryOperation",
    "PS2MemoryUpdateOutput",
    "QueryExpansionOutput",
    "HypotheticalParagraphsOutput",
    "QueryEnhancementOutput",
    "RankedMemory",
    "ReRankingOutput",
]
