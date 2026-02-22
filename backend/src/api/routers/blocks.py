"""Blocks router — memory block lifecycle management."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from backend.src.api.dependencies import get_client
from backend.src.api.models.requests import CreateBlockRequest
from memblocks import MemBlocksClient

router = APIRouter(prefix="/blocks", tags=["blocks"])


@router.post("/", response_model=Dict[str, Any])
async def create_block(
    body: CreateBlockRequest,
    client: MemBlocksClient = Depends(get_client),
) -> Dict[str, Any]:
    """Create a new memory block for a user."""
    block = await client.blocks.create_block(
        user_id=body.user_id,
        name=body.name,
        description=body.description,
        create_semantic=body.create_semantic,
        create_core=body.create_core,
        create_resource=body.create_resource,
    )
    return block.model_dump()


@router.get("/user/{user_id}", response_model=List[Dict[str, Any]])
async def get_user_blocks(
    user_id: str,
    client: MemBlocksClient = Depends(get_client),
) -> List[Dict[str, Any]]:
    """List all memory blocks belonging to a user."""
    blocks = await client.blocks.get_user_blocks(user_id)
    return [b.model_dump() for b in blocks]


@router.get("/{block_id}", response_model=Dict[str, Any])
async def get_block(
    block_id: str,
    client: MemBlocksClient = Depends(get_client),
) -> Dict[str, Any]:
    """Get a specific memory block by ID."""
    block = await client.blocks.get_block(block_id)
    if not block:
        raise HTTPException(status_code=404, detail=f"Block '{block_id}' not found")
    return block.model_dump()


@router.delete("/{block_id}")
async def delete_block(
    block_id: str,
    user_id: str,
    client: MemBlocksClient = Depends(get_client),
) -> Dict[str, Any]:
    """Delete a memory block."""
    success = await client.blocks.delete_block(block_id=block_id, user_id=user_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Block '{block_id}' not found or could not be deleted",
        )
    return {"deleted": True, "block_id": block_id}
