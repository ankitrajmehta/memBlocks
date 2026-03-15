"""Tests for background-dispatch store tools (non-blocking behavior).

These tests verify that the MCP store tools return immediately with accepted
responses while actual storage runs in background tasks.
"""

import asyncio
import json
from unittest import mock
from unittest.mock import AsyncMock, MagicMock

import pytest


class MockBlock:
    """Mock block for testing background dispatch."""

    def __init__(self, block_id: str = "test-block-id"):
        self.id = block_id
        self.core_memory_block_id = block_id
        self._semantic = MockSemantic()
        self._core = MockCore()


class MockSemantic:
    """Mock semantic memory section."""

    async def extract_and_store(self, messages, ps1_prompt=None, min_confidence=0.0):
        """Simulates slow extraction + storage - should NOT be awaited directly."""
        await asyncio.sleep(10)  # Simulate slow LLM operation
        return [MagicMock()]


class MockCore:
    """Mock core memory section."""

    async def update(self, block_id, messages, core_creation_prompt=None):
        """Simulates slow core update - should NOT be awaited directly."""
        await asyncio.sleep(10)  # Simulate slow LLM operation
        return MagicMock(
            persona_content="updated persona", human_content="updated human"
        )


class FakeContext:
    """Fake FastMCP context for testing."""

    def __init__(self, client, user_id="test-user"):
        self.request_context = MagicMock()
        self.request_context.lifespan_context = {
            "client": client,
            "user_id": user_id,
        }


@pytest.fixture
def mock_state(monkeypatch, tmp_path):
    """Fixture that patches state to use tmp_path."""
    from mcp_server import state

    original_state_file = state.STATE_FILE
    state.STATE_FILE = tmp_path / "active_block.json"

    # Set a test active block
    state.set_active_block_id("test-block-id")

    yield state

    # Restore
    state.STATE_FILE = original_state_file


# ---------------------------------------------------------------------------
# Test 1: memblocks_store_semantic returns immediately
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_store_semantic_returns_immediately(mock_state):
    """memblocks_store_semantic should return within 1 second (not wait for PS1+PS2)."""
    from mcp_server.server import memblocks_store_semantic, StoreSemanticInput

    # Create mock client that returns our mock block
    mock_client = MagicMock()
    mock_block = MockBlock()
    mock_client.get_block = AsyncMock(return_value=mock_block)

    ctx = FakeContext(mock_client)

    # Time the call - should complete quickly
    import time

    start = time.time()
    result = await memblocks_store_semantic(StoreSemanticInput(fact="test fact"), ctx)
    elapsed = time.time() - start

    # Should return within 1 second (immediate response, not slow extraction)
    assert elapsed < 1.0, f"Expected immediate return, took {elapsed:.2f}s"

    # Result should be an accepted response
    data = json.loads(result)
    assert "status" in data
    assert data["status"] == "accepted"


@pytest.mark.asyncio
async def test_store_semantic_dispatches_extract_and_store_in_background(
    mock_state, monkeypatch
):
    """memblocks_store_semantic should dispatch extract_and_store in background task."""
    from mcp_server.server import memblocks_store_semantic, StoreSemanticInput

    # Track if extract_and_store was called
    call_tracker = {"called": False, "messages": None}

    original_extract_and_store = MockSemantic.extract_and_store

    async def tracking_extract_and_store(
        self, messages, ps1_prompt=None, min_confidence=0.0
    ):
        call_tracker["called"] = True
        call_tracker["messages"] = messages
        # Don't await the slow operation - just mark it as called
        return await original_extract_and_store(
            self, messages, ps1_prompt, min_confidence
        )

    # Create mock with tracking
    mock_client = MagicMock()
    mock_block = MockBlock()
    mock_block._semantic = MockSemantic()
    mock_block._semantic.extract_and_store = tracking_extract_and_store.__get__(
        mock_block._semantic, MockSemantic
    )
    mock_client.get_block = AsyncMock(return_value=mock_block)

    ctx = FakeContext(mock_client)

    # Call should return immediately but schedule background work
    result = await memblocks_store_semantic(StoreSemanticInput(fact="test fact"), ctx)

    # Verify the method was called (background dispatch)
    assert call_tracker["called"], "extract_and_store should be called"
    assert call_tracker["messages"] == [{"role": "user", "content": "test fact"}]


# ---------------------------------------------------------------------------
# Test 2: memblocks_store_to_core returns immediately
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_store_to_core_returns_immediately(mock_state):
    """memblocks_store_to_core should return within 1 second (not wait for core update)."""
    from mcp_server.server import memblocks_store_to_core, StoreToCoreInput

    mock_client = MagicMock()
    mock_block = MockBlock()
    mock_client.get_block = AsyncMock(return_value=mock_block)

    ctx = FakeContext(mock_client)

    import time

    start = time.time()
    result = await memblocks_store_to_core(StoreToCoreInput(fact="test fact"), ctx)
    elapsed = time.time() - start

    # Should return within 1 second
    assert elapsed < 1.0, f"Expected immediate return, took {elapsed:.2f}s"

    # Result should be an accepted response
    data = json.loads(result)
    assert "status" in data
    assert data["status"] == "accepted"


@pytest.mark.asyncio
async def test_store_to_core_dispatches_update_in_background(mock_state):
    """memblocks_store_to_core should dispatch block._core.update in background task."""
    from mcp_server.server import memblocks_store_to_core, StoreToCoreInput

    call_tracker = {"called": False, "block_id": None, "messages": None}

    original_update = MockCore.update

    async def tracking_update(self, block_id, messages, core_creation_prompt=None):
        call_tracker["called"] = True
        call_tracker["block_id"] = block_id
        call_tracker["messages"] = messages
        return await original_update(self, block_id, messages, core_creation_prompt)

    mock_client = MagicMock()
    mock_block = MockBlock()
    mock_block._core = MockCore()
    mock_block._core.update = tracking_update.__get__(mock_block._core, MockCore)
    mock_client.get_block = AsyncMock(return_value=mock_block)

    ctx = FakeContext(mock_client)

    result = await memblocks_store_to_core(StoreToCoreInput(fact="test fact"), ctx)

    # Verify update was called
    assert call_tracker["called"], "update should be called"
    assert call_tracker["block_id"] == "test-block-id"
    assert call_tracker["messages"] == [{"role": "user", "content": "test fact"}]


# ---------------------------------------------------------------------------
# Test 3: memblocks_store returns immediately with both paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_store_returns_immediately(mock_state):
    """memblocks_store should return within 1 second (dispatching both semantic + core)."""
    from mcp_server.server import memblocks_store, StoreInput

    mock_client = MagicMock()
    mock_block = MockBlock()
    mock_client.get_block = AsyncMock(return_value=mock_block)

    ctx = FakeContext(mock_client)

    import time

    start = time.time()
    result = await memblocks_store(StoreInput(fact="test fact"), ctx)
    elapsed = time.time() - start

    # Should return within 1 second
    assert elapsed < 1.0, f"Expected immediate return, took {elapsed:.2f}s"

    # Result should be an accepted response
    data = json.loads(result)
    assert "status" in data
    assert data["status"] == "accepted"


@pytest.mark.asyncio
async def test_store_dispatches_both_background_tasks(mock_state):
    """memblocks_store should dispatch both semantic and core background work."""
    from mcp_server.server import memblocks_store, StoreInput

    semantic_called = {"called": False}
    core_called = {"called": False}

    async def tracking_semantic(messages, ps1_prompt=None, min_confidence=0.0):
        semantic_called["called"] = True
        return await MockSemantic.extract_and_store(
            MockSemantic(), messages, ps1_prompt, min_confidence
        )

    async def tracking_core(block_id, messages, core_creation_prompt=None):
        core_called["called"] = True
        return await MockCore.update(
            MockCore(), block_id, messages, core_creation_prompt
        )

    mock_client = MagicMock()
    mock_block = MockBlock()
    mock_block._semantic = MockSemantic()
    mock_block._semantic.extract_and_store = tracking_semantic
    mock_block._core = MockCore()
    mock_block._core.update = tracking_core
    mock_client.get_block = AsyncMock(return_value=mock_block)

    ctx = FakeContext(mock_client)

    result = await memblocks_store(StoreInput(fact="test fact"), ctx)

    # Both should be called in background
    assert semantic_called["called"], "extract_and_store should be called"
    assert core_called["called"], "update should be called"


# ---------------------------------------------------------------------------
# Test 4: Edge case - no active block raises ToolError immediately
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_store_semantic_no_active_block_raises_immediately(monkeypatch, tmp_path):
    """No active block should raise ToolError immediately (no background task scheduled)."""
    from mcp_server import state
    from mcp_server.server import memblocks_store_semantic, StoreSemanticInput

    # Reset state to no active block
    original_state_file = state.STATE_FILE
    state.STATE_FILE = tmp_path / "empty_block.json"

    try:
        # Make sure no block is set
        assert state.get_active_block_id() is None

        mock_client = MagicMock()
        ctx = FakeContext(mock_client)

        # Should raise ToolError immediately, not schedule background work
        from fastmcp.exceptions import ToolError

        with pytest.raises(ToolError) as exc_info:
            await memblocks_store_semantic(StoreSemanticInput(fact="test fact"), ctx)

        assert "No active block" in str(exc_info.value)
    finally:
        state.STATE_FILE = original_state_file
