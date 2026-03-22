# memBlocks Library Technical Overview

This technical overview documents the current architecture and runtime behavior of `memblocks_lib`.

Scope of this document:

- `memblocks_lib/src/memblocks/*`
- package-level design for `memblocks` (library), not backend REST APIs

---

## 1) Architecture at a glance

`memblocks_lib` is a memory-management library. It does not own your app's chat loop, prompt policy, or frontend behavior.

### Layered architecture

```text
Application code
  |
  |  (you call)
  v
MemBlocksClient
  |
  +--> Services
  |      - UserManager
  |      - BlockManager
  |      - SessionManager
  |      - SemanticMemoryService
  |      - CoreMemoryService
  |      - MemoryPipeline
  |
  +--> LLM Providers
  |      - GroqLLMProvider
  |      - GeminiLLMProvider
  |      - OpenRouterLLMProvider
  |
  +--> Storage Adapters
         - MongoDBAdapter
         - QdrantAdapter
         - EmbeddingProvider (dense+sparse)
```

### Package structure

```text
memblocks_lib/
  src/memblocks/
    __init__.py
    client.py
    config.py
    logger/
    llm/
      base.py
      task_settings.py
      groq_provider.py
      gemini_provider.py
      openrouter_provider.py
    models/
      block.py
      memory.py
      retrieval.py
      units.py
      llm_outputs.py
      transparency.py
    prompts/
      __init__.py
    services/
      user_manager.py
      block_manager.py
      block.py
      session_manager.py
      session.py
      semantic_memory.py
      core_memory.py
      memory_pipeline.py
      reranker.py
      transparency.py
    storage/
      mongo.py
      qdrant.py
      embeddings.py
```

---

## 2) Key design principles

1. No global singleton managers for core runtime components.
2. Dependency wiring happens in `MemBlocksClient` constructor.
3. Library responsibilities are memory persistence/retrieval and memory pipeline processing.
4. Application controls conversation loop and how `conversation_llm` is used.
5. Observability is built in via logs/history/event bus/usage tracking.

---

## 3) End-to-end flow

### A. Initialization flow

```text
App -> MemBlocksClient(config)
  -> build adapters (Mongo, Embeddings, Qdrant)
  -> build transparency components
  -> resolve per-task llm settings
  -> build provider instances per task
  -> wire managers/services
```

### B. Per-turn flow

```text
1) app receives user message
2) app calls block.retrieve(user_msg)
3) app calls session.get_memory_window() + session.get_recursive_summary()
4) app builds prompt and calls client.conversation_llm.chat(...)
5) app calls session.add(user_msg, ai_response)
6) if window threshold reached, pipeline runs and summary persists
```

---

## 4) `MemBlocksClient` dependency graph

```text
MemBlocksClient
  config
  mongo: MongoDBAdapter
  embeddings: EmbeddingProvider
  qdrant: QdrantAdapter

  llm providers (task-scoped)
    conversation_llm
    _ps1_llm
    _ps2_llm
    _retrieval_llm
    _core_llm
    _summary_llm

  transparency
    event_bus
    operation_log
    retrieval_log
    processing_history
    llm_usage

  services
    _users: UserManager
    _core: CoreMemoryService
    _blocks: BlockManager
    _sessions: SessionManager
```

Provider construction is centralized in `client._build_provider(task_settings, config, usage_tracker, call_type)`.

---

## 5) Configuration system (`MemBlocksConfig`)

`MemBlocksConfig` is a `BaseSettings` model with `.env` support.

### Resolution order

1. constructor args
2. env vars
3. `.env`
4. field defaults

### Important fields

| Category | Fields |
|---|---|
| Provider | `llm_provider_name`, `llm_model`, provider API keys |
| Per-task LLM | `llm_settings` (`LLMSettings`) |
| Mongo | `mongodb_connection_string`, DB/collection names |
| Qdrant | host/port/grpc + collection templates |
| Embeddings | `embeddings_model`, `sparse_embeddings_model`, `ollama_base_url` |
| Pipeline | `memory_window_limit`, `keep_last_n` |
| Retrieval | query enhancement / sparse / reranking controls |
| Monitoring | Arize fields |

### Legacy + modern LLM config bridge

`resolved_llm_settings` does this:

- if `llm_settings` is set, use it directly
- else auto-build task settings from legacy flat fields (`llm_provider_name`, `llm_model`, temperatures)

This preserves backward compatibility while enabling task-level routing.

---

## 6) LLM architecture

### `LLMProvider` contract

Two methods only:

- `create_structured_chain(...)`
- `chat(...)`

Services remain responsible for prompts and data shaping.

### Built-in providers

```text
GroqLLMProvider
GeminiLLMProvider
OpenRouterLLMProvider
```

All support:

- Arize optional instrumentation
- token/latency tracking via `LLMUsageTracker`

OpenRouter-specific behavior:

- optional fallback model list
- optional thinking/reasoning flag

### Task routing map

```text
conversation            -> app-facing chat call
ps1_semantic_extraction -> semantic extraction chain
ps2_conflict_resolution -> conflict resolution chain
retrieval               -> query enhancement
core_memory_extraction  -> core extraction chain
recursive_summary       -> summary chain
```

---

## 7) Data model relationships

### Core entities

```text
User
  has many Block IDs

MemoryBlock
  -> semantic_collection (Qdrant)
  -> core_memory_block_id (Mongo key)
  -> resource_collection (Qdrant, optional)

Session
  belongs to (user_id, block_id)
  holds messages[] and recursive_summary
```

### Memory unit types

```text
SemanticMemoryUnit
  - content/type/confidence/source
  - keywords/entities
  - memory_time/updated_at
  - embedding_text

CoreMemoryUnit
  - persona_content
  - human_content

ResourceMemoryUnit
  - resource metadata payload (resource retrieval path currently stubbed at Block level)
```

### Retrieval envelope

`RetrievalResult` groups `core`, `semantic`, `resource` and renders prompt text.

---

## 8) Storage layer details

### MongoDBAdapter

Collections:

- users
- memory_blocks
- core_memories
- sessions

Session document stores:

- `session_id`, `user_id`, `block_id`, `created_at`
- `messages[]`
- `recursive_summary`

Block document contains references to semantic/core/resource stores and metadata including `meta_data.llm_usage`.

### QdrantAdapter

Per-block collections typically:

- `{block_id}_semantic`
- `{block_id}_resource` (optional)

Supports:

- dense vector insert/search
- sparse-aware upsert
- hybrid retrieval with dense+sparse fusion (`retrieve_hybrid`)
- point deletion
- collection creation with lazy vector dimension resolution

### EmbeddingProvider

Dense path:

- Ollama `/api/embeddings`

Sparse path:

- fastembed SPLADE model (lazy-initialized)

---

## 9) Retrieval flow (current enhanced path)

`SemanticMemoryService.retrieve()` executes per query:

1. query enhancement
   - expanded queries
   - optional hypothetical paragraphs
2. embedding generation for all variants
3. retrieval
   - hybrid (dense+sparse) when enabled
   - dense-only fallback when disabled
4. dedupe by `memory_id`
5. optional Cohere reranking
6. final top-k cutoff
7. retrieval transparency record + event publish

### Retrieval pipeline diagram

```text
query
  -> enhance query variants
  -> embed dense (+ sparse optional)
  -> retrieve from Qdrant
  -> dedupe
  -> rerank (optional)
  -> final top_k
  -> RetrievalEntry + on_memory_retrieved
```

---

## 10) Memory pipeline internals

`MemoryPipeline.run(user_id, block_id, messages, current_summary) -> new_summary`

Execution stages:

1. semantic extraction (PS1)
2. semantic storage with conflict resolution (PS2)
3. core memory update
4. recursive summary generation
5. return new summary to caller

Session-level state changes (outside pipeline):

- persist summary via `set_session_summary`
- trim message history via `trim_session_messages`

### Pipeline sequence diagram

```text
Session.add()
  -> push user/assistant messages
  -> threshold check
  -> snapshot messages + summary
  -> trim messages to keep_last_n
  -> MemoryPipeline.run(...)
       -> semantic.extract
       -> semantic.store (per memory)
       -> core.update
       -> summary generation
       -> processing history + events
  -> set_session_summary(new_summary)
  -> update_block_llm_usage(...)
```

---

## 11) Block and session creation flows

### Block creation

```text
client.create_block(...)
  -> generate block_id
  -> create semantic/resource collections if requested
  -> seed core memory doc if requested
  -> create memory_blocks doc
  -> link block_id to user
  -> return Block handle
```

### Session creation

```text
client.create_session(user_id, block_id)
  -> create sessions doc
  -> derive semantic collection name
  -> build block-scoped SemanticMemoryService + MemoryPipeline
  -> return Session handle
```

---

## 12) Observability and transparency

Provided by `services/transparency.py`:

- `OperationLog`
- `RetrievalLog`
- `ProcessingHistory`
- `EventBus`
- `LLMUsageTracker`

### Event bus event names

```text
on_memory_extracted
on_conflict_resolved
on_memory_stored
on_core_memory_updated
on_summary_generated
on_pipeline_started
on_pipeline_completed
on_pipeline_failed
on_memory_retrieved
on_db_write
on_message_processed
```

### LLM usage tracking model

Each call is captured as `LLMCallRecord` with:

- call type
- provider/model
- input/output/total tokens
- latency
- success/failure
- optional block association

Aggregations available:

- global summary
- per-block summary
- per-run summary (since timestamp)

---

## 13) Current behavior notes and implementation-specific details

1. `Session.add()` trims messages before invoking pipeline, while pipeline still uses the pre-trimmed snapshot.
2. Block deletion via `BlockManager.delete_block()` removes the MongoDB block document; Qdrant collection cleanup is not automatic in this flow.
3. Root package exports include Groq and Gemini provider classes; OpenRouter provider is exported under `memblocks.llm`.
4. Resource retrieval at `Block.resource_retrieve()` is currently a stub returning empty results.
5. Retrieval reranking is via Cohere when enabled and configured; failures degrade gracefully to original ranking.

---

## 14) Storage schema references

### MongoDB collections

| Collection | Core keys |
|---|---|
| `users` | `user_id`, `block_ids[]`, `metadata` |
| `memory_blocks` | `block_id`, `user_id`, section refs, `meta_data` |
| `core_memories` | `block_id`, `persona_content`, `human_content` |
| `sessions` | `session_id`, `block_id`, `messages[]`, `recursive_summary` |

### Qdrant

| Collection pattern | Payload type |
|---|---|
| `{block_id}_semantic` | serialized `SemanticMemoryUnit` |
| `{block_id}_resource` | resource payloads (optional/future path) |

---

## 15) Operational recommendations

1. Keep `MEMORY_WINDOW` and `KEEP_LAST_N` aligned with your latency and memory freshness goals.
2. If you need higher retrieval quality, enable sparse retrieval and Cohere reranking.
3. Subscribe to pipeline events in production apps for monitoring and alerting.
4. Persist and inspect `meta_data.llm_usage` on blocks for cost/performance governance.

---

## Related docs

- `memblocks_lib/docs/01_SETUP_GUIDE.md`
- `memblocks_lib/docs/02_METHODS_AND_INTERFACES.md`
