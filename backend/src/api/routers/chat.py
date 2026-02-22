"""Chat router — session management and conversational turns."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from backend.src.api.dependencies import get_client
from backend.src.api.models.requests import ChatRequest, CreateSessionRequest
from memblocks import MemBlocksClient

router = APIRouter(prefix="/chat", tags=["chat"])


def _session_to_dict(session: Any) -> Dict[str, Any]:
    return {
        "session_id": session.id,
        "user_id": session.user_id,
        "block_id": session.block_id,
        "created_at": session.created_at,
    }


@router.post("/sessions", response_model=Dict[str, Any])
async def create_session(
    body: CreateSessionRequest,
    client: MemBlocksClient = Depends(get_client),
) -> Dict[str, Any]:
    """Create a new chat session attached to a memory block."""
    block = await client.get_block(body.block_id)
    if not block:
        raise HTTPException(
            status_code=404, detail=f"Block '{body.block_id}' not found"
        )

    session = await client.create_session(
        user_id=body.user_id,
        block_id=body.block_id,
    )
    return _session_to_dict(session)


@router.get("/sessions/{session_id}", response_model=Dict[str, Any])
async def get_session(
    session_id: str,
    client: MemBlocksClient = Depends(get_client),
) -> Dict[str, Any]:
    """Get session metadata."""
    session = await client.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return _session_to_dict(session)


@router.post("/sessions/{session_id}/message", response_model=Dict[str, Any])
async def send_message(
    session_id: str,
    body: ChatRequest,
    client: MemBlocksClient = Depends(get_client),
) -> Dict[str, Any]:
    """Send a message and receive an AI response.

    Retrieves memory context from the block, builds a system prompt,
    calls the library's LLM provider, persists the turn, and returns
    the response.
    """
    session = await client.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    block = await client.get_block(session.block_id)
    if not block:
        raise HTTPException(
            status_code=404,
            detail=f"Block '{session.block_id}' attached to session not found",
        )

    # --- Retrieve memory context ---
    context = await block.retrieve(body.message)
    memory_window = await session.get_memory_window()
    summary = await session.get_recursive_summary()

    # --- Build system prompt ---
    system_parts = ["You are a helpful assistant with memory of past conversations."]
    if summary:
        system_parts.append(
            f"<Conversation Summary>\n{summary}\n</Conversation Summary>"
        )
    memory_str = context.to_prompt_string()
    if memory_str:
        system_parts.append(memory_str)
    system_prompt = "\n\n".join(system_parts)

    # --- Build message list for LLM ---
    messages_for_llm = memory_window + [{"role": "user", "content": body.message}]

    # --- Call LLM ---
    messages_for_llm = (
        [{"role": "system", "content": system_prompt}]
        + memory_window
        + [{"role": "user", "content": body.message}]
    )
    ai_response = await client.llm.chat(messages=messages_for_llm)

    # --- Persist turn ---
    await session.add(user_msg=body.message, ai_response=ai_response)

    return {
        "session_id": session_id,
        "response": ai_response,
        "memory_context_used": not context.is_empty(),
    }


@router.get("/sessions/{session_id}/history", response_model=List[Dict[str, Any]])
async def get_chat_history(
    session_id: str,
    limit: int = 100,
    client: MemBlocksClient = Depends(get_client),
) -> List[Dict[str, Any]]:
    """Return the message history for a session."""
    session = await client.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    return await session.get_memory_window()
