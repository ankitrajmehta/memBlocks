"""
Chat session endpoints.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any
import uuid

# Add parent directory to path FIRST
router_file = Path(__file__).resolve()
project_root = router_file.parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import APIRouter, HTTPException, status

from services.block_service import block_service, session_manager
from backend.models.requests import StartSessionRequest, SendMessageRequest
from backend.dependencies import (
    create_chat_session,
    get_chat_service,
    remove_chat_session,
    active_chat_sessions,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def start_session(request: StartSessionRequest) -> Dict[str, Any]:
    """
    Start a new chat session with a memory block.

    Args:
        request: Session start request with user_id and block_id

    Returns:
        Session information with session_id
    """
    try:
        # Verify block exists
        block = await block_service.load_block(request.block_id)
        if not block:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Block {request.block_id} not found for user {request.user_id}",
            )

        # Generate unique session ID
        session_id = f"session_{uuid.uuid4().hex[:12]}"

        # Create ChatService instance
        chat_service = await create_chat_session(
            session_id=session_id, user_id=request.user_id, block_id=request.block_id
        )

        # Attach block to user session
        session_manager.attach_block(request.user_id, request.block_id)

        return {
            "success": True,
            "data": {
                "session_id": session_id,
                "user_id": request.user_id,
                "block_id": request.block_id,
                "block_name": block.name,
                "status": "active",
            },
            "message": f"Chat session started with block '{block.name}'",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Failed to start session for user %s, block %s",
            request.user_id,
            request.block_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start session: {str(e)}",
        )


@router.post("/message")
async def send_message(request: SendMessageRequest) -> Dict[str, Any]:
    """
    Send a message in an active chat session.

    Args:
        request: Message request with session_id and message

    Returns:
        AI response and conversation metadata
    """
    try:
        # Get ChatService instance
        try:
            chat_service = get_chat_service(request.session_id)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {request.session_id} not found or expired",
            )

        # Process message through ChatService
        response = await chat_service.send_message(request.message)

        return {
            "success": True,
            "data": {
                "session_id": request.session_id,
                "user_message": request.message,
                "ai_response": response,
                "message_count": len(chat_service.message_history),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to process message in session %s", request.session_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}",
        )


@router.get("/sessions/{session_id}")
async def get_session_info(session_id: str) -> Dict[str, Any]:
    """
    Get information about an active chat session.

    Args:
        session_id: Session identifier

    Returns:
        Session metadata and conversation history
    """
    try:
        try:
            chat_service = get_chat_service(session_id)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        return {
            "success": True,
            "data": {
                "session_id": session_id,
                "user_id": "N/A",  # ChatService doesn't store user_id directly
                "block_id": chat_service.memory_block.meta_data.id,
                "message_count": len(chat_service.message_history),
                "conversation_history": chat_service.message_history,
                "status": "active",
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get session info for session %s", session_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session info: {str(e)}",
        )


@router.delete("/sessions/{session_id}")
async def end_session(session_id: str) -> Dict[str, Any]:
    """
    End an active chat session.

    Args:
        session_id: Session identifier

    Returns:
        Confirmation message
    """
    try:
        if session_id not in active_chat_sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        remove_chat_session(session_id)

        return {"success": True, "message": f"Session {session_id} ended successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to end session %s", session_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to end session: {str(e)}",
        )


@router.get("/sessions")
async def list_active_sessions() -> Dict[str, Any]:
    """
    List all active chat sessions.

    Returns:
        List of active session IDs and metadata
    """
    try:
        sessions = []
        for session_id, chat_service in active_chat_sessions.items():
            sessions.append(
                {
                    "session_id": session_id,
                    "user_id": "N/A",  # ChatService doesn't store user_id directly
                    "block_id": chat_service.memory_block.meta_data.id,
                    "message_count": len(chat_service.message_history),
                }
            )

        return {"success": True, "data": sessions, "count": len(sessions)}
    except Exception as e:
        logger.exception("Failed to list active sessions")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sessions: {str(e)}",
        )
