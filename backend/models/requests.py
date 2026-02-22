"""
Pydantic request models for the FastAPI endpoints.
"""

from typing import Optional
from pydantic import BaseModel, Field


class CreateUserRequest(BaseModel):
    """Request model for creating a user."""

    user_id: str = Field(..., description="Unique user identifier", min_length=1)


class CreateBlockRequest(BaseModel):
    """Request model for creating a memory block."""

    user_id: str = Field(..., description="User identifier", min_length=1)
    name: str = Field(..., description="Block name", min_length=1)
    description: Optional[str] = Field(None, description="Block description")


class StartSessionRequest(BaseModel):
    """Request model for starting a chat session."""

    user_id: str = Field(..., description="User identifier", min_length=1)
    block_id: str = Field(..., description="Memory block identifier", min_length=1)


class SendMessageRequest(BaseModel):
    """Request model for sending a chat message."""

    session_id: str = Field(..., description="Active session identifier", min_length=1)
    message: str = Field(..., description="User message", min_length=1)
