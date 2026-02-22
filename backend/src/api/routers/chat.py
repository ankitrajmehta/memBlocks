"""Chat router — session management and conversational turns."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from backend.src.api.dependencies import get_client
from backend.src.api.models.requests import ChatRequest, CreateSessionRequest
from memblocks import MemBlocksClient

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=Dict[str, Any])
async def create_session(
    body: CreateSessionRequest,
    client: MemBlocksClient = Depends(get_client),
) -> Dict[str, Any]:
    """Create a new chat session attached to a memory block."""
    block = await client.blocks.get_block(body.block_id)
    if not block:
        raise HTTPException(
            status_code=404, detail=f"Block '{body.block_id}' not found"
        )

    session = await client.sessions.create_session(
        user_id=body.user_id,
        block_id=body.block_id,
    )
    return session


@router.get("/sessions/{session_id}", response_model=Dict[str, Any])
async def get_session(
    session_id: str,
    client: MemBlocksClient = Depends(get_client),
) -> Dict[str, Any]:
    """Get session metadata."""
    session = await client.sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return session


@router.post("/sessions/{session_id}/message", response_model=Dict[str, Any])
async def send_message(
    session_id: str,
    body: ChatRequest,
    client: MemBlocksClient = Depends(get_client),
) -> Dict[str, Any]:
    """Send a message and receive an AI response.

    Looks up the session's attached block, builds a scoped ChatEngine,
    and delegates the turn to ChatEngine.send_message().
    """
    session = await client.sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    block_id: str = session.get("block_id", "")
    block = await client.blocks.get_block(block_id)
    if not block:
        raise HTTPException(
            status_code=404,
            detail=f"Block '{block_id}' attached to session not found",
        )

    engine = client.get_chat_engine(block)
    result = await engine.chat.send_message(
        session_id=session_id, user_message=body.message
    )
    return result


@router.get("/sessions/{session_id}/history", response_model=List[Dict[str, Any]])
async def get_chat_history(
    session_id: str,
    limit: int = 100,
    client: MemBlocksClient = Depends(get_client),
) -> List[Dict[str, Any]]:
    """Return the message history for a session."""
    session = await client.sessions.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    block_id: str = session.get("block_id", "")
    block = await client.blocks.get_block(block_id)
    if not block:
        raise HTTPException(
            status_code=404,
            detail=f"Block '{block_id}' attached to session not found",
        )

    engine = client.get_chat_engine(block)
    return await engine.chat.get_chat_history(session_id=session_id, limit=limit)
