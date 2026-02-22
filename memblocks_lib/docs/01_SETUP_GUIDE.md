# memBlocks Library — Setup Guide

This guide covers installation, prerequisites, configuration, and first-run setup for the `memblocks` library.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [First Run](#first-run)
5. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Infrastructure

The library requires three services to be running:

| Service | Default Port | Purpose |
|---------|--------------|---------|
| **MongoDB** | 27017 | User data, blocks, core memories, sessions |
| **Qdrant** | 6333 (REST), 6334 (gRPC) | Vector storage for semantic memories |
| **Ollama** | 11434 | Local embeddings (nomic-embed-text model) |

### Quick Start with Docker

```bash
# From the project root
docker-compose up -d
```

This starts all three services. Verify they're running:

```bash
docker ps
```

### Pull the Embedding Model

```bash
docker exec -it ollama ollama pull nomic-embed-text
```

---

## Installation

### Using UV (Recommended)

The project uses [UV](https://astral.sh/uv/) as its package manager:

```bash
# Install UV if not already installed
# macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell):
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Sync all workspace packages
uv sync --all-packages
```

### Using pip

```bash
pip install memblocks
```

### Requirements

- **Python**: 3.11 or higher
- **Operating System**: macOS, Linux, or Windows

---

## Configuration

### Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
# === LLM Configuration (Required) ===
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxx
LLM_MODEL=meta-llama/llama-4-maverick-17b-128e-instruct

# === MongoDB (Required) ===
MONGODB_CONNECTION_STRING=mongodb://localhost:27017
MONGODB_DATABASE_NAME=memblocks
MONGO_COLLECTION_USERS=users
MONGO_COLLECTION_BLOCKS=memory_blocks
MONGO_COLLECTION_CORE_MEMORIES=core_memories

# === Qdrant (Required) ===
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_PREFER_GRPC=true

# === Ollama / Embeddings (Required) ===
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDINGS_MODEL=nomic-embed-text

# === Memory Pipeline Behavior (Optional) ===
MEMORY_WINDOW=10          # Messages before triggering pipeline
KEEP_LAST_N=5             # Messages retained after flush
MAX_CONCURRENT_PROCESSING=3

# === LLM Temperatures (Optional) ===
LLM_CONVO_TEMPERATURE=0.7
LLM_SEMANTIC_EXTRACTION_TEMPERATURE=0.0
LLM_CORE_EXTRACTION_TEMPERATURE=0.0
LLM_RECURSIVE_SUMMARY_GEN_TEMPERATURE=0.3
LLM_MEMORY_UPDATE_TEMPERATURE=0.0

# === Arize Monitoring (Optional) ===
ARIZE_SPACE_ID=
ARIZE_API_KEY=
ARIZE_PROJECT_NAME=memBlocks
```

### Configuration via Code

You can also configure programmatically:

```python
from memblocks import MemBlocksClient, MemBlocksConfig

# Option 1: Load from .env (automatic)
config = MemBlocksConfig()

# Option 2: Explicit values
config = MemBlocksConfig(
    groq_api_key="gsk_xxxxxxxxx",
    mongodb_connection_string="mongodb://localhost:27017",
    qdrant_host="localhost",
    qdrant_port=6333,
    ollama_base_url="http://localhost:11434",
    memory_window=10,
    keep_last_n=5,
)

# Create client
client = MemBlocksClient(config)
```

---

## Configuration Reference

### Core Settings

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| `groq_api_key` | `GROQ_API_KEY` | *required* | API key for Groq LLM |
| `llm_model` | `LLM_MODEL` | `meta-llama/llama-4-maverick-17b-128e-instruct` | Model identifier |
| `mongodb_connection_string` | `MONGODB_CONNECTION_STRING` | *required* | MongoDB connection URI |
| `mongodb_database_name` | `MONGODB_DATABASE_NAME` | `memblocks` | Database name |
| `qdrant_host` | `QDRANT_HOST` | `localhost` | Qdrant server host |
| `qdrant_port` | `QDRANT_PORT` | `6333` | Qdrant REST port |
| `qdrant_prefer_grpc` | `QDRANT_PREFER_GRPC` | `true` | Use gRPC for Qdrant |
| `ollama_base_url` | `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `embeddings_model` | `EMBEDDINGS_MODEL` | `nomic-embed-text` | Embedding model name |

### Pipeline Settings

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| `memory_window` | `MEMORY_WINDOW` | `10` | Messages to accumulate before processing |
| `keep_last_n` | `KEEP_LAST_N` | `5` | Messages kept after pipeline flush |
| `max_concurrent_processing` | `MAX_CONCURRENT_PROCESSING` | `3` | Max concurrent pipeline runs |

### Temperature Settings

| Setting | Environment Variable | Default | Purpose |
|---------|---------------------|---------|---------|
| `llm_convo_temperature` | `LLM_CONVO_TEMPERATURE` | `0.7` | Chat responses |
| `llm_semantic_extraction_temperature` | `LLM_SEMANTIC_EXTRACTION_TEMPERATURE` | `0.0` | PS1 memory extraction |
| `llm_core_extraction_temperature` | `LLM_CORE_EXTRACTION_TEMPERATURE` | `0.0` | Core memory updates |
| `llm_recursive_summary_gen_temperature` | `LLM_RECURSIVE_SUMMARY_GEN_TEMPERATURE` | `0.3` | Summary generation |
| `llm_memory_update_temperature` | `LLM_MEMORY_UPDATE_TEMPERATURE` | `0.0` | PS2 conflict resolution |

---

## First Run

### Quick Test

```python
import asyncio
from memblocks import MemBlocksClient, MemBlocksConfig

async def main():
    # Initialize
    config = MemBlocksConfig()
    client = MemBlocksClient(config)
    
    # Create user
    user = await client.users.create_user("alice")
    print(f"Created user: {user['user_id']}")
    
    # Create memory block
    block = await client.blocks.create_block(
        user_id="alice",
        name="Work Memory",
        description="Professional context and project details"
    )
    print(f"Created block: {block.name} ({block.meta_data.id})")
    
    # Create chat session
    engine = client.get_chat_engine(block)
    session = await engine.sessions.create_session("alice", block.meta_data.id)
    print(f"Created session: {session['session_id']}")
    
    # Send a message
    result = await engine.chat.send_message(
        session_id=session["session_id"],
        user_message="Hello! I'm working on a machine learning project."
    )
    print(f"Response: {result['response']}")
    
    # Cleanup
    await client.close()

asyncio.run(main())
```

### Expected Output

```
Created user: alice
   ✓ Created semantic collection: block_xxx_semantic
   ✓ Created core memory document: block_xxx
✅ Created memory block: block_xxx
Created session: session_yyy
💬 Processing message...
🔍 Retrieving memories...
   📚 Semantic: 0 memories
   🧠 Core: No
Response: Hello! I'd be happy to help with your machine learning project...
```

---

## Troubleshooting

### "GROQ_API_KEY not found"

**Solution**: Set the environment variable or pass explicitly:

```python
config = MemBlocksConfig(groq_api_key="gsk_xxx")
```

### "MONGODB_CONNECTION_STRING not found"

**Solution**: Ensure MongoDB is running and the connection string is set:

```bash
# Check MongoDB is running
docker ps | grep mongo

# Start if needed
docker-compose up -d mongodb
```

### "Connection refused" to Qdrant

**Solution**: Verify Qdrant is accessible:

```bash
curl http://localhost:6333/collections
```

### "Ollama embedding error"

**Solution**: Ensure Ollama is running and the model is pulled:

```bash
# Check Ollama
curl http://localhost:11434/api/tags

# Pull model if missing
docker exec -it ollama ollama pull nomic-embed-text
```

### Import errors after installation

**Solution**: Ensure you're using UV to run scripts:

```bash
# Wrong
python my_script.py

# Correct
uv run python my_script.py
```

### Session state not persisting

The library persists sessions to MongoDB. If sessions disappear:

1. Check MongoDB is running
2. Verify `mongodb_connection_string` is correct
3. Check the `sessions` collection exists

---

## Next Steps

- [Methods and Interfaces](./02_METHODS_AND_INTERFACES.md) — API reference with examples
- [Deep Technical Overview](./03_TECHNICAL_OVERVIEW.md) — Architecture and data flow
