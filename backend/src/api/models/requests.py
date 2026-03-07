"""Pydantic request/response models for the memBlocks backend API."""

from typing import Optional
from pydantic import BaseModel, Field


class CreateUserRequest(BaseModel):
    user_id: str = Field(..., description="Unique user identifier")


class CreateBlockRequest(BaseModel):
    name: str = Field(..., description="Human-readable block name")
    description: str = Field("", description="Optional block description")
    create_semantic: bool = Field(True, description="Create semantic Qdrant collection")
    create_core: bool = Field(True, description="Initialise core memory document")
    create_resource: bool = Field(
        False, description="Create resource Qdrant collection"
    )


class CreateSessionRequest(BaseModel):
    block_id: str = Field(..., description="Memory block to attach to this session")


class ChatRequest(BaseModel):
    message: str = Field(..., description="User's message text")


class UpdateCoreMemoryRequest(BaseModel):
    persona_content: Optional[str] = Field(None, description="Persona section text")
    human_content: Optional[str] = Field(None, description="Human facts section text")


class SearchMemoriesRequest(BaseModel):
    query: str = Field(..., description="Search query text")
    top_k: int = Field(5, description="Number of results to return")


__all__ = [
    "CreateUserRequest",
    "CreateBlockRequest",
    "CreateSessionRequest",
    "ChatRequest",
    "UpdateCoreMemoryRequest",
    "SearchMemoriesRequest",
]
