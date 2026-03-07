"""Memory router — core memory and semantic memory search endpoints."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException

from backend.src.api.dependencies import get_client
from backend.src.api.models.requests import (
    SearchMemoriesRequest,
    UpdateCoreMemoryRequest,
)
from backend.src.api.routers.auth import CurrentUser, get_current_user
from memblocks import MemBlocksClient
from memblocks.models.units import CoreMemoryUnit, SemanticMemoryUnit

router = APIRouter(prefix="/memory", tags=["memory"])


async def _get_block_with_auth(
    block_id: str,
    current_user: CurrentUser,
    client: MemBlocksClient,
):
    """Helper to get block and verify ownership."""
    block = await client.get_block(block_id)
    if not block:
        raise HTTPException(status_code=404, detail=f"Block '{block_id}' not found")
    if block.user_id != current_user.user_id:
        raise HTTPException(
            status_code=403,
            detail="Cannot access another user's block",
        )
    return block


# ---- Core Memory ----


@router.get("/core/{block_id}", response_model=Dict[str, Any])
async def get_core_memory(
    block_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    client: MemBlocksClient = Depends(get_client),
) -> Dict[str, Any]:
    """Retrieve the core memory (persona + human facts) for a block."""
    block = await _get_block_with_auth(block_id, current_user, client)
    core = await client._core.get(block.core_memory_block_id or block_id)
    if not core:
        raise HTTPException(
            status_code=404, detail=f"Core memory for block '{block_id}' not found"
        )
    return core.model_dump()


@router.patch("/core/{block_id}", response_model=Dict[str, Any])
async def update_core_memory(
    block_id: str,
    body: UpdateCoreMemoryRequest,
    current_user: CurrentUser = Depends(get_current_user),
    client: MemBlocksClient = Depends(get_client),
) -> Dict[str, Any]:
    """Partially update the core memory for a block.

    Only the provided fields (persona_content, human_content) are updated;
    omitted fields are left unchanged.
    """
    block = await _get_block_with_auth(block_id, current_user, client)
    core = await client._core.get(block.core_memory_block_id or block_id)
    if not core:
        raise HTTPException(
            status_code=404, detail=f"Core memory for block '{block_id}' not found"
        )

    persona = (
        body.persona_content
        if body.persona_content is not None
        else core.persona_content
    )
    human = body.human_content if body.human_content is not None else core.human_content

    updated = await client._core.save(
        block_id=block.core_memory_block_id or block_id,
        memory_unit=CoreMemoryUnit(persona_content=persona, human_content=human),
    )
    return {"persona_content": persona, "human_content": human}


# ---- Semantic Memory ----


@router.post("/semantic/{block_id}/search", response_model=List[Dict[str, Any]])
async def search_semantic_memories(
    block_id: str,
    body: SearchMemoriesRequest,
    current_user: CurrentUser = Depends(get_current_user),
    client: MemBlocksClient = Depends(get_client),
) -> List[Dict[str, Any]]:
    """Search semantic memories in a block's Qdrant collection.

    Returns a flat list of SemanticMemoryUnit dicts ordered by relevance.
    """
    block = await _get_block_with_auth(block_id, current_user, client)

    block._top_k = body.top_k
    results = await block.semantic_retrieve(body.query)
    return [mem.model_dump() for mem in results.semantic]
