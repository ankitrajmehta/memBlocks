# Deployment Guide

This guide covers deploying the current MemBlocks stack in this repository.

---

## 1) Components

Repository workspace members:

- `memblocks_lib` (core Python library)
- `backend` (FastAPI API + CLI)
- `mcp_server` (MCP integration service)

Local infrastructure (via `docker-compose.yml`):

- Qdrant (`6333`, `6334`)
- Ollama (`11434`)
- MongoDB service definition exists but is currently commented out in compose

---

## 2) Local infrastructure bring-up

From repo root:

```bash
docker-compose up -d
docker-compose ps
```

Logs:

```bash
docker-compose logs -f
```

Stop:

```bash
docker-compose down
```

Destroy volumes (data loss):

```bash
docker-compose down -v
```

---

## 3) Environment configuration

Create env file:

```bash
cp .env.example .env
```

Minimum required for backend+library:

```env
LLM_PROVIDER_NAME=groq
GROQ_API_KEY=your_key

MONGODB_CONNECTION_STRING=mongodb://admin:memblocks123@localhost:27017/memblocks?authSource=admin

QDRANT_HOST=localhost
QDRANT_PORT=6333
OLLAMA_BASE_URL=http://localhost:11434
```

Common optional fields:

```env
COHERE_API_KEY=your_key
GEMINI_API_KEY=...
OPENROUTER_API_KEY=...

CLERK_PUBLISHABLE_KEY=...
CLERK_SECRET_KEY=...
```

---

## 4) Run backend API

The backend app lives at `backend/src/api/main.py` and serves API routes under `/api`.

```bash
uv run uvicorn backend.src.api.main:app --reload --port 8001
```

Useful URLs:

- `http://localhost:8001/health`
- `http://localhost:8001/docs`
- `http://localhost:8001/redoc`

---

## 5) Run only library consumers

Install workspace deps:

```bash
uv sync --all-packages
```

Run scripts against workspace env:

```bash
uv run python your_script.py
```

---

## 6) Production considerations

1. Move secrets out of `.env` into a secret manager.
2. Use managed MongoDB/Qdrant where possible for backup and HA.
3. Restrict network exposure of DB/vector ports.
4. Add process supervision and structured logs for API services.
5. Monitor token usage and latency via `LLMUsageTracker`-backed endpoints.

---

## 7) Troubleshooting

### Qdrant unavailable

- Check container status: `docker-compose ps`
- Verify endpoint: `http://localhost:6333`

### Ollama unavailable

- Verify endpoint: `http://localhost:11434`
- Check model availability in Ollama container

### Mongo auth/connection errors

- Validate `MONGODB_CONNECTION_STRING`
- Ensure a Mongo service is actually running (compose file currently comments Mongo service)

### Backend auth errors

- Confirm Clerk keys are set
- Confirm Bearer token is sent and decodable by backend auth router

---

## Related docs

- API docs: `docs/backend/API.md`
- Library setup detail: `docs/memblockslib_docs/01_SETUP_GUIDE.md`
- Library methods: `docs/memblockslib_docs/02_METHODS_AND_INTERFACES.md`
