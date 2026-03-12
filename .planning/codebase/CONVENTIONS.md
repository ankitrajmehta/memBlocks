# Coding Conventions

**Analysis Date:** 2026-03-12

## Language & Environment

**Primary Language:**
- Python 3.11+ (required by pyproject.toml)

**Runtime:**
- asyncio for async operations
- FastAPI for backend web services
- MongoDB and Qdrant for data storage

## Naming Patterns

**Files:**
- Python modules: `snake_case.py` (e.g., `block_manager.py`, `semantic_memory.py`)
- API routers: `snake_case.py` (e.g., `blocks.py`, `memory.py`)

**Classes:**
- PascalCase for class names (e.g., `MemBlocksClient`, `BlockManager`, `SemanticMemoryService`)
- Base classes may use `Base` suffix (e.g., `BaseSettings` from Pydantic)

**Functions/Methods:**
- snake_case (e.g., `create_block`, `get_user`, `_make_semantic_service`)
- Private methods prefixed with underscore: `_method_name`

**Variables:**
- snake_case (e.g., `mongo_adapter`, `qdrant_client`, `block_id`)
- Constants: UPPER_SNAKE_CASE for configuration values

**Types:**
- Type hints using Python's `typing` module
- Use `TYPE_CHECKING` guard for circular imports:
  ```python
  from typing import TYPE_CHECKING
  if TYPE_CHECKING:
      from memblocks.config import MemBlocksConfig
  ```

## Code Style

**Formatting:**
- No explicit formatter configuration found (consider adding Ruff or Black)
- Follow PEP 8 guidelines (4-space indentation)

**Linting:**
- Not detected - recommend adding Ruff for Python

**Docstrings:**
- Use triple-quoted docstrings for modules, classes, and public methods
- Google-style docstrings for complex functions:
  ```python
  def create_block(
      self,
      user_id: str,
      name: str,
      description: str = "",
  ) -> "Block":
      """
      Create a new memory block.

      Args:
          user_id: Owner user ID.
          name: Human-readable block name.
          description: Optional description.

      Returns:
          Stateful Block object ready for retrieval.
      """
  ```

## Import Organization

**Order (top to bottom):**
1. Standard library imports
2. Third-party imports (Pydantic, FastAPI, etc.)
3. Local application imports

**Example:**
```python
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from memblocks.models.block import MemoryBlock, MemoryBlockMetaData
from memblocks.services.block import Block
from memblocks.logger import get_logger
```

**Path Aliases:**
- Relative imports within packages (e.g., `from memblocks.services.core_memory import CoreMemoryService`)
- No explicit path aliases configured

## Error Handling

**Patterns:**
- Use `try/except` blocks for operations that may fail
- Raise specific exception types (e.g., `ValueError`, `HTTPException`)
- Include descriptive error messages with context

**Example from `client.py`:**
```python
def _build_provider(
    task_settings: LLMTaskSettings,
    config: MemBlocksConfig,
    usage_tracker: Optional["LLMUsageTracker"] = None,
    call_type: "LLMCallType" = LLMCallType.CONVERSATION,
) -> "LLMProvider":
    provider_name = task_settings.provider

    if provider_name == "groq":
        api_key = config.groq_api_key
        if not api_key:
            raise ValueError("GROQ_API_KEY not set — required for provider 'groq'")
        # ...
    else:
        raise ValueError(
            f"Unknown LLM provider: '{provider_name}'. "
            "Supported providers: 'groq', 'gemini', 'openrouter'."
        )
```

**HTTP Exceptions:**
- FastAPI uses `HTTPException` with status codes:
  ```python
  from fastapi import HTTPException
  
  if not block:
      raise HTTPException(status_code=404, detail=f"Block '{block_id}' not found")
  if block.user_id != current_user.user_id:
      raise HTTPException(
          status_code=403,
          detail="Cannot access another user's block",
      )
  ```

## Logging

**Framework:** Python standard `logging` module

**Pattern:**
```python
from memblocks.logger import get_logger

logger = get_logger(__name__)

logger.debug("Connecting to Qdrant at %s:%s", host, port)
logger.info("Created block %s", block_id)
logger.warning("Arize monitoring disabled — keys not set")
logger.error("Failed to store vector: %s", exc)
```

**Configuration:**
- Application controls root logger setup
- Library uses `NullHandler` to avoid polluting application logs
- Logger hierarchy: `memblocks.<module>` pattern

## Function Design

**Size:**
- Keep functions focused and single-purpose
- Use helper methods for complex logic (e.g., `_make_block`, `_doc_to_block`)

**Parameters:**
- Use type hints for all parameters
- Use default values for optional parameters
- Group related parameters using data classes or Pydantic models

**Return Values:**
- Always include return type hints
- Use Optional for methods that may return None

## Module Design

**Exports:**
- Use `__all__` to explicitly declare public API:
  ```python
  __all__ = ["MemBlocksClient", "MemBlocksConfig"]
  ```

**Barrel Files:**
- Use `__init__.py` to expose public interfaces:
  ```python
  # memblocks/__init__.py
  from memblocks.client import MemBlocksClient
  from memblocks.config import MemBlocksConfig
  
  __all__ = ["MemBlocksClient", "MemBlocksConfig"]
  ```

## Configuration

**Pattern:**
- Use Pydantic `BaseSettings` for environment configuration
- Use `validation_alias` for env var mapping:
  ```python
  from pydantic_settings import BaseSettings, SettingsConfigDict
  
  class MemBlocksConfig(BaseSettings):
      groq_api_key: Optional[str] = Field(None, validation_alias="GROQ_API_KEY")
      
      model_config = SettingsConfigDict(
          env_file=".env",
          env_file_encoding="utf-8",
          extra="ignore",
      )
  ```

---

*Convention analysis: 2026-03-12*
