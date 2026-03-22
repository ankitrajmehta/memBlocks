# memBlocks Library Setup Guide

This guide is specific to `memblocks_lib` and reflects the current library implementation in `memblocks_lib/src/memblocks`.

---

## 1) Prerequisites

### Runtime services

The library depends on:

| Service | Default | Why it is needed |
|---|---|---|
| MongoDB | `localhost:27017` | users, blocks, core memory, sessions |
| Qdrant | `localhost:6333` | semantic vector storage and hybrid retrieval |
| Ollama | `http://localhost:11434` | dense embeddings (`nomic-embed-text`) |

Optional but recommended:

| Service/API | Why it is needed |
|---|---|
| Cohere API (`COHERE_API_KEY`) | fast retrieval reranking (`rerank-v4.0-fast`) |

### Python

- Python `>=3.11`

---

## 2) Install

### Workspace install (recommended in this monorepo)

```bash
uv sync --all-packages
```

### Editable install of just the library

```bash
uv pip install -e memblocks_lib
```

---

## 3) Configure environment

From repository root:

```bash
cp .env.example .env
```

Then fill values in `.env`.

### Minimum required fields

```env
# Provider selection
LLM_PROVIDER_NAME=groq

# Required for selected provider
GROQ_API_KEY=gsk_xxx
# or GEMINI_API_KEY=...
# or OPENROUTER_API_KEY=...

# Required storage
MONGODB_CONNECTION_STRING=mongodb://admin:memblocks123@localhost:27017/memblocks?authSource=admin
```

### Commonly used fields

```env
LLM_MODEL=mmoonshotai/kimi-k2-instruct-0905

QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_PREFER_GRPC=true

OLLAMA_BASE_URL=http://localhost:11434
EMBEDDINGS_MODEL=nomic-embed-text
SPARSE_EMBEDDINGS_MODEL=prithivida/Splade_PP_en_v1

MEMORY_WINDOW=10
KEEP_LAST_N=4

LLM_CONVO_TEMPERATURE=0.7
LLM_SEMANTIC_EXTRACTION_TEMPERATURE=0.0
LLM_CORE_EXTRACTION_TEMPERATURE=0.0
LLM_RECURSIVE_SUMMARY_GEN_TEMPERATURE=0.3
LLM_MEMORY_UPDATE_TEMPERATURE=0.0

RETRIEVAL_ENABLE_QUERY_EXPANSION=true
RETRIEVAL_ENABLE_HYPOTHETICAL_PARAGRAPHS=false
RETRIEVAL_ENABLE_RERANKING=true
RETRIEVAL_ENABLE_SPARSE=true
RETRIEVAL_TOP_K_PER_QUERY=5
RETRIEVAL_FINAL_TOP_K=10

# Optional, enables Cohere reranking
COHERE_API_KEY=your_cohere_api_key_here
```

---

## 4) Provider setup

The library supports `groq`, `gemini`, and `openrouter` through `MemBlocksClient` task-based provider wiring.

### Groq

```env
LLM_PROVIDER_NAME=groq
GROQ_API_KEY=gsk_xxx
```

### Gemini

```env
LLM_PROVIDER_NAME=gemini
GEMINI_API_KEY=AIzaSy_xxx
LLM_MODEL=gemini-2.0-flash
```

### OpenRouter

```env
LLM_PROVIDER_NAME=openrouter
OPENROUTER_API_KEY=sk-or-xxx
OPENROUTER_FALLBACK_MODELS=anthropic/claude-3.5-sonnet,google/gemini-2.0-flash
OPENROUTER_ENABLE_THINKING=false
```

---

## 5) Per-task LLM routing (optional)

`MemBlocksConfig.llm_settings` lets you assign different providers/models by task.

```python
from memblocks import MemBlocksClient, MemBlocksConfig
from memblocks import LLMSettings, LLMTaskSettings

config = MemBlocksConfig(
    mongodb_connection_string="mongodb://localhost:27017",
    groq_api_key="gsk_xxx",
    openrouter_api_key="sk-or-xxx",
    llm_settings=LLMSettings(
        default=LLMTaskSettings(
            provider="groq",
            model="llama-3.1-8b-instant",
            temperature=0.0,
        ),
        conversation=LLMTaskSettings(
            provider="openrouter",
            model="openai/gpt-4o-mini",
            temperature=0.7,
        ),
        retrieval=LLMTaskSettings(
            provider="groq",
            model="llama-3.1-8b-instant",
            temperature=0.4,
        ),
    ),
)

client = MemBlocksClient(config)
```

Tasks available in `LLMSettings`:

- `conversation`
- `ps1_semantic_extraction`
- `ps2_conflict_resolution`
- `retrieval`
- `core_memory_extraction`
- `recursive_summary`

---

## 6) First run

```python
import asyncio
from memblocks import MemBlocksClient, MemBlocksConfig


async def main() -> None:
    client = MemBlocksClient(MemBlocksConfig())

    await client.get_or_create_user("alice")
    block = await client.create_block(
        user_id="alice",
        name="Work",
        description="Project memory",
    )
    session = await client.create_session(user_id="alice", block_id=block.id)

    user_msg = "I am building a retrieval pipeline with Qdrant."

    context = await block.retrieve(user_msg)
    memory_window = await session.get_memory_window()
    summary = await session.get_recursive_summary()

    system_parts = ["You are a helpful assistant."]
    if summary:
        system_parts.append(f"<Summary>\n{summary}\n</Summary>")
    if not context.is_empty():
        system_parts.append(context.to_prompt_string())
    system_prompt = "\n\n".join(system_parts)

    llm_messages = (
        [{"role": "system", "content": system_prompt}]
        + memory_window
        + [{"role": "user", "content": user_msg}]
    )
    ai_response = await client.conversation_llm.chat(messages=llm_messages)

    await session.add(user_msg=user_msg, ai_response=ai_response)

    # Optional: force processing of short sessions before exit
    await session.flush()

    await client.close()


asyncio.run(main())
```

---

## 7) Logging

The library uses logger namespace `memblocks` and is silent by default (`NullHandler`).

```python
import logging

root = logging.getLogger("memblocks")
root.setLevel(logging.INFO)
root.addHandler(logging.StreamHandler())
```

---

## 8) Troubleshooting

### `GROQ_API_KEY not set - required for provider 'groq'`

- Set `GROQ_API_KEY` or switch `LLM_PROVIDER_NAME` to a provider with its key configured.

### `GEMINI_API_KEY not set - required for provider 'gemini'`

- Set `GEMINI_API_KEY` and a Gemini model.

### `OPENROUTER_API_KEY not set - required for provider 'openrouter'`

- Set `OPENROUTER_API_KEY`.

### `MONGODB_CONNECTION_STRING not found in environment variables`

- Set `MONGODB_CONNECTION_STRING` and ensure MongoDB is reachable.

### Qdrant/Ollama connection errors

- Verify Qdrant at `http://localhost:6333`.
- Verify Ollama at `http://localhost:11434`.
- Ensure Ollama model used by `EMBEDDINGS_MODEL` is available.

### Reranking fails with missing Cohere key

- Retrieval still works; it falls back to original ordering.
- Set `COHERE_API_KEY` to enable reranking.

---

## Next docs

- `memblocks_lib/docs/02_METHODS_AND_INTERFACES.md`
- `memblocks_lib/docs/03_TECHNICAL_OVERVIEW.md`
