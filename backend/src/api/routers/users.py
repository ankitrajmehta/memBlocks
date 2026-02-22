"""Users router — CRUD for memBlocks users."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from backend.src.api.dependencies import get_client
from backend.src.api.models.requests import CreateUserRequest
from memblocks import MemBlocksClient

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=Dict[str, Any])
async def create_user(
    body: CreateUserRequest,
    client: MemBlocksClient = Depends(get_client),
) -> Dict[str, Any]:
    """Create a new user (idempotent — returns existing user if already present)."""
    return await client.create_user(body.user_id)


@router.get("/", response_model=List[Dict[str, Any]])
async def list_users(
    client: MemBlocksClient = Depends(get_client),
) -> List[Dict[str, Any]]:
    """List all users."""
    return await client.list_users()


@router.get("/{user_id}", response_model=Dict[str, Any])
async def get_user(
    user_id: str,
    client: MemBlocksClient = Depends(get_client),
) -> Dict[str, Any]:
    """Get a user by ID."""
    user = await client.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    return user
