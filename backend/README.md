# memBlocks FastAPI Backend

A RESTful API wrapper for the memBlocks intelligent memory management system.

## Overview

This FastAPI backend provides HTTP endpoints for interacting with memBlocks' core services:
- User management
- Memory block creation and management
- Chat sessions with memory-augmented AI
- Memory retrieval (core, summary, semantic)

## Architecture

```
backend/
├── main.py              # FastAPI app entry point
├── routers/
│   ├── users.py         # User CRUD endpoints
│   ├── blocks.py        # Memory block management
│   ├── chat.py          # Chat session handling
│   └── memory.py        # Memory retrieval
├── models/
│   └── requests.py      # Pydantic request models
├── dependencies.py      # Shared dependencies & session storage
└── README.md
```

**Key Design Decisions:**
- **Service Reuse**: Imports existing services from parent directory (no duplication)
- **Async-First**: All endpoints use async/await for I/O operations
- **Type Safety**: Pydantic models for request validation
- **Session Management**: In-memory storage for active ChatService instances
- **CORS Enabled**: Allows frontend access from localhost:5173

---

## Prerequisites

### 1. Infrastructure Services
All services must be running before starting the backend:

```bash
# From project root
docker-compose up -d
```

This starts:
- **MongoDB** (port 27017) - User/block/core memory storage
- **Qdrant** (ports 6333, 6334) - Vector database for semantic memories
- **Ollama** (port 11434) - Embeddings model (nomic-embed-text)

### 2. Environment Configuration
Ensure `.env` file exists in project root with:

```env
GROQ_API_KEY=your_groq_api_key_here
MONGODB_CONNECTION_STRING=mongodb://localhost:27017
QDRANT_HOST=localhost
QDRANT_PORT=6333
OLLAMA_BASE_URL=http://localhost:11434
```

---

## Running the Backend

### Standard Run
```bash
# From project root
uv run python backend/main.py
```

### Development Mode (Auto-reload)
```bash
# From project root
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 80001
```

The backend will start on: **http://localhost:80001**

---

## API Documentation

Once running, access interactive documentation at:

- **Swagger UI**: http://localhost:80001/docs
- **ReDoc**: http://localhost:80001/redoc
- **Health Check**: http://localhost:80001/health

---

## API Endpoints

### Users (`/api/users`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/users` | Create/get user |
| GET | `/api/users` | List all users |
| GET | `/api/users/{user_id}` | Get user details |

### Blocks (`/api/blocks`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/blocks` | Create memory block |
| GET | `/api/blocks/{user_id}` | List user's blocks |
| GET | `/api/blocks/{user_id}/{block_id}` | Get block details |
| DELETE | `/api/blocks/{user_id}/{block_id}` | Delete block |

### Chat (`/api/chat`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/sessions` | Start chat session |
| POST | `/api/chat/message` | Send message |
| GET | `/api/chat/sessions/{session_id}` | Get session info |
| GET | `/api/chat/sessions` | List active sessions |
| DELETE | `/api/chat/sessions/{session_id}` | End session |

### Memory (`/api/memory`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/memory/{block_id}/core` | Get core memory |
| GET | `/api/memory/{block_id}/summary` | Get recursive summary |
| GET | `/api/memory/{block_id}/semantic` | Get semantic memories |
| GET | `/api/memory/{block_id}/search?query=...` | Search memories |
| GET | `/api/memory/{block_id}/stats` | Get memory statistics |

---

## Example Usage

### 1. Create User
```bash
curl -X POST http://localhost:80001/api/users \
  -H "Content-Type: application/json" \
  -d '{"user_id": "alice"}'
```

### 2. Create Memory Block
```bash
curl -X POST http://localhost:80001/api/blocks \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "name": "Work Notes",
    "description": "Professional knowledge base"
  }'
```

### 3. Start Chat Session
```bash
curl -X POST http://localhost:80001/api/chat/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "block_id": "block_abc123"
  }'
```

Response:
```json
{
  "success": true,
  "data": {
    "session_id": "session_f3a1b2c4d5e6",
    "user_id": "alice",
    "block_id": "block_abc123",
    "status": "active"
  }
}
```

### 4. Send Message
```bash
curl -X POST http://localhost:80001/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session_f3a1b2c4d5e6",
    "message": "What do you remember about my work projects?"
  }'
```

---

## Response Format

All endpoints return consistent JSON responses:

**Success Response:**
```json
{
  "success": true,
  "data": { ... },
  "message": "Optional success message"
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Error type",
  "detail": "Detailed error message"
}
```

---

## Session Management

**Active Chat Sessions** are stored in-memory using a dictionary:

```python
active_chat_sessions: Dict[str, ChatService] = {}
```

**⚠️ Production Note**: For production deployments, replace in-memory storage with:
- **Redis**: For distributed session storage
- **Database**: For persistent session recovery
- **Session Expiry**: Implement TTL for inactive sessions

---

## Error Handling

The backend implements multiple layers of error handling:

1. **Input Validation**: Pydantic models validate request data
2. **Service Errors**: Caught and converted to appropriate HTTP exceptions
3. **Global Handler**: Catches unhandled exceptions and returns 500 responses

---

## Development Notes

### Adding New Endpoints

1. Create request model in `models/requests.py`
2. Add router function in appropriate router file
3. Import and register router in `main.py`

### Testing Endpoints

Use the interactive Swagger UI at `/docs` or tools like:
- **curl** (command line)
- **Postman** (GUI client)
- **httpie** (modern CLI tool)

### Debugging

Enable debug logging:
```python
# In main.py
uvicorn.run(
    "main:app",
    host="0.0.0.0",
    port=80001,
    reload=True,
    log_level="debug",  # Change from "info"
)
```

---

## Troubleshooting

### "Service connection failed"
**Fix**: Ensure Docker services are running:
```bash
docker-compose ps  # Check status
docker-compose up -d  # Start services
```

### "Session not found"
**Fix**: Sessions are in-memory only. Restart clears all sessions.

### "Module not found" errors
**Fix**: Backend uses `sys.path.append('..')` to import parent services. Run from project root:
```bash
# ✅ Correct
uv run python backend/main.py

# ❌ Wrong
cd backend && uv run python main.py
```

### CORS errors from frontend
**Fix**: Add your frontend URL to CORS origins in `main.py`:
```python
allow_origins=[
    "http://localhost:5173",  # Add your frontend URL
]
```

---

## Performance Considerations

- **Async Operations**: All I/O operations use async/await
- **Connection Pooling**: MongoDB Motor handles connection pooling
- **Vector Search**: Qdrant provides optimized vector similarity search
- **In-Memory Sessions**: Fast access, but not persistent across restarts

---

## Security Notes

- **Input Validation**: All requests validated with Pydantic
- **Error Handling**: Internal errors don't expose sensitive details
- **CORS**: Restricted to localhost origins (configure for production)
- **API Keys**: Never exposed in responses, stored in environment variables

---

## Future Enhancements

- [ ] JWT authentication
- [ ] Rate limiting
- [ ] WebSocket support for real-time chat
- [ ] Redis-based session storage
- [ ] Request/response logging
- [ ] Metrics and monitoring
- [ ] API versioning (v1, v2)
- [ ] Batch operations for blocks/memories

---

## Related Documentation

- **Project Setup**: `../SETUP_GUIDE.md`
- **Architecture**: `../projectDescription.md`
- **Agent Guide**: `../AGENTS.md`

---

**Built with FastAPI, powered by memBlocks core services** 🚀
