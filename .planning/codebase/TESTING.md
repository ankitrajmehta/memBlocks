# Testing Patterns

**Analysis Date:** 2026-03-12

## Test Framework

**Framework:** Not formally configured (no pytest.ini, setup.cfg, or pyproject.toml test sections)

**Test Discovery:**
- Manual test discovery via file naming
- Test files located in:
  - `tests/` - Integration tests at workspace root
  - `memblocks_lib/` - Ad-hoc test scripts in library root

**Async Support:**
- Uses Python's `asyncio` for async test functions:
  ```python
  import asyncio
  
  async def run_test():
      # async test code
      pass
  
  if __name__ == "__main__":
      asyncio.run(run_test())
  ```

**Running Tests:**
```bash
# Manual execution
python tests/test_hybrid.py
python memblocks_lib/test_cohere_reranker.py
```

## Test File Organization

**Location:**
- Integration tests: `tests/` directory
- Library tests: `memblocks_lib/` root directory
- Ad-hoc test scripts co-exist with source code

**Naming:**
- Test files: `test_*.py` pattern
- Examples:
  - `tests/test_hybrid.py`
  - `memblocks_lib/test_cohere_reranker.py`

**Structure:**
- No formal test framework structure (no conftest.py, fixtures)
- Scripts use main guard pattern for execution:
  ```python
  if __name__ == "__main__":
      asyncio.run(test_function())
  ```

## Test Structure

**Pattern from `tests/test_hybrid.py`:**
```python
import asyncio
import os
import sys

os.environ["PYTHONIOENCODING"] = "utf-8"

from datetime import datetime
from memblocks.client import MemBlocksClient
from memblocks.config import MemBlocksConfig
from memblocks.models.units import SemanticMemoryUnit, MemoryUnitMetaData


async def run_test():
    print("Initializing Config and Client...")
    config = MemBlocksConfig()
    client = MemBlocksClient(config)

    # Test setup
    user = await client.get_or_create_user("test_hybrid_user")
    block = await client.create_block(
        user_id="test_hybrid_user", name="BM25 Hybrid Test Block"
    )

    # Store test memories
    memories = [
        SemanticMemoryUnit(
            content="The user has a meeting in San Francisco...",
            type="event",
            source="conversation",
            confidence=1.0,
            # ... more fields
        ),
    ]
    for mem in memories:
        await block._semantic.store(mem)

    # Run test
    context = await block.retrieve("Tell me about the app in San Francisco?")

    # Assertions
    for mem in context.semantic:
        print(f"- {mem.content}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(run_test())
```

**Pattern from `memblocks_lib/test_cohere_reranker.py`:**
```python
async def test_cohere_reranker():
    """Test the CohereReranker with sample memories."""
    
    # Create sample memories
    memories = [
        SemanticMemoryUnit(
            memory_id="1",
            content="User prefers Python for data science...",
            # ... more fields
        ),
    ]

    # Test query
    query = "What programming languages does the user prefer?"

    try:
        # Initialize and test
        config = MemBlocksConfig()
        reranker = CohereReranker(config=config)
        
        # Test re-ranking
        reranked_memories = await reranker.rerank(
            query=query,
            memories=memories,
            top_n=3
        )
        
        print(f"Got {len(reranked_memories)} results")
        
    except ImportError as e:
        print(f"Import Error: {e}")
    except ValueError as e:
        print(f"Configuration Error: {e}")
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_cohere_reranker())
```

## Mocking

**Approach:**
- No mocking framework detected (no pytest-mock, unittest.mock extensively used)
- Tests use real integrations with actual services (MongoDB, Qdrant, LLM providers)
- Integration tests require actual database connections

**When Mocking Would Help:**
- `tests/test_hybrid.py` - requires MongoDB and Qdrant running
- `test_cohere_reranker.py` - requires Cohere API key
- Tests access internal attributes (e.g., `block._semantic.store(mem)`)

**Recommendations:**
- Add `pytest` and `pytest-asyncio` for test runner
- Add `unittest.mock` or `pytest-mock` for unit testing
- Use dependency injection pattern (already present in `MemBlocksClient`) to swap adapters:
  ```python
  client = MemBlocksClient(
      config,
      mongo_adapter=mock_mongo_adapter,
      qdrant_adapter=mock_qdrant_adapter,
      embedding_provider=mock_embeddings,
  )
  ```

## Fixtures and Factories

**Test Data:**
- Inline fixture creation in test files
- No centralized fixture management
- Example pattern:
  ```python
  memories = [
      SemanticMemoryUnit(
          content="The user has a meeting in San Francisco...",
          type="event",
          source="conversation",
          confidence=1.0,
          memory_time=datetime.utcnow().isoformat(),
          updated_at=datetime.utcnow().isoformat(),
          keywords=["san", "francisco", "app", "delivery"],
          entities=["san francisco", "app", "delivery"],
          embedding_text="...",
          meta_data=MemoryUnitMetaData(
              usage=[], status="active", message_ids=[]
          ),
      ),
  ]
  ```

**Factory Pattern:**
- Use Pydantic models as factories:
  ```python
  config = MemBlocksConfig()  # reads from .env
  client = MemBlocksClient(config)
  ```

## Test Types

**Integration Tests:**
- Primary test type used
- Test end-to-end flows with real services
- Located in `tests/` directory
- Examples:
  - Hybrid retrieval (BM25 + semantic)
  - Cohere re-ranker integration

**Unit Tests:**
- Not currently implemented
- Missing from codebase

**E2E Tests:**
- Not detected in Python codebase
- Frontend may have separate E2E setup

## Coverage

**Requirements:** None enforced

**View Coverage:** Not configured

**Recommendations:**
- Add `pytest-cov` for coverage reporting
- Configure coverage targets for critical paths:
  - `memblocks_lib/src/memblocks/services/` - core business logic
  - `memblocks_lib/src/memblocks/models/` - data validation

## Common Patterns

**Async Testing:**
```python
import asyncio

async def test_function():
    # setup
    result = await async_operation()
    # assert
    assert result is not None
    # cleanup
    await cleanup()

asyncio.run(test_function())
```

**Error Testing:**
```python
try:
    # operation that might fail
    await operation()
except ImportError as e:
    print(f"Import Error: {e}")
except ValueError as e:
    print(f"Configuration Error: {e}")
except Exception as e:
    print(f"Test failed: {e}")
    import traceback
    traceback.print_exc()
```

**Event Subscription Testing:**
```python
def log_retrieval(payload):
    print(f"Retrieved {payload['num_results']} memories")

client.subscribe("on_memory_retrieval", log_retrieval)
# ... run operation
client.unsubscribe("on_memory_retrieval", log_retrieval)
```

## Test Recommendations

**Immediate Actions:**
1. Add `pytest` and `pytest-asyncio` to dependencies
2. Create `pytest.ini` or configure in `pyproject.toml`:
   ```toml
   [tool.pytest.ini_options]
   asyncio_mode = "auto"
   testpaths = ["tests", "memblocks_lib"]
   ```
3. Add `pytest-mock` for unit testing

**Structure:**
- Move integration tests to `tests/` with proper pytest functions
- Add unit tests alongside source files using `pytest` discovery
- Create `conftest.py` for shared fixtures

**Critical Paths to Test:**
- `MemBlocksClient` initialization and wiring
- `BlockManager.create_block()`, `get_block()`, `delete_block()`
- `SemanticMemoryService.store()`, `retrieve()`
- `CoreMemoryService` operations
- API route handlers in `backend/src/api/routers/`

---

*Testing analysis: 2026-03-12*
