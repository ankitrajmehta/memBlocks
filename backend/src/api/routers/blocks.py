"""Blocks router — memory block lifecycle management."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from backend.src.api.dependencies import get_client
from backend.src.api.models.requests import CreateBlockRequest
from backend.src.api.routers.auth import CurrentUser, get_current_user
from memblocks import MemBlocksClient

router = APIRouter(prefix="/blocks", tags=["blocks"])


@router.post("/", response_model=Dict[str, Any])
async def create_block(
    body: CreateBlockRequest,
    current_user: CurrentUser = Depends(get_current_user),
    client: MemBlocksClient = Depends(get_client),
) -> Dict[str, Any]:
    """Create a new memory block for the authenticated user."""
    block = await client.create_block(
        user_id=current_user.user_id,
        name=body.name,
        description=body.description,
        create_semantic=body.create_semantic,
        create_core=body.create_core,
        create_resource=body.create_resource,
    )
    return {
        "block_id": block.id,
        "name": block.name,
        "description": block.description,
        "user_id": block.user_id,
        "semantic_collection": block.semantic_collection,
        "core_memory_block_id": block.core_memory_block_id,
        "resource_collection": block.resource_collection,
        "created_at": block.created_at,
        "updated_at": block.updated_at,
    }


@router.get("/user/{user_id}", response_model=List[Dict[str, Any]])
async def get_user_blocks(
    user_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    client: MemBlocksClient = Depends(get_client),
) -> List[Dict[str, Any]]:
    """List all memory blocks belonging to the authenticated user."""
    if user_id != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="Cannot access another user's blocks",
        )
    blocks = await client.get_user_blocks(user_id)
    return [
        {
            "block_id": b.id,
            "name": b.name,
            "description": b.description,
            "user_id": b.user_id,
            "semantic_collection": b.semantic_collection,
            "core_memory_block_id": b.core_memory_block_id,
            "resource_collection": b.resource_collection,
            "created_at": b.created_at,
            "updated_at": b.updated_at,
        }
        for b in blocks
    ]


@router.get("/{block_id}", response_model=Dict[str, Any])
async def get_block(
    block_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    client: MemBlocksClient = Depends(get_client),
) -> Dict[str, Any]:
    """Get a specific memory block by ID."""
    block = await client.get_block(block_id)
    if not block:
        raise HTTPException(status_code=404, detail=f"Block '{block_id}' not found")
    if block.user_id != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="Cannot access another user's block",
        )
    return {
        "block_id": block.id,
        "name": block.name,
        "description": block.description,
        "user_id": block.user_id,
        "semantic_collection": block.semantic_collection,
        "core_memory_block_id": block.core_memory_block_id,
        "resource_collection": block.resource_collection,
        "created_at": block.created_at,
        "updated_at": block.updated_at,
    }


@router.delete("/{block_id}")
async def delete_block(
    block_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    client: MemBlocksClient = Depends(get_client),
) -> Dict[str, Any]:
    """Delete a memory block."""
    block = await client.get_block(block_id)
    if not block:
        raise HTTPException(
            status_code=404,
            detail=f"Block '{block_id}' not found",
        )
    if block.user_id != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="Cannot delete another user's block",
        )
    success = await client.delete_block(block_id=block_id, user_id=current_user.user_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Block '{block_id}' not found or could not be deleted",
        )
    return {"deleted": True, "block_id": block_id}
