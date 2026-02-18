"""
Shared dependencies for FastAPI endpoints.
"""

import sys
from pathlib import Path
from typing import Dict

# Add parent directory to path to import existing services
sys.path.append(str(Path(__file__).parent.parent))

from services.chat_service import ChatService

# Global storage for active chat sessions
# In production, this should be Redis or another persistent store
active_chat_sessions: Dict[str, ChatService] = {}


def get_chat_service(session_id: str) -> ChatService:
    """
    Retrieve an active ChatService instance.

    Args:
        session_id: The session identifier

    Returns:
        ChatService instance

    Raises:
        KeyError: If session not found
    """
    if session_id not in active_chat_sessions:
        raise KeyError(f"Session {session_id} not found")
    return active_chat_sessions[session_id]


async def create_chat_session(
    session_id: str, user_id: str, block_id: str
) -> ChatService:
    """
    Create and store a new ChatService instance.

    Args:
        session_id: Unique session identifier
        user_id: User identifier
        block_id: Memory block identifier

    Returns:
        Created ChatService instance
    """
    # Import here to avoid circular imports
    from services.block_service import block_service

    # Load the memory block
    memory_block = await block_service.load_block(block_id)
    if not memory_block:
        raise ValueError(f"Block {block_id} not found")

    # Create ChatService with the loaded memory block
    chat_service = ChatService(memory_block=memory_block)
    active_chat_sessions[session_id] = chat_service
    return chat_service


def remove_chat_session(session_id: str) -> None:
    """
    Remove a ChatService instance from active sessions.

    Args:
        session_id: Session identifier to remove
    """
    if session_id in active_chat_sessions:
        del active_chat_sessions[session_id]
