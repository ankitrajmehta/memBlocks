"""
Memory viewing endpoints - access core memory and summaries.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any, List

# Add parent directory to path FIRST
router_file = Path(__file__).resolve()
project_root = router_file.parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import APIRouter, HTTPException, status

from services.block_service import block_service
from vector_db.vector_db_manager import VectorDBManager
from vector_db.mongo_manager import mongo_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("/{block_id}/core")
async def get_core_memory(block_id: str) -> Dict[str, Any]:
    """
    Retrieve the core memory for a memory block.

    Args:
        block_id: Memory block identifier

    Returns:
        Core memory content
    """
    try:
        # Get core memory from MongoDB
        core_memory = await mongo_manager.get_core_memory(block_id)

        if not core_memory:
            return {
                "success": True,
                "data": {
                    "block_id": block_id,
                    "core_memory": None,
                    "message": "No core memory found for this block",
                },
            }

        return {
            "success": True,
            "data": {
                "block_id": block_id,
                "persona_content": core_memory.get("persona_content"),
                "human_content": core_memory.get("human_content"),
                "created_at": core_memory.get("created_at"),
                "updated_at": core_memory.get("updated_at"),
            },
        }
    except Exception as e:
        logger.exception("Failed to retrieve core memory for block %s", block_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve core memory: {str(e)}",
        )


@router.get("/{block_id}/summary")
async def get_recursive_summary(block_id: str) -> Dict[str, Any]:
    """
    Retrieve the recursive summary for a memory block.

    Note: Recursive summary is stored in-memory in ChatService during active sessions.
    This endpoint currently returns a placeholder.

    Args:
        block_id: Memory block identifier

    Returns:
        Recursive summary content
    """
    try:
        return {
            "success": True,
            "data": {
                "block_id": block_id,
                "summary": None,
                "message": "Recursive summary is session-specific and not persisted to database",
            },
        }
    except Exception as e:
        logger.exception("Failed to retrieve recursive summary for block %s", block_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve recursive summary: {str(e)}",
        )


@router.get("/{block_id}/semantic")
async def get_semantic_memories(block_id: str, limit: int = 20) -> Dict[str, Any]:
    """
    Retrieve semantic memories from vector database.

    Args:
        block_id: Memory block identifier
        limit: Maximum number of memories to return

    Returns:
        List of semantic memories
    """
    try:
        # Load block to get collection name
        block = await block_service.load_block(block_id)
        if not block or not block.semantic_memories:
            return {
                "success": True,
                "data": {
                    "block_id": block_id,
                    "memories": [],
                    "count": 0,
                    "message": "No semantic memories configured for this block",
                },
            }

        collection_name = block.semantic_memories.collection_name

        # Get all points from collection
        try:
            memories = VectorDBManager.get_all_points(collection_name, limit=limit)
            return {
                "success": True,
                "data": {
                    "block_id": block_id,
                    "collection": collection_name,
                    "memories": memories,
                    "count": len(memories),
                },
            }
        except Exception as e:
            return {
                "success": True,
                "data": {
                    "block_id": block_id,
                    "memories": [],
                    "count": 0,
                    "message": f"Collection not found or empty: {str(e)}",
                },
            }
    except Exception as e:
        logger.exception("Failed to retrieve semantic memories for block %s", block_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve semantic memories: {str(e)}",
        )


@router.get("/{block_id}/search")
async def search_memories(block_id: str, query: str, limit: int = 5) -> Dict[str, Any]:
    """
    Search semantic memories using vector similarity.

    Args:
        block_id: Memory block identifier
        query: Search query
        limit: Maximum number of results

    Returns:
        List of relevant memories with similarity scores
    """
    try:
        # Load block
        block = await block_service.load_block(block_id)
        if not block or not block.semantic_memories:
            return {
                "success": True,
                "data": {
                    "block_id": block_id,
                    "query": query,
                    "results": [],
                    "count": 0,
                    "message": "No semantic memories configured for this block",
                },
            }

        # Perform search using the semantic memory section's retrieve method
        results = block.semantic_memories.retrieve_memories([query], top_k=limit)

        # Format results
        formatted_results = []
        if results and len(results) > 0:
            for mem in results[0]:  # results is a list of lists
                formatted_results.append(
                    {
                        "content": mem.content,
                        "type": mem.type,
                        "keywords": mem.keywords,
                        "created_at": mem.created_at,
                    }
                )

        return {
            "success": True,
            "data": {
                "block_id": block_id,
                "query": query,
                "results": formatted_results,
                "count": len(formatted_results),
            },
        }
    except Exception as e:
        logger.exception("Failed to search memories for block %s (query=%r)", block_id, query)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search memories: {str(e)}",
        )


@router.get("/{block_id}/stats")
async def get_memory_stats(block_id: str) -> Dict[str, Any]:
    """
    Get statistics about memories in a block.

    Args:
        block_id: Memory block identifier

    Returns:
        Memory statistics
    """
    try:
        # Get counts from database
        core_memory = await mongo_manager.get_core_memory(block_id)

        # Load block for semantic memories
        block = await block_service.load_block(block_id)
        semantic_count = 0
        if block and block.semantic_memories:
            try:
                memories = VectorDBManager.get_all_points(
                    block.semantic_memories.collection_name, limit=10000
                )
                semantic_count = len(memories)
            except:
                semantic_count = 0

        return {
            "success": True,
            "data": {
                "block_id": block_id,
                "has_core_memory": core_memory is not None,
                "semantic_memory_count": semantic_count,
                "stats": {
                    "persona_size": len(core_memory.get("persona_content", ""))
                    if core_memory
                    else 0,
                    "human_size": len(core_memory.get("human_content", ""))
                    if core_memory
                    else 0,
                },
            },
        }
    except Exception as e:
        logger.exception("Failed to retrieve memory stats for block %s", block_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve memory stats: {str(e)}",
        )
