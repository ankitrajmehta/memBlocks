"""
FastMCP server for MemBlocks.

Exposes MemBlocks memory tools to AI agents via stdio MCP protocol.
"""

import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP, Context
from pydantic import BaseModel, Field, ConfigDict

from memblocks import MemBlocksClient, MemBlocksConfig
from memblocks.llm.task_settings import LLMSettings, LLMTaskSettings
from mcp_server.state import get_active_block_id, set_active_block_id

# --- Logging setup ---
# stdout is reserved for MCP stdio protocol — all logging goes to stderr + file.
LOG_DIR = Path("memblocks_mcp_logs")
LOG_DIR.mkdir(exist_ok=True)


class FlushingFileHandler(logging.FileHandler):
    """FileHandler that flushes to disk after every emitted record."""

    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        self.flush()


def setup_logging() -> None:
    fmt = "%(asctime)s [%(name)s] %(levelname)s %(message)s"

    # Root logger - only server logs go here
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    # stderr handler (MCP host may surface this)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(logging.Formatter(fmt))
    stderr_handler.addFilter(lambda r: not r.name.startswith("memblocks"))
    root.addHandler(stderr_handler)

    # mcp_server.log - server + MCP framework logs
    server_file = FlushingFileHandler(LOG_DIR / "mcp_server.log")
    server_file.setFormatter(logging.Formatter(fmt))
    server_file.addFilter(lambda r: not r.name.startswith("memblocks"))
    root.addHandler(server_file)

    # memblocks library — dedicated file for deep inspection
    mb_logger = logging.getLogger("memblocks")
    mb_logger.setLevel(logging.DEBUG)
    mb_logger.handlers.clear()
    mb_file = FlushingFileHandler(LOG_DIR / "memblocks.log")
    mb_file.setFormatter(logging.Formatter(fmt))
    mb_logger.addHandler(mb_file)

    # Suppress noisy third-party loggers
    for name in ("httpx", "httpcore", "groq", "pymongo", "urllib3", "openinference"):
        logging.getLogger(name).setLevel(logging.WARNING)


setup_logging()
logger = logging.getLogger(__name__)
logger.info(f"MCP server starting — logs at {LOG_DIR.absolute()}")


# --- Lifespan — singleton client initialization ---
@asynccontextmanager
async def app_lifespan(server: FastMCP):
    user_id = os.environ.get("MEMBLOCKS_USER_ID", "default_user")
    logger.info(f"Initializing MemBlocksClient for user: {user_id}")
    config = MemBlocksConfig(
        llm_settings=LLMSettings(
            default=LLMTaskSettings(
                provider="groq", model="moonshotai/kimi-k2-instruct-0905"
            ),
            retrieval=LLMTaskSettings(provider="groq", model="openai/gpt-oss-20b"),
            ps1_semantic_extraction=LLMTaskSettings(
                provider="groq", model="openai/gpt-oss-120b"
            ),
            ps2_conflict_resolution=LLMTaskSettings(
                provider="groq", model="moonshotai/kimi-k2-instruct-0905"
            ),
            core_memory_extraction=LLMTaskSettings(
                provider="groq", model="openai/gpt-oss-120b"
            ),
            recursive_summary=LLMTaskSettings(
                provider="groq", model="openai/gpt-oss-120b"
            ),
        )
    )
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
    logger.info("memblocks_list_blocks: called")
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
    logger.info(
        f"memblocks_list_blocks: returning {len(result)} block(s), active_id={active_id}"
    )
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
    logger.info(f"memblocks_create_block: name={params.name!r}")
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
    logger.info(f"memblocks_create_block: created block id={block.id}")
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
    logger.info(f"memblocks_set_block: block_id={params.block_id!r}")
    client: MemBlocksClient = ctx.request_context.lifespan_context["client"]
    user_id: str = ctx.request_context.lifespan_context["user_id"]

    block = await client.get_block(params.block_id)
    if block is None:
        logger.warning(f"memblocks_set_block: block not found: {params.block_id}")
        return json.dumps(
            {
                "error": f"Block '{params.block_id}' not found. "
                "Call `memblocks_list_blocks` to see available block IDs."
            }
        )
    if block.user_id != user_id:
        logger.warning(
            f"memblocks_set_block: block {params.block_id} belongs to {block.user_id}, not {user_id}"
        )
        return json.dumps(
            {"error": f"Block '{params.block_id}' does not belong to the current user."}
        )

    set_active_block_id(params.block_id)
    logger.info(f"memblocks_set_block: active block set to {params.block_id}")

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
    logger.info(f"memblocks_store_semantic: fact={params.fact[:80]!r}")
    client: MemBlocksClient = ctx.request_context.lifespan_context["client"]

    # Check for active block
    block_id, error = _active_block_id_or_error()
    if error:
        logger.warning(f"memblocks_store_semantic: no active block — {error}")
        return json.dumps({"error": error})

    # Get the block
    block = await client.get_block(block_id)
    if block is None:
        logger.warning(f"memblocks_store_semantic: block not found: {block_id}")
        return json.dumps({"error": f"Block '{block_id}' not found."})

    # Wrap fact as messages for PS1 extraction
    messages = [{"role": "user", "content": params.fact}]

    # PS1: Extract semantic memories
    logger.debug("memblocks_store_semantic: running PS1 extraction")
    extracted = await block._semantic.extract(messages)
    logger.info(f"memblocks_store_semantic: PS1 extracted {len(extracted)} memories")

    # PS2: Store each memory with conflict resolution
    operations = []
    for i, memory in enumerate(extracted):
        logger.debug(
            f"memblocks_store_semantic: PS2 storing memory {i + 1}/{len(extracted)}: {str(memory)[:80]}"
        )
        ops = await block._semantic.store(memory)
        logger.info(
            f"memblocks_store_semantic: PS2 operations for memory {i + 1}: {[op.operation for op in ops]}"
        )
        operations.extend(ops)

    result = {
        "message": "Stored to semantic memory",
        "count": len(extracted),
        "operations": [
            {"type": op.operation, "memory_id": str(op.memory_id)} for op in operations
        ],
    }
    logger.info(
        f"memblocks_store_semantic: done — {len(extracted)} extracted, {len(operations)} operations"
    )
    return json.dumps(result, indent=2)


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
    logger.info(f"memblocks_store_to_core: fact={params.fact[:80]!r}")
    client: MemBlocksClient = ctx.request_context.lifespan_context["client"]

    # Check for active block
    block_id, error = _active_block_id_or_error()
    if error:
        logger.warning(f"memblocks_store_to_core: no active block — {error}")
        return json.dumps({"error": error})

    # Get the block
    block = await client.get_block(block_id)
    if block is None:
        logger.warning(f"memblocks_store_to_core: block not found: {block_id}")
        return json.dumps({"error": f"Block '{block_id}' not found."})

    # Determine core_block_id
    core_block_id = block.core_memory_block_id or block.id
    logger.debug(f"memblocks_store_to_core: core_block_id={core_block_id}")

    # Get existing core memory
    old_core = await block._core.get(core_block_id)
    logger.debug(
        f"memblocks_store_to_core: old_core persona={str(old_core.persona_content)[:60] if old_core else None}"
    )

    # Wrap fact as messages for extraction
    messages = [{"role": "user", "content": params.fact}]

    # Extract new core memory by combining old + new via LLM
    logger.debug("memblocks_store_to_core: running core extraction LLM")
    new_core = await block._core.extract(messages, old_core)
    logger.info(
        f"memblocks_store_to_core: extraction done — persona={str(new_core.persona_content)[:60]!r}"
    )

    # Save updated core memory
    await block._core.save(core_block_id, new_core)
    logger.info("memblocks_store_to_core: core memory saved")

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


# --- Tool 6 — memblocks_store (STOR-03) ---
class StoreInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    fact: str = Field(
        ...,
        description="The fact or knowledge to store in both semantic and core memory",
        min_length=1,
    )


@mcp.tool(
    name="memblocks_store",
    annotations={
        "title": "Store to Both Memories",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def memblocks_store(params: StoreInput, ctx: Context) -> str:
    """Store a fact or knowledge to both semantic and core memory in a single call.

    This is a convenience tool that runs both the semantic storage pipeline
    (PS1 extraction + PS2 conflict resolution) and the core memory update
    pipeline (LLM extraction + save) sequentially. Use this when you want
    to persist a fact to both memory systems without making two separate calls.

    Input:
      - fact (str): Plain text fact or knowledge to store

    Returns a JSON object with:
      - message (str): Success confirmation
      - semantic (dict): Results from semantic storage (count, operations)
      - core (dict): Results from core memory update (updated, previews)
    """
    logger.info(f"memblocks_store: fact={params.fact[:80]!r}")
    client: MemBlocksClient = ctx.request_context.lifespan_context["client"]

    # Check for active block
    block_id, error = _active_block_id_or_error()
    if error:
        logger.warning(f"memblocks_store: no active block — {error}")
        return json.dumps({"error": error})

    # Get the block
    block = await client.get_block(block_id)
    if block is None:
        logger.warning(f"memblocks_store: block not found: {block_id}")
        return json.dumps({"error": f"Block '{block_id}' not found."})

    # Wrap fact as messages for both extractions
    messages = [{"role": "user", "content": params.fact}]

    # === Semantic Pipeline (PS1 + PS2) ===
    logger.debug("memblocks_store: running PS1 extraction")
    extracted = await block._semantic.extract(messages)
    logger.info(f"memblocks_store: PS1 extracted {len(extracted)} memories")

    semantic_operations = []
    for i, memory in enumerate(extracted):
        logger.debug(f"memblocks_store: PS2 storing memory {i + 1}/{len(extracted)}")
        ops = await block._semantic.store(memory)
        logger.info(
            f"memblocks_store: PS2 operations for memory {i + 1}: {[op.operation for op in ops]}"
        )
        semantic_operations.extend(ops)

    # === Core Pipeline ===
    core_block_id = block.core_memory_block_id or block.id
    logger.debug(f"memblocks_store: core_block_id={core_block_id}")

    old_core = await block._core.get(core_block_id)
    logger.debug("memblocks_store: running core extraction LLM")
    new_core = await block._core.extract(messages, old_core)
    logger.info(
        f"memblocks_store: core extraction done — persona={str(new_core.persona_content)[:60]!r}"
    )

    await block._core.save(core_block_id, new_core)
    logger.info("memblocks_store: core memory saved")

    result = {
        "message": "Stored to both semantic and core memory",
        "semantic": {
            "count": len(extracted),
            "operations": [
                {"type": op.operation, "memory_id": str(op.memory_id)}
                for op in semantic_operations
            ],
        },
        "core": {
            "updated": True,
            "persona_preview": new_core.persona_content[:100]
            if new_core.persona_content
            else "",
            "human_preview": new_core.human_content[:100]
            if new_core.human_content
            else "",
        },
    }
    logger.info(
        f"memblocks_store: done — semantic_ops={len(semantic_operations)}, core_updated=True"
    )
    return json.dumps(result, indent=2)


# --- Tool 7 — memblocks_retrieve (RETR-01) ---
class RetrieveInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    query: str = Field(
        ...,
        description="The query string to search semantic memory for",
        min_length=1,
    )


@mcp.tool(
    name="memblocks_retrieve",
    annotations={
        "title": "Retrieve from Memory",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def memblocks_retrieve(params: RetrieveInput, ctx: Context) -> str:
    """Retrieve memories from the active block using semantic search.

    This tool performs a combined retrieval from both core memory (full content)
    and semantic memory (vector search). Returns formatted context ready for
    LLM injection.

    Input:
      - query (str): Search query for semantic memory retrieval

    Returns a string formatted for LLM injection, containing:
      - Core memory (persona + stable human facts)
      - Semantically relevant memories matching the query
    """
    logger.info(f"memblocks_retrieve: query={params.query[:80]!r}")
    client: MemBlocksClient = ctx.request_context.lifespan_context["client"]

    # Check for active block
    block_id, error = _active_block_id_or_error()
    if error:
        logger.warning(f"memblocks_retrieve: no active block — {error}")
        return json.dumps({"error": error})

    # Get the block
    block = await client.get_block(block_id)
    if block is None:
        logger.warning(f"memblocks_retrieve: block not found: {block_id}")
        return json.dumps({"error": f"Block '{block_id}' not found."})

    # Combined retrieval (core + semantic)
    result = await block.retrieve(params.query)
    logger.info(
        f"memblocks_retrieve: done — core={result.core is not None}, semantic={len(result.semantic)}"
    )
    return result.to_prompt_string()


# --- Tool 8 — memblocks_retrieve_core (RETR-02) ---
@mcp.tool(
    name="memblocks_retrieve_core",
    annotations={
        "title": "Retrieve Core Memory Only",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def memblocks_retrieve_core(ctx: Context) -> str:
    """Retrieve only the core memory from the active block.

    Core memory contains persona (AI's perspective on the human) and stable
    human facts. This returns the full core memory contents regardless of any
    query - useful when you need the complete context about the human.

    Returns a string containing the full core memory, formatted for LLM injection.
    No input parameters needed.
    """
    logger.info("memblocks_retrieve_core: called")
    client: MemBlocksClient = ctx.request_context.lifespan_context["client"]

    # Check for active block
    block_id, error = _active_block_id_or_error()
    if error:
        logger.warning(f"memblocks_retrieve_core: no active block — {error}")
        return json.dumps({"error": error})

    # Get the block
    block = await client.get_block(block_id)
    if block is None:
        logger.warning(f"memblocks_retrieve_core: block not found: {block_id}")
        return json.dumps({"error": f"Block '{block_id}' not found."})

    # Core-only retrieval (no query needed)
    result = await block.core_retrieve()
    logger.info(f"memblocks_retrieve_core: done — core={result.core is not None}")
    return result.to_prompt_string()


# --- Tool 9 — memblocks_retrieve_semantic (RETR-03) ---
@mcp.tool(
    name="memblocks_retrieve_semantic",
    annotations={
        "title": "Retrieve Semantic Memory Only",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def memblocks_retrieve_semantic(params: RetrieveInput, ctx: Context) -> str:
    """Retrieve only semantic memories from the active block.

    Semantic memory contains facts, knowledge, and learned information retrieved
    via vector search. This excludes core memory - useful when you only need
    facts/knowledge without persona or human context.

    Input:
      - query (str): Search query for semantic memory retrieval

    Returns a string containing only semantically relevant memories, formatted
    for LLM injection.
    """
    logger.info(f"memblocks_retrieve_semantic: query={params.query[:80]!r}")
    client: MemBlocksClient = ctx.request_context.lifespan_context["client"]

    # Check for active block
    block_id, error = _active_block_id_or_error()
    if error:
        logger.warning(f"memblocks_retrieve_semantic: no active block — {error}")
        return json.dumps({"error": error})

    # Get the block
    block = await client.get_block(block_id)
    if block is None:
        logger.warning(f"memblocks_retrieve_semantic: block not found: {block_id}")
        return json.dumps({"error": f"Block '{block_id}' not found."})

    # Semantic-only retrieval
    result = await block.semantic_retrieve(params.query)
    logger.info(f"memblocks_retrieve_semantic: done — semantic={len(result.semantic)}")
    return result.to_prompt_string()


# --- Entry point ---
def main() -> None:
    """Entry point for `memblocks-mcp` CLI command."""
    mcp.run()  # stdio transport by default


if __name__ == "__main__":
    main()
