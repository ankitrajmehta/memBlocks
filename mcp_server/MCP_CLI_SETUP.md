# Quick Setup: MCP Server + CLI Agent

This is a fast setup guide for running MemBlocks as an MCP server and connecting it from the OpenCode CLI agent.

## 1) Prerequisites

- Python 3.11+
- `uv` installed
- OpenCode CLI installed on your machine

## 2) Install project dependencies

From the repo root:

```bash
uv sync --all-packages
```

## 3) Install the MemBlocks CLI commands

This project exposes two scripts from `mcp_server/pyproject.toml`:

- `memblocks-mcp` (starts MCP server)
- `memblocks-cli` (manage active block + MCP lock)

Install editable package (recommended):

```bash
uv pip install -e mcp_server
```

Verify:

```bash
memblocks-cli --help
memblocks-mcp --help
```

If your shell cannot find these commands, run through uv:

```bash
uv run memblocks-cli --help
uv run memblocks-mcp
```

## 4) Configure OpenCode MCP (`opencode.json`)

Use this structure (already present in this repo at `opencode.json`):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "memblocks": {
      "type": "local",
      "command": ["uv", "run", "python", "-m", "mcp_server.server"],
      "environment": {
        "MEMBLOCKS_USER_ID": "1234"
      },
      "enabled": true
    }
  }
}
```

Notes:

- `MEMBLOCKS_USER_ID` controls which user context the MCP server uses.
- Change `"1234"` to your actual user ID.
- Keeping `command` as `uv run python -m mcp_server.server` avoids path issues.

## 5) Run and use the CLI agent flow

Start OpenCode with this config, then use the MemBlocks tools from the agent.

Useful terminal commands:

```bash
memblocks-cli whoami
memblocks-cli list-blocks
memblocks-cli set-block <block_id>
memblocks-cli get-block
memblocks-cli lock
memblocks-cli unlock
```

## 6) Shared state file (important)

CLI and MCP share active state through:

`~/.config/memblocks/active_block.json`

This stores values like:

- `user_id`
- `block_id`
- `mcp_locked`

So when you run `memblocks-cli set-block <id>`, the MCP server picks it up on subsequent tool calls.

## 7) Quick smoke test

1. `memblocks-cli list-blocks`
2. `memblocks-cli set-block <real_block_id>`
3. `memblocks-cli get-block` (should show the same ID)
4. In your OpenCode agent session, call a MemBlocks MCP tool (for example list/retrieve) and confirm it operates on that active block.

## 8) Common fixes

- `ModuleNotFoundError: No module named 'mcp_server'`
  - Re-run: `uv pip install -e mcp_server`
  - Then retry: `memblocks-cli --help`
- Command not found for `memblocks-cli`
  - Use `uv run memblocks-cli ...` or ensure your venv scripts path is on `PATH`.
