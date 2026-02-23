# memBlocks Library — Methods and Interfaces

This document provides a complete API reference for the `memblocks` library with practical usage examples.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [MemBlocksClient](#memblocksclient)
3. [Block](#block)
4. [Session](#session)
5. [RetrievalResult](#retrievalresult)
6. [CoreMemoryService (Internal)](#corememoryservice-internal)
7. [SemanticMemoryService (Internal)](#semanticmemoryservice-internal)
8. [Transparency Layer](#transparency-layer)
9. [Data Models](#data-models)

---

## Quick Start

```python
import asyncio
from memblocks import MemBlocksClient, MemBlocksConfig

async def main():
    # Create client (reads from .env automatically)
    config = MemBlocksConfig()
    client = MemBlocksClient(config)
    
    # Phase A — Initialization
    user = await client.get_or_create_user("alice")
    block = await client.create_block("alice", "Work Memory")
    session = await client.create_session(user_id="alice", block_id=block.id)
    
    # Phase B — Per-turn loop
    user_msg = "Hello! I'm working on a Python project."
    
    # Retrieve context
    context = await block.retrieve(user_msg)
    messages = await session.get_memory_window()
    summary = await session.get_recursive_summary()
    
    # Build prompt and call YOUR LLM
    system = "You are helpful.\n\n" + context.to_prompt_string()
    ai_response = await client.llm.chat([
        {"role": "system", "content": system},
        *messages,
        {"role": "user", "content": user_msg},
    ])
    
    # Persist the turn
    await session.add(user_msg=user_msg, ai_response=ai_response)
    print(ai_response)
    
    await client.close()

asyncio.run(main())
```

---

## MemBlocksClient

The main entry point for the library. Wires all dependencies and provides a **flat API** for users, blocks, and sessions.

### Constructor

```python
from memblocks import MemBlocksClient, MemBlocksConfig
from memblocks.llm.groq_provider import GroqLLMProvider

config = MemBlocksConfig()

# Default setup
client = MemBlocksClient(config)

# With custom LLM provider
my_llm = GroqLLMProvider(config)
client = MemBlocksClient(config, llm_provider=my_llm)

# With custom storage adapters (for testing)
client = MemBlocksClient(
    config,
    mongo_adapter=custom_mongo,
    qdrant_adapter=custom_qdrant,
    embedding_provider=custom_embeddings,
)
```

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `mongo` | `MongoDBAdapter` | MongoDB operations |
| `qdrant` | `QdrantAdapter` | Qdrant vector operations |
| `embeddings` | `EmbeddingProvider` | Ollama embedding wrapper |
| `llm` | `LLMProvider` | LLM abstraction (default: Groq) |
| `event_bus` | `EventBus` | Pub/sub for internal events |
| `operation_log` | `OperationLog` | Database write log |
| `retrieval_log` | `RetrievalLog` | Memory retrieval log |
| `processing_history` | `ProcessingHistory` | Pipeline run history |

### User Methods

#### `create_user(user_id: str, metadata: dict = None) -> Dict[str, Any]`

Create a new user (idempotent — returns existing if found).

```python
user = await client.create_user("alice", {"role": "admin"})
print(user["user_id"])  # "alice"
```

#### `get_user(user_id: str) -> Optional[Dict[str, Any]]`

Retrieve a user by ID.

```python
user = await client.get_user("alice")
if user:
    print(user["block_ids"])  # List of block IDs
```

#### `get_or_create_user(user_id: str, metadata: dict = None) -> Dict[str, Any]`

Get existing user or create if not found.

```python
user = await client.get_or_create_user("alice")
```

#### `list_users() -> List[Dict[str, Any]]`

List all users.

```python
users = await client.list_users()
for u in users:
    print(u["user_id"])
```

### Block Methods

#### `create_block(user_id, name, description="", ...) -> Block`

Create a new memory block. Returns a stateful `Block` object.

```python
block = await client.create_block(
    user_id="alice",
    name="Work Memory",
    description="Professional context and project details",
    create_semantic=True,   # Create Qdrant collection for semantic memories
    create_core=True,       # Create MongoDB document for core memory
    create_resource=False,  # Create Qdrant collection for resources
)

print(block.id)                      # "block_xxx..."
print(block.name)                    # "Work Memory"
print(block.semantic_collection)     # "block_xxx_semantic"
print(block.core_memory_block_id)    # "block_xxx..."
```

#### `get_block(block_id: str) -> Optional[Block]`

Load a memory block by ID. Returns a stateful `Block` object.

```python
block = await client.get_block("block_abc123")
if block:
    print(block.name)
```

#### `get_user_blocks(user_id: str) -> List[Block]`

List all blocks for a user. Returns list of `Block` objects.

```python
blocks = await client.get_user_blocks("alice")
for b in blocks:
    print(f"{b.name}: {b.description}")
```

#### `delete_block(block_id: str, user_id: str) -> bool`

Delete a memory block.

```python
success = await client.delete_block("block_abc123", "alice")
```

### Session Methods

#### `create_session(user_id: str, block_id: str) -> Session`

Create a new chat session attached to a block. Returns a stateful `Session` object.

```python
session = await client.create_session(
    user_id="alice",
    block_id="block_abc123"
)
print(session.id)  # "session_xxx..."
```

#### `get_session(session_id: str) -> Optional[Session]`

Retrieve a session. Returns a stateful `Session` object.

```python
session = await client.get_session("session_xxx")
if session:
    print(session.block_id)
```

### Transparency Methods

#### `subscribe(event_name: str, callback: Callable) -> None`

Subscribe to internal library events.

```python
def on_pipeline_done(payload):
    print(f"Pipeline completed: {payload['task_id']}")

client.subscribe("on_pipeline_completed", on_pipeline_done)
```

#### `unsubscribe(event_name: str, callback: Callable) -> None`

Remove a callback from event subscriptions.

```python
client.unsubscribe("on_pipeline_completed", on_pipeline_done)
```

#### `get_operation_log() -> OperationLog`

Return the OperationLog for inspecting database writes.

```python
log = client.get_operation_log()
```

#### `get_retrieval_log() -> RetrievalLog`

Return the RetrievalLog for inspecting memory retrievals.

```python
log = client.get_retrieval_log()
```

#### `get_processing_history() -> ProcessingHistory`

Return the ProcessingHistory for inspecting pipeline runs.

```python
history = client.get_processing_history()
```

#### `close() -> None`

Gracefully close all connections.

```python
await client.close()
```

---

## Block

Stateful handle to a memory block with retrieval methods.

**Returned by:** `client.create_block()`, `client.get_block()`

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | `str` | Block ID (e.g., "block_abc123") |
| `name` | `str` | Human-readable block name |
| `description` | `str` | Block description |
| `user_id` | `str` | Owner user ID |
| `semantic_collection` | `Optional[str]` | Qdrant collection name |
| `core_memory_block_id` | `Optional[str]` | MongoDB key for core memory |
| `resource_collection` | `Optional[str]` | Qdrant collection for resources |
| `created_at` | `str` | ISO 8601 creation timestamp |
| `updated_at` | `str` | ISO 8601 last-updated timestamp |

### Retrieval Methods

#### `retrieve(query: str) -> RetrievalResult`

Retrieve all available memory types relevant to *query*. Combines core memory and semantic memories.

```python
context = await block.retrieve("What projects am I working on?")

if not context.is_empty():
    print(context.to_prompt_string())
```

#### `core_retrieve() -> RetrievalResult`

Retrieve only the core memory for this block.

```python
context = await block.core_retrieve()
if context.core:
    print(f"Persona: {context.core.persona_content}")
    print(f"Human: {context.core.human_content}")
```

#### `semantic_retrieve(query: str) -> RetrievalResult`

Retrieve only semantic memories relevant to *query* via vector search.

```python
context = await block.semantic_retrieve("machine learning")
for mem in context.semantic:
    print(f"[{mem.type}] {mem.content}")
```

#### `resource_retrieve(query: str) -> RetrievalResult`

Retrieve resource memories. **Stub — always returns empty for now.**

```python
context = await block.resource_retrieve("documentation")
# context.resource is always []
```

---

## Session

Stateful handle to a conversation session with message window and summary management.

**Returned by:** `client.create_session()`, `client.get_session()`

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `id` | `str` | Session ID (e.g., "session_abc123") |
| `user_id` | `str` | Owner user ID |
| `block_id` | `str` | Associated memory block ID |
| `created_at` | `str` | ISO 8601 creation timestamp |

### Methods

#### `get_memory_window() -> List[Dict[str, Any]]`

Return the current message window from MongoDB.

```python
messages = await session.get_memory_window()
for msg in messages:
    print(f"{msg['role']}: {msg['content']}")
```

#### `get_recursive_summary() -> str`

Return the persisted rolling recursive summary for this session.

```python
summary = await session.get_recursive_summary()
if summary:
    print(f"Summary: {summary}")
```

#### `add(user_msg: str, ai_response: str) -> None`

Persist a conversation turn. Triggers memory pipeline when window is full.

```python
await session.add(
    user_msg="I'm working on a FastAPI project.",
    ai_response="That's great! FastAPI is excellent for..."
)
```

**What happens when window is full:**
1. Memory pipeline runs (semantic + core + summary)
2. New summary persisted to MongoDB
3. Messages trimmed to `keep_last_n`

**Fire-and-forget option:**

```python
import asyncio

# Option 1: Await inline (blocks until done)
await session.add(user_msg, ai_response)

# Option 2: Background task (non-blocking)
asyncio.create_task(session.add(user_msg, ai_response))
```

---

## RetrievalResult

Structured container returned by `Block.retrieve()` and friends.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `core` | `Optional[CoreMemoryUnit]` | Core memory (persona + human facts) |
| `semantic` | `List[SemanticMemoryUnit]` | Vector-searched memories |
| `resource` | `List[ResourceMemoryUnit]` | Resource memories (stub) |

### Methods

#### `to_prompt_string() -> str`

Render as a formatted string for LLM prompts.

```python
context = await block.retrieve(query)
prompt_section = context.to_prompt_string()
# Returns:
# <Core Memory>
# [PERSONA]
# ...
# [HUMAN]
# ...
# </Core Memory>
#
# <Semantic Memories>
# [EVENT] ...
#   Keywords: ...
# </Semantic Memories>
```

#### `is_empty() -> bool`

Return True if no memories were retrieved.

```python
if not context.is_empty():
    system_prompt += "\n\n" + context.to_prompt_string()
```

---

## CoreMemoryService (Internal)

> **Note:** This service is used internally by the library. Users typically interact with core memory through `Block.retrieve()` and `Block.core_retrieve()`. Direct access is not exposed via `MemBlocksClient`.

Manage persistent "facts about the user."

Core memory consists of two sections:
- **Persona**: How the AI should behave
- **Human**: Stable facts about the user

### Methods

#### `get(block_id: str) -> Optional[CoreMemoryUnit]`

Retrieve core memory for a block.

```python
core = await core_service.get("block_abc123")
if core:
    print(f"Persona: {core.persona_content}")
    print(f"Human: {core.human_content}")
```

#### `extract(messages: List[Dict], old_core_memory: Optional[CoreMemoryUnit] = None, ...) -> CoreMemoryUnit`

Create an updated CoreMemoryUnit from conversation messages and previous state.

```python
messages = [{"role": "user", "content": "My name is Alice and I live in NYC."}]
new_core = await core_service.extract(messages, old_core_memory)
```

#### `save(block_id: str, memory_unit: CoreMemoryUnit) -> bool`

Manually save core memory.

```python
from memblocks import CoreMemoryUnit

core = CoreMemoryUnit(
    persona_content="The AI is helpful and concise.",
    human_content="User is named Alice, lives in NYC."
)
await core_service.save("block_abc123", core)
```

#### `update(block_id: str, messages: List[Dict], ...) -> CoreMemoryUnit`

Extract and immediately persist updated core memory.

```python
# Usually called automatically by MemoryPipeline
messages = [{"role": "user", "content": "My name is Alice and I live in NYC."}]
updated = await core_service.update("block_abc123", messages)
```

---

## SemanticMemoryService (Internal)

> **Note:** This service is used internally by the library. Users typically interact with semantic memory through `Block.retrieve()` and `Block.semantic_retrieve()`. Direct access is not exposed via `MemBlocksClient`.

Manage vector-searchable memories.

### Methods

#### `extract(messages: List[Dict], ps1_prompt: str = PS1_SEMANTIC_PROMPT) -> List[SemanticMemoryUnit]`

Extract semantic memories from conversation (PS1 pipeline step).

```python
from memblocks.prompts import PS1_SEMANTIC_PROMPT

messages = [
    {"role": "user", "content": "I just finished my ML certification."},
    {"role": "assistant", "content": "Congratulations!"},
]

memories = await semantic_service.extract(messages, PS1_SEMANTIC_PROMPT)
for mem in memories:
    print(f"[{mem.type}] {mem.content}")
```

#### `store(memory_unit: SemanticMemoryUnit) -> List[MemoryOperation]`

Store a memory with PS2 conflict resolution.

```python
operations = await semantic_service.store(memory)
for op in operations:
    print(f"{op.operation}: {op.content[:50]}...")
```

#### `extract_and_store(messages: List[Dict], ps1_prompt: str = PS1_SEMANTIC_PROMPT, min_confidence: float = 0.0) -> List[SemanticMemoryUnit]`

Convenience method: extract AND store semantic memories in one call.

```python
memories = await semantic_service.extract_and_store(
    messages=messages,
    min_confidence=0.7,
)
for mem in memories:
    print(f"[{mem.type}] {mem.content}")
```

#### `retrieve(query_texts: List[str], top_k: int = 5) -> List[List[SemanticMemoryUnit]]`

Retrieve semantically similar memories. **Note: This is a synchronous method.**

```python
# This is NOT async - don't use await
results = semantic_service.retrieve(
    query_texts=["machine learning projects"],
    top_k=5,
)

for query_results in results:
    for memory in query_results:
        print(f"[{memory.type}] {memory.content}")
```

---

## Transparency Layer

Observe internal library operations for debugging and monitoring.

### OperationLog

Thread-safe log of all database writes.

```python
# Get recent MongoDB operations
ops = client.operation_log.get_entries(limit=50, db_type="mongo")
for op in ops:
    print(f"{op.operation_type} on {op.collection_name}: {op.payload_summary}")

# Get summary counts
summary = client.operation_log.summary()
print(summary)  # {'insert': 10, 'update': 5, 'delete': 1}
```

### RetrievalLog

Track memory retrievals.

```python
# Get recent retrievals
retrievals = client.retrieval_log.get_entries(limit=20)
for r in retrievals:
    print(f"Query: {r.query_text}")
    print(f"Results: {r.num_results}")
```

### ProcessingHistory

Track memory pipeline runs.

```python
# Get recent pipeline runs
runs = client.processing_history.get_runs(limit=10)
for run in runs:
    print(f"Task: {run.task_id}")
    print(f"Status: {run.status}")
    print(f"Messages processed: {run.input_message_count}")
```

### EventBus

Subscribe to real-time events.

```python
def on_memory_stored(payload):
    print(f"Memory stored: {payload['content'][:50]}")

def on_pipeline_complete(payload):
    print(f"Pipeline done: {payload['task_id']}")

client.subscribe("on_memory_stored", on_memory_stored)
client.subscribe("on_pipeline_completed", on_pipeline_complete)
```

**Available Events:**

| Event | When Fired |
|-------|------------|
| `on_memory_extracted` | After PS1 extraction |
| `on_conflict_resolved` | After PS2 conflict resolution |
| `on_memory_stored` | After memory written to Qdrant |
| `on_core_memory_updated` | After core memory updated |
| `on_summary_generated` | After summary created |
| `on_pipeline_started` | When pipeline begins |
| `on_pipeline_completed` | When pipeline finishes |
| `on_pipeline_failed` | When pipeline errors |
| `on_memory_retrieved` | When memories retrieved |
| `on_db_write` | On any DB write |
| `on_message_processed` | After a chat message is fully processed |

---

## Data Models

### Block (Stateful Object)

```python
from memblocks import Block

# Returned by client.create_block() / client.get_block()
block.id                      # "block_xxx"
block.name                    # "Work Memory"
block.description             # "..."
block.user_id                 # "alice"
block.semantic_collection     # "block_xxx_semantic"
block.core_memory_block_id    # "block_xxx"
block.resource_collection     # "block_xxx_resource"
```

### Session (Stateful Object)

```python
from memblocks import Session

# Returned by client.create_session() / client.get_session()
session.id         # "session_xxx"
session.user_id    # "alice"
session.block_id   # "block_xxx"
session.created_at # "2024-01-15T10:00:00"
```

### MemoryBlock (Pydantic Model)

Internal model for MongoDB persistence. Used by `BlockManager`.

```python
from memblocks import MemoryBlock, MemoryBlockMetaData

block = MemoryBlock(
    meta_data=MemoryBlockMetaData(
        id="block_xxx",
        created_at="2024-01-15T10:00:00",
        updated_at="2024-01-15T10:00:00",
        usage=[],
        user_id="alice",
    ),
    name="Work Memory",
    description="Professional context",
    semantic_collection="block_xxx_semantic",
    core_memory_block_id="block_xxx",
    resource_collection="block_xxx_resource",
    is_active=False,
)
```

### SemanticMemoryUnit

```python
from memblocks import SemanticMemoryUnit
from memblocks.models import MemoryUnitMetaData

memory = SemanticMemoryUnit(
    content="User completed a machine learning certification.",
    type="event",
    source="conversation",
    confidence=0.95,
    memory_time="2024-01-15T10:30:00",  # Optional, mainly for "event" type
    entities=["machine learning", "certification"],
    keywords=["ML certification", "completed"],
    updated_at="2024-01-15T10:30:00",
    meta_data=MemoryUnitMetaData(usage=["2024-01-15T10:30:00"]),
)
```

### CoreMemoryUnit

```python
from memblocks import CoreMemoryUnit

core = CoreMemoryUnit(
    persona_content="The AI is helpful and concise.",
    human_content="User is named Alice, a software engineer in NYC."
)
```

### RetrievalResult

```python
from memblocks import RetrievalResult

result = RetrievalResult(
    core=CoreMemoryUnit(...),
    semantic=[SemanticMemoryUnit(...), ...],
    resource=[],
)

print(result.to_prompt_string())
print(result.is_empty())
```

### MemoryOperation

```python
from memblocks import MemoryOperation

op = MemoryOperation(
    operation="ADD",  # "ADD" | "UPDATE" | "DELETE" | "NONE"
    content="Memory content here",
    memory_id="uuid-optional",
    old_content="Previous content for UPDATE",
)
```

---

## Complete Example

```python
import asyncio
from memblocks import MemBlocksClient, MemBlocksConfig

async def main():
    config = MemBlocksConfig()
    client = MemBlocksClient(config)
    
    # --- Phase A: Initialization ---
    user = await client.get_or_create_user("alice")
    block = await client.create_block(
        user_id="alice",
        name="Personal Assistant",
        description="General-purpose memory"
    )
    session = await client.create_session(user_id="alice", block_id=block.id)
    
    # --- Phase B: Conversation Loop ---
    messages_to_send = [
        "Hi, I'm Alice. I work as a software engineer.",
        "I'm currently learning machine learning.",
        "My favorite framework is PyTorch.",
    ]
    
    for user_msg in messages_to_send:
        # 1. Retrieve context
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
        
        # 3. Call LLM
        messages = (
            [{"role": "system", "content": system_prompt}]
            + memory_window
            + [{"role": "user", "content": user_msg}]
        )
        ai_response = await client.llm.chat(messages=messages)
        
        print(f"User: {user_msg}")
        print(f"Assistant: {ai_response}\n")
        
        # 4. Persist turn
        await session.add(user_msg=user_msg, ai_response=ai_response)
    
    # --- Inspect Memory ---
    core_context = await block.core_retrieve()
    if core_context.core:
        print("=== Core Memory ===")
        print(f"Persona: {core_context.core.persona_content}")
        print(f"Human: {core_context.core.human_content}")
    
    await client.close()

asyncio.run(main())
```

---

## Next Steps

- [Setup Guide](./01_SETUP_GUIDE.md) — Installation and configuration
- [Deep Technical Overview](./03_TECHNICAL_OVERVIEW.md) — Architecture and data flow
