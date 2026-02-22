# memBlocks Refactoring Plan

## 1. What This Refactoring Does and Why

This plan separates memBlocks into three packages:

| Package | Purpose | Lines Today |
|---------|---------|-------------|
| **`memblocks_lib/`** | Installable Python library — the product itself | ~3,030 across 15 files |
| **`backend/`** | Demo FastAPI API + CLI, consumes the library | ~1,116 across 8 files |
| **`frontend/`** | Demo React app (mostly untouched) | ~1,793 |

The library will be centered around a single **`MemBlocksClient`** class that accepts a config object and wires all internal services via constructor injection — no singletons, no globals, fully testable with mocks.

**What changes:**
- Models become pure data (no LLM calls, no DB operations inside Pydantic classes)
- Singletons (`llm_manager`, `mongo_manager`, `VectorDBManager`) become regular instances created by the client
- `ChatService` splits into `ChatEngine` (conversation) + `MemoryPipeline` (background processing)
- An abstract `LLMProvider` ABC lets users plug in any LLM backend (Groq/LangChain is the default implementation)
- A transparency/observability layer exposes every memory operation, retrieval, and pipeline run — not just to internal logs, but through a subscribable event system
- `services/background_utils.py` (which exists only to work around singleton thread-safety) gets deleted entirely
- The incomplete `_process_memory_window_task` (line 288 of `chat_service.py` is literally `pass`) gets fully implemented

**What doesn't change:**
- The memory pipeline flow (PS1 extraction → PS2 conflict resolution → core memory update → recursive summary)
- All 5 prompts stay in one file (user preference)
- `ResourceMemorySection` stubs are preserved in the new structure
- The frontend is untouched

## 2. What's Wrong With the Current Code (12 Specific Problems)

### CRITICAL

**Problem 1: Pydantic Models Contain All Business Logic** (`models/sections.py`, 682 lines)

`SemanticMemorySection(BaseModel)` has 5 methods that make LLM calls, embed vectors, query Qdrant, and run PS2 conflict resolution — all inside a Pydantic model. For example, `store_memory()` (line 166) does:
- Calls `VectorDBManager.get_embedder().embed_text()` (line 190)
- Queries Qdrant via `VectorDBManager.retrieve_from_vector()` (line 192-193)
- Maps Qdrant `ScoredPoint` IDs to simple ints for the LLM (lines 203-209)
- Creates a LangChain structured chain with `PS2_MEMORY_UPDATE_PROMPT` (lines 228-232)
- Executes ADD/UPDATE/DELETE operations on Qdrant (lines 259-336)

Similarly, `CoreMemorySection(BaseModel)` has `create_new_core_memory()` (line 425) which calls LLM via `llm.create_structured_chain(CORE_MEMORY_PROMPT, CoreMemoryOutput)` and `store_memory()` (line 487) which writes directly to MongoDB via `db.save_core_memory()`.

**→ Fix:** Extract all methods to `SemanticMemoryService` and `CoreMemoryService`. Models become pure data holders.

**Problem 2: Three Different Singleton Patterns**

| Singleton | File | Pattern | Problem |
|-----------|------|---------|---------|
| `LLMManager` | `llm/llm_manager.py:28` | `__new__` class-level `_instance` | Can't create a second instance with different config for testing |
| `MongoDBManager` | `vector_db/mongo_manager.py` | Same `__new__` pattern, `mongo_manager = MongoDBManager()` at module level | Same issue; plus `BackgroundMongoDBManager` in `background_utils.py` exists solely to work around this |
| `VectorDBManager` | `vector_db/vector_db_manager.py:9-14` | All static methods + class-level attributes | `client = QdrantClient(host="localhost", port=6333)` runs at **import time** (line 12), `embedder.get_dimension()` makes an HTTP call to Ollama **on import** (line 14) |

The `VectorDBManager` pattern is the worst — just importing the module connects to Qdrant and Ollama. If either is down, the import fails.

**→ Fix:** All three become regular classes instantiated by `MemBlocksClient` with config injection.

### HIGH

**Problem 3: Monolithic ChatService** (`services/chat_service.py`, 653 lines)

One class does everything:
- Message history management (`self.message_history: List[Dict]`, line 180)
- Memory retrieval (`_retrieve_semantic_memories`, line 437)
- Context assembly with XML tags (`_build_system_prompt`, line 455 — builds `<CORE_MEMORY>`, `<CONVERSATION_SUMMARY>`, `<SEMANTIC_MEMORY>` blocks)
- LLM response generation (`send_message`, line 507 — calls `llm_manager.get_chat_llm().ainvoke()`)
- Background thread orchestration (creates `self._bg_loop = asyncio.new_event_loop()` + `self._bg_thread` on line 199-201)
- Background resource initialization (`_init_bg_resources`, line 211 — creates `BackgroundMongoDBManager` and `BackgroundLLMProvider`)
- Task tracking (`BackgroundTaskTracker` inner class, lines 34-121)
- Processing history (`ProcessingHistoryTracker`, lines 123-143)
- Memory window flushing (keeps last `keep_last_n=4` messages, line 353)
- Session metrics and status printing (lines 592-640)

**→ Fix:** Split into `ChatEngine` (conversation flow, context assembly) + `MemoryPipeline` (background processing, task tracking).

**Problem 4: `sys.path` Hacks** (`backend/main.py:3`, `backend/dependencies.py:4`)

Both files have `sys.path.insert(0, str(project_root))` at the top to import from root-level modules. Every router file does the same. This breaks with proper packaging.

**→ Fix:** UV workspace with `memblocks_lib` as an installable dependency for `backend`.

### MEDIUM

**Problem 5: Half-DI Pattern in Models** (`models/sections.py`)

`extract_semantic_memories()` (line 53) accepts `llm_provider=None` and falls back to `global_llm_manager` (line 86). Same pattern in `store_memory()` (line 166, falls back on line 227) and `CoreMemorySection.store_memory()` (line 487, falls back to `mongo_manager` on line 498). The intent was dependency injection, but the fallback to globals defeats the purpose — you can't test without mocking module-level singletons.

**→ Fix:** Services receive their dependencies via constructor. No fallbacks to globals.

**Problem 6: Hardcoded Infrastructure** (`vector_db/vector_db_manager.py:12-14`)

```python
client = QdrantClient(host="localhost", port=6333, prefer_grpc=True)  # line 12
embedder = OllamaEmbeddings()  # line 13 — uses settings internally
vector_size = embedder.get_dimension()  # line 14 — HTTP call on import!
```

Despite `config.py` having `qdrant_host` and `qdrant_port` fields, `VectorDBManager` ignores them entirely.

**→ Fix:** `QdrantAdapter` takes `MemBlocksConfig` in constructor, reads host/port from it.

**Problem 7: Incomplete Memory Pipeline** (`services/chat_service.py:224-288`)

`_process_memory_window_task()` runs semantic extraction (Step 1) and core memory update (Step 2), then hits Step 3 ("Recursive Summary") which is... `pass` on line 288. The method `_generate_recursive_summary_bg()` exists (line 294) but is never called from within the task. Instead, it's called from `_process_memory_window()` (line 339) *after* the task completes, but only because that wrapper orchestrates the sequence — creating a confusing split between what runs in the background thread vs. main thread.

**→ Fix:** `MemoryPipeline.process_memory_window()` will execute all steps (extract → conflict resolve → core update → summarize → flush) as one coherent async flow.

### LOW

**Problem 8: Type Lie** — `SemanticMemorySection.store_memory()` (line 166) says `-> bool` but returns `List[MemoryOperation]` (line 223, 255, 338). Every caller gets back a list, not a boolean.

**Problem 9: Port Typo** — `backend/main.py` line 76 log message says `80001` instead of `8001`.

**Problem 10: API Method Mismatch** — Frontend `searchMemories` sends POST, backend `memory.py` router expects GET.

**Problem 11: Mixed Concerns** — `SessionManager` class lives inside `services/block_service.py` alongside `BlockService`. They manage completely different things.

**Problem 12: The `background_utils.py` Workaround** — `services/background_utils.py` (131 lines) creates `BackgroundMongoDBManager` and `BackgroundLLMProvider` — complete duplicates of the real classes — because the singletons can't be safely used from a background thread's event loop. Once singletons are gone, this file is deleted.

## 3. Target Architecture

### 3.1 Directory Structure

```
memBlocks/                          # UV workspace root
├── pyproject.toml                  # Workspace config: members = ["memblocks_lib", "backend"]
├── docker-compose.yml              # Qdrant + MongoDB + Ollama (unchanged)
├── .env                            # Shared env vars
│
├── memblocks_lib/                  # ★ THE LIBRARY — installable, publishable to PyPI
│   ├── pyproject.toml              # name="memblocks", depends on pydantic/motor/qdrant-client/langchain
│   └── src/memblocks/
│       ├── __init__.py             # Exports: MemBlocksClient, MemBlocksConfig, LLMProvider
│       ├── client.py               # MemBlocksClient — the single entry point
│       ├── config.py               # MemBlocksConfig(BaseSettings) — NOT a singleton
│       │
│       ├── models/                 # Pure Pydantic data — ZERO business logic
│       │   ├── __init__.py         # Re-exports all model classes
│       │   ├── block.py            # MemoryBlock, MemoryBlockMetaData  (from container.py)
│       │   ├── memory.py           # SemanticMemoryData, CoreMemoryData, ResourceMemoryData (from sections.py, stripped)
│       │   ├── units.py            # SemanticMemoryUnit, CoreMemoryUnit, ResourceMemoryUnit, MemoryOperation, ProcessingEvent (from units.py)
│       │   ├── llm_outputs.py      # SemanticMemoriesOutput, CoreMemoryOutput, SummaryOutput, PS2MemoryUpdateOutput (from output_models.py)
│       │   └── transparency.py     # OperationEntry, RetrievalEntry, PipelineRunEntry (new)
│       │
│       ├── llm/                    # Abstract LLM interface + default Groq implementation
│       │   ├── __init__.py
│       │   ├── base.py             # LLMProvider(ABC) — 5 abstract methods
│       │   └── groq_provider.py    # GroqLLMProvider(LLMProvider) — uses langchain_groq
│       │
│       ├── storage/                # Database adapters — regular classes, not singletons
│       │   ├── __init__.py
│       │   ├── mongo.py            # MongoDBAdapter (from mongo_manager.py, de-singletoned)
│       │   ├── qdrant.py           # QdrantAdapter (from vector_db_manager.py, de-singletoned + de-static'd)
│       │   └── embeddings.py       # EmbeddingProvider (from embeddings.py, config-injected)
│       │
│       ├── services/               # All business logic lives here
│       │   ├── __init__.py
│       │   ├── semantic_memory.py  # SemanticMemoryService (logic from SemanticMemorySection methods)
│       │   ├── core_memory.py      # CoreMemoryService (logic from CoreMemorySection methods)
│       │   ├── memory_pipeline.py  # MemoryPipeline (background processing from ChatService)
│       │   ├── chat_engine.py      # ChatEngine (conversation + context assembly from ChatService)
│       │   ├── block_manager.py    # BlockManager (from BlockService in block_service.py)
│       │   ├── user_manager.py     # UserManager (from UserService in user_service.py)
│       │   ├── session_manager.py  # SessionManager (extracted from block_service.py)
│       │   └── transparency.py     # OperationLog, RetrievalLog, ProcessingHistory, EventBus (new)
│       │
│       └── prompts/
│           └── __init__.py         # All 5 prompts: PS1_SEMANTIC_PROMPT, CORE_MEMORY_PROMPT,
│                                   # SUMMARY_SYSTEM_PROMPT, PS2_MEMORY_UPDATE_PROMPT, ASSISTANT_BASE_PROMPT
│
├── backend/                        # Demo app — consumes memblocks_lib as a dependency
│   ├── pyproject.toml              # name="memblocks-backend", depends on memblocks + fastapi + uvicorn
│   └── src/
│       ├── api/
│       │   ├── __init__.py
│       │   ├── main.py             # FastAPI app (from backend/main.py, no sys.path hacks)
│       │   ├── dependencies.py     # get_memblocks_client() FastAPI dependency
│       │   ├── routers/
│       │   │   ├── users.py        # User endpoints (updated to use MemBlocksClient)
│       │   │   ├── blocks.py       # Block endpoints
│       │   │   ├── chat.py         # Chat endpoints
│       │   │   └── memory.py       # Memory search (POST, fixing GET mismatch)
│       │   └── models/
│       │       └── requests.py     # API request Pydantic models (moved from backend/models/)
│       └── cli/
│           └── main.py             # Interactive CLI (from root main.py, 314 lines → uses MemBlocksClient)
│
└── frontend/                       # React app (unchanged except searchMemories POST fix)
    └── ...
```

### 3.2 Where Each Current File Goes

| Current File | Lines | Destination | What Changes |
|---|---|---|---|
| `config.py` | 71 | `memblocks_lib/src/memblocks/config.py` | `Settings` → `MemBlocksConfig`, remove singleton `settings = Settings()` |
| `prompts.py` | 435 | `memblocks_lib/src/memblocks/prompts/__init__.py` | Copy as-is, all 5 constants |
| `models/container.py` | 104 | `memblocks_lib/src/memblocks/models/block.py` | Remove `save()`/`load()` methods (they call `mongo_manager` directly) |
| `models/sections.py` | 682 | Split: `models/memory.py` + `services/semantic_memory.py` + `services/core_memory.py` | **Biggest change.** All methods extracted to services. ResourceMemorySection stubs preserved. |
| `models/units.py` | 156 | `memblocks_lib/src/memblocks/models/units.py` | Copy as-is — already pure data |
| `llm/llm_manager.py` | 103 | `memblocks_lib/src/memblocks/llm/groq_provider.py` | Remove `__new__` singleton. Constructor takes `MemBlocksConfig`. |
| `llm/output_models.py` | 76 | `memblocks_lib/src/memblocks/models/llm_outputs.py` | Copy as-is — already pure data |
| `vector_db/mongo_manager.py` | 267 | `memblocks_lib/src/memblocks/storage/mongo.py` | Remove `__new__` singleton. Constructor takes `MemBlocksConfig` + optional `OperationLog`. |
| `vector_db/vector_db_manager.py` | 168 | `memblocks_lib/src/memblocks/storage/qdrant.py` | Static → instance methods. Class-level client → constructor from config. |
| `vector_db/embeddings.py` | 84 | `memblocks_lib/src/memblocks/storage/embeddings.py` | Constructor takes config instead of reading `settings` global. |
| `services/chat_service.py` | 653 | Split: `services/chat_engine.py` + `services/memory_pipeline.py` | ChatEngine gets conversation. MemoryPipeline gets background processing. |
| `services/block_service.py` | 187 | Split: `services/block_manager.py` + `services/session_manager.py` | Separate `BlockService` and `SessionManager`. |
| `services/user_service.py` | 69 | `memblocks_lib/src/memblocks/services/user_manager.py` | Remove static methods, take `MongoDBAdapter` in constructor. |
| `services/background_utils.py` | 131 | **DELETED** | No longer needed — singletons are gone. |
| `main.py` (root) | 314 | `backend/src/cli/main.py` | Refactor to use `MemBlocksClient`. |
| `backend/main.py` | 189 | `backend/src/api/main.py` | Remove `sys.path` hack, fix port typo, use `MemBlocksClient`. |
| `backend/dependencies.py` | 73 | `backend/src/api/dependencies.py` | Replace in-memory session dict with `MemBlocksClient` dependency. |

### 3.3 Dependency Flow

```
┌──────────────────────────────────────────────────────────┐
│                    MemBlocksClient                        │
│  (creates everything, wires dependencies, exposes API)    │
└──────┬────────┬──────────┬──────────┬──────────┬─────────┘
       │        │          │          │          │
       ▼        ▼          ▼          ▼          ▼
  ChatEngine  MemoryPipeline  BlockManager  UserManager  SessionManager
       │        │    │              │
       │        ▼    ▼              │
       │  SemanticMemoryService     │
       │  CoreMemoryService         │
       │        │    │              │
       ▼        ▼    ▼              ▼
  ┌─────────┐ ┌──────────┐ ┌─────────────────┐
  │LLMProvider│ │QdrantAdapter│ │MongoDBAdapter    │
  │(abstract) │ │(from config)│ │(from config)     │
  └─────────┘ └──────────┘ └─────────────────┘
       │              │              │
       ▼              ▼              ▼
  ┌─────────┐ ┌──────────┐ ┌─────────────────┐
  │Groq API │ │Qdrant DB │ │MongoDB           │
  └─────────┘ └──────────┘ └─────────────────┘
                    ▲
                    │
              EmbeddingProvider
                    │
                    ▼
              ┌──────────┐
              │Ollama API│
              └──────────┘
```

**Key rule:** Dependencies flow downward only. Services never import other services' internals — they receive collaborators via constructor. Models import nothing except `pydantic` and standard library.

## 4. `memblocks_lib` — Detailed Component Design

This section specifies every module in the library by tracing back to the exact current code it replaces, with real method signatures, real line numbers, and real patterns.

### 4.1 `client.py` — `MemBlocksClient`

**What it replaces:** There is no equivalent today. Currently, wiring is done by singletons (`llm_manager` at `llm/llm_manager.py:103`, `mongo_manager` at `vector_db/mongo_manager.py:267`) and by import-time side effects (`VectorDBManager` class-level `client = QdrantClient(...)` at `vector_db/vector_db_manager.py:12`). The client takes over all of that wiring.

**Constructor — dependency injection with sensible defaults:**

```python
class MemBlocksClient:
    def __init__(
        self,
        config: MemBlocksConfig,
        llm_provider: Optional[LLMProvider] = None,       # Plug in your own LLM
        mongo_adapter: Optional[MongoDBAdapter] = None,    # Or your own storage
        qdrant_adapter: Optional[QdrantAdapter] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
    ):
```

**What `__init__` does, in order:**

1. **Creates infrastructure** (replaces all three singletons):
   ```python
   self.mongo = mongo_adapter or MongoDBAdapter(config)
   # Replaces: mongo_manager = MongoDBManager() singleton (mongo_manager.py:267)
   # AND BackgroundMongoDBManager() workaround (background_utils.py:12-78)
   
   self.embeddings = embedding_provider or EmbeddingProvider(config)
   # Replaces: embedder = OllamaEmbeddings() class-level (vector_db_manager.py:13)
   # Constructor reads config.ollama_base_url + config.embeddings_model
   # instead of settings global (embeddings.py:9)
   
   self.qdrant = qdrant_adapter or QdrantAdapter(config, self.embeddings)
   # Replaces: client = QdrantClient(host="localhost", port=6333, prefer_grpc=True)
   # class-level at vector_db_manager.py:12 — now reads config.qdrant_host/port
   # Also replaces: vector_size = embedder.get_dimension() on import (line 14)
   # — dimension is lazily resolved on first collection creation instead
   
   self.llm = llm_provider or GroqLLMProvider(config)
   # Replaces: llm_manager = LLMManager() singleton (llm_manager.py:102-103)
   # AND BackgroundLLMProvider duplicate (background_utils.py:80-131)
   ```

2. **Creates transparency layer** (always-on, replaces partial tracking):
   ```python
   self.event_bus = EventBus()
   # New. 11 subscribable events — see Section 5
   
   self.operation_log = OperationLog()
   # Replaces: ad-hoc print() statements like "✓ Added new memory" (sections.py:218)
   # and "✓ Deleted vector" (vector_db_manager.py:164)
   
   self.retrieval_log = RetrievalLog()
   # Replaces: nothing — retrieval was invisible. ChatService._retrieve_semantic_memories
   # (chat_service.py:437) returned memories but never logged what was retrieved or why
   
   self.processing_history = ProcessingHistory()
   # Replaces: ProcessingHistoryTracker (chat_service.py:123-143) — same concept but
   # now lives in the client, not buried inside ChatService
   ```

3. **Creates services** (replaces logic currently inside models and monolithic ChatService):
   ```python
   self.users = UserManager(self.mongo)
   # Replaces: UserService with @staticmethod methods using mongo_manager global (user_service.py:7-66)
   
   self.blocks = BlockManager(self.mongo, self.qdrant)
   # Replaces: BlockService with @staticmethod methods (block_service.py:13-143)
   # BlockService.create_block() currently calls VectorDBManager.create_collection() directly (line 56)
   # and mongo_manager.save_core_memory() (line 72) — BlockManager receives adapters instead
   
   self.sessions = SessionManager(self.mongo)
   # Replaces: SessionManager class in block_service.py:146-183
   # Currently in-memory only (self.active_sessions: dict). Will persist to MongoDB.
   
   self.semantic_memory = SemanticMemoryService(
       self.llm, self.embeddings, self.qdrant,
       self.operation_log, self.event_bus
   )
   # Replaces: All methods on SemanticMemorySection(BaseModel) in sections.py:
   #   extract_semantic_memories()  — lines 53-125
   #   store_memory()               — lines 166-338 (the 172-line PS2 monster)
   #   retrieve_memories()          — lines 344-378
   #   extract_and_store_memories() — lines 127-160
   
   self.core_memory = CoreMemoryService(
       self.llm, self.mongo,
       self.operation_log, self.event_bus
   )
   # Replaces: All methods on CoreMemorySection(BaseModel) in sections.py:
   #   create_new_core_memory() — lines 425-485
   #   store_memory()           — lines 487-507
   #   get_memories()           — lines 509-529
   
   self.pipeline = MemoryPipeline(
       self.semantic_memory, self.core_memory, self.llm,
       self.processing_history, self.event_bus, config
   )
   # Replaces: Background processing in ChatService:
   #   _process_memory_window_task()     — lines 224-292 (incomplete — line 288 is `pass`)
   #   _process_memory_window()          — lines 323-364 (orchestrator)
   #   _generate_recursive_summary_bg()  — lines 294-321
   #   _trigger_memory_processing()      — lines 403-431
   #   BackgroundTaskTracker             — lines 34-121
   # Also replaces: The separate background event loop + thread:
   #   self._bg_loop = asyncio.new_event_loop()   (line 199)
   #   self._bg_thread = threading.Thread(...)     (line 200)
   
   self.chat = ChatEngine(
       self.llm, self.semantic_memory, self.core_memory,
       self.pipeline, self.retrieval_log, self.event_bus, config
   )
   # Replaces: The conversation half of ChatService (chat_service.py):
   #   send_message()             — lines 507-565
   #   _retrieve_semantic_memories() — lines 437-447
   #   _build_system_prompt()     — lines 455-501
   #   _get_core_memory()         — lines 449-453
   ```

**Key difference from current code:** Today `ChatService.__init__` (line 158) takes a `MemoryBlock` and uses its `.semantic_memories` / `.core_memories` attributes (which are `SemanticMemorySection` / `CoreMemorySection` Pydantic models with embedded business logic). In the new design, `ChatEngine` receives *services* instead. The `MemoryBlock` becomes pure data — it just carries collection names and block IDs. Services use those identifiers to operate on the databases directly.

### 4.2 `config.py` — `MemBlocksConfig`

**What it replaces:** `config.py` (71 lines) — specifically the `Settings(BaseSettings)` class (line 18) and the module-level singleton `settings = Settings()` (line 68). Every module currently imports `from config import settings` to access config values.

**What changes:**
- Class name: `Settings` → `MemBlocksConfig` (clearer as a library export)
- No module-level singleton. Users create an instance: `config = MemBlocksConfig()` 
- `.env` path resolution changes — currently `_ENV_FILE = Path(__file__).resolve().parent / ".env"` (config.py:15) is hardcoded relative to the source file. In the library, `env_file` defaults to `".env"` (cwd) but can be overridden by the caller.
- New fields: `memory_window` and `keep_last_n` (currently hardcoded in `ChatService.__init__` at chat_service.py:161-162 as `memory_window: int = 10, keep_last_n: int = 4`)
- New field: `mongodb_database_name` (currently hardcoded as `"memblocks"` at mongo_manager.py:47: `self._db = self._client.memblocks`)

```python
class MemBlocksConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- LLM (from current config.py lines 40-57) ---
    groq_api_key: Optional[str] = Field(None, env="GROQ_API_KEY")
    llm_model: str = Field("meta-llama/llama-4-maverick-17b-128e-instruct", env="LLM_MODEL")
    llm_convo_temperature: float = Field(0.7, env="LLM_CONVO_TEMPERATURE")
    llm_semantic_extraction_temperature: float = Field(0.0, env="LLM_SEMANTIC_EXTRACTION_TEMPERATURE")
    llm_core_extraction_temperature: float = Field(0.0, env="LLM_CORE_EXTRACTION_TEMPERATURE")
    llm_recursive_summary_gen_temperature: float = Field(0.3, env="LLM_RECURSIVE_SUMMARY_GEN_TEMPERATURE")
    llm_memory_update_temperature: float = Field(0.0, env="LLM_MEMORY_UPDATE_TEMPERATURE")

    # --- Embeddings (from current config.py lines 29-32) ---
    ollama_base_url: str = Field("http://localhost:11434", env="OLLAMA_BASE_URL")
    embeddings_model: str = Field("nomic-embed-text", env="EMBEDDINGS_MODEL")

    # --- MongoDB (connection string from config.py:26-28, db name from mongo_manager.py:47) ---
    mongodb_connection_string: Optional[str] = Field(None, env="MONGODB_CONNECTION_STRING")
    mongodb_database_name: str = Field("memblocks", env="MONGODB_DATABASE_NAME")
    # NEW: collection names (currently hardcoded as attribute names in mongo_manager.py:50-52)
    mongo_collection_users: str = "users"
    mongo_collection_blocks: str = "blocks"
    mongo_collection_core_memories: str = "core_memories"

    # --- Qdrant (from current config.py lines 35-37) ---
    qdrant_host: str = Field("localhost", env="QDRANT_HOST")
    qdrant_port: int = Field(6333, env="QDRANT_PORT")
    qdrant_prefer_grpc: bool = Field(True, env="QDRANT_PREFER_GRPC")

    # --- Memory pipeline (from ChatService.__init__ hardcoded defaults, chat_service.py:161-163) ---
    memory_window: int = Field(10, env="MEMORY_WINDOW")
    keep_last_n: int = Field(4, env="KEEP_LAST_N")
    max_concurrent_processing: int = Field(1, env="MAX_CONCURRENT_PROCESSING")

    # --- Monitoring (from config.py lines 60-62) ---
    arize_space_id: Optional[str] = Field(None, env="ARIZE_SPACE_ID")
    arize_api_key: Optional[str] = Field(None, env="ARIZE_API_KEY")
    arize_project_name: str = Field("memBlocks", env="ARIZE_PROJECT_NAME")
```

**Diff from current `Settings`:** +3 new fields (`mongodb_database_name`, `memory_window`, `keep_last_n`, `max_concurrent_processing`, collection names). The 5 LLM temperature fields and all existing env mappings are preserved exactly. The `_ENV_FILE` path hack is removed — standard `env_file=".env"` behavior.

### 4.3 `models/` — Pure Data (Zero Business Logic)

**The rule:** No model class may import anything from `llm/`, `storage/`, or `services/`. Models import only `pydantic`, `typing`, `datetime`, and other models.

**`models/block.py`** (from `models/container.py`, 104 lines)

Keep: `MemoryBlockMetaData` (line 8), `MemoryBlock` (line 15), `to_dict()` (line 45), `from_dict()` (line 63).

Remove: `save()` (line 83 — calls `mongo_manager.save_block()` directly) and `load()` (line 88 — calls `mongo_manager.load_block()`). These become `BlockManager.save_block()` and `BlockManager.load_block()` in the services layer.

Remove: `from vector_db.mongo_manager import mongo_manager` (container.py:6) — the model no longer knows about MongoDB.

The section reference fields (`semantic_memories`, `core_memories`, `resource_memories`) change type. Currently they are `SemanticMemorySection` / `CoreMemorySection` / `ResourceMemorySection` — Pydantic models that carry business logic. In the new structure, they become simple string identifiers:

```python
class MemoryBlock(BaseModel):
    meta_data: MemoryBlockMetaData
    name: str
    description: str
    # Was: semantic_memories: Optional[SemanticMemorySection]
    # Now: just the collection name string
    semantic_collection: Optional[str] = None
    # Was: core_memories: Optional[CoreMemorySection]
    # Now: just the block_id that keys into MongoDB core_memories
    core_memory_block_id: Optional[str] = None
    # Was: resource_memories: Optional[ResourceMemorySection]
    # Now: just the collection name string (preserved for future use)
    resource_collection: Optional[str] = None
```

This eliminates the need for the `model_validator` hacks in `SemanticMemorySection` (sections.py:35-47) and `CoreMemorySection` (sections.py:417-423) that allowed initializing a section from a bare string.

**`models/memory.py`** (extracted from `models/sections.py`, 682 lines)

The three `*Section` classes currently live in `sections.py` and contain all business logic. After extraction, the only things left as models are the *data shapes* these sections carry. However, `SemanticMemorySection` and `CoreMemorySection` don't actually hold data beyond their identifiers (collection name / block ID), and those identifiers now live on `MemoryBlock` (see above). So `models/memory.py` is primarily for:

- `ResourceMemoryData(BaseModel)` — preserves the `ResourceMemorySection` stub fields (type, collection_name) for future implementation.
- Any new data shapes needed by the transparency layer (see `models/transparency.py`).

**`models/units.py`** (from `models/units.py`, 156 lines — **copy as-is**)

Already pure data. Contains:
- `MemoryUnitMetaData` (line 5) — usage timestamps, status, parent IDs
- `SemanticMemoryUnit` (line 21) — content, type, confidence, keywords, embedding_text, entities
- `CoreMemoryUnit` (line 91) — persona_content, human_content
- `ResourceMemoryUnit` (line 108) — content, resource_type, resource_link
- `MemoryOperation` (line 127) — operation type (ADD/UPDATE/DELETE/NONE), memory_id, content, old_content
- `ProcessingEvent` (line 142) — event_id, timestamp, messages_processed, operations list

No changes needed. These classes have zero imports from `llm/`, `vector_db/`, or `services/`.

**`models/llm_outputs.py`** (from `llm/output_models.py`, 76 lines — **copy as-is**)

Already pure data. Contains all structured output schemas the LLM returns:
- `SemanticExtractionOutput` (line 7) — keywords, content, type, entities, confidence
- `SemanticMemoriesOutput` (line 17) — list of `SemanticExtractionOutput`
- `CoreMemoryOutput` (line 23) — persona_content, human_content
- `SummaryOutput` (line 34) — summary string
- `PS2NewMemoryOperation` (line 42) — operation (ADD/NONE), reason
- `PS2ExistingMemoryOperation` (line 53) — id, operation (UPDATE/DELETE/NONE), updated_memory dict, reason
- `PS2MemoryUpdateOutput` (line 68) — new_memory_operation + list of existing_memory_operations

No changes needed.

**`models/transparency.py`** (new — data shapes for the observability layer)

```python
class OperationEntry(BaseModel):
    """One logged database write operation."""
    timestamp: str
    db_type: Literal["mongo", "qdrant"]
    operation: Literal["insert", "update", "upsert", "delete"]
    collection: str
    document_id: Optional[str] = None
    summary: str  # Human-readable, e.g. "Added semantic memory: 'User likes hiking...'"

class RetrievalEntry(BaseModel):
    """One logged memory retrieval."""
    timestamp: str
    query: str
    source: Literal["semantic", "core", "resource"]
    results_count: int
    top_score: Optional[float] = None
    memories_returned: List[str]  # content previews

class PipelineRunEntry(BaseModel):
    """One complete pipeline run record."""
    run_id: str
    started_at: str
    completed_at: Optional[str] = None
    status: Literal["running", "completed", "failed"]
    messages_processed: int
    semantic_extracted: int = 0
    semantic_stored: int = 0
    core_updated: bool = False
    summary_generated: bool = False
    operations: List[MemoryOperation] = []
    error: Optional[str] = None
```

### 4.4 `llm/` — Abstract LLM Interface

**What it replaces:** `llm/llm_manager.py` (103 lines) — the `LLMManager` singleton, plus `services/background_utils.py:80-131` — the `BackgroundLLMProvider` duplicate.

The current `LLMManager` exposes two methods that services actually call:
1. `create_structured_chain(system_prompt, pydantic_model, temperature)` → returns a LangChain `Runnable` (llm_manager.py:69-99). Used by `SemanticMemorySection.extract_semantic_memories()` (sections.py:87-88), `store_memory()` (sections.py:228-232), `CoreMemorySection.create_new_core_memory()` (sections.py:466-467), and `ChatService._generate_recursive_summary_bg()` (chat_service.py:310-311).
2. `get_chat_llm(temperature)` → returns a `ChatGroq` instance (llm_manager.py:56-67). Used by `ChatService.send_message()` (chat_service.py:536).

**`llm/base.py` — `LLMProvider(ABC)`**

The abstract interface mirrors these two actual call patterns, plus `ainvoke` for direct chat:

```python
from abc import ABC, abstractmethod
from typing import Optional, Type
from pydantic import BaseModel

class LLMProvider(ABC):
    @abstractmethod
    def create_structured_chain(
        self,
        system_prompt: str,
        pydantic_model: Type[BaseModel],
        temperature: float = 0.0,
    ) -> Any:
        """Return a runnable chain that accepts {"input": str} and returns a pydantic_model instance.
        
        Must support: result = await chain.ainvoke({"input": user_input})
        
        Currently called by:
        - SemanticMemoryService (PS1 extraction + PS2 conflict resolution)
        - CoreMemoryService (core memory creation)
        - MemoryPipeline (recursive summary generation)
        """
        ...

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
    ) -> str:
        """Send a list of {"role": ..., "content": ...} messages and return the assistant's response text.
        
        Currently called by ChatEngine.send_message() — replaces:
          llm = llm_manager.get_chat_llm(temperature=settings.llm_convo_temperature)
          response = await llm.ainvoke(messages)  # chat_service.py:536-537
          assistant_response = response.content     # chat_service.py:538
        """
        ...
```

Note: The v1 plan had 4 domain-specific abstract methods (`extract_semantic_memories`, `extract_core_memories`, `generate_summary`, `resolve_conflicts`). That was wrong — those are *service* methods, not LLM methods. The LLM interface should be generic (structured chain + direct chat). Services compose prompts and call the generic interface.

**`llm/groq_provider.py` — `GroqLLMProvider(LLMProvider)`**

Default implementation using `langchain_groq.ChatGroq`. Mirrors the logic from `LLMManager._initialize_llm()` (llm_manager.py:37-47) and `create_structured_chain()` (llm_manager.py:69-99):

```python
class GroqLLMProvider(LLMProvider):
    def __init__(self, config: MemBlocksConfig):
        self._config = config
        api_key = config.groq_api_key
        if not api_key:
            raise ValueError("GROQ_API_KEY not found — set it in .env or pass to MemBlocksConfig")
        self._api_key = api_key
        self._model = config.llm_model
        # Optional: Arize instrumentation (from llm_manager.py:9-19)
        # Only if config.arize_space_id and config.arize_api_key are set

    def create_structured_chain(self, system_prompt, pydantic_model, temperature=0.0):
        # Exact same logic as llm_manager.py:69-99:
        # 1. ChatGroq(model=self._model, temperature=temperature, groq_api_key=self._api_key)
        # 2. llm.with_structured_output(pydantic_model, method="json_schema", include_raw=False)
        # 3. ChatPromptTemplate.from_messages([("system", system_prompt), ("user", "{input}")])
        # 4. return prompt | structured_llm
        ...

    async def chat(self, messages, temperature=None):
        # Replaces llm_manager.get_chat_llm(temperature) + await llm.ainvoke(messages)
        # Returns response.content (str)
        ...
```

**What gets deleted:** `BackgroundLLMProvider` (background_utils.py:80-131) — it exists because `LLMManager` is a singleton and can't be safely shared across threads. With `GroqLLMProvider` being a regular class, we just pass the same instance or create a new one. The Arize instrumentation module-level side-effect (llm_manager.py:9-19) moves into the constructor, conditional on config.

### 4.5 `storage/` — Database Adapters (De-Singletoned)

**`storage/mongo.py` — `MongoDBAdapter`**

**What it replaces:** `vector_db/mongo_manager.py` (267 lines) — the `MongoDBManager` singleton with `__new__` pattern (line 17) and module-level instance `mongo_manager = MongoDBManager()` (line 267). Also replaces `BackgroundMongoDBManager` (background_utils.py:12-78) entirely.

**Changes from `MongoDBManager`:**
1. Constructor takes `MemBlocksConfig` instead of reading `settings` global (mongo_manager.py:42):
   ```python
   class MongoDBAdapter:
       def __init__(self, config: MemBlocksConfig):
           self._client = AsyncIOMotorClient(config.mongodb_connection_string)
           self._db = self._client[config.mongodb_database_name]
           # Was: self._db = self._client.memblocks (hardcoded, mongo_manager.py:47)
           self.users = self._db[config.mongo_collection_users]
           self.blocks = self._db[config.mongo_collection_blocks]
           self.core_memories = self._db[config.mongo_collection_core_memories]
   ```
2. No `__new__` override, no `_instance` class variable. It's a regular class.
3. Same 10 async methods preserved, same signatures:
   - User ops: `create_user()` (line 58), `get_user()` (line 81), `add_block_to_user()` (line 94), `list_users()` (line 111)
   - Block ops: `save_block()` (line 121), `load_block()` (line 144), `list_user_blocks()` (line 157), `delete_block()` (line 175)
   - Core memory ops: `save_core_memory()` (line 192), `get_core_memory()` (line 230), `delete_core_memory()` (line 243)
   - Utility: `close()` (line 260)
4. The `_serialize_doc()` static helper (line 26) is preserved as-is — converts `ObjectId` to string.

**Why `BackgroundMongoDBManager` is deleted:** It's a copy-paste of `MongoDBManager` that exists only because the singleton pattern prevents creating a second Motor client for the background thread (background_utils.py:26 comment: "Create a NEW client instance, bypassing the singleton logic"). With `MongoDBAdapter` being a regular class, you can create as many instances as needed — one for the main loop, one for the background loop, or share one.

**`storage/qdrant.py` — `QdrantAdapter`**

**What it replaces:** `vector_db/vector_db_manager.py` (168 lines) — the all-static `VectorDBManager` class with class-level attributes that execute on import (lines 12-14).

**Changes from `VectorDBManager`:**
1. **No import-time connections.** The current code runs at import:
   ```python
   # vector_db_manager.py:12-14 — runs when any module imports VectorDBManager
   client = QdrantClient(host="localhost", port=6333, prefer_grpc=True)
   embedder = OllamaEmbeddings()
   vector_size = embedder.get_dimension()  # HTTP call to Ollama!
   ```
   New code: constructor takes config, creates client lazily:
   ```python
   class QdrantAdapter:
       def __init__(self, config: MemBlocksConfig, embeddings: EmbeddingProvider):
           self._client = QdrantClient(
               host=config.qdrant_host,       # Was: hardcoded "localhost" 
               port=config.qdrant_port,        # Was: hardcoded 6333
               prefer_grpc=config.qdrant_prefer_grpc
           )
           self._embeddings = embeddings
           self._vector_size: Optional[int] = None  # Lazy — resolved on first create_collection
   ```

2. **Static → instance methods.** All 6 methods lose `@staticmethod` and `VectorDBManager.get_client()` calls:
   - `create_collection(collection_name)` (was line 29) — now uses `self._client` and lazy `self._get_vector_size()`
   - `store_vector(collection_name, vector, payload, point_id=None)` (was line 61) — same logic, `self._client.upsert()`
   - `retrieve_from_vector(collection_name, query_vector, top_k=5)` (was line 88) — `self._client.query_points()`
   - `retrieve_from_payload(collection_name, payload_filter, top_k=5)` (was line 111) — `self._client.scroll()`
   - `delete_vector(collection_name, point_id)` (was line 146) — `self._client.delete()`
   - `get_embedder()` → removed (the `EmbeddingProvider` is accessed through the service, not through the DB adapter)

3. **Config-driven:** Uses `config.qdrant_host` and `config.qdrant_port` instead of ignoring them (see Problem 6 in Section 2).

**`storage/embeddings.py` — `EmbeddingProvider`**

**What it replaces:** `vector_db/embeddings.py` (84 lines) — the `OllamaEmbeddings` class.

**Changes from `OllamaEmbeddings`:**
1. Constructor currently uses settings global as default args: `def __init__(self, model=settings.embeddings_model, base_url=settings.ollama_base_url)` (embeddings.py:9). New constructor takes `MemBlocksConfig`:
   ```python
   class EmbeddingProvider:
       def __init__(self, config: MemBlocksConfig):
           self._model = config.embeddings_model
           self._base_url = config.ollama_base_url
           self._endpoint = f"{config.ollama_base_url}/api/embeddings"
   ```

2. Same three methods, same signatures:
   - `embed_text(text: str) -> List[float]` (was line 14) — synchronous `requests.post()`, unchanged
   - `embed_documents(texts: List[str]) -> List[List[float]]` (was line 35) — `ThreadPoolExecutor`, unchanged
   - `get_dimension() -> int` (was line 40) — makes a test embedding call, unchanged

3. **No `settings` import at module level.** The current `embeddings.py:4` does `from config import settings` and uses it in the default parameter, which evaluates at import time.

### 4.6 `services/` — All Business Logic

Every method currently embedded inside a Pydantic model or the monolithic `ChatService` moves here. Services receive dependencies via constructor — no globals, no fallbacks.

**`services/semantic_memory.py` — `SemanticMemoryService`**

**What it replaces:** All 4 methods on `SemanticMemorySection(BaseModel)` in `models/sections.py`:

| Current Method (on Pydantic model) | New Method (on service) | Lines |
|---|---|---|
| `SemanticMemorySection.extract_semantic_memories(messages, ps1_prompt, llm_provider)` | `SemanticMemoryService.extract(messages, collection_name, ps1_prompt)` | sections.py:53-125 |
| `SemanticMemorySection.store_memory(memory_unit, llm_provider)` | `SemanticMemoryService.store(memory_unit, collection_name)` | sections.py:166-338 |
| `SemanticMemorySection.extract_and_store_memories(messages, ps1_prompt, min_confidence, llm_provider)` | `SemanticMemoryService.extract_and_store(messages, collection_name, min_confidence)` | sections.py:127-160 |
| `SemanticMemorySection.retrieve_memories(query_texts, top_k)` | `SemanticMemoryService.retrieve(query_texts, collection_name, top_k)` | sections.py:344-378 |

```python
class SemanticMemoryService:
    def __init__(
        self,
        llm: LLMProvider,
        embeddings: EmbeddingProvider,
        qdrant: QdrantAdapter,
        operation_log: OperationLog,
        event_bus: EventBus,
    ):
        self._llm = llm
        self._embeddings = embeddings
        self._qdrant = qdrant
        self._log = operation_log
        self._bus = event_bus
```

**Key method: `store()` — the 172-line PS2 conflict resolution flow**

This is the most complex method in the codebase (sections.py:166-338). The logic is preserved exactly, but dependencies are injected instead of accessed via globals:

| Current code (sections.py) | New code |
|---|---|
| `embedder = VectorDBManager.get_embedder()` (line 181) | `self._embeddings.embed_text(...)` |
| `VectorDBManager.retrieve_from_vector(self.collection_name, ...)` (line 192) | `self._qdrant.retrieve_from_vector(collection_name, ...)` |
| `llm = llm_provider or global_llm_manager` (line 227) | `self._llm.create_structured_chain(...)` — no fallback |
| `VectorDBManager.store_vector(self.collection_name, ...)` (lines 213, 248, 261, 302) | `self._qdrant.store_vector(collection_name, ...)` |
| `VectorDBManager.delete_vector(self.collection_name, ...)` (line 324) | `self._qdrant.delete_vector(collection_name, ...)` |
| `print(f"✓ Added new memory: ...")` (line 218, 266, etc.) | `self._log.record(...)` + `self._bus.emit("memory_stored", ...)` |

The `collection_name` parameter is passed explicitly instead of being stored as `self.collection_name` on the Pydantic model (sections.py:31-33).

**Fix: Return type lie.** Current `store_memory()` at line 166 declares `-> bool` but returns `List[MemoryOperation]` at lines 223, 255, 338. New `store()` correctly declares `-> List[MemoryOperation]`.

**`services/core_memory.py` — `CoreMemoryService`**

**What it replaces:** All 3 methods on `CoreMemorySection(BaseModel)` in `models/sections.py`:

| Current Method | New Method | Lines |
|---|---|---|
| `CoreMemorySection.create_new_core_memory(messages, old_core_memory, core_creation_prompt, llm_provider)` | `CoreMemoryService.create_or_update(messages, block_id, prompt)` | sections.py:425-485 |
| `CoreMemorySection.store_memory(memory_unit, db_provider)` | `CoreMemoryService.save(block_id, memory_unit)` | sections.py:487-507 |
| `CoreMemorySection.get_memories(db_provider)` | `CoreMemoryService.get(block_id)` | sections.py:509-529 |

```python
class CoreMemoryService:
    def __init__(
        self,
        llm: LLMProvider,
        mongo: MongoDBAdapter,
        operation_log: OperationLog,
        event_bus: EventBus,
    ):
        self._llm = llm
        self._mongo = mongo
        self._log = operation_log
        self._bus = event_bus
```

The half-DI pattern is eliminated:
- `llm = llm_provider or global_llm_manager` (sections.py:465) → `self._llm` always
- `db = db_provider or mongo_manager` (sections.py:498, 519) → `self._mongo` always

**`services/chat_engine.py` — `ChatEngine`**

**What it replaces:** The conversation half of `ChatService` in `services/chat_service.py` (653 lines). Specifically:

| Current Method (ChatService) | New Method (ChatEngine) | Lines |
|---|---|---|
| `send_message(user_message)` | `send_message(user_message, block)` | chat_service.py:507-565 |
| `_retrieve_semantic_memories(query, top_k)` | `_retrieve_semantic(query, collection_name, top_k)` | chat_service.py:437-447 |
| `_get_core_memory()` | `_get_core(block_id)` | chat_service.py:449-453 |
| `_build_system_prompt(semantic_memories, core_memory, base_prompt)` | `_build_system_prompt(semantic_memories, core_memory, summary)` | chat_service.py:455-501 |

```python
class ChatEngine:
    def __init__(
        self,
        llm: LLMProvider,
        semantic_memory: SemanticMemoryService,
        core_memory: CoreMemoryService,
        pipeline: MemoryPipeline,
        retrieval_log: RetrievalLog,
        event_bus: EventBus,
        config: MemBlocksConfig,
    ):
        self._llm = llm
        self._semantic = semantic_memory
        self._core = core_memory
        self._pipeline = pipeline
        self._retrieval_log = retrieval_log
        self._bus = event_bus
        self._config = config
        
        # Per-session state (was on ChatService, chat_service.py:180-181)
        self.message_history: List[Dict[str, str]] = []
        self.recursive_summary: str = ""
```

**Context assembly** (`_build_system_prompt`) is preserved exactly — the XML tag format `<CORE_MEMORY>`, `<CONVERSATION_SUMMARY>`, `<SEMANTIC_MEMORY>` from chat_service.py:482-499 is unchanged. The base prompt is `ASSISTANT_BASE_PROMPT` from `prompts.py`.

**Key change in `send_message()`:** Currently (chat_service.py:536-538):
```python
llm = llm_manager.get_chat_llm(temperature=settings.llm_convo_temperature)
response = await llm.ainvoke(messages)
assistant_response = response.content
```
Becomes:
```python
assistant_response = await self._llm.chat(messages, temperature=self._config.llm_convo_temperature)
```
Single line, uses the abstract `LLMProvider.chat()` method.

**Memory window trigger** (chat_service.py:549-553) stays the same — when `len(self.message_history) >= self._config.memory_window`, call `self._pipeline.trigger(...)`.

**`services/memory_pipeline.py` — `MemoryPipeline`**

**What it replaces:** The background processing half of `ChatService`:
- `_process_memory_window_task()` (chat_service.py:224-292) — **the incomplete method with `pass` at line 288**
- `_process_memory_window()` (chat_service.py:323-364) — the orchestrator
- `_generate_recursive_summary_bg()` (chat_service.py:294-321) — summary generation
- `_generate_recursive_summary()` (chat_service.py:366-401) — duplicate of above for main thread
- `_trigger_memory_processing()` (chat_service.py:403-431) — creates asyncio task
- `BackgroundTaskTracker` (chat_service.py:34-121) — task status tracking
- `ProcessingHistoryTracker` (chat_service.py:123-143) — event tracking

```python
class MemoryPipeline:
    def __init__(
        self,
        semantic_memory: SemanticMemoryService,
        core_memory: CoreMemoryService,
        llm: LLMProvider,
        processing_history: ProcessingHistory,
        event_bus: EventBus,
        config: MemBlocksConfig,
    ):
        self._semantic = semantic_memory
        self._core = core_memory
        self._llm = llm
        self._history = processing_history
        self._bus = event_bus
        self._config = config
        self._semaphore = asyncio.Semaphore(config.max_concurrent_processing)
```

**The complete pipeline flow** (fixing the incomplete current implementation):

```python
async def process_window(
    self,
    messages: List[Dict[str, str]],
    block: MemoryBlock,
    current_summary: str,
) -> PipelineResult:
    """
    Execute the full memory pipeline. Currently broken into 3 steps in
    _process_memory_window_task (chat_service.py:224-292) but Step 3 is `pass`.
    
    This method unifies all steps:
    1. PS1: Semantic extraction (was chat_service.py:240-254)
    2. PS2: Store with conflict resolution (was chat_service.py:249-253)
    3. Core memory update (was chat_service.py:256-269)
    4. Recursive summary (was chat_service.py:271-288 — THE MISSING STEP)
    5. Return results for ChatEngine to flush history
    """
```

**Key fix:** Step 3 in the current code (chat_service.py:271-288) is:
```python
print(f"   → STEP 3: Recursive Summary...")
# ... comments about thread safety ...
pass  # <-- THIS IS THE BUG
```
The `_generate_recursive_summary_bg()` method (line 294) exists but is called from `_process_memory_window()` (line 339) as a *separate* step after the task, creating a confusing split. The new `MemoryPipeline.process_window()` runs all steps sequentially in one coherent async flow.

**Background threading eliminated.** The current approach:
```python
# chat_service.py:199-201
self._bg_loop = asyncio.new_event_loop()
self._bg_thread = threading.Thread(target=self._run_bg_loop, daemon=True)
self._bg_thread.start()
```
This exists because the singletons (`MongoDBManager`, `LLMManager`) can't be shared across event loops. With regular class instances, the pipeline runs as an `asyncio.create_task()` on the main event loop — no separate thread, no `asyncio.run_coroutine_threadsafe()`, no `asyncio.wrap_future()`. The entire `background_utils.py` (131 lines) is deleted.

**`services/block_manager.py` — `BlockManager`**

**What it replaces:** `BlockService` in `services/block_service.py:13-143` — all `@staticmethod` methods.

```python
class BlockManager:
    def __init__(self, mongo: MongoDBAdapter, qdrant: QdrantAdapter):
        self._mongo = mongo
        self._qdrant = qdrant
```

Methods, same logic:
- `create_block(user_id, name, description, ...)` — was `BlockService.create_block()` (block_service.py:17-96). Currently calls `VectorDBManager.create_collection()` (line 56) and `mongo_manager.save_core_memory()` (line 72) directly. New version calls `self._qdrant.create_collection()` and `self._mongo.save_core_memory()`.
- `load_block(block_id)` — was `BlockService.load_block()` (line 99-109). Currently calls `MemoryBlock.load()` which calls `mongo_manager.load_block()`. New version calls `self._mongo.load_block()` + `MemoryBlock.from_dict()`.
- `list_user_blocks(user_id)` — was `BlockService.list_user_blocks()` (line 112-127). Same pattern.
- `delete_block(block_id, user_id)` — was `BlockService.delete_block()` (line 130-143). TODO comment preserved — full deletion (Qdrant collections + MongoDB) to be implemented properly.

**`services/user_manager.py` — `UserManager`**

**What it replaces:** `UserService` in `services/user_service.py` (69 lines) — all `@staticmethod` methods.

```python
class UserManager:
    def __init__(self, mongo: MongoDBAdapter):
        self._mongo = mongo
```

Methods, same logic:
- `create_user(user_id, metadata)` — was `UserService.create_user()` (user_service.py:11-30). Replaces `mongo_manager.create_user()` call (line 28) with `self._mongo.create_user()`.
- `get_user(user_id)` — was `UserService.get_user()` (line 33-43). Same.
- `list_users()` — was `UserService.list_users()` (line 46-48). Same.
- `get_or_create_user(user_id)` — was `UserService.get_or_create_user()` (line 51-65). Same.

**`services/session_manager.py` — `SessionManager`**

**What it replaces:** `SessionManager` class in `services/block_service.py:146-183` — currently shares a file with `BlockService` (see Problem 11).

Current implementation is **in-memory only** (line 150: `self.active_sessions: dict[str, dict] = {}`). In the new design, the constructor takes `MongoDBAdapter` and persists sessions to MongoDB. Same 5 method signatures:
- `create_session(user_id)` → returns session_id
- `attach_block(session_id, block_id)`
- `detach_block(session_id)`
- `get_attached_block(session_id)` → returns block_id or None
- `get_session(session_id)` → returns session dict or None

**Message history storage:** Currently messages live in `ChatEngine.message_history` (in-memory list) and `backend/dependencies.py:active_chat_sessions`. The new `SessionManager` gains a `messages` sub-collection in MongoDB and becomes the source of truth for all message history. Add methods:
- `add_message(session_id, role, content)` — appends to message list in MongoDB
- `get_messages(session_id, limit)` — retrieves message history from MongoDB
- `clear_messages(session_id)` — clears after pipeline processes a window

This replaces the in-memory `ChatEngine.message_history` list and `active_chat_sessions` dict.

### 4.7 `prompts/` — All Prompts in One File

**What it replaces:** `prompts.py` (435 lines) — copy as-is into `memblocks_lib/src/memblocks/prompts/__init__.py`.

All 5 prompt constants, unchanged:
1. `PS1_SEMANTIC_PROMPT` — used by `SemanticMemoryService.extract()` (was sections.py:88)
2. `PS2_MEMORY_UPDATE_PROMPT` — used by `SemanticMemoryService.store()` (was sections.py:229)
3. `CORE_MEMORY_PROMPT` — used by `CoreMemoryService.create_or_update()` (was sections.py:429)
4. `SUMMARY_SYSTEM_PROMPT` — used by `MemoryPipeline._generate_summary()` (was chat_service.py:311/391)
5. `ASSISTANT_BASE_PROMPT` — used by `ChatEngine._build_system_prompt()` (was chat_service.py:459)

User explicitly confirmed: keep all prompts in one file, not split across modules.

## 5. Transparency & Observability

**What exists today:** Almost nothing. The current code tracks operations through scattered `print()` statements (e.g., `"✓ Added new memory"` at sections.py:218, `"✓ Deleted vector"` at vector_db_manager.py:164) and a `ProcessingHistoryTracker` (chat_service.py:123-143) that records `ProcessingEvent` objects but is buried inside `ChatService` with no external access. `BackgroundTaskTracker` (chat_service.py:34-121) tracks task status but only within the `ChatService` instance.

The new design makes transparency a first-class library feature, always-on (no opt-in flag needed — the overhead is negligible for in-memory append-only lists).

### 5.1 `services/transparency.py` — Four Components

All four classes live in one file: `memblocks_lib/src/memblocks/services/transparency.py`.

**`OperationLog`** — Records every database write

Replaces all the ad-hoc `print()` calls that currently announce DB operations:
- `"✓ Added new memory (no similar existing): ..."` (sections.py:218)
- `"Updated memory {real_id[:8]}...: ..."` (sections.py:311)
- `"Deleted memory {real_id[:8]}..."` (sections.py:327)
- `"✓ Deleted vector {point_id} from {collection_name}"` (vector_db_manager.py:164)

```python
class OperationLog:
    def __init__(self):
        self._entries: List[OperationEntry] = []
    
    def record(
        self,
        db_type: Literal["mongo", "qdrant"],
        operation: Literal["insert", "update", "upsert", "delete"],
        collection: str,
        summary: str,
        document_id: Optional[str] = None,
    ) -> None:
        """Called by storage adapters and services after each DB write."""
        ...
    
    def get_entries(self, since: Optional[str] = None) -> List[OperationEntry]:
        """Get all entries, optionally filtered by timestamp."""
        ...
    
    def clear(self) -> None: ...
```

**`RetrievalLog`** — Records every memory retrieval

Replaces nothing — retrieval is currently invisible. `ChatService._retrieve_semantic_memories()` (chat_service.py:437-447) calls `self.memory_block.semantic_memories.retrieve_memories([query], top_k=5)` and returns the results, but never logs what query was used, how many results came back, or what scores they had.

```python
class RetrievalLog:
    def __init__(self):
        self._entries: List[RetrievalEntry] = []
    
    def record(
        self,
        query: str,
        source: Literal["semantic", "core", "resource"],
        results_count: int,
        top_score: Optional[float] = None,
        memories_returned: Optional[List[str]] = None,
    ) -> None:
        """Called by ChatEngine and SemanticMemoryService after retrieval."""
        ...
    
    def get_entries(self, since: Optional[str] = None) -> List[RetrievalEntry]: ...
    def clear(self) -> None: ...
```

**`ProcessingHistory`** — Records pipeline runs

Replaces `ProcessingHistoryTracker` (chat_service.py:123-143) — same concept, more detail. The current tracker just stores `ProcessingEvent` objects with `event_id`, `timestamp`, `messages_processed`, and `operations`. The new one tracks the full pipeline lifecycle including per-step timing, extraction counts, and errors.

```python
class ProcessingHistory:
    def __init__(self):
        self._runs: List[PipelineRunEntry] = []
    
    def start_run(self, run_id: str, messages_count: int) -> PipelineRunEntry:
        """Called by MemoryPipeline at start of process_window()."""
        ...
    
    def complete_run(self, run_id: str, error: Optional[str] = None) -> None:
        """Called at end of process_window()."""
        ...
    
    def get_runs(self, status: Optional[str] = None) -> List[PipelineRunEntry]: ...
    def get_latest_run(self) -> Optional[PipelineRunEntry]: ...
    def clear(self) -> None: ...
```

### 5.2 `EventBus` — 11 Subscribable Events

The EventBus allows external code to react to internal library events in real-time. User explicitly confirmed they want **very transparent** operation.

```python
class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {event: [] for event in self.EVENTS}
    
    EVENTS = [
        # --- Chat lifecycle ---
        "message_received",          # Payload: {user_message, session_id}
        "message_responded",         # Payload: {assistant_response, retrieved_memories_count}
        
        # --- Memory retrieval ---
        "memories_retrieved",        # Payload: {query, semantic_count, core_present, scores}
        
        # --- Pipeline lifecycle ---
        "pipeline_started",          # Payload: {run_id, messages_count}
        "pipeline_completed",        # Payload: {run_id, duration_ms, operations_count}
        "pipeline_failed",           # Payload: {run_id, error}
        
        # --- Memory mutations ---
        "memory_extracted",          # Payload: {count, memories: List[SemanticMemoryUnit]}
        "memory_stored",             # Payload: {operation: MemoryOperation} — one per ADD/UPDATE/DELETE
        "core_memory_updated",       # Payload: {block_id, old_persona, new_persona, old_human, new_human}
        
        # --- Summary ---
        "summary_generated",         # Payload: {old_summary_length, new_summary_length, summary_preview}
        
        # --- DB operations (low-level) ---
        "db_operation",              # Payload: {OperationEntry} — every Qdrant/MongoDB write
    ]
    
    def on(self, event: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Subscribe to an event. Raises ValueError if event name is unknown."""
        ...
    
    def off(self, event: str, callback: Callable) -> None:
        """Unsubscribe from an event."""
        ...
    
    def emit(self, event: str, payload: Dict[str, Any]) -> None:
        """Emit an event to all subscribers. Exceptions in callbacks are caught and logged."""
        ...
```

**Where events are emitted:**

| Event | Emitted by | Replaces |
|---|---|---|
| `message_received` | `ChatEngine.send_message()` | Nothing — was invisible |
| `message_responded` | `ChatEngine.send_message()` | Print at chat_service.py:518-519 |
| `memories_retrieved` | `ChatEngine._retrieve_semantic()` | Print at chat_service.py:524-525 |
| `pipeline_started` | `MemoryPipeline.process_window()` | Print at chat_service.py:229-230 |
| `pipeline_completed` | `MemoryPipeline.process_window()` | Print at chat_service.py:360 |
| `pipeline_failed` | `MemoryPipeline.process_window()` | Print at chat_service.py:291 |
| `memory_extracted` | `SemanticMemoryService.extract()` | Print at chat_service.py:247 |
| `memory_stored` | `SemanticMemoryService.store()` | Prints at sections.py:218, 266, 311, 327 |
| `core_memory_updated` | `CoreMemoryService.save()` | Print at chat_service.py:269 |
| `summary_generated` | `MemoryPipeline._generate_summary()` | Print at chat_service.py:355 |
| `db_operation` | `MongoDBAdapter`/`QdrantAdapter` wrappers | Prints at vector_db_manager.py:164 |

**Usage example (from library consumer's perspective):**

```python
client = MemBlocksClient(config)

# Subscribe to see every memory that gets stored
def on_stored(payload):
    op = payload["operation"]
    print(f"[{op.operation}] {op.content[:80]}")

client.event_bus.on("memory_stored", on_stored)

# Subscribe to pipeline completion
client.event_bus.on("pipeline_completed", lambda p: print(f"Pipeline done in {p['duration_ms']}ms"))
```

## 6. Public API Reference

The library exports a single entry point: `MemBlocksClient`. All functionality is accessed through it. Services are internal — not exported.

### 6.1 Library Exports (`memblocks_lib/src/memblocks/__init__.py`)

```python
# Primary API
from memblocks.client import MemBlocksClient
from memblocks.config import MemBlocksConfig

# Abstract interfaces (for users who want to provide custom implementations)
from memblocks.llm.base import LLMProvider
from memblocks.storage.base import StorageAdapter  # Optional: abstract storage if needed

# Data models (read-only for users)
from memblocks.models.block import MemoryBlock, MemoryBlockMetaData
from memblocks.models.units import (
    SemanticMemoryUnit,
    CoreMemoryUnit,
    ResourceMemoryUnit,
    MemoryOperation,
    ProcessingEvent,
)
from memblocks.models.transparency import (
    OperationEntry,
    RetrievalEntry,
    PipelineRunEntry,
)

# Event types (for type hints in event handlers)
from memblocks.services.transparency import EventBus

__all__ = [
    "MemBlocksClient",
    "MemBlocksConfig",
    "LLMProvider",
    "MemoryBlock",
    "MemoryBlockMetaData",
    "SemanticMemoryUnit",
    "CoreMemoryUnit",
    "ResourceMemoryUnit",
    "MemoryOperation",
    "ProcessingEvent",
    "OperationEntry",
    "RetrievalEntry",
    "PipelineRunEntry",
    "EventBus",
]
```

### 6.2 `MemBlocksClient` Method Reference

**User Management** (delegates to `UserManager`):

```python
async def create_user(self, user_id: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """Create a new user. Replaces UserService.create_user() (user_service.py:11-30)."""
    ...

async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID. Replaces UserService.get_user() (user_service.py:33-43)."""
    ...

async def list_users(self) -> List[Dict[str, Any]]:
    """List all users. Replaces UserService.list_users() (user_service.py:46-48)."""
    ...
```

**Block Management** (delegates to `BlockManager`):

```python
async def create_block(
    self,
    user_id: str,
    name: str,
    description: str = "",
    *,
    create_semantic: bool = True,
    create_core: bool = True,
    create_resource: bool = False,
) -> MemoryBlock:
    """Create a new memory block. Replaces BlockService.create_block() (block_service.py:17-96)."""
    ...

async def load_block(self, block_id: str) -> Optional[MemoryBlock]:
    """Load a block by ID. Replaces BlockService.load_block() (block_service.py:99-109)."""
    ...

async def list_user_blocks(self, user_id: str) -> List[MemoryBlock]:
    """Get all blocks for a user. Replaces BlockService.list_user_blocks() (block_service.py:112-127)."""
    ...

async def delete_block(self, block_id: str) -> bool:
    """Delete a block. Replaces BlockService.delete_block() (block_service.py:130-143)."""
    ...
```

**Chat Session Management** (delegates to `SessionManager` + `ChatEngine`):

```python
async def create_session(self, user_id: str) -> str:
    """Create a new chat session. Returns session_id. Replaces SessionManager.create_session() (block_service.py:152-160)."""
    ...

async def attach_block(self, session_id: str, block_id: str) -> None:
    """Attach a memory block to a session. Replaces SessionManager.attach_block() (block_service.py:162-166)."""
    ...

async def detach_block(self, session_id: str) -> None:
    """Detach block from session. Replaces SessionManager.detach_block() (block_service.py:168-172)."""
    ...
```

**Chat Interaction** (delegates to `ChatEngine`):

```python
async def send_message(
    self,
    session_id: str,
    message: str,
) -> Dict[str, Any]:
    """Send a message and get a response. Returns {response, retrieved_context, operations}.
    
    Replaces ChatService.send_message() (chat_service.py:507-565).
    
    Flow:
    1. Retrieve semantic memories from attached block's collection
    2. Retrieve core memory from attached block
    3. Build system prompt with XML-tagged memory context
    4. Call LLM and get response
    5. If message_history >= memory_window, trigger MemoryPipeline
    6. Return response + context
    """
    ...

async def get_chat_history(self, session_id: str) -> List[Dict[str, str]]:
    """Get message history for a session. Was self.message_history on ChatService (chat_service.py:180)."""
    ...
```

**Memory Operations** (delegates to `SemanticMemoryService`, `CoreMemoryService`):

```python
async def search_memories(
    self,
    block_id: str,
    query: str,
    top_k: int = 5,
) -> List[SemanticMemoryUnit]:
    """Search semantic memories. Replaces SemanticMemorySection.retrieve_memories() (sections.py:344-378)."""
    ...

async def get_core_memory(self, block_id: str) -> Optional[CoreMemoryUnit]:
    """Get core memory for a block. Replaces CoreMemorySection.get_memories() (sections.py:509-529)."""
    ...
```

**Transparency Access**:

```python
@property
def operation_log(self) -> OperationLog:
    """Access all DB operation records. Replaces scattered print() statements."""
    ...

@property
def retrieval_log(self) -> RetrievalLog:
    """Access all memory retrieval records. New — was invisible before."""
    ...

@property
def processing_history(self) -> ProcessingHistory:
    """Access pipeline run records. Replaces ProcessingHistoryTracker (chat_service.py:123-143)."""
    ...

@property
def event_bus(self) -> EventBus:
    """Subscribe to real-time events. New capability."""
    ...
```

### 6.3 Usage Example

```python
from memblocks import MemBlocksClient, MemBlocksConfig

# Initialize
config = MemBlocksConfig()  # Reads from .env
client = MemBlocksClient(config)

# Create user and block
await client.create_user("user_alice")
block = await client.create_block("user_alice", "Personal Assistant", "General chat")

# Create session and attach block
session_id = await client.create_session("user_alice")
await client.attach_block(session_id, block.meta_data.id)

# Chat
result = await client.send_message(session_id, "I'm planning a trip to Japan next month")
print(result["response"])  # Assistant's response
print(result["retrieved_context"])  # What memories were retrieved

# After several messages, check what happened
runs = client.processing_history.get_runs(status="completed")
print(f"Pipeline ran {len(runs)} times")

ops = client.operation_log.get_entries()
for op in ops:
    print(f"[{op.operation}] {op.collection}: {op.summary}")

# Subscribe to events
def on_memory_stored(payload):
    op = payload["operation"]
    print(f"New {op.operation}: {op.content[:50]}...")

client.event_bus.on("memory_stored", on_memory_stored)
```

## 7. Backend Restructuring

The `backend/` FastAPI app is a **demo consumer** of the library. It becomes a thin routing layer that delegates all logic to `MemBlocksClient`.

### 7.1 Workspace Structure

```
memBlocks/                      # UV workspace root
├── pyproject.toml              # workspace config
├── memblocks_lib/              # THE LIBRARY
│   └── pyproject.toml          # name = "memblocks"
└── backend/                    # DEMO APP
    └── pyproject.toml          # dependencies = ["memblocks", "fastapi", "uvicorn"]
```

Root `pyproject.toml`:
```toml
[tool.uv.workspace]
members = ["memblocks_lib", "backend"]
```

`backend/pyproject.toml`:
```toml
[project]
name = "memblocks-backend"
dependencies = ["memblocks", "fastapi", "uvicorn[standard]"]

[tool.uv.sources]
memblocks = { workspace = true }  # Local editable dependency
```

### 7.2 Files Changed

| Current File | Destination | Changes |
|---|---|---|
| `backend/main.py` (189 lines) | `backend/src/api/main.py` | Remove `sys.path.insert(0, ...)` hack (line 3), fix port typo `80001` → `8001` (line 76), create `MemBlocksClient` at startup |
| `backend/dependencies.py` (73 lines) | `backend/src/api/dependencies.py` | Remove `sys.path.insert(0, ...)` hack (line 4), replace in-memory `sessions = {}` with `MemBlocksClient` dependency |
| `backend/routers/users.py` | `backend/src/api/routers/users.py` | Use injected `MemBlocksClient` instead of `from services.user_service import user_service` |
| `backend/routers/blocks.py` | `backend/src/api/routers/blocks.py` | Use injected `MemBlocksClient` instead of `from services.block_service import block_service, session_manager` |
| `backend/routers/chat.py` | `backend/src/api/routers/chat.py` | Use injected `MemBlocksClient` instead of `ChatService` imports |
| `backend/routers/memory.py` | `backend/src/api/routers/memory.py` | Fix GET → POST for `searchMemories` (see Problem 10) |
| `backend/models/requests.py` | `backend/src/api/models/requests.py` | Move as-is |
| `main.py` (root, 314 lines) | `backend/src/cli/main.py` | Refactor `MemBlocksCLI` class to use `MemBlocksClient` |

### 7.3 FastAPI App Initialization

Current `backend/main.py` (lines 1-30):
```python
import sys
from pathlib import Path
project_root = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, project_root)  # ← DELETE THIS HACK

from fastapi import FastAPI
from backend.routers import users, blocks, chat, memory
# ↑ These imports currently fail without sys.path hack
```

New `backend/src/api/main.py`:
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from memblocks import MemBlocksClient, MemBlocksConfig
from .routers import users, blocks, chat, memory
from .dependencies import get_client

# Global client instance
_client: Optional[MemBlocksClient] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _client
    config = MemBlocksConfig()
    _client = MemBlocksClient(config)
    yield
    # Cleanup if needed
    ...

app = FastAPI(lifespan=lifespan)
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(blocks.router, prefix="/blocks", tags=["blocks"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(memory.router, prefix="/memory", tags=["memory"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)  # Fixed: was 80001
```

### 7.4 Dependency Injection

Current `backend/dependencies.py` (lines 1-20):
```python
import sys
from pathlib import Path
project_root = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, project_root)  # ← DELETE THIS HACK

from fastapi import Depends
from typing import Dict
sessions: Dict[str, any] = {}  # In-memory session storage

def get_chat_service(session_id: str = None) -> ChatService:
    # Complex logic to create ChatService from session + block
    ...
```

New `backend/src/api/dependencies.py`:
```python
from fastapi import Depends, HTTPException
from memblocks import MemBlocksClient
from .main import _client

def get_client() -> MemBlocksClient:
    if _client is None:
        raise RuntimeError("MemBlocksClient not initialized")
    return _client
```

Each router receives `client: MemBlocksClient = Depends(get_client)` and calls methods on it. No in-memory session dict — `SessionManager` (now inside the library) persists sessions to MongoDB.

### 7.5 Router Example: `chat.py`

Current approach (simplified from `backend/routers/chat.py`):
```python
from services.chat_service import ChatService
from backend.dependencies import get_chat_service

@router.post("/send")
async def send_message(session_id: str, message: str, service: ChatService = Depends(get_chat_service)):
    result = await service.send_message(message)
    return result
```

New approach:
```python
from fastapi import Depends
from memblocks import MemBlocksClient
from ..dependencies import get_client

@router.post("/send")
async def send_message(
    session_id: str,
    message: str,
    client: MemBlocksClient = Depends(get_client),
):
    result = await client.send_message(session_id, message)
    return result

@router.post("/search")  # Changed from GET to POST
async def search_memories(
    block_id: str,
    query: str,
    top_k: int = 5,
    client: MemBlocksClient = Depends(get_client),
):
    memories = await client.search_memories(block_id, query, top_k)
    return {"memories": [m.model_dump() for m in memories]}
```

### 7.6 CLI Migration

The root `main.py` (314 lines) defines a `MemBlocksCLI` class that currently:
- Imports `mongo_manager`, `block_service`, `user_service` directly (lines ~10-15)
- Creates blocks via `BlockService.create_block()` (line ~120)
- Creates `ChatService` instances manually (line ~180)

The new `backend/src/cli/main.py`:
- Imports `MemBlocksClient` from `memblocks`
- Creates a single client at startup: `self.client = MemBlocksClient(MemBlocksConfig())`
- All operations go through `self.client.create_block()`, `self.client.send_message()`, etc.
- Same interactive loop, same commands, just delegating to the client

## 8. Bug Fixes Included

These 5 bugs are fixed as part of the refactoring. Each fix is grounded in specific code locations.

### Bug 1: Port Typo

**Location:** `backend/main.py` line 76

**Current code:**
```python
print(f"🚀 Server running on http://localhost:80001")
```

**Fix:** Change `80001` → `8001`. The actual uvicorn run call on line ~85 uses 8001, but the print message is wrong.

---

### Bug 2: API Method Mismatch

**Location:** `backend/routers/memory.py` (exact lines depend on file)

**Current:** Frontend `searchMemories` sends POST, backend expects GET.

**Fix:** Change the FastAPI route decorator from `@router.get("/search")` to `@router.post("/search")`. Alternatively, support both:
```python
@router.api_route("/search", methods=["GET", "POST"])
```

---

### Bug 3: `store_memory` Return Type Lie

**Location:** `models/sections.py` line 166

**Current code:**
```python
async def store_memory(self, memory_unit: SemanticMemoryUnit, llm_provider=None) -> bool:
    """...Returns: bool: True if storage was successful"""
```

**Actual behavior:** Returns `List[MemoryOperation]` at lines 223, 255, and 338. Every caller receives a list, not a boolean.

**Fix in new code:** `SemanticMemoryService.store()` correctly declares:
```python
async def store(self, memory_unit: SemanticMemoryUnit, collection_name: str) -> List[MemoryOperation]:
```

---

### Bug 4: Incomplete Pipeline (The `pass` Statement)

**Location:** `services/chat_service.py` lines 271-288

**Current code:**
```python
print(f"   → STEP 3: Recursive Summary...")
# ... 10 lines of comments about thread safety ...
pass  # Line 288

# The method exists below but is called separately:
async def _generate_recursive_summary_bg(self, messages, previous_summary) -> str:
    # Lines 294-321 — actual implementation
```

**The bug:** Step 3 of `_process_memory_window_task()` does nothing. Summary generation happens in `_process_memory_window()` (line 339) as a *separate* step after the task completes, creating a confusing split.

**Fix in new code:** `MemoryPipeline.process_window()` executes all steps in sequence:
```python
async def process_window(self, messages, block, current_summary) -> PipelineResult:
    # Step 1: PS1 extraction
    extracted = await self._semantic.extract(messages, block.semantic_collection)
    
    # Step 2: PS2 conflict resolution + store
    for mem in extracted:
        await self._semantic.store(mem, block.semantic_collection)
    
    # Step 3: Core memory update
    old_core = await self._core.get(block.core_memory_block_id)
    new_core = await self._core.create_or_update(messages, block.core_memory_block_id)
    await self._core.save(block.core_memory_block_id, new_core)
    
    # Step 4: Recursive summary — THE MISSING STEP NOW IMPLEMENTED
    new_summary = await self._generate_summary(messages, current_summary)
    
    return PipelineResult(
        summary=new_summary,
        operations=operations,
        semantic_extracted=len(extracted),
    )
```

---

### Bug 5: Hardcoded Qdrant Connection

**Location:** `vector_db/vector_db_manager.py` lines 12-14

**Current code:**
```python
class VectorDBManager:
    client = QdrantClient(host="localhost", port=6333, prefer_grpc=True)  # Hardcoded
    embedder = OllamaEmbeddings()
    vector_size = embedder.get_dimension()  # HTTP call on import
```

**Problem:** Even though `config.py` defines `qdrant_host` and `qdrant_port` (config.py:35-37), `VectorDBManager` ignores them entirely. And `vector_size = embedder.get_dimension()` makes an HTTP call to Ollama at import time — if Ollama is down, importing the module fails.

**Fix in new code:** `QdrantAdapter.__init__` takes `MemBlocksConfig`:
```python
class QdrantAdapter:
    def __init__(self, config: MemBlocksConfig, embeddings: EmbeddingProvider):
        self._client = QdrantClient(
            host=config.qdrant_host,      # From config, not hardcoded
            port=config.qdrant_port,
            prefer_grpc=config.qdrant_prefer_grpc,
        )
        self._embeddings = embeddings
        self._vector_size: Optional[int] = None  # Lazy, resolved on first use
```

---

### Bug 6: Missing get_all_points() Method

**Location:** `backend/routers/memory.py` lines 129 and 238 call `VectorDBManager.get_all_points()`, but this method does not exist in `vector_db/vector_db_manager.py`.

**Problem:** The router expects to list all points in a collection (for debugging/admin purposes), but the method is not implemented.

**Fix in new code:** Add `get_all_points()` to `QdrantAdapter`:
```python
async def get_all_points(self, collection_name: str) -> List[Dict[str, Any]]:
    """Retrieve all points from a collection."""
    ...
```

---

## Summary

| Bug | Severity | Location | Fix Location |
|---|---|---|---|
| Port typo | LOW | backend/main.py:76 | backend/src/api/main.py |
| API mismatch | MEDIUM | backend/routers/memory.py | backend/src/api/routers/memory.py |
| Return type lie | LOW | sections.py:166 | SemanticMemoryService.store() |
| Incomplete pipeline | HIGH | chat_service.py:288 | MemoryPipeline.process_window() |
| Hardcoded connection | HIGH | vector_db_manager.py:12-14 | QdrantAdapter.__init__() |
| Missing get_all_points() | HIGH | vector_db_manager.py | QdrantAdapter.get_all_points() |

All 6 bugs are fixed as a consequence of the architectural refactoring — no separate bug-fix passes needed.

---

*This plan provides the architectural blueprint. See `migration-guide.md` for phase-by-phase execution instructions.*
