# memBlocks Library Methods and Interfaces

This document is the API-facing reference for the current `memblocks_lib` package.

It reflects the actual interfaces in:

- `memblocks_lib/src/memblocks/client.py`
- `memblocks_lib/src/memblocks/services/*.py`
- `memblocks_lib/src/memblocks/models/*.py`

---

## 1) Quick start interface map

```python
from memblocks import MemBlocksClient, MemBlocksConfig

config = MemBlocksConfig()
client = MemBlocksClient(config)

# Initialization
await client.get_or_create_user("alice")
block = await client.create_block(user_id="alice", name="Work")
session = await client.create_session(user_id="alice", block_id=block.id)

# Per-turn usage
context = await block.retrieve("What did we decide about deployment?")
window = await session.get_memory_window()
summary = await session.get_recursive_summary()

response = await client.conversation_llm.chat(
    messages=[
        {"role": "system", "content": "You are helpful."},
        *window,
        {"role": "user", "content": "What did we decide about deployment?"},
    ]
)

await session.add(user_msg="What did we decide about deployment?", ai_response=response)
await client.close()
```

---

## 2) `MemBlocksClient`

Main composition root that wires storage, providers, services, and transparency.

Constructor:

```python
from memblocks import MemBlocksClient, MemBlocksConfig

client = MemBlocksClient(MemBlocksConfig())
```

### Injected constructor arguments

```python
MemBlocksClient(
    config: MemBlocksConfig,
    *,
    mongo_adapter: Optional[MongoDBAdapter] = None,
    embedding_provider: Optional[EmbeddingProvider] = None,
    qdrant_adapter: Optional[QdrantAdapter] = None,
)
```

### Attributes (public)

| Attribute | Type | Purpose |
|---|---|---|
| `mongo` | `MongoDBAdapter` | Mongo persistence adapter |
| `qdrant` | `QdrantAdapter` | Qdrant vector adapter |
| `embeddings` | `EmbeddingProvider` | dense+sparse embedding provider |
| `conversation_llm` | `LLMProvider` | provider used for user-facing chat |
| `llm` | `LLMProvider` | alias of `conversation_llm` |
| `event_bus` | `EventBus` | pub/sub events |
| `operation_log` | `OperationLog` | write operation log |
| `retrieval_log` | `RetrievalLog` | retrieval log |
| `processing_history` | `ProcessingHistory` | pipeline run history |
| `llm_usage` | `LLMUsageTracker` | token/latency tracking |

### User methods

#### `create_user(user_id: str, metadata: dict | None = None) -> dict`

Creates user or returns existing one.

#### `get_user(user_id: str) -> dict | None`

Returns user document by `user_id`.

#### `get_or_create_user(user_id: str, metadata: dict | None = None) -> dict`

Idempotent helper.

#### `list_users() -> list[dict]`

Returns all users.

### Block methods

#### `create_block(...) -> Block`

```python
create_block(
    user_id: str,
    name: str,
    description: str = "",
    create_semantic: bool = True,
    create_core: bool = True,
    create_resource: bool = False,
) -> Block
```

Creates Mongo block doc and optional Qdrant collections/core memory seed doc.

#### `get_block(block_id: str) -> Block | None`

Loads a stateful `Block` handle.

#### `get_user_blocks(user_id: str) -> list[Block]`

Loads all blocks for a user.

#### `delete_block(block_id: str, user_id: str) -> bool`

Deletes block document from MongoDB.

### Session methods

#### `create_session(user_id: str, block_id: str) -> Session`

Creates session document and returns stateful `Session`.

#### `get_session(session_id: str) -> Session | None`

Loads existing session.

### Transparency helpers

#### `subscribe(event_name: str, callback: Callable) -> None`
#### `unsubscribe(event_name: str, callback: Callable) -> None`
#### `get_operation_log() -> OperationLog`
#### `get_retrieval_log() -> RetrievalLog`
#### `get_processing_history() -> ProcessingHistory`
#### `get_llm_usage() -> LLMUsageTracker`

### Lifecycle

#### `close() -> None`

Closes Mongo client connection.

---

## 3) `Block` (stateful retrieval handle)

Returned by `client.create_block()` and `client.get_block()`.

### Attributes

| Attribute | Type |
|---|---|
| `id` | `str` |
| `name` | `str` |
| `description` | `str` |
| `user_id` | `str` |
| `semantic_collection` | `str | None` |
| `core_memory_block_id` | `str | None` |
| `resource_collection` | `str | None` |
| `created_at` | `str` |
| `updated_at` | `str` |

### Methods

#### `retrieve(query: str) -> RetrievalResult`

Returns core + semantic (resource currently empty).

#### `core_retrieve() -> RetrievalResult`

Core only.

#### `semantic_retrieve(query: str) -> RetrievalResult`

Semantic only.

#### `resource_retrieve(query: str) -> RetrievalResult`

Stub currently returning empty `resource` list.

---

## 4) `Session` (stateful turn persistence handle)

Returned by `client.create_session()` and `client.get_session()`.

### Attributes

| Attribute | Type |
|---|---|
| `id` | `str` |
| `user_id` | `str` |
| `block_id` | `str` |
| `created_at` | `str` |

### Methods

#### `get_memory_window() -> list[dict[str, Any]]`

Returns recent session messages from MongoDB (window-limited).

#### `get_recursive_summary() -> str`

Returns persisted session summary.

#### `add(user_msg: str, ai_response: str) -> None`

Persists one user+assistant turn and triggers pipeline when message count reaches `memory_window_limit`.

Pipeline behavior in `add()`:

1. push user/assistant messages
2. if threshold reached, snapshot messages+summary
3. trim messages to `keep_last_n`
4. run memory pipeline
5. save new recursive summary
6. persist block-level LLM usage snapshot

#### `flush() -> str`

Manually run pipeline for current session messages even before threshold; returns new summary.

---

## 5) `RetrievalResult`

Structured return object for `Block` retrieval methods.

### Fields

| Field | Type |
|---|---|
| `core` | `CoreMemoryUnit | None` |
| `semantic` | `list[SemanticMemoryUnit]` |
| `resource` | `list[ResourceMemoryUnit]` |

### Methods

#### `to_prompt_string() -> str`

Formats context into tagged sections suitable for system prompt injection:

- `<Core Memory>` with `[PERSONA]` and `[HUMAN]`
- `<Semantic Memories>` entries with type/content and timestamps

#### `is_empty() -> bool`

True when no core/semantic/resource payload exists.

---

## 6) LLM interfaces

### `LLMProvider` base class

Implemented methods required by all providers:

```python
class LLMProvider:
    def create_structured_chain(
        self,
        system_prompt: str,
        pydantic_model: Type[BaseModel],
        temperature: float = 0.0,
    ) -> Any: ...

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
    ) -> str: ...
```

### Built-in providers

| Provider | Module | Notes |
|---|---|---|
| `GroqLLMProvider` | `memblocks.llm.groq_provider` | default provider path |
| `GeminiLLMProvider` | `memblocks.llm.gemini_provider` | Gemini chat + structured outputs |
| `OpenRouterLLMProvider` | `memblocks.llm.openrouter_provider` | fallback model list + thinking flag |

All providers support usage tracking integration through `LLMUsageTracker` records.

### Per-task LLM config objects

#### `LLMTaskSettings`

| Field | Type | Meaning |
|---|---|---|
| `provider` | `str` | `groq` / `gemini` / `openrouter` |
| `model` | `str` | model id |
| `temperature` | `float` | task temperature |
| `fallback_models` | `list[str]` | OpenRouter-specific |
| `enable_thinking` | `bool` | OpenRouter-specific |

#### `LLMSettings`

Task routing container:

- `default`
- `conversation`
- `ps1_semantic_extraction`
- `ps2_conflict_resolution`
- `retrieval`
- `core_memory_extraction`
- `recursive_summary`

Helper:

```python
settings.for_task("conversation")
```

---

## 7) Internal service interfaces (advanced)

These are internal-by-design but useful for contributors and advanced integrations.

### `CoreMemoryService`

| Method | Purpose |
|---|---|
| `get(block_id)` | load core memory |
| `extract(messages, old_core_memory, core_creation_prompt)` | LLM extraction |
| `save(block_id, memory_unit)` | upsert core memory |
| `update(block_id, messages, core_creation_prompt)` | extract+save |

### `SemanticMemoryService`

| Method | Purpose |
|---|---|
| `extract(messages, ps1_prompt)` | PS1 memory extraction |
| `store(memory_unit)` | PS2 conflict resolution + Qdrant ops |
| `extract_and_store(messages, ps1_prompt, min_confidence)` | convenience path |
| `retrieve(query_texts, top_k)` | enhanced retrieval pipeline |

Retrieval pipeline behavior includes:

- query enhancement (expansions + optional hypothetical paragraphs)
- hybrid retrieval (dense + sparse via Qdrant RRF) when enabled
- optional Cohere reranking
- transparency logging and event publishing

### `MemoryPipeline`

Public method:

```python
await pipeline.run(
    user_id: str,
    block_id: str,
    messages: list[dict[str, str]],
    current_summary: str = "",
) -> str
```

Pipeline stages:

1. semantic extraction + storage
2. core memory update
3. recursive summary generation

### `EventBus`

Valid events:

- `on_memory_extracted`
- `on_conflict_resolved`
- `on_memory_stored`
- `on_core_memory_updated`
- `on_summary_generated`
- `on_pipeline_started`
- `on_pipeline_completed`
- `on_pipeline_failed`
- `on_memory_retrieved`
- `on_db_write`
- `on_message_processed`

---

## 8) Storage adapter interfaces (advanced)

### `MongoDBAdapter`

Core method groups:

- user CRUD (`create_user`, `get_user`, `list_users`, `add_block_to_user`)
- block CRUD (`create_memory_block`, `get_memory_block`, `list_user_blocks`, `delete_memory_block`)
- core memory (`save_core_memory`, `get_core_memory`, `delete_core_memory`)
- session persistence (`create_session`, `get_session`, `add_message_to_session`, `get_session_messages`, `trim_session_messages`, `set_session_summary`, `get_session_summary`, `update_block_llm_usage`)

### `QdrantAdapter`

Main methods:

- `create_collection(name, vector_size=None)`
- `store_vector(collection, vector, payload, point_id=None, sparse_vector=None)`
- `retrieve_from_vector(collection, query_vector, top_k)`
- `retrieve_hybrid(collection, dense_query_vector, sparse_query_vector, top_k)`
- `delete_vector(collection, point_id)`
- `get_all_points(collection, limit=100)`

### `EmbeddingProvider`

Methods:

- dense: `embed_text`, `embed_documents`, `get_dimension`
- sparse (SPLADE): `embed_sparse_text`, `embed_sparse_documents`

---

## 9) Key data models

### `MemoryBlock` / `MemoryBlockMetaData`

Represents persisted block state and metadata, including `meta_data.llm_usage`.

### `SemanticMemoryUnit`

Primary semantic memory payload stored in Qdrant.

Fields include:

- `content`, `type`, `source`, `confidence`
- `memory_time`, `updated_at`
- `keywords`, `entities`, `embedding_text`
- optional `memory_id`, `meta_data`

### `CoreMemoryUnit`

- `persona_content`
- `human_content`

### `MemoryOperation`

Pipeline operation record:

- `operation`: `ADD` / `UPDATE` / `DELETE` / `NONE`
- `memory_id`, `content`, `old_content`

### Transparency models

- `OperationEntry`
- `RetrievalEntry`
- `PipelineRunEntry`
- `LLMCallRecord`
- `LLMUsageSummary`

---

## 10) Exported public API

Convenience imports from package root:

```python
from memblocks import (
    MemBlocksClient,
    MemBlocksConfig,
    Block,
    Session,
    RetrievalResult,
    LLMProvider,
    GroqLLMProvider,
    GeminiLLMProvider,
    LLMTaskSettings,
    LLMSettings,
    MemoryBlock,
    MemoryBlockMetaData,
    SemanticMemoryUnit,
    CoreMemoryUnit,
    ResourceMemoryUnit,
    MemoryOperation,
)
```

Note: `OpenRouterLLMProvider` is exported from `memblocks.llm`, but not currently re-exported at the package root.

---

## Related docs

- `memblocks_lib/docs/01_SETUP_GUIDE.md`
- `memblocks_lib/docs/03_TECHNICAL_OVERVIEW.md`
