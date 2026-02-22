"""SessionManager — replaces in-memory SessionManager from services/block_service.py."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from memblocks.storage.mongo import MongoDBAdapter
    from memblocks.services.transparency import OperationLog


class SessionManager:
    """
    Manages chat session state, persisted in MongoDB.

    Replaces: SessionManager (block_service.py:146-183).

    Key changes from the original:
    - Session state is persisted to MongoDB (was in-memory dict → lost on restart).
    - Messages are stored per session in MongoDB (SessionManager now owns message
      persistence that was previously in-memory in ChatService.message_history).
    - Dependency-injected MongoDBAdapter (no global singletons).
    """

    def __init__(
        self,
        mongo_adapter: "MongoDBAdapter",
        operation_log: Optional["OperationLog"] = None,
    ) -> None:
        """
        Args:
            mongo_adapter: MongoDB persistence layer.
            operation_log: Phase-9 transparency placeholder.
        """
        self._mongo = mongo_adapter
        self._log = operation_log

    # ------------------------------------------------------------------ #
    # Session lifecycle
    # ------------------------------------------------------------------ #

    async def create_session(
        self,
        user_id: str,
        block_id: str,
    ) -> Dict[str, Any]:
        """
        Create and persist a new chat session.

        Mirrors SessionManager.create_session() (block_service.py:152-160) but
        persists to MongoDB instead of an in-memory dict.

        Args:
            user_id: Owner of the session.
            block_id: Memory block attached to this session.

        Returns:
            Session document dict with at least "session_id".
        """
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        session_data: Dict[str, Any] = {
            "session_id": session_id,
            "user_id": user_id,
            "block_id": block_id,
            "created_at": datetime.utcnow().isoformat(),
            "messages": [],
        }
        await self._mongo.create_session(session_data)
        print(f"✅ Created session: {session_id} (block: {block_id})")
        return session_data

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session metadata.

        Mirrors SessionManager.get_session() (block_service.py:180-182).

        Args:
            session_id: Session identifier.

        Returns:
            Session document or None.
        """
        return await self._mongo.get_session(session_id)

    # ------------------------------------------------------------------ #
    # Block attachment helpers
    # ------------------------------------------------------------------ #

    async def attach_block(self, session_id: str, block_id: str) -> None:
        """
        Attach (or re-attach) a memory block to an existing session.

        Mirrors SessionManager.attach_block() (block_service.py:162-166).
        """
        await self._mongo.update_session(session_id, {"block_id": block_id})
        print(f"✅ Attached block {block_id} to session {session_id}")

    async def detach_block(self, session_id: str) -> None:
        """
        Remove the block attachment from a session.

        Mirrors SessionManager.detach_block() (block_service.py:168-172).
        """
        await self._mongo.update_session(session_id, {"block_id": None})
        print(f"✅ Detached block from session {session_id}")

    async def get_attached_block(self, session_id: str) -> Optional[str]:
        """
        Return the block_id attached to a session, or None.

        Mirrors SessionManager.get_attached_block() (block_service.py:174-178).
        """
        session = await self._mongo.get_session(session_id)
        if session:
            return session.get("block_id")
        return None

    # ------------------------------------------------------------------ #
    # Message management
    # ------------------------------------------------------------------ #

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        """
        Append a message to the session's history in MongoDB.

        Args:
            session_id: Session identifier.
            role: "user" or "assistant".
            content: Message text.
        """
        message: Dict[str, Any] = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self._mongo.add_message_to_session(session_id, message)

    async def get_messages(
        self,
        session_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Return the most recent messages for a session.

        Args:
            session_id: Session identifier.
            limit: Maximum number of messages.

        Returns:
            List of {"role": ..., "content": ...} dicts.
        """
        return await self._mongo.get_session_messages(session_id, limit)

    async def get_message_count(self, session_id: str) -> int:
        """
        Return the total number of messages in a session.

        Args:
            session_id: Session identifier.

        Returns:
            Message count.
        """
        return await self._mongo.get_session_message_count(session_id)

    async def clear_messages(self, session_id: str) -> None:
        """
        Clear all messages from a session (e.g. after pipeline flush).

        Args:
            session_id: Session identifier.
        """
        await self._mongo.clear_session_messages(session_id)
