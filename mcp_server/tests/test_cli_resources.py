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


# CLI tests - cli.py doesn't exist yet, so these are stubs/skip for Wave 0


class TestCLISetBlock:
    """Test CLI set-block command."""

    def test_set_block_writes_state_and_exits_zero(self, tmp_path):
        """Test: CLI set-block <block_id> writes state and exits 0."""
        # cli.py doesn't exist yet - skip until implemented
        pytest.skip("cli.py not yet implemented")

    def test_set_block_no_block_id_prints_usage_error(self, tmp_path):
        """Test: CLI set-block with no block_id prints usage error and exits 1."""
        pytest.skip("cli.py not yet implemented")

    def test_set_block_command_via_subprocess(self, tmp_path):
        """Test: CLI set-block via subprocess.run."""
        pytest.skip("cli.py not yet implemented")


class TestCLIGetBlock:
    """Test CLI get-block command."""

    def test_get_block_prints_active_block(self, tmp_path):
        """Test: CLI get-block prints 'Active block: {block_id}' when state is set."""
        pytest.skip("cli.py not yet implemented")

    def test_get_block_prints_no_block_when_empty(self, tmp_path):
        """Test: CLI get-block prints 'No active block set.' when state file is empty."""
        pytest.skip("cli.py not yet implemented")

    def test_get_block_via_subprocess(self, tmp_path):
        """Test: CLI get-block via subprocess.run."""
        pytest.skip("cli.py not yet implemented")


class TestCLIHelp:
    """Test CLI help."""

    def test_help_shows_subcommands(self, tmp_path):
        """Test: CLI --help shows available subcommands."""
        pytest.skip("cli.py not yet implemented")
