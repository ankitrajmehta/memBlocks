"""User management service."""

from typing import Optional, List, Dict, Any
from vector_db.mongo_manager import mongo_manager


class UserService:
    """Service for user operations."""
    
    @staticmethod
    async def create_user(user_id: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a new user.
        
        Args:
            user_id: Unique user identifier
            metadata: Optional user metadata
            
        Returns:
            Created user document
        """
        # Check if user already exists
        existing_user = await mongo_manager.get_user(user_id)
        if existing_user:
            print(f"⚠️ User {user_id} already exists")
            return existing_user
        
        user_doc = await mongo_manager.create_user(user_id, metadata)
        print(f"✅ Created user: {user_id}")
        return user_doc
    
    @staticmethod
    async def get_user(user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by ID.
        
        Args:
            user_id: User identifier
            
        Returns:
            User document or None
        """
        return await mongo_manager.get_user(user_id)
    
    @staticmethod
    async def list_users() -> List[Dict[str, Any]]:
        """Get all users."""
        return await mongo_manager.list_users()
    
    @staticmethod
    async def get_or_create_user(user_id: str) -> Dict[str, Any]:
        """
        Get user or create if doesn't exist.
        
        Args:
            user_id: User identifier
            
        Returns:
            User document
        """
        user = await mongo_manager.get_user(user_id)
        if not user:
            user = await mongo_manager.create_user(user_id)
            print(f"✅ Created new user: {user_id}")
        return user


# Singleton instance
user_service = UserService()
