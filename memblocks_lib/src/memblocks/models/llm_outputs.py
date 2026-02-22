"""Pure data models for LLM structured outputs.

Copied from llm/output_models.py — zero service or DB imports.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict


class SemanticExtractionOutput(BaseModel):
    """Output model for single semantic memory extraction."""

    keywords: List[str] = Field(description="Key terms and concepts from the content")
    content: str = Field(description="The actual memory content")
    type: str = Field(description="Memory type")
    entities: List[str] = Field(description="Named entities (people, places, organizations)")
    confidence: float = Field(description="Confidence score between 0 and 1")


class SemanticMemoriesOutput(BaseModel):
    """Output model for list of semantic memories."""

    memories: List[SemanticExtractionOutput] = Field(
        description="List of extracted semantic memories"
    )


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
    updated_memory: Optional[Dict] = Field(
        default=None, description="Complete updated memory dict for UPDATE operation"
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


__all__ = [
    "SemanticExtractionOutput",
    "SemanticMemoriesOutput",
    "CoreMemoryOutput",
    "SummaryOutput",
    "PS2NewMemoryOperation",
    "PS2ExistingMemoryOperation",
    "PS2MemoryUpdateOutput",
]
