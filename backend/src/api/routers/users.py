"""Users router — user info endpoints (user creation is automatic via Clerk OAuth)."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from backend.src.api.dependencies import get_client
from backend.src.api.routers.auth import CurrentUser, get_current_user
from memblocks import MemBlocksClient

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=Dict[str, Any])
async def get_current_user_info(
    current_user: CurrentUser = Depends(get_current_user),
    client: MemBlocksClient = Depends(get_client),
) -> Dict[str, Any]:
    """Get the current authenticated user's info."""
    user = await client.get_user(current_user.user_id)
    if not user:
        return {
            "user_id": current_user.user_id,
            "email": current_user.email,
            "name": current_user.name,
            "image_url": current_user.image_url,
        }
    return user
