"""Pydantic models for structured LLM outputs."""

from pydantic import BaseModel, Field
from typing import List, Optional


class SemanticExtractionOutput(BaseModel):
    """Output model for semantic memory extraction."""
    
    keywords: List[str] = Field(description="Key terms and concepts from the content")
    content: str = Field(description="The actual memory content")
    type: str = Field(description="Memory type: event_factual, opinion, or world_knowledge")
    entities: List[str] = Field(description="Named entities (people, places, organizations)")
    confidence: float = Field(description="Confidence score between 0 and 1")


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
