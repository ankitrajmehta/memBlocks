"""
FastMCP server for MemBlocks.

Exposes MemBlocks memory tools to AI agents via stdio MCP protocol.
"""

import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

from fastmcp import FastMCP, Context
from pydantic import BaseModel, Field, ConfigDict

from memblocks import MemBlocksClient, MemBlocksConfig
from mcp_server.state import get_active_block_id, set_active_block_id

# --- Logging setup ---
# MUST log to stderr only. stdout is reserved for MCP stdio protocol.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [memblocks-mcp] %(levelname)s %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


# --- Lifespan — singleton client initialization ---
@asynccontextmanager
async def app_lifespan(server: FastMCP):
    user_id = os.environ.get("MEMBLOCKS_USER_ID", "default_user")
    logger.info(f"Initializing MemBlocksClient for user: {user_id}")
    config = MemBlocksConfig()
    client = MemBlocksClient(config)
    # Ensure user exists
    await client.get_or_create_user(user_id)
    logger.info("MemBlocksClient ready")
    yield {"client": client, "user_id": user_id}
    logger.info("Shutting down MemBlocksClient")
    await client.close()


mcp = FastMCP("memblocks_mcp", lifespan=app_lifespan)


# --- Helper — active block guard ---
def _active_block_id_or_error() -> tuple[str | None, str | None]:
    """Returns (block_id, None) on success or (None, error_message) if not set."""
    block_id = get_active_block_id()
    if not block_id:
        return None, (
            "Error: No active block is set. "
            "Call `memblocks_list_blocks` to see available blocks, "
            "then call `memblocks_set_block` with the desired block ID to activate one."
        )
    return block_id, None


# --- Tool 1 — memblocks_list_blocks ---
@mcp.tool(
    name="memblocks_list_blocks",
    annotations={
        "title": "List Memory Blocks",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def memblocks_list_blocks(ctx: Context) -> str:
    """List all memory blocks for the configured user, flagging which is currently active.

    Returns a JSON array of block objects. Each object includes:
      - id (str): block ID
      - name (str): human-readable block name
      - description (str): optional block description
      - is_active (bool): true if this is the currently active block

    Returns an empty array if the user has no blocks.
    """
    client: MemBlocksClient = ctx.request_context.lifespan_context["client"]
    user_id: str = ctx.request_context.lifespan_context["user_id"]
    active_id = get_active_block_id()

    blocks = await client.get_user_blocks(user_id)
    result = [
        {
            "id": b.id,
            "name": b.name,
            "description": b.description,
            "is_active": b.id == active_id,
        }
        for b in blocks
    ]
    return json.dumps(result, indent=2)


# --- Tool 2 — memblocks_create_block ---
class CreateBlockInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str = Field(
        ...,
        description="Human-readable name for the new block",
        min_length=1,
        max_length=100,
    )
    description: str = Field(
        default="",
        description="Optional description of the block's purpose",
        max_length=500,
    )


@mcp.tool(
    name="memblocks_create_block",
    annotations={
        "title": "Create Memory Block",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def memblocks_create_block(params: CreateBlockInput, ctx: Context) -> str:
    """Create a new memory block for the configured user.

    Creates a block with semantic and core memory collections initialized.
    The new block is NOT automatically set as active — call `memblocks set-block`
    to activate it.

    Returns a JSON object with the created block's details:
      - id (str): new block ID
      - name (str): block name
      - description (str): block description
      - message (str): success confirmation
    """
    client: MemBlocksClient = ctx.request_context.lifespan_context["client"]
    user_id: str = ctx.request_context.lifespan_context["user_id"]

    block = await client.create_block(
        user_id=user_id,
        name=params.name,
        description=params.description,
    )
    result = {
        "id": block.id,
        "name": block.name,
        "description": block.description,
        "message": f"Block '{block.name}' created successfully. Use `memblocks set-block {block.id}` to activate it.",
    }
    return json.dumps(result, indent=2)


# --- Tool 3 — memblocks_set_block ---
class SetBlockInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    block_id: str = Field(
        ...,
        description="ID of the block to activate",
        min_length=1,
    )


@mcp.tool(
    name="memblocks_set_block",
    annotations={
        "title": "Set Active Memory Block",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def memblocks_set_block(params: SetBlockInput, ctx: Context) -> str:
    """Activate a memory block, making it the target for all subsequent memory operations.

    Validates that the block exists and belongs to the configured user before
    activating it. The active block ID is persisted to
    ~/.config/memblocks/active_block.json so the CLI and other tools share state.

    Returns a JSON object with:
      - block_id (str): the newly activated block ID
      - name (str): human-readable block name
      - message (str): confirmation message
    """
    client: MemBlocksClient = ctx.request_context.lifespan_context["client"]
    user_id: str = ctx.request_context.lifespan_context["user_id"]

    block = await client.get_block(params.block_id)
    if block is None:
        return json.dumps(
            {
                "error": f"Block '{params.block_id}' not found. "
                "Call `memblocks_list_blocks` to see available block IDs."
            }
        )
    if block.user_id != user_id:
        return json.dumps(
            {"error": f"Block '{params.block_id}' does not belong to the current user."}
        )

    set_active_block_id(params.block_id)
    logger.info(f"Active block set to: {params.block_id}")

    return json.dumps(
        {
            "block_id": block.id,
            "name": block.name,
            "message": f"Block '{block.name}' ({block.id}) is now active.",
        }
    )


# --- Tool 4 — memblocks_store_semantic ---
class StoreSemanticInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    fact: str = Field(
        ...,
        description="The fact or knowledge to store in semantic memory",
        min_length=1,
    )


@mcp.tool(
    name="memblocks_store_semantic",
    annotations={
        "title": "Store to Semantic Memory",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def memblocks_store_semantic(params: StoreSemanticInput, ctx: Context) -> str:
    """Store a fact or knowledge to semantic memory.

    This tool wraps the input as a user message, then runs it through PS1
    (extraction) and PS2 (conflict resolution) pipelines. Useful for persisting
    facts, learned information, or knowledge that should be retrievable.

    Input:
      - fact (str): Plain text fact or knowledge to store

    Returns a JSON object with:
      - message (str): Success confirmation
      - count (int): Number of semantic memory units stored
      - operations (list): List of operations performed (ADD/UPDATE/DELETE)
    """
    client: MemBlocksClient = ctx.request_context.lifespan_context["client"]

    # Check for active block
    block_id, error = _active_block_id_or_error()
    if error:
        return json.dumps({"error": error})

    # Get the block
    block = await client.get_block(block_id)
    if block is None:
        return json.dumps({"error": f"Block '{block_id}' not found."})

    # Wrap fact as messages for PS1 extraction
    messages = [{"role": "user", "content": params.fact}]

    # PS1: Extract semantic memories
    extracted = await block._semantic.extract(messages)

    # PS2: Store each memory with conflict resolution
    operations = []
    for memory in extracted:
        ops = await block._semantic.store(memory)
        operations.extend(ops)

    return json.dumps(
        {
            "message": "Stored to semantic memory",
            "count": len(extracted),
            "operations": [
                {"type": op.operation_type.value, "memory_id": str(op.memory_id)}
                for op in operations
            ],
        },
        indent=2,
    )


# --- Tool 5 — memblocks_store_to_core ---
class StoreToCoreInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    fact: str = Field(
        ...,
        description="The fact or knowledge to add/update in core memory",
        min_length=1,
    )


@mcp.tool(
    name="memblocks_store_to_core",
    annotations={
        "title": "Store to Core Memory",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def memblocks_store_to_core(params: StoreToCoreInput, ctx: Context) -> str:
    """Store a fact or knowledge to core memory.

    This tool gets the existing core memory, combines it with the new fact
    using the LLM-driven extraction pipeline, and saves the updated core memory.
    Useful for updating persona information, human details, or core knowledge.

    Input:
      - fact (str): Plain text fact or knowledge to add/update in core memory

    Returns a JSON object with:
      - message (str): Success confirmation
      - persona_preview (str): First 100 chars of updated persona content
      - human_preview (str): First 100 chars of updated human content
    """
    client: MemBlocksClient = ctx.request_context.lifespan_context["client"]

    # Check for active block
    block_id, error = _active_block_id_or_error()
    if error:
        return json.dumps({"error": error})

    # Get the block
    block = await client.get_block(block_id)
    if block is None:
        return json.dumps({"error": f"Block '{block_id}' not found."})

    # Determine core_block_id (use dedicated core memory block if exists, otherwise block id)
    core_block_id = block.core_memory_block_id or block.id

    # Get existing core memory
    old_core = await block._core.get(core_block_id)

    # Wrap fact as messages for extraction
    messages = [{"role": "user", "content": params.fact}]

    # Extract new core memory by combining old + new via LLM
    new_core = await block._core.extract(messages, old_core)

    # Save updated core memory
    await block._core.save(core_block_id, new_core)

    return json.dumps(
        {
            "message": "Core memory updated",
            "persona_preview": new_core.persona_content[:100]
            if new_core.persona_content
            else "",
            "human_preview": new_core.human_content[:100]
            if new_core.human_content
            else "",
        },
        indent=2,
    )


# --- Entry point ---
def main() -> None:
    """Entry point for `memblocks-mcp` CLI command."""
    mcp.run()  # stdio transport by default


if __name__ == "__main__":
    main()
