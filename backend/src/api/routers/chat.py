"""Chat router — session management and conversational turns."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from backend.src.api.dependencies import get_client
from backend.src.api.models.requests import ChatRequest, CreateSessionRequest
from backend.src.api.routers.auth import CurrentUser, get_current_user
from memblocks import MemBlocksClient
from memblocks.prompts import ASSISTANT_BASE_PROMPT

router = APIRouter(prefix="/chat", tags=["chat"])


def _session_to_dict(session: Any) -> Dict[str, Any]:
    return {
        "session_id": session.id,
        "user_id": session.user_id,
        "block_id": session.block_id,
        "created_at": session.created_at,
    }


# ------------------------------------------------------------------ #
# Session CRUD
# ------------------------------------------------------------------ #

@router.post("/sessions", response_model=Dict[str, Any])
async def create_session(
    body: CreateSessionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    client: MemBlocksClient = Depends(get_client),
) -> Dict[str, Any]:
    """Create a new chat session attached to a memory block."""
    block = await client.get_block(body.block_id)
    if not block:
        raise HTTPException(
            status_code=404, detail=f"Block '{body.block_id}' not found"
        )
    
    if block.user_id != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="Cannot create session for another user's block",
        )

    session = await client.create_session(
        user_id=current_user.user_id,
        block_id=body.block_id,
    )
    return _session_to_dict(session)


@router.get("/sessions/{session_id}", response_model=Dict[str, Any])
async def get_session(
    session_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    client: MemBlocksClient = Depends(get_client),
) -> Dict[str, Any]:
    """Get session metadata."""
    session = await client.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    if session.user_id != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="Cannot access another user's session",
        )
    return _session_to_dict(session)


@router.get("/sessions/block/{block_id}", response_model=List[Dict[str, Any]])
async def list_block_sessions(
    block_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    client: MemBlocksClient = Depends(get_client),
) -> List[Dict[str, Any]]:
    """List all sessions for a block, ordered by creation time (newest first).
    
    Used by the frontend to show session history and allow resuming sessions.
    """
    block = await client.get_block(block_id)
    if not block:
        raise HTTPException(status_code=404, detail=f"Block '{block_id}' not found")
    if block.user_id != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="Cannot access another user's block sessions",
        )
    
    # Query MongoDB directly for all sessions in this block
    cursor = client.mongo.sessions.find(
        {"block_id": block_id, "user_id": current_user.user_id},
        {"session_id": 1, "user_id": 1, "block_id": 1, "created_at": 1, "recursive_summary": 1, "_id": 0},
    ).sort("created_at", -1)
    docs = await cursor.to_list(length=50)
    
    result = []
    for doc in docs:
        # Get message count for display
        msg_count = await client.mongo.get_session_message_count(doc["session_id"])
        result.append({
            "session_id": doc["session_id"],
            "user_id": doc.get("user_id", ""),
            "block_id": doc.get("block_id", ""),
            "created_at": doc.get("created_at", ""),
            "message_count": msg_count,
            "has_summary": bool(doc.get("recursive_summary", "")),
        })
    return result


# ------------------------------------------------------------------ #
# Chat turn — send message and get AI response
# ------------------------------------------------------------------ #

@router.post("/sessions/{session_id}/message", response_model=Dict[str, Any])
async def send_message(
    session_id: str,
    body: ChatRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(get_current_user),
    client: MemBlocksClient = Depends(get_client),
) -> Dict[str, Any]:
    """Send a message and receive an AI response.

    Retrieves memory context from the block, builds a system prompt using
    the ASSISTANT_BASE_PROMPT + retrieved context, calls the LLM, persists
    the turn (triggering memory pipeline if window is full), and returns
    the response with updated analytics data.
    """
    session = await client.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    
    if session.user_id != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="Cannot send message to another user's session",
        )

    block = await client.get_block(session.block_id)
    if not block:
        raise HTTPException(
            status_code=404,
            detail=f"Block '{session.block_id}' attached to session not found",
        )

    # --- Retrieve memory context ---
    context = None
    try:
        context = await block.retrieve(body.message)
    except Exception as e:
        print(f"Error retrieving context: {e}")
    
    memory_window = []
    try:
        memory_window = await session.get_memory_window()
    except Exception as e:
        print(f"Error getting memory window: {e}")
    
    summary = ""
    try:
        summary = await session.get_recursive_summary()
    except Exception as e:
        print(f"Error getting summary: {e}")

    # --- Build system prompt using library's ASSISTANT_BASE_PROMPT ---
    system_parts = [ASSISTANT_BASE_PROMPT]
    
    if summary:
        system_parts.append(
            f"<Conversation Summary>\n{summary}\n</Conversation Summary>"
        )
    
    if context and not context.is_empty():
        memory_str = context.to_prompt_string()
        if memory_str:
            system_parts.append(f"<Memory Context>\n{memory_str}\n</Memory Context>")
    
    system_prompt = "\n\n".join(system_parts)

    # --- Build message list for LLM ---
    messages_for_llm = (
        [{"role": "system", "content": system_prompt}]
        + memory_window
        + [{"role": "user", "content": body.message}]
    )

    # --- Call LLM ---
    try:
        ai_response = await client.conversation_llm.chat(messages=messages_for_llm)
    except Exception as e:
        print(f"Error calling LLM: {e}")
        raise HTTPException(status_code=500, detail=f"LLM call failed: {str(e)}")

    # --- Persist turn (runs memory pipeline in background to keep UI fast) ---
    processing_triggered = False
    try:
        background_tasks.add_task(session.add, user_msg=body.message, ai_response=ai_response)
    except Exception as e:
        print(f"Error persisting turn: {e}")

    # --- Fetch updated core memory and summary AFTER the turn ---
    core_memory_data = None
    try:
        core_result = await block.core_retrieve()
        if core_result and core_result.core:
            core = core_result.core
            core_memory_data = {
                "persona_content": core.persona_content or "",
                "human_content": core.human_content or "",
            }
    except Exception as e:
        print(f"Error getting core memory post-turn: {e}")

    updated_summary = ""
    try:
        updated_summary = await session.get_recursive_summary()
    except Exception as e:
        print(f"Error getting updated summary: {e}")

    # --- Get transparency stats ---
    pipeline_runs = []
    try:
        recent_runs = client.processing_history.get_runs(limit=5)
        pipeline_runs = [
            {
                "task_id": run.task_id,
                "status": run.status,
                "trigger_event": run.trigger_event,
                "input_message_count": run.input_message_count,
                "extracted_semantic_count": run.extracted_semantic_count,
                "conflicts_resolved_count": run.conflicts_resolved_count,
                "core_memory_updated": run.core_memory_updated,
                "summary_generated": run.summary_generated,
                "timestamp_started": run.timestamp_started.isoformat() if run.timestamp_started else None,
                "timestamp_completed": run.timestamp_completed.isoformat() if run.timestamp_completed else None,
            }
            for run in recent_runs
        ]
    except Exception as e:
        print(f"Error getting pipeline runs: {e}")

    operation_summary = {}
    try:
        operation_summary = client.operation_log.summary()
    except Exception as e:
        print(f"Error getting operation summary: {e}")

    # --- Get current message count ---
    current_msg_count = 0
    try:
        current_msg_count = await client.mongo.get_session_message_count(session_id)
    except Exception:
        pass

    return {
        "session_id": session_id,
        "response": ai_response,
        "memory_context_used": context is not None and not context.is_empty(),
        "memory_window_size": len(memory_window),
        "current_message_count": current_msg_count,
        "summary": updated_summary,
        "core_memory": core_memory_data,
        "processing_triggered": processing_triggered,
        "pipeline_runs": pipeline_runs,
        "operation_summary": operation_summary,
    }


# ------------------------------------------------------------------ #
# Manual Flush
# ------------------------------------------------------------------ #

@router.post("/sessions/{session_id}/flush", response_model=Dict[str, Any])
async def flush_session(
    session_id: str,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(get_current_user),
    client: MemBlocksClient = Depends(get_client),
) -> Dict[str, Any]:
    """Manually flush a session's messages through the memory pipeline."""
    session = await client.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    
    if session.user_id != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="Cannot flush another user's session",
        )
    
    try:
        background_tasks.add_task(session.flush)
        return {
            "session_id": session_id,
            "status": "flush_enqueued",
            "summary": "Updating in background",
        }
    except Exception as e:
        print(f"Error flushing session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------ #
# History and summary endpoints
# ------------------------------------------------------------------ #

@router.get("/sessions/{session_id}/history", response_model=List[Dict[str, Any]])
async def get_chat_history(
    session_id: str,
    limit: int = 100,
    current_user: CurrentUser = Depends(get_current_user),
    client: MemBlocksClient = Depends(get_client),
) -> List[Dict[str, Any]]:
    """Return the message history for a session (from memory window)."""
    session = await client.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    
    if session.user_id != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="Cannot access another user's session history",
        )

    return await session.get_memory_window()


@router.get("/sessions/{session_id}/full-context", response_model=Dict[str, Any])
async def get_full_session_context(
    session_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    client: MemBlocksClient = Depends(get_client),
) -> Dict[str, Any]:
    """Return the full session context: all messages + recursive summary + core memory.
    
    Used by the frontend on session resume to restore the complete state.
    """
    session = await client.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    
    if session.user_id != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="Cannot access another user's session",
        )

    # Get all messages (not just window)
    doc = await client.mongo.sessions.find_one({"session_id": session_id})
    messages = doc.get("messages", []) if doc else []
    
    # Get recursive summary
    summary = await session.get_recursive_summary()
    
    # Get core memory from the block
    block = await client.get_block(session.block_id)
    core_memory_data = None
    if block:
        try:
            core_result = await block.core_retrieve()
            if core_result and core_result.core:
                core = core_result.core
                core_memory_data = {
                    "persona_content": core.persona_content or "",
                    "human_content": core.human_content or "",
                }
        except Exception:
            pass

    # Get pipeline runs
    pipeline_runs = []
    try:
        recent_runs = client.processing_history.get_runs(limit=5)
        pipeline_runs = [
            {
                "task_id": run.task_id,
                "status": run.status,
                "trigger_event": run.trigger_event,
                "input_message_count": run.input_message_count,
                "extracted_semantic_count": run.extracted_semantic_count,
                "core_memory_updated": run.core_memory_updated,
                "summary_generated": run.summary_generated,
            }
            for run in recent_runs
        ]
    except Exception:
        pass

    return {
        "session_id": session_id,
        "block_id": session.block_id,
        "messages": messages,
        "summary": summary,
        "core_memory": core_memory_data,
        "pipeline_runs": pipeline_runs,
        "message_count": len(messages),
    }


@router.get("/sessions/{session_id}/summary", response_model=Dict[str, Any])
async def get_session_summary(
    session_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    client: MemBlocksClient = Depends(get_client),
) -> Dict[str, Any]:
    """Get the recursive summary for a session."""
    session = await client.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    
    if session.user_id != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="Cannot access another user's session summary",
        )
    
    summary = await session.get_recursive_summary()
    return {
        "session_id": session_id,
        "summary": summary,
    }
