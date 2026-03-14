---
phase: phase-1
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - mcp_server/__init__.py
  - mcp_server/state.py
  - mcp_server/server.py
  - mcp_server/pyproject.toml
autonomous: true
requirements: [FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05, BLCK-01, BLCK-02]

must_haves:
  truths:
    - "Running `memblocks-mcp` starts the FastMCP server without errors"
    - "Agent connects via stdio and receives a tool list containing `memblocks_list_blocks` and `memblocks_create_block`"
    - "Agent calls `memblocks_list_blocks` and receives all blocks for the configured user, with the active block flagged"
    - "Agent calls `memblocks_create_block` and the new block appears in subsequent list calls"
    - "Any tool call when no active block is set returns a clear descriptive error string — server does not crash"
    - "MEMBLOCKS_USER_ID env var controls which user's blocks are served"
  artifacts:
    - path: "mcp_server/server.py"
      provides: "FastMCP server entry point, lifespan, tool registrations"
      exports: ["mcp", "main"]
    - path: "mcp_server/state.py"
      provides: "Active block state read/write via ~/.config/memblocks/active_block.json"
      exports: ["get_active_block_id", "set_active_block_id"]
    - path: "mcp_server/pyproject.toml"
      provides: "Package config, fastmcp dependency, memblocks-mcp entry point script"
      contains: "memblocks-mcp"
  key_links:
    - from: "mcp_server/server.py lifespan"
      to: "MemBlocksClient"
      via: "ctx.request_context.lifespan_state['client']"
      pattern: "lifespan_state\\[.client.\\]"
    - from: "mcp_server/server.py tools"
      to: "mcp_server/state.py"
      via: "get_active_block_id() on every tool call"
      pattern: "get_active_block_id"
    - from: "mcp_server/pyproject.toml"
      to: "mcp_server/server.py:main"
      via: "[project.scripts] memblocks-mcp entry point"
      pattern: "memblocks-mcp"
---

<objective>
Build the complete Phase 1 MCP server: a new `mcp_server/` package with a FastMCP stdio server, singleton MemBlocksClient initialized at startup via lifespan, shared JSON active-block state, and two block management tools (`memblocks_list_blocks`, `memblocks_create_block`).

Purpose: Establish the foundation agents use to connect to MemBlocks memory. All subsequent phases (store, retrieve, CLI) depend on this working server.
Output: A runnable `memblocks-mcp` command that agents can connect to via stdio.
</objective>

<execution_context>
@C:/Users/Lenovo/.config/opencode/get-shit-done/workflows/execute-plan.md
@C:/Users/Lenovo/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md

<!-- Key source files for reference -->
@memblocks_lib/src/memblocks/client.py
@memblocks_lib/src/memblocks/config.py
@memblocks_lib/src/memblocks/services/block.py
@backend/pyproject.toml
@memblocks_lib/pyproject.toml
@.agents/skills/mcp-builder/reference/python_mcp_server.md

<interfaces>
<!-- Key types and contracts executors need. No codebase exploration required. -->

From memblocks_lib/src/memblocks/client.py:
```python
class MemBlocksClient:
    async def get_or_create_user(self, user_id: str, metadata=None) -> Dict[str, Any]: ...
    async def get_user_blocks(self, user_id: str) -> List[Block]: ...
    async def create_block(self, user_id: str, name: str, description: str = "",
                           create_semantic: bool = True, create_core: bool = True,
                           create_resource: bool = False) -> Block: ...
    async def close(self) -> None: ...
```

From memblocks_lib/src/memblocks/services/block.py:
```python
class Block:
    id: str            # e.g. "block_abc123"
    name: str
    description: str
    user_id: str
    created_at: str    # ISO 8601
    updated_at: str    # ISO 8601
```

From memblocks_lib/src/memblocks/config.py:
```python
class MemBlocksConfig(BaseSettings):
    # Reads ALL config from env vars / .env file automatically
    # No extra args needed for basic instantiation: MemBlocksConfig()
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
```

FastMCP lifespan pattern (from python_mcp_server.md):
```python
from contextlib import asynccontextmanager
from fastmcp import FastMCP, Context

@asynccontextmanager
async def app_lifespan(server: FastMCP):
    client = MemBlocksClient(MemBlocksConfig())
    yield {"client": client}
    await client.close()

mcp = FastMCP("memblocks_mcp", lifespan=app_lifespan)

@mcp.tool()
async def my_tool(ctx: Context) -> str:
    client: MemBlocksClient = ctx.request_context.lifespan_state["client"]
    ...
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Active block state module</name>
  <files>mcp_server/__init__.py, mcp_server/state.py</files>
  <action>
Create `mcp_server/` as a Python package.

**`mcp_server/__init__.py`** — empty (marks it as a package).

**`mcp_server/state.py`** — Shared active-block state via `~/.config/memblocks/active_block.json`.

Implement two functions:

```python
STATE_FILE = Path.home() / ".config" / "memblocks" / "active_block.json"

def get_active_block_id() -> str | None:
    """Read active block ID from shared state file. Returns None if not set."""
    ...

def set_active_block_id(block_id: str) -> None:
    """Write active block ID to shared state file. Creates parent dirs if needed."""
    ...
```

Implementation notes:
- `get_active_block_id`: If file does not exist OR JSON parse fails → return `None`. Read JSON, return `data.get("block_id")`.
- `set_active_block_id`: `STATE_FILE.parent.mkdir(parents=True, exist_ok=True)`, write `{"block_id": block_id}` as JSON.
- NEVER log to stdout — this file has no logging (the MCP server will log to stderr via the logging module).
- Use only stdlib: `json`, `pathlib.Path`.
  </action>
  <verify>
    <automated>cd mcp_server && python -c "from state import get_active_block_id, set_active_block_id; set_active_block_id('test_123'); assert get_active_block_id() == 'test_123'; print('state OK')"</automated>
  </verify>
  <done>
    - `mcp_server/__init__.py` exists
    - `mcp_server/state.py` exports `get_active_block_id` and `set_active_block_id`
    - `get_active_block_id()` returns `None` when file is absent, returns block_id string when file exists
    - `set_active_block_id("x")` writes `{"block_id": "x"}` to `~/.config/memblocks/active_block.json`
  </done>
</task>

<task type="auto">
  <name>Task 2: FastMCP server with singleton client and block tools</name>
  <files>mcp_server/server.py</files>
  <action>
Create the FastMCP MCP server. **CRITICAL: never write to stdout — use `logging` directed to stderr only.**

```python
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

from fastmcp import FastMCP, Context
from pydantic import BaseModel, Field, ConfigDict

from memblocks import MemBlocksClient, MemBlocksConfig
from mcp_server.state import get_active_block_id

# --- Logging setup ---
# MUST log to stderr only. stdout is reserved for MCP stdio protocol.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [memblocks-mcp] %(levelname)s %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)
```

**Lifespan — singleton client initialization:**
```python
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
```

**Helper — active block guard:**
```python
def _active_block_id_or_error() -> tuple[str | None, str | None]:
    """Returns (block_id, None) on success or (None, error_message) if not set."""
    block_id = get_active_block_id()
    if not block_id:
        return None, (
            "Error: No active block is set. "
            "Use `memblocks set-block <block_id>` in the terminal to set one, "
            "or call `memblocks_list_blocks` to see available blocks."
        )
    return block_id, None
```

**Tool 1 — `memblocks_list_blocks`:**
Input model: no required fields.
```python
@mcp.tool(
    name="memblocks_list_blocks",
    annotations={"title": "List Memory Blocks", "readOnlyHint": True,
                 "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
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
    client: MemBlocksClient = ctx.request_context.lifespan_state["client"]
    user_id: str = ctx.request_context.lifespan_state["user_id"]
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
```

**Tool 2 — `memblocks_create_block`:**
```python
class CreateBlockInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str = Field(..., description="Human-readable name for the new block", min_length=1, max_length=100)
    description: str = Field(default="", description="Optional description of the block's purpose", max_length=500)

@mcp.tool(
    name="memblocks_create_block",
    annotations={"title": "Create Memory Block", "readOnlyHint": False,
                 "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}
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
    client: MemBlocksClient = ctx.request_context.lifespan_state["client"]
    user_id: str = ctx.request_context.lifespan_state["user_id"]

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
```

**Entry point:**
```python
def main() -> None:
    """Entry point for `memblocks-mcp` CLI command."""
    mcp.run()  # stdio transport by default

if __name__ == "__main__":
    main()
```

**Important constraints:**
- All `logger.*` calls go to stderr — zero stdout writes.
- `mcp.run()` uses stdio transport by default — do not pass `transport=` unless needed.
- `_active_block_id_or_error()` is defined but Phase 1 tools (list/create) do NOT require an active block — it's available for Phase 2/3 tools. Do NOT call it in list or create.
- The `CreateBlockInput` Pydantic model validates before the function body runs.
  </action>
  <verify>
    <automated>python -c "import py_compile; py_compile.compile('mcp_server/server.py', doraise=True); print('syntax OK')"</automated>
  </verify>
  <done>
    - `mcp_server/server.py` compiles without syntax errors
    - `mcp` is a `FastMCP` instance named `"memblocks_mcp"`
    - Lifespan reads `MEMBLOCKS_USER_ID` env var (falls back to `"default_user"`)
    - `memblocks_list_blocks` tool registered — returns JSON array with `is_active` field
    - `memblocks_create_block` tool registered — accepts `name` + optional `description`, returns JSON object
    - All logging uses `sys.stderr` — no stdout writes outside MCP protocol
    - `main()` function defined as entry point calling `mcp.run()`
  </done>
</task>

<task type="auto">
  <name>Task 3: Package config and entry point registration</name>
  <files>mcp_server/pyproject.toml</files>
  <action>
Create `mcp_server/pyproject.toml` to register `mcp_server` as a UV workspace member and expose `memblocks-mcp` as a runnable CLI command.

```toml
[project]
name = "memblocks-mcp"
version = "0.1.0"
description = "MCP server that exposes MemBlocks memory tools to AI agents via stdio"
requires-python = ">=3.11"
dependencies = [
    "fastmcp>=3.1.0",
    "memblocks",
]

[project.scripts]
memblocks-mcp = "mcp_server.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["mcp_server"]
```

Then add `mcp_server` to the UV workspace by editing the root `pyproject.toml`:

Current root `pyproject.toml` `[tool.uv.workspace]` section:
```toml
[tool.uv.workspace]
members = ["memblocks_lib", "backend"]
```

Update to:
```toml
[tool.uv.workspace]
members = ["memblocks_lib", "backend", "mcp_server"]
```

After editing both files, run:
```bash
uv sync
```

This installs `fastmcp` and registers the `memblocks-mcp` entry point.
  </action>
  <verify>
    <automated>uv run memblocks-mcp --help 2>&1 | head -5 || uv run python -c "from mcp_server.server import mcp; print('import OK', mcp.name)"</automated>
  </verify>
  <done>
    - `mcp_server/pyproject.toml` exists with `fastmcp>=3.1.0` dependency and `memblocks-mcp` script
    - Root `pyproject.toml` lists `mcp_server` in `[tool.uv.workspace] members`
    - `uv sync` completes without errors
    - `uv run memblocks-mcp --help` exits without import errors (may show FastMCP help or just exit 0)
    - `from mcp_server.server import mcp` succeeds
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>
    Complete Phase 1 MCP server:
    - `mcp_server/state.py` — active block state via `~/.config/memblocks/active_block.json`
    - `mcp_server/server.py` — FastMCP stdio server with `memblocks_list_blocks` and `memblocks_create_block` tools
    - `mcp_server/pyproject.toml` — package config with `memblocks-mcp` entry point
    - UV workspace updated and synced
  </what-built>
  <how-to-verify>
    Run this end-to-end smoke test. Requires the `.env` file and running MongoDB + Qdrant:

    ```bash
    # 1. Verify the entry point is registered
    uv run memblocks-mcp --help

    # 2. Test the server starts and exposes tools (pipe a tools/list request)
    echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | \
      MEMBLOCKS_USER_ID=test_user uv run memblocks-mcp 2>/dev/null | \
      python -c "import sys,json; d=json.load(sys.stdin); tools=[t['name'] for t in d['result']['tools']]; print(tools); assert 'memblocks_list_blocks' in tools and 'memblocks_create_block' in tools, 'Missing tools'"

    # 3. Verify list returns JSON (even if empty)
    # Use MCP inspector or the above pipe pattern with a tools/call request

    # 4. Verify no active block → check the helper function returns a clear error:
    uv run python -c "
    from mcp_server.server import _active_block_id_or_error
    from mcp_server.state import STATE_FILE
    import os
    if STATE_FILE.exists(): os.rename(STATE_FILE, str(STATE_FILE) + '.bak')
    bid, err = _active_block_id_or_error()
    print('block_id:', bid)
    print('error:', err)
    assert bid is None
    assert 'No active block' in err
    print('PASS: graceful error when no active block')
    "
    ```

    Expected outcomes:
    - Step 1: Help text or usage shown (no ImportError / ModuleNotFoundError)
    - Step 2: Tool list contains both `memblocks_list_blocks` and `memblocks_create_block`
    - Step 4: `_active_block_id_or_error()` returns `(None, "Error: No active block is set. ...")`
  </how-to-verify>
  <resume-signal>Type "approved" if all checks pass, or describe any failures</resume-signal>
</task>

</tasks>

<verification>
Phase 1 is complete when all five success criteria from ROADMAP.md are true:

1. **Server starts**: `uv run memblocks-mcp` starts without errors (even with a `.env` file present)
2. **Tool list**: `tools/list` MCP call returns both `memblocks_list_blocks` and `memblocks_create_block`
3. **List blocks**: `memblocks_list_blocks` returns a JSON array; each item has `id`, `name`, `description`, `is_active`
4. **Create block**: `memblocks_create_block` creates a block that appears in the next `memblocks_list_blocks` call
5. **Graceful no-active-block**: `_active_block_id_or_error()` returns a clear error string — not an exception

Structural checks:
- `mcp_server/state.py` reads/writes `~/.config/memblocks/active_block.json`
- `mcp_server/server.py` never writes to stdout (all logging → stderr)
- `MEMBLOCKS_USER_ID` env var controls user identity (defaults to `"default_user"`)
- `memblocks-mcp` is registered as a script in `mcp_server/pyproject.toml`
</verification>

<success_criteria>
- [ ] `uv run memblocks-mcp --help` exits without ImportError
- [ ] `from mcp_server.server import mcp, main` imports cleanly
- [ ] `from mcp_server.state import get_active_block_id, set_active_block_id` imports cleanly
- [ ] `mcp.name == "memblocks_mcp"`
- [ ] Tool list includes `memblocks_list_blocks` and `memblocks_create_block`
- [ ] `_active_block_id_or_error()` returns `(None, "Error: No active block is set. ...")` when no state file exists
- [ ] All logging in `server.py` uses `sys.stderr` — zero stdout writes from application code
</success_criteria>

<output>
After completion, create `.planning/phases/phase-1/phase-1-01-SUMMARY.md` with:
- Files created/modified
- Key decisions made during implementation (e.g., FastMCP import path confirmed)
- Any deviations from this plan and why
- Verification results
</output>
