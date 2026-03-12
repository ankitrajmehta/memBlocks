"""
Active block state module.

Reads and writes the active block ID via a shared JSON state file at
~/.config/memblocks/active_block.json.

The CLI writes this file; the MCP server reads it on every tool call (no caching).
Uses only stdlib — no external dependencies.
"""

import json
from pathlib import Path

STATE_FILE = Path.home() / ".config" / "memblocks" / "active_block.json"


def get_active_block_id() -> str | None:
    """Read active block ID from shared state file.

    Returns None if the file does not exist or cannot be parsed.
    Never raises — always returns str or None.
    """
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data.get("block_id")
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def set_active_block_id(block_id: str) -> None:
    """Write active block ID to shared state file.

    Creates parent directories if they do not exist.
    """
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps({"block_id": block_id}),
        encoding="utf-8",
    )
