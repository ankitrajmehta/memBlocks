"""Test scaffold for Phase 4 CLI resources.

Wave 0: Tests for set-block and get-block CLI commands.
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

        monkeypatch.setattr(sys, "argv", ["memblocks", "--help"])

        with pytest.raises(SystemExit):
            cli.main()

        captured = capsys.readouterr()
        assert "set-block" in captured.out
        assert "get-block" in captured.out
