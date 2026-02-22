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

# === LLM Temperatures (Optional) ===
LLM_CONVO_TEMPERATURE=0.7
LLM_SEMANTIC_EXTRACTION_TEMPERATURE=0.0
LLM_CORE_EXTRACTION_TEMPERATURE=0.0
LLM_RECURSIVE_SUMMARY_GEN_TEMPERATURE=0.3
LLM_MEMORY_UPDATE_TEMPERATURE=0.0
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
    
    # Phase A — Initialization (once per run/user/session)
    user = await client.get_or_create_user("alice")
    print(f"User: {user['user_id']}")
    
    block = await client.create_block(
        user_id="alice",
        name="Work Memory",
        description="Professional context and project details"
    )
    print(f"Created block: {block.name} ({block.id})")
    
    session = await client.create_session(user_id="alice", block_id=block.id)
    print(f"Created session: {session.id}")
    
    # Phase B — Per-turn loop
    user_msg = "Hello! I'm working on a machine learning project."
    
    # 1. Retrieve memory context
    context = await block.retrieve(user_msg)
    memory_window = await session.get_memory_window()
    summary = await session.get_recursive_summary()
    
    # 2. Build system prompt
    system_parts = ["You are a helpful assistant."]
    if summary:
        system_parts.append(f"<Summary>\n{summary}\n</Summary>")
    if not context.is_empty():
        system_parts.append(context.to_prompt_string())
    system_prompt = "\n\n".join(system_parts)
    
    # 3. Call LLM (you control this!)
    messages = (
        [{"role": "system", "content": system_prompt}]
        + memory_window
        + [{"role": "user", "content": user_msg}]
    )
    ai_response = await client.llm.chat(messages=messages)
    print(f"Response: {ai_response}")
    
    # 4. Persist the turn
    await session.add(user_msg=user_msg, ai_response=ai_response)
    
    # Cleanup
    await client.close()

asyncio.run(main())
```

### Expected Output

```
User: alice
   ✓ Created semantic collection: block_xxx_semantic
   ✓ Created core memory document: block_xxx
✅ Created memory block: block_xxx
✅ Created session: session_yyy (block: block_xxx)
Response: Hello! I'd be happy to help with your machine learning project...
```

---

## Library Philosophy

**memBlocks is a memory management library — not an inference engine.**

You control the LLM calls. The library handles:
- Memory retrieval (semantic, core, resource)
- Memory storage and deduplication
- Conversation window management
- Recursive summary generation

This design gives you maximum flexibility:
- Use any LLM provider
- Use any prompting strategy
- Use any conversation format
- The library stays out of your way

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
