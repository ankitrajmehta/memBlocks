"""
    Models related to various types of data extractions using LLMs.
"""

from pydantic import BaseModel, Field

class Semantic_extraction(BaseModel):
    """Schema for response from llm to fill in SemanticMemoryUnit fields."""
    keywords: list[str] = Field(
        ...,
        description="List of keywords representing the main topics or concepts in the resource.",
    )
    context: str = Field(
        ...,
        description="A single sentence summarizing the core content of the resource.",
    )
    tags: list[str] = Field(
        ...,
        description="Categorical tags for organizing and retrieving the resource.",
    )
    entities: list[str] = Field(
        ...,
        description="Named entities mentioned in the resource for better identification.",
    )
    confidence: float = Field(..., ge=0, le=1, description="Confidence score between 0 and 1.")