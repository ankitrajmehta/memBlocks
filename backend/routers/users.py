"""
User management endpoints.
"""

import sys
import logging
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path FIRST
router_file = Path(__file__).resolve()
project_root = router_file.parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import APIRouter, HTTPException, status

from services.user_service import user_service
from backend.models.requests import CreateUserRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(request: CreateUserRequest) -> Dict[str, Any]:
    """
    Create a new user or get existing user.

    Args:
        request: User creation request with user_id

    Returns:
        User document with metadata
    """
    try:
        user = await user_service.get_or_create_user(request.user_id)
        return {
            "success": True,
            "data": user,
            "message": f"User {request.user_id} ready",
        }
    except Exception as e:
        logger.exception("Failed to create user %s", request.user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}",
        )


@router.get("")
async def list_users() -> Dict[str, Any]:
    """
    List all users in the system.

    Returns:
        List of user documents
    """
    try:
        users = await user_service.list_users()
        return {"success": True, "data": users, "count": len(users)}
    except Exception as e:
        logger.exception("Failed to list users")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list users: {str(e)}",
        )


@router.get("/{user_id}")
async def get_user(user_id: str) -> Dict[str, Any]:
    """
    Get user details by user_id.

    Args:
        user_id: User identifier

    Returns:
        User document with metadata
    """
    try:
        user = await user_service.get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found",
            )
        return {"success": True, "data": user}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get user %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user: {str(e)}",
        )
