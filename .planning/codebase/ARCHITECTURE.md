# Architecture

**Analysis Date:** 2026-03-12

## Pattern Overview

**Overall:** Client-Server with Library Abstraction

The system follows a layered client-server architecture where:
- **Frontend**: React SPA (Single Page Application) running in browser
- **Backend**: FastAPI REST API acting as orchestration layer
- **Library**: `memblocks` Python library providing core memory management capabilities
- **Infrastructure**: MongoDB (document storage) + Qdrant (vector storage)

**Key Characteristics:**
- Dependency injection throughout (FastAPI `Depends()`, library constructor injection)
- Async/await pattern for all I/O operations
- Stateless API layer with stateful library instances per request
- Event-driven transparency layer for observability

## Layers

### 1. Frontend Layer (React SPA)

**Purpose:** User interface for memory management and chat interactions

**Location:** `frontend/src/`

**Contains:**
- Pages: `Landing.jsx`, `Workspace.jsx`
- Components: Chat interface, memory viewer, block manager, analytics panels
- API client: `api/client.js` - Axios-based HTTP client

**Depends on:**
- `@clerk/react` for authentication
- Backend REST API

**Used by:** End users through browser

---

### 2. API Layer (FastAPI)

**Purpose:** REST API orchestration, authentication, request validation

**Location:** `backend/src/api/`

**Contains:**
- `main.py` - FastAPI app factory with CORS, routing, lifespan management
- `dependencies.py` - Dependency injection for shared MemBlocksClient
- `routers/` - Endpoint handlers:
  - `auth.py` - Clerk authentication integration
  - `users.py` - User management
  - `blocks.py` - Memory block CRUD
  - `chat.py` - Session management and chat turns
  - `memory.py` - Core/semantic memory operations
  - `transparency.py` - Observability endpoints
- `models/requests.py` - Pydantic request models

**Depends on:**
- `memblocks` library

**Used by:** Frontend via HTTP

---

### 3. Library Layer (Core Business Logic)

**Purpose:** Memory management orchestration - the brain of the system

**Location:** `memblocks_lib/src/memblocks/`

**Contains:**

#### Client (`client.py`)
- **Purpose:** Single entry point wiring all services together
- **Pattern:** Constructor injection of adapters and LLM providers
- Exposes: User, Block, Session management methods

#### Services (`services/`)
- **Purpose:** Core domain logic
- Key services:
  - `block_manager.py` - Block lifecycle, creates Block stateful objects
  - `session_manager.py` - Session lifecycle, creates Session stateful objects
  - `semantic_memory.py` - Vector storage operations
  - `core_memory.py` - Core memory extraction and retrieval
  - `memory_pipeline.py` - Orchestrates semantic extraction, conflict resolution, summary
  - `reranker.py` - Memory ranking (Cohere)
  - `transparency.py` - Event bus, operation logs, retrieval logs, LLM usage tracking

#### Models (`models/`)
- **Purpose:** Domain entities and data transfer objects
- Key models:
  - `block.py` - Block document structure
  - `memory.py` - Memory unit models
  - `units.py` - CoreMemoryUnit, SemanticMemoryUnit, ResourceMemoryUnit
  - `retrieval.py` - RetrievalResult with to_prompt_string()
  - `transparency.py` - OperationEntry, RetrievalLog, LLMCallType

#### Storage (`storage/`)
- **Purpose:** Infrastructure adapters
- Adapters:
  - `mongo.py` - MongoDBAdapter (async Motor client)
  - `qdrant.py` - QdrantAdapter (vector search)
  - `embeddings.py` - EmbeddingProvider (FastEmbed/Cohere)

#### LLM (`llm/`)
- **Purpose:** LLM provider abstraction
- Providers:
  - `base.py` - Abstract LLMProvider base class
  - `groq_provider.py`, `gemini_provider.py`, `openrouter_provider.py`
- Task settings: `task_settings.py` - Per-task LLM configuration

#### Prompts (`prompts/`)
- **Purpose:** System prompt templates
- `__init__.py` - ASSISTANT_BASE_PROMPT

---

### 4. Infrastructure Layer

**Purpose:** Data persistence and external services

**Components:**
- **MongoDB** - Document storage (users, blocks, sessions, messages, core memories)
- **Qdrant** - Vector database for semantic memories
- **LLM Providers** - Groq, Gemini, OpenRouter (via langchain)
- **Embedding Provider** - FastEmbed for text vectorization

---

## Data Flow

### Chat Flow:

```
User Message
    ↓
Frontend (ChatInterface.jsx)
    ↓ HTTP POST /api/chat/sessions/{id}/message
Backend Router (chat.py: send_message)
    ↓
MemBlocksClient.get_session() → Session
    ↓
Block.retrieve(query) → RetrievalResult (core + semantic)
Session.get_memory_window() → message list
Session.get_recursive_summary() → summary string
    ↓
Build system prompt: ASSISTANT_BASE_PROMPT + summary + memory context
    ↓
LLM.chat(messages) → AI response
    ↓
Background: session.add(user_msg, ai_response)
  - Persists messages to MongoDB
  - If window full: triggers MemoryPipeline
    - PS1: Semantic extraction (LLM)
    - PS2: Conflict resolution (LLM)
    - Core memory update
    - Recursive summary generation
    - Trim window, persist summary
    ↓
Response to frontend with context, summary, analytics
```

### Memory Retrieval Flow:

```
Query string
    ↓
Block.retrieve(query)
    ├→ CoreMemoryService.get() → CoreMemoryUnit (full retrieval)
    └→ SemanticMemoryService.retrieve() → List[SemanticMemoryUnit]
        ↓
        QdrantAdapter.hybrid_search() (keyword + vector)
        ↓
        Optional: Reranker.rank()
    ↓
RetrievalResult(core, semantic, resource)
    ↓
context.to_prompt_string() → formatted string for LLM
```

---

## Key Abstractions

### Block (Stateful Object)
- **Purpose:** Stateful handle to a memory block
- **Pattern:** Created by BlockManager, returned to caller
- **Examples:** `memblocks_lib/src/memblocks/services/block.py`
- **Methods:** `retrieve()`, `core_retrieve()`, `semantic_retrieve()`, `resource_retrieve()`

### Session (Stateful Object)
- **Purpose:** Stateful handle to a conversation session
- **Pattern:** Created by SessionManager, returned to caller
- **Examples:** `memblocks_lib/src/memblocks/services/session.py`
- **Methods:** `get_memory_window()`, `get_recursive_summary()`, `add()`, `flush()`

### RetrievalResult
- **Purpose:** Container for memory retrieval results
- **Pattern:** Value object with `to_prompt_string()` method
- **Examples:** `memblocks_lib/src/memblocks/models/retrieval.py`

### LLMProvider (Abstract)
- **Purpose:** Pluggable LLM backends
- **Pattern:** Strategy pattern with concrete implementations
- **Examples:** `memblocks_lib/src/memblocks/llm/groq_provider.py`, `gemini_provider.py`, `openrouter_provider.py`

### MongoDBAdapter
- **Purpose:** Async database operations
- **Pattern:** Repository pattern
- **Examples:** `memblocks_lib/src/memblocks/storage/mongo.py`

---

## Entry Points

### Backend Entry Point
- **Location:** `backend/src/api/main.py`
- **Triggers:** `uvicorn backend.src.api.main:app`
- **Responsibilities:** FastAPI app creation, router registration, CORS, lifespan management

### Frontend Entry Point
- **Location:** `frontend/src/main.jsx`
- **Triggers:** `vite` dev server or production build
- **Responsibilities:** React app bootstrap, ClerkProvider, BrowserRouter setup

### Library Entry Point
- **Location:** `memblocks_lib/src/memblocks/client.py`
- **Triggers:** Backend dependency injection (`get_client()`)
- **Responsibilities:** Client instantiation, service wiring, lifecycle management

### CLI Entry Point
- **Location:** `backend/src/cli/main.py`
- **Triggers:** `memblocks` command
- **Responsibilities:** Command-line interface for library operations

---

## Error Handling

**Strategy:** Propagating exceptions with HTTP status codes

**Patterns:**
- FastAPI: `HTTPException(status_code, detail)` for API errors
- Library: Exceptions propagate from services to API layer
- Frontend: Axios interceptors handle 401 (redirect to login), other errors logged

---

## Cross-Cutting Concerns

**Logging:** 
- Python: `memblocks_lib/src/memblocks/logger/__init__.py` (custom logger)
- Frontend: `console.warn/error`

**Validation:**
- FastAPI: Pydantic models in `backend/src/api/models/requests.py`
- Library: Pydantic models in `memblocks_lib/src/memblocks/models/`

**Authentication:**
- Frontend: Clerk (`@clerk/react`)
- Backend: Clerk Backend API (`clerk-backend-api`)
- Token stored in localStorage, passed as Bearer token

**Transparency/Observability:**
- EventBus for internal events
- OperationLog for database writes
- RetrievalLog for memory retrievals
- ProcessingHistory for pipeline runs
- LLMUsageTracker for token usage

---

*Architecture analysis: 2026-03-12*
