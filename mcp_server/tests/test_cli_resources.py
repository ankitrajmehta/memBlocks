"""Tests for Phase 4 CLI resources.

Covers: set-block, get-block, list-blocks, lock, unlock CLI commands,
and the MCP lock guard on create_block / set_block server tools.
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest


# Test the state layer functions directly (they already exist)


class TestStateLayer:
    """Test the state.py functions."""

    def test_set_and_get_block_id(self, tmp_path):
        """Test: set_active_block_id writes state, get_active_block_id returns it."""
        from mcp_server import state

        # Monkeypatch STATE_FILE to tmp location
        original_state_file = state.STATE_FILE
        state.STATE_FILE = tmp_path / "active_block.json"

        try:
            state.set_active_block_id("abc123")
            result = state.get_active_block_id()
            assert result == "abc123"
        finally:
            state.STATE_FILE = original_state_file

    def test_get_block_id_returns_none_when_file_missing(self, tmp_path):
        """Test: get_active_block_id returns None when STATE_FILE does not exist."""
        from mcp_server import state

        original_state_file = state.STATE_FILE
        state.STATE_FILE = tmp_path / "nonexistent.json"

        try:
            result = state.get_active_block_id()
            assert result is None
        finally:
            state.STATE_FILE = original_state_file


# CLI tests - now with cli.py implemented


class TestCLISetBlock:
    """Test CLI set-block command."""

    def test_set_block_writes_state_and_exits_zero(self, tmp_path, monkeypatch):
        """Test: CLI set-block <block_id> writes state and exits 0."""
        from mcp_server import state, cli

        original_state_file = state.STATE_FILE
        state.STATE_FILE = tmp_path / "active_block.json"

        try:
            # Capture exit code
            exit_code = None
            monkeypatch.setattr(sys, "argv", ["memblocks", "set-block", "abc123"])

            try:
                cli.main()
            except SystemExit as e:
                exit_code = e.code

            assert exit_code == 0
            # Verify state file was written
            assert state.get_active_block_id() == "abc123"
        finally:
            state.STATE_FILE = original_state_file

    def test_set_block_no_block_id_prints_usage_error(self, tmp_path, monkeypatch):
        """Test: CLI set-block with no block_id prints usage error and exits 1."""
        from mcp_server import state, cli

        original_state_file = state.STATE_FILE
        state.STATE_FILE = tmp_path / "active_block.json"

        try:
            monkeypatch.setattr(sys, "argv", ["memblocks", "set-block"])

            with pytest.raises(SystemExit) as exc_info:
                cli.main()

            assert exc_info.value.code in (1, 2)  # argparse returns 2 for errors
        finally:
            state.STATE_FILE = original_state_file


class TestCLIGetBlock:
    """Test CLI get-block command."""

    def test_get_block_prints_active_block(self, tmp_path, capsys, monkeypatch):
        """Test: CLI get-block prints 'Active block: {block_id}' when state is set."""
        from mcp_server import state, cli

        original_state_file = state.STATE_FILE
        state.STATE_FILE = tmp_path / "active_block.json"

        try:
            # First set a block
            state.set_active_block_id("xyz789")

            # Now run get-block - expect sys.exit(0)
            monkeypatch.setattr(sys, "argv", ["memblocks", "get-block"])
            with pytest.raises(SystemExit):
                cli.main()

            captured = capsys.readouterr()
            assert "Active block: xyz789" in captured.out
        finally:
            state.STATE_FILE = original_state_file

    def test_get_block_prints_no_block_when_empty(self, tmp_path, capsys, monkeypatch):
        """Test: CLI get-block prints 'No active block set.' when state file is empty."""
        from mcp_server import state, cli

        original_state_file = state.STATE_FILE
        state.STATE_FILE = tmp_path / "nonexistent.json"

        try:
            monkeypatch.setattr(sys, "argv", ["memblocks", "get-block"])
            with pytest.raises(SystemExit):
                cli.main()

            captured = capsys.readouterr()
            assert "No active block set." in captured.out
        finally:
            state.STATE_FILE = original_state_file


class TestCLIHelp:
    """Test CLI help."""

    def test_help_shows_subcommands(self, capsys, monkeypatch):
        """Test: CLI --help shows available subcommands."""
        from mcp_server import cli

        monkeypatch.setattr(sys, "argv", ["memblocks-cli", "--help"])

        with pytest.raises(SystemExit):
            cli.main()

        captured = capsys.readouterr()
        assert "set-block" in captured.out
        assert "get-block" in captured.out
        assert "list-blocks" in captured.out
        assert "lock" in captured.out
        assert "unlock" in captured.out


# ---------------------------------------------------------------------------
# State layer: mcp_lock
# ---------------------------------------------------------------------------


class TestStateMcpLock:
    """Test get_mcp_lock / set_mcp_lock in state.py."""

    def test_lock_defaults_to_false_when_no_file(self, tmp_path):
        from mcp_server import state

        original = state.STATE_FILE
        state.STATE_FILE = tmp_path / "active_block.json"
        try:
            assert state.get_mcp_lock() is False
        finally:
            state.STATE_FILE = original

    def test_set_lock_true_then_get_returns_true(self, tmp_path):
        from mcp_server import state

        original = state.STATE_FILE
        state.STATE_FILE = tmp_path / "active_block.json"
        try:
            state.set_mcp_lock(True)
            assert state.get_mcp_lock() is True
        finally:
            state.STATE_FILE = original

    def test_set_lock_false_then_get_returns_false(self, tmp_path):
        from mcp_server import state

        original = state.STATE_FILE
        state.STATE_FILE = tmp_path / "active_block.json"
        try:
            state.set_mcp_lock(True)
            state.set_mcp_lock(False)
            assert state.get_mcp_lock() is False
        finally:
            state.STATE_FILE = original

    def test_lock_preserves_block_id(self, tmp_path):
        """set_mcp_lock must not clobber an existing block_id."""
        from mcp_server import state

        original = state.STATE_FILE
        state.STATE_FILE = tmp_path / "active_block.json"
        try:
            state.set_active_block_id("myblock")
            state.set_mcp_lock(True)
            assert state.get_active_block_id() == "myblock"
            assert state.get_mcp_lock() is True
        finally:
            state.STATE_FILE = original

    def test_set_block_preserves_lock(self, tmp_path):
        """set_active_block_id must not clobber an existing mcp_locked flag."""
        from mcp_server import state

        original = state.STATE_FILE
        state.STATE_FILE = tmp_path / "active_block.json"
        try:
            state.set_mcp_lock(True)
            state.set_active_block_id("myblock")
            assert state.get_mcp_lock() is True
            assert state.get_active_block_id() == "myblock"
        finally:
            state.STATE_FILE = original


# ---------------------------------------------------------------------------
# CLI: lock / unlock commands
# ---------------------------------------------------------------------------


class TestCLILock:
    """Test CLI lock and unlock commands."""

    def test_lock_sets_mcp_lock_true(self, tmp_path, capsys, monkeypatch):
        from mcp_server import state, cli

        original = state.STATE_FILE
        state.STATE_FILE = tmp_path / "active_block.json"
        try:
            monkeypatch.setattr(sys, "argv", ["memblocks-cli", "lock"])
            with pytest.raises(SystemExit) as exc:
                cli.main()
            assert exc.value.code == 0
            assert state.get_mcp_lock() is True
            out = capsys.readouterr().out
            assert "locked" in out.lower()
        finally:
            state.STATE_FILE = original

    def test_unlock_sets_mcp_lock_false(self, tmp_path, capsys, monkeypatch):
        from mcp_server import state, cli

        original = state.STATE_FILE
        state.STATE_FILE = tmp_path / "active_block.json"
        try:
            state.set_mcp_lock(True)
            monkeypatch.setattr(sys, "argv", ["memblocks-cli", "unlock"])
            with pytest.raises(SystemExit) as exc:
                cli.main()
            assert exc.value.code == 0
            assert state.get_mcp_lock() is False
            out = capsys.readouterr().out
            assert "unlocked" in out.lower()
        finally:
            state.STATE_FILE = original


# ---------------------------------------------------------------------------
# Server: lock guard on create_block and set_block
# ---------------------------------------------------------------------------


class TestServerLockGuard:
    """Test that locked state blocks create_block and set_block MCP tools."""

    def test_create_block_blocked_when_locked(self, tmp_path, monkeypatch):
        """memblocks_create_block returns error JSON when MCP is locked."""
        import json
        import asyncio
        from mcp_server import state
        from mcp_server.server import memblocks_create_block, CreateBlockInput

        original = state.STATE_FILE
        state.STATE_FILE = tmp_path / "active_block.json"
        try:
            state.set_mcp_lock(True)

            # Build a minimal fake context (not needed — lock check fires first)
            class FakeCtx:
                pass

            params = CreateBlockInput(name="should-not-be-created")
            result = asyncio.run(memblocks_create_block(params, FakeCtx()))
            data = json.loads(result)
            assert "error" in data
            assert "locked" in data["error"].lower()
        finally:
            state.STATE_FILE = original

    def test_set_block_blocked_when_locked(self, tmp_path, monkeypatch):
        """memblocks_set_block returns error JSON when MCP is locked."""
        import json
        import asyncio
        from mcp_server import state
        from mcp_server.server import memblocks_set_block, SetBlockInput

        original = state.STATE_FILE
        state.STATE_FILE = tmp_path / "active_block.json"
        try:
            state.set_mcp_lock(True)

            class FakeCtx:
                pass

            params = SetBlockInput(block_id="some-block-id")
            result = asyncio.run(memblocks_set_block(params, FakeCtx()))
            data = json.loads(result)
            assert "error" in data
            assert "locked" in data["error"].lower()
        finally:
            state.STATE_FILE = original

    def test_create_block_allowed_when_unlocked(self, tmp_path, monkeypatch):
        """Lock check passes when unlocked — proceeds to client call (may fail without real client)."""
        import asyncio
        from mcp_server import state
        from mcp_server.server import memblocks_create_block, CreateBlockInput

        original = state.STATE_FILE
        state.STATE_FILE = tmp_path / "active_block.json"
        try:
            state.set_mcp_lock(False)

            # Without a real client the call will fail, but it must NOT return a lock error.
            # We verify by checking it raises AttributeError (missing lifespan_context)
            # rather than returning a lock-error JSON.
            class FakeCtx:
                request_context = None

            params = CreateBlockInput(name="test-block")
            with pytest.raises((AttributeError, TypeError)):
                asyncio.run(memblocks_create_block(params, FakeCtx()))
        finally:
            state.STATE_FILE = original
