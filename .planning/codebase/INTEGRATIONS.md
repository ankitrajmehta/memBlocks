# External Integrations

**Analysis Date:** 2026-03-12

## APIs & External Services

**LLM Providers:**
- **Groq** - Primary LLM provider
  - SDK: `langchain-groq` 
  - Auth: `GROQ_API_KEY` env var
  - Used in: `memblocks_lib` core library

- **OpenRouter** - Fallback LLM provider
  - SDK: `langchain-openai` (OpenAI-compatible)
  - Auth: `OPENROUTER_API_KEY` env var
  - Configuration: `OPENROUTER_FALLBACK_MODELS` (optional), `OPENROUTER_ENABLE_THINKING` (optional)

- **Google Gemini** - LLM provider
  - SDK: `langchain-google-genai`
  - Auth: Google AI API (via `GOOGLE_API_KEY` implied)
  - Used in: `memblocks_lib` for Gemini model support

- **Ollama** - Local LLM provider
  - SDK: Native HTTP (`langchain-community` or direct)
  - Auth: None (local)
  - Endpoint: `OLLAMA_BASE_URL` (default: `http://localhost:11434`)

- **Cohere** - Reranking service
  - SDK: `cohere` Python package
  - Auth: `COHERE_API_KEY` env var
  - Used in: `memblocks_lib` for document reranking

## Data Storage

**Document Database:**
- **MongoDB**
  - Client: `motor` (async Python driver)
  - Connection: `MONGODB_CONNECTION_STRING` env var
  - Default: `mongodb://admin:memblocks123@localhost:27017/memblocks?authSource=admin`
  - Auth source: `admin`
  - Used in: `memblocks_lib` for persistent storage

**Vector Database:**
- **Qdrant**
  - Client: `qdrant-client`
  - Connection: `QDRANT_HOST` + `QDRANT_PORT`
  - Default: `localhost:6333` (REST), `6334` (gRPC)
  - Used in: `memblocks_lib` for vector storage and similarity search

**Local Embeddings:**
- **FastEmbed**
  - Used for local embedding generation
  - No external service required
  - Enables offline embedding generation

## Authentication & Identity

**Auth Provider:**
- **Clerk** - Authentication and user management
  - Frontend SDK: `@clerk/react`
  - Backend SDK: `clerk-backend-api`
  - Auth via OAuth: Google OAuth supported
  - Keys:
    - `CLERK_PUBLISHABLE_KEY` - Frontend (public)
    - `CLERK_SECRET_KEY` - Backend (secret)
  - Configuration: Dashboard at `https://dashboard.clerk.com`

## Monitoring & Observability

**Error Tracking & Tracing:**
- **Arize AI** - LLM observability platform
  - SDK: `arize-otel` (OpenTelemetry integration)
  - Instrumentation: `openinference-instrumentation-langchain`
  - Configuration:
    - `ARIZE_SPACE_ID`
    - `ARIZE_API_KEY`
    - `ARIZE_PROJECT_NAME` (default: `'memBlocks'`)
  - Purpose: Trace LLM calls, monitor performance

**Logging:**
- Approach: Standard Python logging + Arize tracing
- No dedicated logging service detected

## CI/CD & Deployment

**Containerization:**
- **Docker** - Container runtime
- **Docker Compose** - Orchestration
  - Services defined in `docker-compose.yml`:
    - Qdrant (vector DB)
    - Ollama (local LLM)
    - MongoDB (commented out, optional)

**Deployment Files:**
- `docker-compose.yml` - Local development orchestration
- `Dockerfile.ollama` - Custom Ollama image
- `.dockerignore` - Docker build exclusions

## Environment Configuration

**Required env vars:**
- `GROQ_API_KEY` - Groq LLM access
- `MONGODB_CONNECTION_STRING` - Database connection
- `CLERK_PUBLISHABLE_KEY` - Frontend auth
- `CLERK_SECRET_KEY` - Backend auth
- `QDRANT_HOST` - Vector DB host
- `QDRANT_PORT` - Vector DB port

**Optional env vars:**
- `OPENROUTER_API_KEY` - Fallback LLM
- `OPENROUTER_FALLBACK_MODELS` - Fallback model list
- `OPENROUTER_ENABLE_THINKING` - Reasoning mode
- `COHERE_API_KEY` - Reranking
- `ARIZE_SPACE_ID`, `ARIZE_API_KEY`, `ARIZE_PROJECT_NAME` - Monitoring
- `OLLAMA_BASE_URL` - Local LLM
- `GOOGLE_API_KEY` - Gemini access (inferred)

**Secrets location:**
- Environment variables (`.env` file, not committed)
- Template provided in `.env.example`

## Webhooks & Callbacks

**Incoming:**
- Not detected - No webhook endpoints configured

**Outgoing:**
- Not detected - No outgoing webhook integrations

## Project Structure

**Monorepo Layout:**
```
MemBlocks/
├── frontend/              # React SPA (Vite)
├── backend/               # FastAPI backend + CLI
├── memblocks_lib/         # Core Python library
├── docker-compose.yml    # Infrastructure services
├── .env.example          # Environment template
└── pyproject.toml        # UV workspace root
```

**Integration Architecture:**
1. Frontend (React) → Clerk for auth
2. Frontend → Backend (FastAPI) via proxied `/api`
3. Backend → Clerk for auth verification
4. Backend → memblocks_lib for core logic
5. memblocks_lib → MongoDB (documents)
6. memblocks_lib → Qdrant (vectors)
7. memblocks_lib → LLM providers (Groq, OpenRouter, Gemini, Ollama)
8. memblocks_lib → Cohere (reranking)
9. memblocks_lib → Arize (observability)

---

*Integration audit: 2026-03-12*
