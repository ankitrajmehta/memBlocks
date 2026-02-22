"""Memory router — core memory and semantic memory search endpoints."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException

from backend.src.api.dependencies import get_client
from backend.src.api.models.requests import (
    SearchMemoriesRequest,
    UpdateCoreMemoryRequest,
)
from memblocks import MemBlocksClient

router = APIRouter(prefix="/memory", tags=["memory"])


# ---- Core Memory ----


@router.get("/core/{block_id}", response_model=Dict[str, Any])
async def get_core_memory(
    block_id: str,
    client: MemBlocksClient = Depends(get_client),
) -> Dict[str, Any]:
    """Retrieve the core memory (persona + human facts) for a block."""
    core = await client.core.get(block_id)
    if not core:
        raise HTTPException(
            status_code=404, detail=f"Core memory for block '{block_id}' not found"
        )
    return core.model_dump()


@router.patch("/core/{block_id}", response_model=Dict[str, Any])
async def update_core_memory(
    block_id: str,
    body: UpdateCoreMemoryRequest,
    client: MemBlocksClient = Depends(get_client),
) -> Dict[str, Any]:
    """Partially update the core memory for a block.

    Only the provided fields (persona_content, human_content) are updated;
    omitted fields are left unchanged.
    """
    core = await client.core.get(block_id)
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

    updated = await client.core.update(
        block_id=block_id,
        persona_content=persona,
        human_content=human,
    )
    return updated.model_dump()


# ---- Semantic Memory ----


@router.post("/semantic/{block_id}/search", response_model=List[Dict[str, Any]])
async def search_semantic_memories(
    block_id: str,
    body: SearchMemoriesRequest,
    client: MemBlocksClient = Depends(get_client),
) -> List[Dict[str, Any]]:
    """Search semantic memories in a block's Qdrant collection.

    Returns a flat list of SemanticMemoryUnit dicts ordered by relevance.
    """
    block = await client.blocks.get_block(block_id)
    if not block:
        raise HTTPException(status_code=404, detail=f"Block '{block_id}' not found")

    engine = client.get_chat_engine(block)
    results_grouped = engine.chat._semantic.retrieve(
        query_texts=[body.query],
        top_k=body.top_k,
    )
    flat: List[Dict[str, Any]] = [
        mem.model_dump() for group in results_grouped for mem in group
    ]
    return flat
