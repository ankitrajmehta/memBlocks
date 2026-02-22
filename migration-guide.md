# memBlocks Migration Guide

## Overview

This guide provides a phase-by-phase execution plan for refactoring the `memBlocks` project from its current monolithic structure into a clean, modular architecture. Each phase is designed to be independently verifiable, with clear inputs, outputs, and rollback strategies.

**Pre-requisites:**
- All infrastructure services running (`docker-compose up -d`)
- Current branch: `feature/embedding-retrieval-test`
- UV package manager installed

**Estimated Total Phases:** 13
**Estimated Total Tasks:** ~45

---

## Phase 1: UV Workspace Setup

**Goal:** Configure the project root as a UV workspace with `memblocks_lib` and `backend` as members. No code moves yet — just scaffolding.

**Complexity:** Low
**Estimated Time:** 5–10 minutes

### Tasks

#### Task 1.1: Create `memblocks_lib` package skeleton
- **Agent:** `backend-specialist`
- **INPUT:** Current root `pyproject.toml`
- **OUTPUT:** 
  - `memblocks_lib/pyproject.toml` with package metadata and core dependencies
  - `memblocks_lib/src/memblocks/__init__.py` (empty for now)
- **VERIFY:** `uv sync` succeeds from root with no errors

**Files to create:**
```
memblocks_lib/
├── pyproject.toml
└── src/
    └── memblocks/
        └── __init__.py
```

**`memblocks_lib/pyproject.toml` contents:**
```toml
[project]
name = "memblocks"
version = "0.1.0"
description = "Intelligent modular memory management system for LLMs"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "motor>=3.0",
    "qdrant-client>=1.7",
    "langchain>=0.1",
    "langchain-groq>=0.1",
    "langchain-core>=0.1",
    "httpx>=0.25",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/memblocks"]
```

#### Task 1.2: Create `backend` package skeleton
- **Agent:** `backend-specialist`
- **INPUT:** Current `backend/` directory
- **OUTPUT:**
  - `backend/pyproject.toml` with dependency on `memblocks`
  - `backend/src/` directory structure
- **VERIFY:** `uv sync` succeeds from root with no errors

**`backend/pyproject.toml` contents:**
```toml
[project]
name = "memblocks-backend"
version = "0.1.0"
description = "Demo FastAPI + CLI application for memBlocks"
requires-python = ">=3.11"
dependencies = [
    "memblocks",
    "fastapi>=0.100",
    "uvicorn>=0.20",
    "python-dotenv>=1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src"]
```

#### Task 1.3: Update root `pyproject.toml` to UV workspace
- **Agent:** `backend-specialist`
- **INPUT:** Current root `pyproject.toml`
- **OUTPUT:** Root `pyproject.toml` with workspace members defined
- **VERIFY:** `uv sync` resolves all workspace members

**Root `pyproject.toml` additions:**
```toml
[tool.uv.workspace]
members = ["memblocks_lib", "backend"]

[tool.uv.sources]
memblocks = { workspace = true }
```

#### Verification for Phase 1
```bash
uv sync
# Expected: All workspace members resolved, no errors
uv run python -c "import memblocks; print('memblocks_lib OK')"
# Expected: Prints "memblocks_lib OK"
```

#### Rollback
- Delete `memblocks_lib/` and `backend/pyproject.toml`
- Revert root `pyproject.toml` changes

---

## Phase 2: Move Pure Data Models

**Goal:** Move all Pydantic data models into `memblocks_lib/src/memblocks/models/`. Strip business logic from `models/sections.py` — only move the pure data structures. Business logic extraction happens in Phase 6.

**Complexity:** Medium
**Estimated Time:** 15–20 minutes

### Tasks

#### Task 2.1: Create `models/block.py`
- **Agent:** `backend-specialist`
- **INPUT:** `models/container.py` (105 lines)
- **OUTPUT:** `memblocks_lib/src/memblocks/models/block.py`
- **Action:** Copy `MemoryBlock` and `MemoryBlockMetaData` classes, BUT:
  - Update `from method: Remove_dict()` class the Section class instantiations (`SemanticMemorySection(...)`, `CoreMemorySection(...)`, `ResourceMemorySection(...)`). Replace with plain string fields: `semantic_collection`, `core_memory_block_id`, `resource_collection`.
  - Remove `save()` method (calls `mongo_manager` directly — DB logic belongs in storage adapter)
  - Remove `load()` class method (DB logic belongs in storage adapter)
  - Rename fields as noted in Task 2.2: `semantic_memories` → `semantic_collection`, etc.
- **VERIFY:** `uv run python -c "from memblocks.models.block import MemoryBlock, MemoryBlockMetaData"`

#### Task 2.2: Create `models/memory.py`
- **Agent:** `backend-specialist`
- **INPUT:** `models/sections.py` (683 lines)
- **OUTPUT:** `memblocks_lib/src/memblocks/models/memory.py`
- **Action:** Extract ONLY the Pydantic field definitions and `__init__` signatures from `SemanticMemorySection`, `CoreMemorySection`, and `ResourceMemorySection`. All methods (`store_memory`, `retrieve_memories`, `_resolve_memory_conflicts`, etc.) are **NOT copied** — they move to services in Phase 6. The data models will be renamed:
  - `SemanticMemorySection` → `SemanticMemoryData`
  - `CoreMemorySection` → `CoreMemoryData`
  - `ResourceMemorySection` → `ResourceMemoryData` (stub preserved)
- **VERIFY:** `uv run python -c "from memblocks.models.memory import SemanticMemoryData, CoreMemoryData, ResourceMemoryData"`

**`models/memory.py` structure (sketch):**
```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from memblocks.models.units import SemanticMemoryUnit

class SemanticMemoryData(BaseModel):
    """Pure data model for semantic memory section state."""
    user_id: str
    memory_block_id: str
    memories: List[SemanticMemoryUnit] = Field(default_factory=list)
    collection_name: str = "semantic_memories"

class CoreMemoryData(BaseModel):
    """Pure data model for core memory section state."""
    user_id: str
    memory_block_id: str
    content: str = ""
    bio: str = ""
    preferences: Dict[str, Any] = Field(default_factory=dict)

class ResourceMemoryData(BaseModel):
    """Pure data model for resource memory section state (stub)."""
    user_id: str
    memory_block_id: str
    resources: List[Dict[str, Any]] = Field(default_factory=list)
    collection_name: str = "resource_memories"
```

#### Task 2.3: Create `models/units.py`
- **Agent:** `backend-specialist`
- **INPUT:** `models/units.py` (156 lines)
- **OUTPUT:** `memblocks_lib/src/memblocks/models/units.py`
- **Action:** Copy as-is. All 6 classes are already pure data with zero service/DB imports.
- **VERIFY:** `uv run python -c "from memblocks.models.units import MemoryUnitMetaData, SemanticMemoryUnit, CoreMemoryUnit, ResourceMemoryUnit, MemoryOperation, ProcessingEvent"`

> **Note on actual class names** (the file has 6 classes, not 3):
> - `MemoryUnitMetaData` — timestamps, status, parent IDs
> - `SemanticMemoryUnit` — content, type, confidence, keywords, embedding_text, entities
> - `CoreMemoryUnit` — persona_content, human_content
> - `ResourceMemoryUnit` — content, resource_type, resource_link
> - `MemoryOperation` — operation (ADD/UPDATE/DELETE/NONE), memory_id, content, old_content
> - `ProcessingEvent` — event_id, timestamp, messages_processed, operations list
>
> There is **no** base `MemoryUnit` class. Always use the concrete names above in imports.

#### Task 2.4: Create `models/llm_outputs.py`
- **Agent:** `backend-specialist`
- **INPUT:** `llm/output_models.py` (77 lines)
- **OUTPUT:** `memblocks_lib/src/memblocks/models/llm_outputs.py`
- **Action:** Copy as-is. These are pure Pydantic models for structured LLM outputs.
- **VERIFY:** `uv run python -c "from memblocks.models.llm_outputs import SemanticMemoryOutput, CoreMemoryOutput"`

#### Task 2.5: Create `models/__init__.py` with re-exports
- **Agent:** `backend-specialist`
- **OUTPUT:** `memblocks_lib/src/memblocks/models/__init__.py`
- **Action:** Re-export all public model classes for convenient imports.
- **VERIFY:** `uv run python -c "from memblocks.models import MemoryBlock, SemanticMemoryData, CoreMemoryData, ResourceMemoryData"`

#### Verification for Phase 2
```bash
uv run python -c "
from memblocks.models.block import MemoryBlock, MemoryBlockMetaData
from memblocks.models.memory import SemanticMemoryData, CoreMemoryData, ResourceMemoryData
from memblocks.models.units import MemoryUnitMetaData, SemanticMemoryUnit, CoreMemoryUnit, ResourceMemoryUnit, MemoryOperation, ProcessingEvent
from memblocks.models.llm_outputs import SemanticMemoryOutput
print('All models import successfully')
"
```

#### Rollback
- Delete `memblocks_lib/src/memblocks/models/`
- Old models remain untouched in `models/`

---

## Phase 3: Move Prompts

**Goal:** Move all LLM prompt constants into `memblocks_lib`.

**Complexity:** Low
**Estimated Time:** 5 minutes

### Tasks

#### Task 3.1: Create `prompts/__init__.py`
- **Agent:** `backend-specialist`
- **INPUT:** `prompts.py` (436 lines)
- **OUTPUT:** `memblocks_lib/src/memblocks/prompts/__init__.py`
- **Action:** Copy all 5 prompt constants (`PS1_SEMANTIC_PROMPT`, `CORE_MEMORY_PROMPT`, `SUMMARY_SYSTEM_PROMPT`, `PS2_MEMORY_UPDATE_PROMPT`, `ASSISTANT_BASE_PROMPT`) into a single file.
- **VERIFY:** `uv run python -c "from memblocks.prompts import PS1_SEMANTIC_PROMPT, ASSISTANT_BASE_PROMPT"`

#### Verification for Phase 3
```bash
uv run python -c "
from memblocks.prompts import PS1_SEMANTIC_PROMPT, CORE_MEMORY_PROMPT, SUMMARY_SYSTEM_PROMPT, PS2_MEMORY_UPDATE_PROMPT, ASSISTANT_BASE_PROMPT
print('All prompts imported successfully')
"
```

#### Rollback
- Delete `memblocks_lib/src/memblocks/prompts/`

---

## Phase 4: Create Config Module

**Goal:** Create the `MemBlocksConfig` Pydantic settings model in the library.

**Complexity:** Low
**Estimated Time:** 5–10 minutes

### Tasks

#### Task 4.1: Create `config.py`
- **Agent:** `backend-specialist`
- **INPUT:** Root `config.py` (72 lines)
- **OUTPUT:** `memblocks_lib/src/memblocks/config.py`
- **Action:** Create `MemBlocksConfig` as a Pydantic `BaseSettings` model. Include all settings currently in `config.py`, plus any new transparency-related settings. This is NOT a singleton — it's a regular class that users instantiate.
- **VERIFY:** `uv run python -c "from memblocks.config import MemBlocksConfig; c = MemBlocksConfig(); print(c.qdrant_host)"`

#### Verification for Phase 4
```bash
uv run python -c "
from memblocks.config import MemBlocksConfig
config = MemBlocksConfig()
print(f'Qdrant: {config.qdrant_host}:{config.qdrant_port}')
print(f'MongoDB: {config.mongodb_database_name}')
print('Config OK')
"
```

#### Rollback
- Delete `memblocks_lib/src/memblocks/config.py`

---

## Phase 5: Refactor Storage Adapters

**Goal:** Create non-singleton database adapters in `memblocks_lib/src/memblocks/storage/`. Each adapter takes `MemBlocksConfig` in its constructor and optionally accepts an `OperationLog` for transparency.

**Complexity:** High
**Estimated Time:** 25–35 minutes

### Tasks

#### Task 5.1: Create `storage/embeddings.py`
- **Agent:** `backend-specialist`
- **INPUT:** `vector_db/embeddings.py` (85 lines)
- **OUTPUT:** `memblocks_lib/src/memblocks/storage/embeddings.py`
- **Action:** Create `EmbeddingProvider` class. Constructor takes `MemBlocksConfig`. Provides `async get_embeddings(texts: List[str]) -> List[List[float]]`. Remove hardcoded URLs — use config.
- **VERIFY:** Unit import check + manual embedding test against running Ollama

#### Task 5.2: Create `storage/mongo.py`
- **Agent:** `backend-specialist`
- **INPUT:** `vector_db/mongo_manager.py` (268 lines)
- **OUTPUT:** `memblocks_lib/src/memblocks/storage/mongo.py`
- **Action:** Create `MongoDBAdapter` class. Constructor takes `MemBlocksConfig` and optional `OperationLog`. Migrate ALL methods from `MongoDBManager` singleton but:
  - Remove the `__new__` singleton pattern
  - Accept config in `__init__` instead of reading global settings
  - Before each write operation, record to `OperationLog` if provided
  - Keep all async methods
- **VERIFY:** Import check + connect to running MongoDB

**Key method signatures:**
```python
class MongoDBAdapter:
    def __init__(self, config: MemBlocksConfig, operation_log: Optional[OperationLog] = None): ...
    
    # User operations
    async def create_user(self, user_id: str) -> Dict[str, Any]: ...
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]: ...
    
    # Block operations
    async def create_memory_block(self, user_id: str, block_data: Dict) -> Dict[str, Any]: ...
    async def get_memory_block(self, block_id: str) -> Optional[Dict[str, Any]]: ...
    async def get_user_memory_blocks(self, user_id: str) -> List[Dict[str, Any]]: ...
    async def update_memory_block(self, block_id: str, update_data: Dict) -> Dict[str, Any]: ...
    async def delete_memory_block(self, block_id: str) -> bool: ...
    
    # Core memory operations
    async def get_core_memory(self, user_id: str) -> Optional[Dict[str, Any]]: ...
    async def upsert_core_memory(self, user_id: str, content: Dict) -> Dict[str, Any]: ...
    
    # Session operations
    async def create_session(self, session_data: Dict) -> Dict[str, Any]: ...
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]: ...
    async def update_session(self, session_id: str, update_data: Dict) -> Dict[str, Any]: ...
    async def add_message_to_session(self, session_id: str, message: Dict) -> None: ...
    async def get_session_messages(self, session_id: str, limit: int) -> List[Dict]: ...
    
    # Processing task operations
    async def create_processing_task(self, task_data: Dict) -> Dict[str, Any]: ...
    async def update_processing_task(self, task_id: str, update_data: Dict) -> Dict[str, Any]: ...
```

#### Task 5.3: Create `storage/qdrant.py`
- **Agent:** `backend-specialist`
- **INPUT:** `vector_db/vector_db_manager.py` (169 lines)
- **OUTPUT:** `memblocks_lib/src/memblocks/storage/qdrant.py`
- **Action:** Create `QdrantAdapter` class. Constructor takes `MemBlocksConfig` and optional `OperationLog`. Migrate methods from `VectorDBManager`:
  - Remove static methods pattern — make instance methods
  - Resolve host/port from config (fixes hardcoded localhost bug)
  - Record write operations to `OperationLog` if provided
- **VERIFY:** Import check + connect to running Qdrant

**Key method signatures:**
```python
class QdrantAdapter:
    def __init__(self, config: MemBlocksConfig, operation_log: Optional[OperationLog] = None): ...
    
    async def ensure_collection(self, collection_name: str, vector_size: int = 768) -> None: ...
    async def insert_vectors(self, collection_name: str, ids: List[str], vectors: List[List[float]], payloads: List[Dict]) -> None: ...
    async def search_vectors(self, collection_name: str, query_vector: List[float], limit: int = 5, filters: Optional[Dict] = None) -> List[Dict]: ...
    async def delete_vectors(self, collection_name: str, ids: List[str]) -> None: ...
    async def get_vectors_by_filter(self, collection_name: str, filters: Dict) -> List[Dict]: ...
```

#### Task 5.4: Create `storage/__init__.py` with re-exports
- **Agent:** `backend-specialist`
- **OUTPUT:** `memblocks_lib/src/memblocks/storage/__init__.py`
- **VERIFY:** `uv run python -c "from memblocks.storage import MongoDBAdapter, QdrantAdapter, EmbeddingProvider"`

#### Verification for Phase 5
```bash
uv run python -c "
from memblocks.storage.mongo import MongoDBAdapter
from memblocks.storage.qdrant import QdrantAdapter
from memblocks.storage.embeddings import EmbeddingProvider
from memblocks.config import MemBlocksConfig
config = MemBlocksConfig()
mongo = MongoDBAdapter(config)
qdrant = QdrantAdapter(config)
embedding = EmbeddingProvider(config)
print('All storage adapters instantiate successfully')
"
```

#### Rollback
- Delete `memblocks_lib/src/memblocks/storage/`

---

## Phase 6: Create Abstract LLM Interface + Groq Implementation

**Goal:** Define the `LLMProvider` abstract interface and implement it with the existing Groq/LangChain logic.

**Complexity:** High
**Estimated Time:** 20–30 minutes

### Tasks

#### Task 6.1: Create `llm/base.py` — `LLMProvider` ABC
- **Agent:** `backend-specialist`
- **INPUT:** `llm/llm_manager.py` (104 lines) — specifically `create_structured_chain()` (line 69) and `get_chat_llm()` (line 56)
- **OUTPUT:** `memblocks_lib/src/memblocks/llm/base.py`
- **Action:** Define the abstract interface with **two generic methods only**. Domain logic (PS1/PS2/summarization) belongs in services — services compose prompts and call these methods. The LLM interface stays generic.

> **Why not domain-specific methods?** An earlier draft of this interface had 5 methods (`extract_semantic_memories`, `resolve_memory_conflicts`, etc.). That was incorrect — those are *service* responsibilities. The LLM interface should be generic so any LLM backend can implement it without understanding memBlocks-specific concepts.

**Full interface:**
```python
from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional, Type
from pydantic import BaseModel

class LLMProvider(ABC):
    """Generic LLM interface. Two methods only — services handle all domain logic."""

    @abstractmethod
    def create_structured_chain(
        self,
        system_prompt: str,
        pydantic_model: Type[BaseModel],
        temperature: float = 0.0,
    ) -> Any:
        """Return a runnable that accepts {"input": str} and returns a pydantic_model instance.

        Must support: result = await chain.ainvoke({"input": user_input})

        Replaces: LLMManager.create_structured_chain() (llm_manager.py:69-99).
        Called by:
        - SemanticMemoryService (PS1 extraction: PS1_SEMANTIC_PROMPT + SemanticMemoriesOutput)
        - SemanticMemoryService (PS2 conflict resolution: PS2_MEMORY_UPDATE_PROMPT + PS2MemoryUpdateOutput)
        - CoreMemoryService (core extraction: CORE_MEMORY_PROMPT + CoreMemoryOutput)
        - MemoryPipeline (summary: SUMMARY_SYSTEM_PROMPT + SummaryOutput)
        """
        ...

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
    ) -> str:
        """Send a list of {"role": ..., "content": ...} messages and return the response text.

        Replaces: LLMManager.get_chat_llm(temperature) + await llm.ainvoke(messages)
        (chat_service.py:536-538). Returns response.content as a plain string.

        Called by: ChatEngine.send_message() for the main conversation turn.
        """
        ...
```

#### Task 6.2: Create `llm/groq_provider.py` — Default Implementation
- **Agent:** `backend-specialist`
- **INPUT:** `llm/llm_manager.py` (104 lines) — `_initialize_llm()` (line 37), `create_structured_chain()` (line 69), `get_chat_llm()` (line 56)
- **OUTPUT:** `memblocks_lib/src/memblocks/llm/groq_provider.py`
- **Action:** Implement `LLMProvider` using `langchain_groq.ChatGroq`. Constructor takes `MemBlocksConfig`.

**Key implementation notes:**
- Constructor reads `config.groq_api_key`, `config.llm_model` — no global `settings` import
- **Arize instrumentation** (currently `llm_manager.py:9-19`, runs at module import time with `settings` globals) moves **inside `__init__`**: `if config.arize_space_id and config.arize_api_key: ...register(...) LangChainInstrumentor().instrument(...)`. This eliminates the module-level side-effect.
- `create_structured_chain()` mirrors `llm_manager.py:69-99` exactly: `ChatGroq(...).with_structured_output(pydantic_model, method="json_schema") | ChatPromptTemplate`
- `chat()` replaces `llm_manager.get_chat_llm(temperature).ainvoke(messages)` + `.content` extraction (chat_service.py:536-538)

#### Task 6.3: Create `llm/__init__.py`
- **Agent:** `backend-specialist`
- **OUTPUT:** `memblocks_lib/src/memblocks/llm/__init__.py`
- **VERIFY:** `uv run python -c "from memblocks.llm.base import LLMProvider; from memblocks.llm.groq_provider import GroqLLMProvider"`

#### Verification for Phase 6
```bash
uv run python -c "
from memblocks.llm.base import LLMProvider
from memblocks.llm.groq_provider import GroqLLMProvider
from memblocks.config import MemBlocksConfig
config = MemBlocksConfig()
provider = GroqLLMProvider(config)
print(f'LLM Provider created: {type(provider).__name__}')
print(f'Implements LLMProvider: {isinstance(provider, LLMProvider)}')
"
```

#### Rollback
- Delete `memblocks_lib/src/memblocks/llm/`

---

## Phase 7: Extract Services from Models (The Big One)

**Goal:** Extract all business logic from `models/sections.py` and split `services/chat_service.py` into focused service classes. This is the most complex phase.

**Complexity:** Very High
**Estimated Time:** 45–60 minutes

### Source → Destination Mapping

| Source File | Source Code Section | Destination Service |
|---|---|---|
| `models/sections.py` | `SemanticMemorySection.store_memory()` | `services/semantic_memory.py` → `SemanticMemoryService.store()` |
| `models/sections.py` | `SemanticMemorySection.retrieve_memories()` | `services/semantic_memory.py` → `SemanticMemoryService.retrieve()` |
| `models/sections.py` | `SemanticMemorySection._resolve_memory_conflicts()` | `services/semantic_memory.py` → `SemanticMemoryService._resolve_conflicts()` |
| `models/sections.py` | `CoreMemorySection.update_core_memory()` | `services/core_memory.py` → `CoreMemoryService.update()` |
| `models/sections.py` | `CoreMemorySection.get_core_memory()` | `services/core_memory.py` → `CoreMemoryService.get()` |
| `services/chat_service.py` | Message management methods | `services/chat_engine.py` → `ChatEngine` |
| `services/chat_service.py` | Memory retrieval + context assembly | `services/chat_engine.py` → `ChatEngine` |
| `services/chat_service.py` | Background processing + task tracking | `services/memory_pipeline.py` → `MemoryPipeline` |
| `services/chat_service.py` | Summary generation | `services/memory_pipeline.py` → `MemoryPipeline` |
| `services/block_service.py` | `BlockService` class | `services/block_manager.py` → `BlockManager` |
| `services/block_service.py` | `SessionManager` class | `services/session_manager.py` → `SessionManager` |
| `services/user_service.py` | `UserService` class | `services/user_manager.py` → `UserManager` |

### Tasks

#### Task 7.1: Create `services/semantic_memory.py`
- **Agent:** `backend-specialist`
- **INPUT:** `models/sections.py` methods: `store_memory`, `retrieve_memories`, `_resolve_memory_conflicts`
- **OUTPUT:** `memblocks_lib/src/memblocks/services/semantic_memory.py`

```python
class SemanticMemoryService:
    def __init__(
        self,
        llm_provider: LLMProvider,
        embedding_provider: EmbeddingProvider,
        qdrant_adapter: QdrantAdapter,
        collection_name: str,
        operation_log: Optional[OperationLog] = None,
    ): ...

    async def store(
        self,
        user_id: str,
        block_id: str,
        conversation_history: List[Dict[str, Any]],
        existing_memories: List[SemanticMemoryUnit],
    ) -> List[MemoryOperation]:
        """
        Full semantic memory pipeline:
        1. Extract memories via LLM (PS1)
        2. Retrieve similar existing memories from Qdrant
        3. Resolve conflicts via LLM (PS2)
        4. Store final memories in Qdrant
        Returns list of operations performed (for transparency).
        """
        ...

    async def retrieve(
        self,
        query: str,
        user_id: str,
        block_id: str,
        limit: int = 5,
    ) -> List[SemanticMemoryUnit]:
        """Retrieve relevant semantic memories for a query."""
        ...

    async def _resolve_conflicts(
        self,
        proposed: List[SemanticMemoryOutput],
        existing: List[Dict[str, Any]],
    ) -> List[SemanticMemoryOutput]:
        """Internal: use LLM to resolve conflicts between proposed and existing memories."""
        ...
```
- **VERIFY:** Import check, method signatures match expected interface

#### Task 7.2: Create `services/core_memory.py`
- **Agent:** `backend-specialist`
- **INPUT:** `models/sections.py` methods: `update_core_memory`, `get_core_memory`
- **OUTPUT:** `memblocks_lib/src/memblocks/services/core_memory.py`

```python
class CoreMemoryService:
    def __init__(
        self,
        llm_provider: LLMProvider,
        mongo_adapter: MongoDBAdapter,
        operation_log: Optional[OperationLog] = None,
    ): ...

    async def get(self, user_id: str) -> CoreMemoryData:
        """Retrieve the current core memory for a user."""
        ...

    async def update(
        self,
        user_id: str,
        conversation_history: List[Dict[str, Any]],
    ) -> CoreMemoryData:
        """Extract and update core memories from conversation history."""
        ...
```
- **VERIFY:** Import check

#### Task 7.3: Create `services/memory_pipeline.py`
- **Agent:** `backend-specialist`
- **INPUT:** `services/chat_service.py` background processing logic, `BackgroundTaskTracker`, `ProcessingHistoryTracker`
- **OUTPUT:** `memblocks_lib/src/memblocks/services/memory_pipeline.py`

```python
class MemoryPipeline:
    def __init__(
        self,
        semantic_memory_service: SemanticMemoryService,
        core_memory_service: CoreMemoryService,
        embedding_provider: EmbeddingProvider,
        qdrant_adapter: QdrantAdapter,
        config: MemBlocksConfig,
        processing_history: Optional[ProcessingHistory] = None,
        operation_log: Optional[OperationLog] = None,
    ): ...

    async def process_memory_window(
        self,
        user_id: str,
        block_id: str,
        messages: List[Dict[str, Any]],
        existing_memories: List[SemanticMemoryUnit],
    ) -> str:
        """
        Full memory processing pipeline (runs as background task):
        1. Semantic memory extraction + conflict resolution + storage
        2. Core memory update
        3. Summary generation
        4. History flush (trim processed messages, keep summary)
        
        Returns task_id for tracking.
        """
        ...

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a background processing task."""
        ...
```
- **VERIFY:** Import check
- **CRITICAL FIX:** The incomplete `_process_memory_window_task` (currently `pass` on line 288 of `chat_service.py`) will be fully implemented here with all pipeline stages wired.

#### Task 7.4: Create `services/chat_engine.py`
- **Agent:** `backend-specialist`
- **INPUT:** `services/chat_service.py` conversation management logic
- **OUTPUT:** `memblocks_lib/src/memblocks/services/chat_engine.py`

```python
class ChatEngine:
    def __init__(
        self,
        user_manager: UserManager,
        block_manager: BlockManager,
        session_manager: SessionManager,
        semantic_memory_service: SemanticMemoryService,
        core_memory_service: CoreMemoryService,
        memory_pipeline: MemoryPipeline,
        llm_provider: LLMProvider,
        config: MemBlocksConfig,
        retrieval_log: Optional[RetrievalLog] = None,
    ): ...

    async def send_message(
        self,
        session_id: str,
        user_message: str,
    ) -> Tuple[Dict[str, Any], List[SemanticMemoryUnit]]:
        """
        Process a user message:
        1. Store message in session history
        2. Retrieve relevant memories (semantic + core)
        3. Assemble context
        4. Generate response via LLM
        5. Store assistant response in session history
        6. Check if memory window is full → trigger MemoryPipeline
        
        Returns (response_message_dict, retrieved_memories)
        """
        ...

    async def get_chat_history(
        self,
        session_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get message history for a session."""
        ...

    async def _assemble_context(
        self,
        user_id: str,
        block_id: str,
        query: str,
    ) -> Tuple[str, List[SemanticMemoryUnit]]:
        """
        Internal: Retrieve and assemble memory context for LLM.
        Returns (context_string, retrieved_memories).
        Logs to RetrievalLog if provided.
        """
        ...
```
- **VERIFY:** Import check

#### Task 7.5: Create `services/block_manager.py`
- **Agent:** `backend-specialist`
- **INPUT:** `services/block_service.py` → `BlockService` class
- **OUTPUT:** `memblocks_lib/src/memblocks/services/block_manager.py`

```python
class BlockManager:
    def __init__(
        self,
        mongo_adapter: MongoDBAdapter,
        embedding_provider: EmbeddingProvider,
        qdrant_adapter: QdrantAdapter,
        operation_log: Optional[OperationLog] = None,
    ): ...

    async def create_block(self, user_id: str, name: str) -> MemoryBlock: ...
    async def get_block(self, block_id: str) -> Optional[MemoryBlock]: ...
    async def get_user_blocks(self, user_id: str) -> List[MemoryBlock]: ...
    async def update_block_status(self, block_id: str, is_active: bool) -> MemoryBlock: ...
    async def delete_block(self, block_id: str) -> bool: ...
```
- **VERIFY:** Import check

#### Task 7.6: Create `services/user_manager.py`
- **Agent:** `backend-specialist`
- **INPUT:** `services/user_service.py` (70 lines)
- **OUTPUT:** `memblocks_lib/src/memblocks/services/user_manager.py`

```python
class UserManager:
    def __init__(self, mongo_adapter: MongoDBAdapter): ...

    async def create_user(self, user_id: str) -> Dict[str, Any]: ...
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]: ...
```
- **VERIFY:** Import check

#### Task 7.7: Create `services/session_manager.py`
- **Agent:** `backend-specialist`
- **INPUT:** `services/block_service.py` → `SessionManager` class
- **OUTPUT:** `memblocks_lib/src/memblocks/services/session_manager.py`

```python
class SessionManager:
    def __init__(
        self,
        mongo_adapter: MongoDBAdapter,
        operation_log: Optional[OperationLog] = None,
    ): ...

    async def create_session(self, user_id: str, block_id: str) -> Dict[str, Any]: ...
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]: ...
    async def add_message(self, session_id: str, role: str, content: str) -> None: ...
    async def get_messages(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]: ...
    async def get_message_count(self, session_id: str) -> int: ...
```
- **VERIFY:** Import check

#### Task 7.8: Create `services/__init__.py` with re-exports
- **Agent:** `backend-specialist`
- **OUTPUT:** `memblocks_lib/src/memblocks/services/__init__.py`
- **VERIFY:** All services importable from `memblocks.services`

#### Verification for Phase 7
```bash
uv run python -c "
from memblocks.services.semantic_memory import SemanticMemoryService
from memblocks.services.core_memory import CoreMemoryService
from memblocks.services.memory_pipeline import MemoryPipeline
from memblocks.services.chat_engine import ChatEngine
from memblocks.services.block_manager import BlockManager
from memblocks.services.user_manager import UserManager
from memblocks.services.session_manager import SessionManager
print('All services import successfully')
"
```

#### Rollback
- Delete `memblocks_lib/src/memblocks/services/`

---

## Phase 8: Build `MemBlocksClient`

**Goal:** Create the main entry point that wires all services together via constructor injection.

**Complexity:** Medium
**Estimated Time:** 15–20 minutes

### Tasks

#### Task 8.1: Create `client.py`
- **Agent:** `backend-specialist`
- **INPUT:** All services, storage adapters, LLM interface, config
- **OUTPUT:** `memblocks_lib/src/memblocks/client.py`
- **Action:** Implement the full `MemBlocksClient` as designed in Section 4.1 of `refactoring-plan.md`. Wire all dependencies.
- **VERIFY:** Can instantiate `MemBlocksClient(config)` with defaults

#### Task 8.2: Update `memblocks_lib/src/memblocks/__init__.py` with public exports
- **Agent:** `backend-specialist`
- **OUTPUT:** Updated `__init__.py` exporting `MemBlocksClient`, `MemBlocksConfig`, key models, `LLMProvider`
- **VERIFY:** `from memblocks import MemBlocksClient, MemBlocksConfig`

#### Verification for Phase 8
```bash
uv run python -c "
from memblocks import MemBlocksClient, MemBlocksConfig
config = MemBlocksConfig()
client = MemBlocksClient(config)
print(f'Client created: {type(client).__name__}')
print(f'Transparency always-on: operation_log={client.get_operation_log() is not None}')
print(f'Services: user_manager={type(client.user_manager).__name__}, chat_engine={type(client.chat_engine).__name__}')
"
```

#### Rollback
- Delete `memblocks_lib/src/memblocks/client.py`
- Revert `__init__.py`

---

## Phase 9: Add Transparency & Observability Layer

**Goal:** Implement `OperationLog`, `RetrievalLog`, `ProcessingHistory`, and the event subscription system.

**Complexity:** Medium
**Estimated Time:** 20–25 minutes

### Tasks

#### Task 9.1: Create transparency models
- **Agent:** `backend-specialist`
- **OUTPUT:** `memblocks_lib/src/memblocks/models/transparency.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from enum import Enum

class DBType(str, Enum):
    MONGO = "mongo"
    QDRANT = "qdrant"

class OperationType(str, Enum):
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    UPSERT = "upsert"

class OperationEntry(BaseModel):
    """A single recorded database operation."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    db_type: DBType
    collection_name: str
    operation_type: OperationType
    document_id: Optional[str] = None
    payload_summary: str = ""  # Brief description of what changed
    success: bool = True
    error: Optional[str] = None

class RetrievalEntry(BaseModel):
    """A single recorded memory retrieval event."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    query_text: str
    source: str  # "semantic", "core", "resource"
    num_results: int = 0
    top_scores: List[float] = Field(default_factory=list)
    memory_ids: List[str] = Field(default_factory=list)
    memory_summaries: List[str] = Field(default_factory=list)  # Brief text of each retrieved memory

class PipelineRunEntry(BaseModel):
    """A single recorded pipeline processing run."""
    task_id: str
    timestamp_started: datetime = Field(default_factory=datetime.utcnow)
    timestamp_completed: Optional[datetime] = None
    status: str = "running"  # running, success, failure
    trigger_event: str = ""  # e.g., "message_window_full"
    input_message_count: int = 0
    extracted_semantic_count: int = 0
    conflicts_resolved_count: int = 0
    core_memory_updated: bool = False
    summary_generated: bool = False
    error_details: Optional[str] = None
```

#### Task 9.2: Create log classes
- **Agent:** `backend-specialist`
- **OUTPUT:** `memblocks_lib/src/memblocks/services/transparency.py`

```python
class OperationLog:
    """Thread-safe log of all database operations."""
    
    def __init__(self, max_entries: int = 1000): ...
    
    def record(self, entry: OperationEntry) -> None: ...
    def get_entries(self, limit: int = 100, db_type: Optional[DBType] = None) -> List[OperationEntry]: ...
    def get_entries_since(self, since: datetime) -> List[OperationEntry]: ...
    def clear(self) -> None: ...
    def summary(self) -> Dict[str, int]:
        """Returns count of operations by type. E.g., {'insert': 5, 'update': 3, 'delete': 1}"""
        ...

class RetrievalLog:
    """Thread-safe log of all memory retrieval events."""
    
    def __init__(self, max_entries: int = 1000): ...
    
    def record(self, entry: RetrievalEntry) -> None: ...
    def get_entries(self, limit: int = 100, source: Optional[str] = None) -> List[RetrievalEntry]: ...
    def get_last_retrieval(self) -> Optional[RetrievalEntry]: ...
    def clear(self) -> None: ...

class ProcessingHistory:
    """Thread-safe log of all memory pipeline processing runs."""
    
    def __init__(self, max_entries: int = 500): ...
    
    def record_start(self, task_id: str, trigger_event: str, message_count: int) -> PipelineRunEntry: ...
    def record_complete(self, task_id: str, result: Dict[str, Any]) -> PipelineRunEntry: ...
    def record_failure(self, task_id: str, error: str) -> PipelineRunEntry: ...
    def get_runs(self, limit: int = 50, status: Optional[str] = None) -> List[PipelineRunEntry]: ...
    def get_run(self, task_id: str) -> Optional[PipelineRunEntry]: ...
    def get_last_run(self) -> Optional[PipelineRunEntry]: ...
    def clear(self) -> None: ...

class EventBus:
    """Simple synchronous event bus for transparency callbacks."""
    
    VALID_EVENTS = [
        "on_memory_extracted",       # Fired after PS1 semantic extraction
        "on_conflict_resolved",      # Fired after PS2 conflict resolution
        "on_memory_stored",          # Fired after memories written to Qdrant
        "on_core_memory_updated",    # Fired after core memory updated in Mongo
        "on_summary_generated",      # Fired after conversation summary created
        "on_pipeline_started",       # Fired when memory pipeline begins
        "on_pipeline_completed",     # Fired when memory pipeline finishes
        "on_pipeline_failed",        # Fired when memory pipeline errors
        "on_memory_retrieved",       # Fired when memories are retrieved for context
        "on_db_write",               # Fired on any database write operation
        "on_message_processed",      # Fired after a chat message is fully processed
    ]
    
    def __init__(self): ...
    
    def subscribe(self, event_name: str, callback: Callable[[Any], None]) -> None:
        """Subscribe to an event. Raises ValueError if event_name is not valid."""
        ...
    
    def unsubscribe(self, event_name: str, callback: Callable[[Any], None]) -> None:
        """Unsubscribe from an event."""
        ...
    
    def publish(self, event_name: str, payload: Any) -> None:
        """Publish an event to all subscribers. Swallows callback exceptions."""
        ...
```

#### Task 9.3: Wire transparency into storage adapters and services
- **Agent:** `backend-specialist`
- **INPUT:** All storage adapters and services from previous phases
- **OUTPUT:** Updated constructors and methods to accept and use `OperationLog`, `RetrievalLog`, `ProcessingHistory`, and `EventBus`
- **Action:** Add `self._operation_log.record(...)` calls before/after each DB write in `MongoDBAdapter` and `QdrantAdapter`. Add `self._retrieval_log.record(...)` calls in `SemanticMemoryService.retrieve()` and `ChatEngine._assemble_context()`. Add `self._processing_history.record_*()` calls in `MemoryPipeline`. Add `self._event_bus.publish(...)` calls at key pipeline stages.
- **VERIFY:** Create a client, perform operations, check logs are populated (transparency is always-on)

#### Task 9.4: Wire `EventBus` into `MemBlocksClient`
- **Agent:** `backend-specialist`
- **INPUT:** `client.py`
- **OUTPUT:** Updated `client.py` with `subscribe()` and `unsubscribe()` methods delegating to `EventBus`
- **VERIFY:** Subscribe to an event, trigger an action, verify callback fires

#### Verification for Phase 9
```bash
uv run python -c "
from memblocks import MemBlocksClient, MemBlocksConfig
config = MemBlocksConfig()
client = MemBlocksClient(config)

# Check logs exist
assert client.get_operation_log() is not None
assert client.get_retrieval_log() is not None
assert client.get_processing_history() is not None

# Check event subscription works
events_received = []
client.subscribe('on_db_write', lambda e: events_received.append(e))
print('Transparency layer OK')
"
```

#### Rollback
- Delete `memblocks_lib/src/memblocks/models/transparency.py`
- Delete `memblocks_lib/src/memblocks/services/transparency.py`
- Revert constructor changes in adapters/services

---

## Phase 10: Restructure Backend

**Goal:** Update the `backend/` application to use `MemBlocksClient` from `memblocks_lib`. Remove all `sys.path` hacks. Fix known bugs.

**Complexity:** High
**Estimated Time:** 30–40 minutes

### Tasks

#### Task 10.1: Create `backend/src/api/dependencies.py`
- **Agent:** `backend-specialist`
- **INPUT:** Current `backend/dependencies.py` (74 lines)
- **OUTPUT:** `backend/src/api/dependencies.py`
- **Action:** Create a single `MemBlocksClient` instance on startup. Provide a FastAPI dependency function.

```python
from memblocks import MemBlocksClient, MemBlocksConfig

_client: Optional[MemBlocksClient] = None

async def get_memblocks_client() -> MemBlocksClient:
    global _client
    if _client is None:
        config = MemBlocksConfig()
        _client = MemBlocksClient(config)
    return _client
```
- **VERIFY:** FastAPI app starts without import errors

#### Task 10.2: Update `backend/src/api/main.py`
- **Agent:** `backend-specialist`
- **INPUT:** Current `backend/main.py` (190 lines)
- **OUTPUT:** `backend/src/api/main.py`
- **Action:** Update to use the new dependency. Fix port typo (`80001` → `8001`). Remove `sys.path` hacks. Add startup/shutdown lifecycle hooks for the client.
- **VERIFY:** `uv run uvicorn backend.src.api.main:app --reload` starts correctly

#### Task 10.3: Update all routers
- **Agent:** `backend-specialist`
- **INPUT:** Current `backend/routers/` (users.py, blocks.py, chat.py, memory.py)
- **OUTPUT:** `backend/src/api/routers/` (same files, updated)
- **Action:** For each router:
  - Remove `sys.path.insert(0, project_root)` hacks
  - Replace direct service/manager imports with `MemBlocksClient` dependency injection
  - Fix `memory.py`: Change `searchMemories` endpoint from GET to POST (matching frontend)
  - Fix `memory.py`: Replace `VectorDBManager.get_all_points()` calls with new `QdrantAdapter.get_all_points()` method (does not exist in current code — implement it)
- **VERIFY:** All endpoints respond correctly

#### Task 10.4: Move API request models
- **Agent:** `backend-specialist`
- **INPUT:** Current `backend/models/requests.py` (35 lines)
- **OUTPUT:** `backend/src/api/models/requests.py`
- **Action:** Move as-is, update imports.
- **VERIFY:** Import check

#### Verification for Phase 10
```bash
# Start the server
uv run uvicorn backend.src.api.main:app --port 8001 &

# Test key endpoints
curl http://localhost:8001/health
curl -X POST http://localhost:8001/api/users -d '{"user_id": "test"}'
curl http://localhost:8001/api/blocks/test

# Kill server
kill %1
```

#### Rollback
- Revert `backend/` to original structure
- Keep old `backend/main.py`, `backend/dependencies.py`, `backend/routers/`

---

## Phase 11: Move CLI to Backend

**Goal:** Move the root `main.py` CLI application into `backend/src/cli/main.py`, update it to use `MemBlocksClient`.

**Complexity:** Medium
**Estimated Time:** 15–20 minutes

### Tasks

#### Task 11.1: Create `backend/src/cli/main.py`
- **Agent:** `backend-specialist`
- **INPUT:** Root `main.py` (315 lines)
- **OUTPUT:** `backend/src/cli/main.py`
- **Action:** Refactor to use `MemBlocksClient` instead of direct service imports. Keep the interactive CLI loop, update all method calls to go through the client.
- **VERIFY:** `uv run python -m backend.src.cli.main` starts the interactive CLI

#### Task 11.2: Add CLI entry point to `backend/pyproject.toml`
- **Agent:** `backend-specialist`
- **OUTPUT:** Updated `backend/pyproject.toml` with `[project.scripts]` section
```toml
[project.scripts]
memblocks-cli = "backend.src.cli.main:main"
```
- **VERIFY:** `uv run memblocks-cli` starts the interactive CLI

#### Verification for Phase 11
```bash
# Test CLI starts
echo "exit" | uv run python -m backend.src.cli.main
# Expected: CLI starts, processes "exit", shuts down cleanly
```

#### Rollback
- Delete `backend/src/cli/`
- Root `main.py` remains unchanged

---

## Phase 12: Cleanup & Final Verification

**Goal:** Move old files to depricated folder, verify everything works end-to-end, ensure no broken imports.

**Complexity:** Medium
**Estimated Time:** 20–30 minutes

### Tasks

#### Task 12.1: Move old root-level source files to depricated folder
- **Agent:** `backend-specialist`
- **Action:** Move the following files/directories that have been migrated to /depricated/ folder:
  - `config.py` (→ `memblocks_lib/src/memblocks/config.py`)
  - `prompts.py` (→ `memblocks_lib/src/memblocks/prompts/__init__.py`)
  - `models/` (→ `memblocks_lib/src/memblocks/models/`)
  - `services/` (→ `memblocks_lib/src/memblocks/services/`)
  - `llm/` (→ `memblocks_lib/src/memblocks/llm/`)
  - `vector_db/` (→ `memblocks_lib/src/memblocks/storage/`)
  - `vector_db/try/` (test scripts — imports from old structure, no longer needed after migration)
  - `main.py` (→ `backend/src/cli/main.py`)
  - Old `backend/main.py`, `backend/dependencies.py`, `backend/routers/`, `backend/models/` (→ `backend/src/`)
- **VERIFY:** `uv sync` succeeds, no dangling imports

#### Task 12.2: Update root `pyproject.toml`
- **Agent:** `backend-specialist`
- **Action:** Remove dependencies that now belong to `memblocks_lib/pyproject.toml` or `backend/pyproject.toml`. Keep only workspace-level config.
- **VERIFY:** `uv sync` succeeds

#### Task 12.3: Run full import verification
- **Agent:** `backend-specialist`
- **Action:** Verify all public APIs are importable and functional.

```bash
uv run python -c "
# Library imports
from memblocks import MemBlocksClient, MemBlocksConfig
from memblocks.models import MemoryBlock, SemanticMemoryData, CoreMemoryData, ResourceMemoryData, SemanticMemoryUnit, CoreMemoryUnit, ResourceMemoryUnit, MemoryOperation, ProcessingEvent
from memblocks.llm.base import LLMProvider
from memblocks.llm.groq_provider import GroqLLMProvider
from memblocks.storage import MongoDBAdapter, QdrantAdapter, EmbeddingProvider
from memblocks.services import SemanticMemoryService, CoreMemoryService, MemoryPipeline, ChatEngine, BlockManager, UserManager, SessionManager
from memblocks.prompts import PS1_SEMANTIC_PROMPT, CORE_MEMORY_PROMPT, SUMMARY_SYSTEM_PROMPT, PS2_MEMORY_UPDATE_PROMPT, ASSISTANT_BASE_PROMPT

# Instantiation
config = MemBlocksConfig()
client = MemBlocksClient(config)
print('✅ All imports and instantiation successful')
print(f'   Client: {type(client).__name__}')
print(f'   Config: qdrant={config.qdrant_host}:{config.qdrant_port}, mongo={config.mongodb_database_name}')
print(f'   Transparency: operation_log={client.get_operation_log() is not None}, retrieval_log={client.get_retrieval_log() is not None}')
"
```

#### Task 12.4: Run end-to-end integration test
- **Agent:** `test-engineer`
- **Action:** Start infrastructure, start backend, verify:
  1. Create user via API
  2. Create memory block via API
  3. Send messages via API
  4. Verify memories are extracted (check transparency logs)
  5. Search memories via API
  6. Verify CLI starts and can interact

```bash
# Start infrastructure
docker-compose up -d

# Start backend
uv run uvicorn backend.src.api.main:app --port 8001 &
sleep 3

# Run integration checks
curl -s http://localhost:8001/health | python -m json.tool
curl -s -X POST http://localhost:8001/api/users -H "Content-Type: application/json" -d '{"user_id":"integration_test_user"}' | python -m json.tool

# Kill backend
kill %1
```

#### Task 12.5: Verify frontend still works
- **Agent:** `frontend-specialist`
- **Action:** Start backend + frontend, verify the React app can:
  1. Connect to backend
  2. Create/list blocks
  3. Send chat messages
  4. Display memories

```bash
# Start backend
uv run uvicorn backend.src.api.main:app --port 8001 &

# Start frontend
cd frontend && npm run dev &

# Manual verification: open http://localhost:5173
```

#### Task 12.6: Remove `services/background_utils.py` workaround
- **Agent:** `backend-specialist`
- **Action:** This file (`BackgroundMongoDBManager`, `BackgroundLLMProvider`) was a workaround for singletons. With constructor injection in place, it's no longer needed. Verify no code references it, then delete.
- **VERIFY:** Grep for `background_utils` returns no results

#### Task 12.7: Migrate existing MongoDB data for renamed MemoryBlock fields
- **Agent:** `backend-specialist`
- **Action:** Existing memory blocks in MongoDB have old field names (`semantic_memories`, `core_memory`, `resource_memories`). The new schema uses plain string fields (`semantic_collection`, `core_memory_block_id`, `resource_collection`). Run a one-time migration script:
  ```python
  # Migrate MemoryBlock documents
  for block in mongo.memory_blocks.find({}):
      updates = {}
      if "semantic_memories" in block:
          updates["semantic_collection"] = block["semantic_memories"].get("collection_name", "semantic_memories")
      if "core_memory" in block:
          updates["core_memory_block_id"] = block["core_memory"].get("block_id", block["_id"])
      if "resource_memories" in block:
          updates["resource_collection"] = block["resource_memories"].get("collection_name", "resource_memories")
      if updates:
          mongo.memory_blocks.update_one({"_id": block["_id"]}, {"$set": updates, "$unset": {"semantic_memories": "", "core_memory": "", "resource_memories": ""}})
  ```
- **VERIFY:** Query a block, verify new field names exist and old ones are removed

### Phase 12 Final Checklist
```
[ ] All old root-level source files deleted
[ ] Root pyproject.toml cleaned up
[ ] `uv sync` succeeds
[ ] All library imports work
[ ] All services instantiate correctly via MemBlocksClient
[ ] Backend API starts and responds
[ ] CLI starts and interacts
[ ] Frontend connects and works
[ ] No sys.path hacks remain
[ ] No singleton patterns remain in library
[ ] Transparency logs populate during operations
[ ] Event callbacks fire correctly
[ ] No references to deleted files remain
```

---

## Phase X: Final Verification

**Goal:** Run all automated verification scripts and ensure the project meets quality standards.

### Checklist

```
[ ] Lint & Type Check: `uv run ruff check memblocks_lib/src/ backend/src/` (if ruff configured)
[ ] Import Verification: All public APIs importable (Task 12.3 script)
[ ] Backend Health: `curl http://localhost:8001/health` returns 200
[ ] Integration Test: Create user → Create block → Send messages → Verify memories
[ ] CLI Test: `echo "exit" | uv run memblocks-cli` exits cleanly
[ ] Frontend Test: React app connects and functions
[ ] No Dangling Imports: `uv run python -c "import memblocks"` succeeds
[ ] No sys.path Hacks: `grep -r "sys.path" backend/` returns nothing
[ ] No Singletons in Library: `grep -r "__new__" memblocks_lib/` returns nothing
[ ] Transparency Works: Operation log, retrieval log, processing history all populate
[ ] Event Callbacks Work: Subscribe → trigger → callback fires
[ ] Port Fix Verified: Backend runs on 8001 (not 80001)
[ ] API Method Fix: searchMemories accepts POST
[ ] Return Type Fix: store_memory returns List[MemoryOperation]
[ ] Background Pipeline Complete: _process_memory_window_task fully implemented
```

### Phase X Completion Marker
```markdown
## ✅ PHASE X COMPLETE
- Import Verification: ✅ Pass
- Backend Health: ✅ Pass
- Integration Test: ✅ Pass
- CLI Test: ✅ Pass
- Frontend Test: ✅ Pass
- Transparency: ✅ Pass
- Bug Fixes: ✅ All 5 verified
- Date: [Current Date]
```

---

## Dependency Graph (Execution Order)

```
Phase 1: UV Workspace Setup
    │
    ├── Phase 2: Move Pure Data Models
    │       │
    │       ├── Phase 3: Move Prompts (parallel with Phase 4)
    │       │
    │       └── Phase 4: Create Config Module
    │               │
    │               ├── Phase 5: Refactor Storage Adapters
    │               │       │
    │               │       └── Phase 6: Create LLM Interface
    │               │               │
    │               │               └── Phase 7: Extract Services (depends on 5 + 6)
    │               │                       │
    │               │                       └── Phase 8: Build MemBlocksClient
    │               │                               │
    │               │                               └── Phase 9: Transparency Layer
    │               │                                       │
    │               │                                       ├── Phase 10: Restructure Backend
    │               │                                       │
    │               │                                       └── Phase 11: Move CLI
    │               │                                               │
    │               │                                               └── Phase 12: Cleanup & Verify
    │               │                                                       │
    │               │                                                       └── Phase X: Final Verification
```

**Parallelizable pairs:**
- Phase 3 + Phase 4 (prompts + config — no dependencies on each other)
- Phase 10 + Phase 11 (backend restructure + CLI move — different files)

**Serial dependencies (strict):**
- Phase 1 → everything else
- Phase 5 + 6 → Phase 7 (services need storage adapters and LLM interface)
- Phase 7 → Phase 8 (client needs services)
- Phase 8 → Phase 9 (transparency wires into client)
- Phase 9 → Phase 10 + 11 (backend/CLI need the complete library)
- Phase 10 + 11 → Phase 12 (cleanup after all moves)
- Phase 12 → Phase X (verify after cleanup)

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Circular imports between models and services | Medium | High | Services import models, never reverse. Models are pure data. |
| Background thread issues after removing singletons | Medium | High | MemoryPipeline creates its own event loop / uses asyncio.create_task within the existing loop. Test thoroughly. |
| Missing method during service extraction | Low | Medium | Each phase has import verification. Compare method lists before/after. |
| UV workspace resolution issues | Low | Medium | Test `uv sync` at every phase. Follow UV workspace docs. |
| Frontend breaks due to API changes | Low | Medium | Only one API change (GET→POST for searchMemories). Update frontend simultaneously. |
| Ollama embedding model not pulling correctly | Low | Low | Document in setup guide. Test in Phase 12 integration test. |
