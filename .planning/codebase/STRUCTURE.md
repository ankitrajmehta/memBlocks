# Codebase Structure

**Analysis Date:** 2026-03-12

## Directory Layout

```
MemBlocks/                          # Project root
├── backend/                        # FastAPI backend
│   ├── src/
│   │   ├── api/                   # REST API layer
│   │   │   ├── main.py            # FastAPI app factory
│   │   │   ├── dependencies.py    # Dependency injection
│   │   │   ├── models/            # Pydantic request/response models
│   │   │   └── routers/           # Endpoint handlers
│   │   └── cli/                   # Command-line interface
│   └── pyproject.toml
├── frontend/                       # React SPA
│   ├── src/
│   │   ├── main.jsx               # App entry point
│   │   ├── App.jsx                # Root component
│   │   ├── api/                   # HTTP client
│   │   ├── components/            # React components
│   │   ├── pages/                 # Page components
│   │   └── styles/                # CSS files
│   ├── public/                    # Static assets
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
├── memblocks_lib/                  # Core memory management library
│   ├── src/
│   │   └── memblocks/
│   │       ├── __init__.py        # Public exports
│   │       ├── client.py          # MemBlocksClient entry point
│   │       ├── config.py          # Configuration
│   │       ├── models/            # Domain models
│   │       ├── services/           # Business logic
│   │       ├── storage/            # Infrastructure adapters
│   │       ├── llm/                # LLM providers
│   │       ├── prompts/            # Prompt templates
│   │       └── logger/             # Logging utilities
│   ├── docs/                      # Documentation
│   └── pyproject.toml
├── tests/                         # Test files
├── deprecated/                    # Deprecated code (vector_db_old, llm_old, models_old)
├── public/                        # Static documentation assets
├── docker-compose.yml             # Container orchestration
├── Dockerfile.ollama
├── pyproject.toml                 # Root workspace config
└── .env.example                   # Environment template
```

---

## Directory Purposes

### `backend/src/api/`
- **Purpose:** REST API layer built with FastAPI
- **Contains:** Application factory, routers, request models, dependency injection
- **Key files:**
  - `main.py` - `create_app()` factory, router registration, CORS, lifespan
  - `dependencies.py` - `get_client()` cached dependency for MemBlocksClient
  - `routers/auth.py` - Clerk authentication integration
  - `routers/chat.py` - Session and message handling (most complex router)
  - `routers/blocks.py` - Memory block CRUD
  - `routers/memory.py` - Core/semantic memory operations
  - `routers/transparency.py` - Observability endpoints

### `frontend/src/`
- **Purpose:** React single-page application
- **Contains:** Components, pages, API client, routing
- **Key files:**
  - `main.jsx` - ReactDOM render with ClerkProvider, BrowserRouter
  - `App.jsx` - Root component with auth-aware routing
  - `api/client.js` - Axios client with interceptors for auth tokens
  - `pages/Landing.jsx` - Landing page for unauthenticated users
  - `pages/Workspace.jsx` - Main workspace for authenticated users
  - `components/ChatInterface.jsx` - Main chat UI
  - `components/BlockManager.jsx` - Memory block management UI

### `memblocks_lib/src/memblocks/`
- **Purpose:** Core memory management library
- **Contains:** All business logic, storage adapters, LLM providers

#### Key Subdirectories:

**`models/`**
- **Purpose:** Domain entities and data transfer objects
- **Files:**
  - `block.py` - Block document structure
  - `memory.py` - Memory document structures
  - `units.py` - CoreMemoryUnit, SemanticMemoryUnit, ResourceMemoryUnit
  - `retrieval.py` - RetrievalResult with to_prompt_string()
  - `transparency.py` - OperationEntry, LLMCallType, etc.
  - `llm_outputs.py` - LLM response models

**`services/`**
- **Purpose:** Core business logic
- **Files:**
  - `client.py` - NOT HERE - see root of memblocks/
  - `block.py` - Block stateful object
  - `block_manager.py` - Block lifecycle management
  - `session.py` - Session stateful object
  - `session_manager.py` - Session lifecycle management
  - `semantic_memory.py` - Semantic memory retrieval
  - `core_memory.py` - Core memory extraction/retrieval
  - `memory_pipeline.py` - Pipeline orchestration (PS1, PS2, summary)
  - `reranker.py` - Memory ranking (Cohere)
  - `transparency.py` - Event bus, logs, usage tracking

**`storage/`**
- **Purpose:** Infrastructure adapters
- **Files:**
  - `mongo.py` - MongoDBAdapter (async Motor)
  - `qdrant.py` - QdrantAdapter (vector search)
  - `embeddings.py` - EmbeddingProvider (FastEmbed)

**`llm/`**
- **Purpose:** LLM provider implementations
- **Files:**
  - `base.py` - Abstract LLMProvider
  - `groq_provider.py` - Groq implementation
  - `gemini_provider.py` - Gemini implementation
  - `openrouter_provider.py` - OpenRouter implementation
  - `task_settings.py` - Per-task LLM configuration

**`prompts/`**
- **Purpose:** Prompt templates
- **Files:**
  - `__init__.py` - ASSISTANT_BASE_PROMPT export

**`logger/`**
- **Purpose:** Logging utilities
- **Files:**
  - `__init__.py` - get_logger() function

---

## Key File Locations

### Entry Points

- **Backend:** `backend/src/api/main.py` - `create_app()` factory, runs on `uvicorn backend.src.api.main:app`
- **Frontend:** `frontend/src/main.jsx` - React entry, runs on `vite`
- **Library:** `memblocks_lib/src/memblocks/client.py` - `MemBlocksClient` class

### Configuration

- **Backend config:** `backend/src/api/dependencies.py` - `get_config()` with LLM settings hardcoded
- **Library config:** `memblocks_lib/src/memblocks/config.py` - `MemBlocksConfig` from environment
- **Frontend config:** `frontend/vite.config.js` - Vite configuration
- **Tailwind:** `frontend/tailwind.config.js` - CSS framework config

### Core Logic

- **Client wiring:** `memblocks_lib/src/memblocks/client.py`
- **Block operations:** `memblocks_lib/src/memblocks/services/block_manager.py`
- **Session operations:** `memblocks_lib/src/memblocks/services/session_manager.py`
- **Memory pipeline:** `memblocks_lib/src/memblocks/services/memory_pipeline.py`

### Storage

- **MongoDB adapter:** `memblocks_lib/src/memblocks/storage/mongo.py`
- **Qdrant adapter:** `memblocks_lib/src/memblocks/storage/qdrant.py`
- **Embeddings:** `memblocks_lib/src/memblocks/storage/embeddings.py`

### Testing

- **Unit tests:** `tests/test_hybrid.py`
- **Integration tests:** `memblocks_lib/test_cohere_reranker.py`

---

## Naming Conventions

### Files

- **Python modules:** `snake_case.py` (e.g., `block_manager.py`, `session_manager.py`)
- **React components:** `PascalCase.jsx` (e.g., `ChatInterface.jsx`, `BlockManager.jsx`)
- **API client:** `camelCase.js` (e.g., `client.js`)

### Directories

- **All directories:** `snake_case/` (e.g., `api/`, `routers/`, `storage/`, `services/`)

### Classes

- **Python classes:** `PascalCase` (e.g., `MemBlocksClient`, `Block`, `Session`, `MongoDBAdapter`)
- **React components:** `PascalCase` (e.g., `ChatInterface`, `Workspace`)

### Functions/Methods

- **Python:** `snake_case` (e.g., `get_block()`, `create_session()`, `get_memory_window()`)
- **JavaScript:** `camelCase` (e.g., `createBlock()`, `sendMessage()`)

### Constants

- **Python:** `UPPER_SNAKE_CASE` (e.g., `LLMCallType.CONVERSATION`)
- **JavaScript:** `camelCase` (e.g., `apiBaseUrl`)

---

## Where to Add New Code

### New Feature (Backend API)

1. **Add router:** Create new file in `backend/src/api/routers/` (e.g., `analytics.py`)
2. **Define endpoints:** Add `@router.post()`, `@router.get()` etc. in the new router
3. **Register router:** Import and include in `backend/src/api/main.py`
4. **Add request models:** Add Pydantic models in `backend/src/api/models/requests.py`

**Example path:** `backend/src/api/routers/analytics.py`

### New Feature (Library Service)

1. **Add service:** Create new file in `memblocks_lib/src/memblocks/services/` (e.g., `analytics.py`)
2. **Implement logic:** Create service class with async methods
3. **Wire in client:** Import and inject in `memblocks_lib/src/memblocks/client.py` constructor

**Example path:** `memblocks_lib/src/memblocks/services/analytics.py`

### New Component (Frontend)

1. **Add component:** Create new file in `frontend/src/components/` (e.g., `AnalyticsPanel.jsx`)
2. **Import in page:** Import and use in appropriate page (`Workspace.jsx`)
3. **Add API endpoint:** If backend needed, follow "New Feature (Backend API)"

**Example path:** `frontend/src/components/AnalyticsPanel.jsx`

### New Storage Adapter

1. **Add adapter:** Create new file in `memblocks_lib/src/memblocks/storage/` (e.g., `redis.py`)
2. **Implement interface:** Follow pattern from `MongoDBAdapter` or `QdrantAdapter`
3. **Wire in client:** Import and inject in `memblocks_lib/src/memblocks/client.py`

**Example path:** `memblocks_lib/src/memblocks/storage/redis.py`

### New LLM Provider

1. **Add provider:** Create new file in `memblocks_lib/src/memblocks/llm/` (e.g., `anthropic_provider.py`)
2. **Extend base:** Inherit from `LLMProvider` base class
3. **Wire in client:** Add provider case in `memblocks_lib/src/memblocks/client.py` `_build_provider()` function

**Example path:** `memblocks_lib/src/memblocks/llm/anthropic_provider.py`

### New Test

1. **Add test file:** Create in appropriate location:
   - Library tests: `tests/` or `memblocks_lib/test_*.py`
   - Frontend tests: Not currently using (no test framework detected)
2. **Follow patterns:** Use existing test patterns

**Example path:** `tests/test_new_feature.py`

---

## Special Directories

### `deprecated/`
- **Purpose:** Old code replaced during refactoring
- **Contains:** `vector_db_old/`, `llm_old/`, `models_old/`
- **Generated:** No
- **Committed:** Yes (for reference)

### `public/`
- **Purpose:** Static assets and documentation
- **Contains:** Images, diagrams, mem0 explanation markdown
- **Generated:** No
- **Committed:** Yes

### `.planning/codebase/`
- **Purpose:** Architecture documentation (generated by this analysis)
- **Contains:** ARCHITECTURE.md, STRUCTURE.md, STACK.md, etc.
- **Generated:** Yes (by GSD mapper)
- **Committed:** Yes (for future reference)

---

*Structure analysis: 2026-03-12*
