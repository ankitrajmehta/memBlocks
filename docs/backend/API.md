# MemBlocks Backend REST API

This document covers the current FastAPI backend under `backend/src/api`.

Base API router prefix: `/api`

Examples:

- health check: `GET /health`
- API docs (when server runs): `/docs`, `/redoc`

---

## Auth model

- Most `/api/*` routes require `Authorization: Bearer <token>`.
- Auth is handled by Clerk-based JWT parsing in `backend/src/api/routers/auth.py`.
- User records are auto-created/ensured by `get_current_user()`.

Header:

```http
Authorization: Bearer <clerk_jwt_token>
Content-Type: application/json
```

---

## Route map (current)

### Auth (`/api/auth`)

- `GET /api/auth/me`

### Users (`/api/users`)

- `GET /api/users/me`

### Blocks (`/api/blocks`)

- `POST /api/blocks/`
- `GET /api/blocks/user/{user_id}`
- `GET /api/blocks/{block_id}`
- `DELETE /api/blocks/{block_id}`

### Chat / Sessions (`/api/chat`)

- `POST /api/chat/sessions`
- `GET /api/chat/sessions/{session_id}`
- `GET /api/chat/sessions/block/{block_id}`
- `POST /api/chat/sessions/{session_id}/message`
- `POST /api/chat/sessions/{session_id}/flush`
- `GET /api/chat/sessions/{session_id}/history`
- `GET /api/chat/sessions/{session_id}/full-context`
- `GET /api/chat/sessions/{session_id}/summary`

### Memory (`/api/memory`)

- `GET /api/memory/core/{block_id}`
- `PATCH /api/memory/core/{block_id}`
- `POST /api/memory/semantic/{block_id}/search`

### Transparency (`/api/transparency`)

- `GET /api/transparency/stats`
- `GET /api/transparency/processing-history`

---

## Request models (selected)

Defined in `backend/src/api/models/requests.py`.

### Create block

`POST /api/blocks/`

```json
{
  "name": "Work Memory",
  "description": "Project context",
  "create_semantic": true,
  "create_core": true,
  "create_resource": false
}
```

### Create session

`POST /api/chat/sessions`

```json
{
  "block_id": "block_xxx"
}
```

### Send message

`POST /api/chat/sessions/{session_id}/message`

```json
{
  "message": "What did we decide about deployment?"
}
```

### Patch core memory

`PATCH /api/memory/core/{block_id}`

```json
{
  "persona_content": "Be concise and technical.",
  "human_content": "User prefers direct answers."
}
```

### Search semantic memory

`POST /api/memory/semantic/{block_id}/search`

```json
{
  "query": "deployment decisions",
  "top_k": 5
}
```

---

## Notes on behavior

1. Chat message persistence and memory processing are queued in background tasks (`BackgroundTasks`) in `chat.py` for responsive API returns.
2. Core memory endpoints currently use internal client service access (`client._core`) and are intentionally block-owner protected.
3. Route paths above are exact for the current backend; older docs mentioning `/blocks` without `/api` prefix or obsolete endpoints are outdated.

---

## Run locally

From repo root:

```bash
uv run uvicorn backend.src.api.main:app --reload --port 8001
```

Or from backend package context with equivalent module path.

---

## Related docs

- Deployment guide: `docs/backend/DEPLOYMENT.md`
- memblocks library setup: `docs/memblockslib_docs/01_SETUP_GUIDE.md`
- memblocks library deep docs: `docs/memblockslib_docs/03_TECHNICAL_OVERVIEW.md`
