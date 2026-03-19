# MemBlocks REST API Documentation

The MemBlocks backend provides a RESTful API built with FastAPI for managing memory blocks, storing memories, and conversational interactions.

## Base URL

```
http://localhost:8000
```

## Authentication

All API endpoints (except health checks) require authentication via **Clerk JWT tokens**.

### Headers

```http
Authorization: Bearer <clerk_jwt_token>
Content-Type: application/json
```

### Getting Started

1. Set up Clerk authentication (see `.env.example`)
2. Obtain JWT token from Clerk SDK
3. Include token in `Authorization` header

---

## API Documentation

### Interactive API Docs

FastAPI provides auto-generated interactive documentation:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## Endpoints Overview

### Authentication & Users
- `POST /auth/register` - Register new user
- `GET /auth/me` - Get current user info
- `GET /users/{user_id}` - Get user by ID

### Memory Blocks
- `POST /blocks` - Create new memory block
- `GET /blocks` - List user's memory blocks
- `GET /blocks/{block_id}` - Get specific block details
- `PUT /blocks/{block_id}` - Update block metadata
- `DELETE /blocks/{block_id}` - Delete memory block
- `POST /blocks/{block_id}/activate` - Set as active block

### Memory Operations
- `POST /memory/semantic` - Add semantic memory
- `POST /memory/episodic` - Add episodic memory
- `POST /memory/core` - Update core memory
- `POST /memory/resources` - Upload document/resource
- `GET /memory/{block_id}/semantic` - Retrieve semantic memories
- `GET /memory/{block_id}/episodic` - Retrieve episodic memories
- `GET /memory/{block_id}/core` - Get core memory
- `DELETE /memory/{memory_id}` - Delete specific memory

### Chat & Conversation
- `POST /chat` - Send message and get response
- `POST /chat/flush` - Force memory pipeline processing
- `GET /chat/history` - Get conversation history
- `POST /chat/new` - Start new conversation session

### Transparency & Analytics
- `GET /transparency/operation-log` - Get operation logs
- `GET /transparency/retrieval-log` - Get retrieval logs
- `GET /transparency/processing-history` - Get processing history
- `GET /transparency/llm-usage` - Get LLM usage stats

---

## Detailed Endpoint Reference

### Memory Blocks

#### Create Memory Block

```http
POST /blocks
```

**Request Body**:
```json
{
  "name": "Work Projects",
  "description": "Memory block for work-related information",
  "tags": ["work", "projects"]
}
```

**Response**:
```json
{
  "id": "block_abc123",
  "name": "Work Projects",
  "description": "Memory block for work-related information",
  "tags": ["work", "projects"],
  "owner_id": "user_xyz789",
  "created_at": "2024-03-15T10:30:00Z",
  "updated_at": "2024-03-15T10:30:00Z",
  "is_active": false
}
```

#### List Memory Blocks

```http
GET /blocks
```

**Query Parameters**:
- `skip`: Number of records to skip (default: 0)
- `limit`: Max records to return (default: 10)
- `tags`: Filter by tags (comma-separated)

**Response**:
```json
{
  "blocks": [
    {
      "id": "block_abc123",
      "name": "Work Projects",
      "description": "Memory block for work-related information",
      "tags": ["work", "projects"],
      "is_active": true,
      "memory_count": {
        "semantic": 45,
        "episodic": 12,
        "resources": 3
      }
    }
  ],
  "total": 5,
  "skip": 0,
  "limit": 10
}
```

#### Get Block Details

```http
GET /blocks/{block_id}
```

**Response**:
```json
{
  "id": "block_abc123",
  "name": "Work Projects",
  "description": "Memory block for work-related information",
  "tags": ["work", "projects"],
  "owner_id": "user_xyz789",
  "created_at": "2024-03-15T10:30:00Z",
  "updated_at": "2024-03-15T10:30:00Z",
  "is_active": true,
  "core_memory": {
    "persona": "Professional AI assistant for project management",
    "human": "Software engineer working on ML projects"
  },
  "metadata": {
    "memory_counts": {
      "semantic": 45,
      "episodic": 12,
      "resources": 3
    },
    "last_accessed": "2024-03-15T14:20:00Z"
  }
}
```

#### Delete Memory Block

```http
DELETE /blocks/{block_id}
```

**Response**:
```json
{
  "message": "Memory block deleted successfully",
  "block_id": "block_abc123"
}
```

---

### Memory Operations

#### Add Semantic Memory

```http
POST /memory/semantic
```

**Request Body**:
```json
{
  "block_id": "block_abc123",
  "content": "Project deadline is March 25, 2024",
  "metadata": {
    "source": "user_provided",
    "category": "event_factual",
    "entities": ["project", "deadline"],
    "timestamp": "2024-03-15T10:00:00Z"
  }
}
```

**Response**:
```json
{
  "memory_id": "mem_xyz456",
  "block_id": "block_abc123",
  "content": "Project deadline is March 25, 2024",
  "created_at": "2024-03-15T10:00:00Z",
  "vector_id": "vec_123abc"
}
```

#### Add Episodic Memory (Conversation Summary)

```http
POST /memory/episodic
```

**Request Body**:
```json
{
  "block_id": "block_abc123",
  "summary": "Discussed project timeline and agreed on deliverables",
  "messages": [
    {"role": "user", "content": "When is the deadline?"},
    {"role": "assistant", "content": "March 25, 2024"}
  ],
  "metadata": {
    "session_id": "session_789",
    "duration_seconds": 120,
    "key_points": ["timeline", "deliverables"]
  }
}
```

**Response**:
```json
{
  "episodic_id": "epi_def789",
  "block_id": "block_abc123",
  "summary": "Discussed project timeline and agreed on deliverables",
  "created_at": "2024-03-15T10:05:00Z"
}
```

#### Update Core Memory

```http
POST /memory/core
```

**Request Body**:
```json
{
  "block_id": "block_abc123",
  "persona": "Professional AI assistant specialized in project management and ML",
  "human": "Software engineer working on ML projects, prefers Python"
}
```

**Response**:
```json
{
  "block_id": "block_abc123",
  "core_memory": {
    "persona": "Professional AI assistant specialized in project management and ML",
    "human": "Software engineer working on ML projects, prefers Python"
  },
  "updated_at": "2024-03-15T10:10:00Z"
}
```

#### Upload Resource (Document)

```http
POST /memory/resources
```

**Request Body** (multipart/form-data):
```
file: <binary file>
block_id: block_abc123
metadata: {"type": "pdf", "category": "documentation"}
```

**Response**:
```json
{
  "resource_id": "res_ghi012",
  "block_id": "block_abc123",
  "filename": "api_documentation.pdf",
  "chunks_created": 25,
  "processed_at": "2024-03-15T10:15:00Z"
}
```

---

### Chat & Conversation

#### Send Chat Message

```http
POST /chat
```

**Request Body**:
```json
{
  "message": "What's the project deadline?",
  "block_id": "block_abc123",
  "session_id": "session_789",
  "include_transparency": true
}
```

**Response**:
```json
{
  "response": "Based on our previous discussion, the project deadline is March 25, 2024.",
  "session_id": "session_789",
  "context_used": {
    "semantic_memories": 3,
    "episodic_memories": 1,
    "core_memory": true
  },
  "transparency": {
    "retrieval_log": {
      "query": "project deadline",
      "results_found": 4,
      "reranked": true
    },
    "llm_usage": {
      "input_tokens": 450,
      "output_tokens": 25,
      "model": "gpt-4"
    }
  }
}
```

#### Flush Memory Pipeline

```http
POST /chat/flush
```

**Request Body**:
```json
{
  "block_id": "block_abc123",
  "session_id": "session_789"
}
```

**Response**:
```json
{
  "message": "Memory pipeline processed successfully",
  "memories_extracted": {
    "semantic": 2,
    "core_updates": 1,
    "episodic_summary": true
  }
}
```

#### Get Conversation History

```http
GET /chat/history?session_id=session_789&limit=50
```

**Response**:
```json
{
  "session_id": "session_789",
  "messages": [
    {
      "role": "user",
      "content": "What's the project deadline?",
      "timestamp": "2024-03-15T10:20:00Z"
    },
    {
      "role": "assistant",
      "content": "Based on our previous discussion, the project deadline is March 25, 2024.",
      "timestamp": "2024-03-15T10:20:05Z"
    }
  ],
  "total_messages": 2
}
```

---

### Transparency & Analytics

#### Get Operation Logs

```http
GET /transparency/operation-log?block_id=block_abc123&limit=10
```

**Response**:
```json
{
  "logs": [
    {
      "timestamp": "2024-03-15T10:20:00Z",
      "operation": "semantic_memory_add",
      "block_id": "block_abc123",
      "details": {
        "content_length": 45,
        "embedding_generated": true
      },
      "duration_ms": 150
    }
  ],
  "total": 50
}
```

#### Get Retrieval Logs

```http
GET /transparency/retrieval-log?block_id=block_abc123&limit=5
```

**Response**:
```json
{
  "retrievals": [
    {
      "timestamp": "2024-03-15T10:20:05Z",
      "query": "project deadline",
      "block_id": "block_abc123",
      "results": {
        "semantic": 3,
        "episodic": 1,
        "resources": 0
      },
      "reranking_applied": true,
      "latency_ms": 45
    }
  ]
}
```

#### Get LLM Usage Statistics

```http
GET /transparency/llm-usage?block_id=block_abc123
```

**Response**:
```json
{
  "block_id": "block_abc123",
  "usage_summary": {
    "total_requests": 125,
    "total_input_tokens": 45000,
    "total_output_tokens": 12000,
    "total_cost_usd": 0.85,
    "by_operation": {
      "semantic_extraction": {
        "requests": 50,
        "input_tokens": 20000,
        "output_tokens": 5000
      },
      "retrieval": {
        "requests": 40,
        "input_tokens": 15000,
        "output_tokens": 4000
      },
      "conversation": {
        "requests": 35,
        "input_tokens": 10000,
        "output_tokens": 3000
      }
    }
  }
}
```

---

## Error Responses

### Standard Error Format

```json
{
  "error": "ErrorType",
  "message": "Human-readable error description",
  "details": {
    "field": "Additional context"
  },
  "status_code": 400
}
```

### Common Error Codes

| Code | Error | Description |
|------|-------|-------------|
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource already exists |
| 422 | Unprocessable Entity | Validation error |
| 500 | Internal Server Error | Server-side error |

---

## Rate Limiting

Currently no rate limiting is enforced. For production deployments, consider:
- 100 requests/minute per user for standard operations
- 10 requests/minute for resource uploads
- 1000 requests/minute for retrieval operations

---

## Pagination

List endpoints support pagination:

```http
GET /blocks?skip=20&limit=10
```

**Response includes**:
```json
{
  "data": [...],
  "total": 55,
  "skip": 20,
  "limit": 10
}
```

---

## Running the API

### Development

```bash
cd backend
uvicorn src.api.main:app --reload --port 8000
```

### Production

```bash
cd backend
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Additional Resources

- [Architecture Overview](./ARCHITECTURE.md)
- [Deployment Guide](./DEPLOYMENT.md)
- [Python Library Usage](./LIBRARY.md)
- API Interactive Docs: `http://localhost:8000/docs`

---

**For issues or questions, please open a GitHub issue.**
