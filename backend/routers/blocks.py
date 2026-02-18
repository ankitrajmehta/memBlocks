"""
Memory block management endpoints.
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

from services.block_service import block_service
from backend.models.requests import CreateBlockRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/blocks", tags=["blocks"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_block(request: CreateBlockRequest) -> Dict[str, Any]:
    """
    Create a new memory block for a user.

    Args:
        request: Block creation request with user_id, name, description

    Returns:
        Created MemoryBlock data
    """
    try:
        block = await block_service.create_block(
            user_id=request.user_id,
            name=request.name,
            description=request.description or "",
        )
        return {
            "success": True,
            "data": block.model_dump(),
            "message": f"Block '{request.name}' created successfully",
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Failed to create block '%s' for user %s", request.name, request.user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create block: {str(e)}",
        )


@router.get("/{user_id}")
async def list_user_blocks(user_id: str) -> Dict[str, Any]:
    """
    List all memory blocks for a user.

    Args:
        user_id: User identifier

    Returns:
        List of MemoryBlock data
    """
    try:
        blocks = await block_service.list_user_blocks(user_id)
        return {
            "success": True,
            "data": [block.model_dump() for block in blocks],
            "count": len(blocks),
        }
    except Exception as e:
        logger.exception("Failed to list blocks for user %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list blocks: {str(e)}",
        )


@router.get("/{user_id}/{block_id}")
async def get_block(user_id: str, block_id: str) -> Dict[str, Any]:
    """
    Get a specific memory block by ID.

    Args:
        user_id: User identifier
        block_id: Block identifier

    Returns:
        MemoryBlock data
    """
    try:
        block = await block_service.load_block(block_id)
        if not block:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Block {block_id} not found for user {user_id}",
            )
        return {"success": True, "data": block.model_dump()}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get block %s for user %s", block_id, user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get block: {str(e)}",
        )


@router.delete("/{user_id}/{block_id}")
async def delete_block(user_id: str, block_id: str) -> Dict[str, Any]:
    """
    Delete a memory block.

    Args:
        user_id: User identifier
        block_id: Block identifier

    Returns:
        Success confirmation
    """
    try:
        success = await block_service.delete_block(block_id, user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Block {block_id} not found for user {user_id}",
            )
        return {"success": True, "message": f"Block {block_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to delete block %s for user %s", block_id, user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete block: {str(e)}",
        )
