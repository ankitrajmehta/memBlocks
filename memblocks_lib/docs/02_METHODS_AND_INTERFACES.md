# memBlocks Library — Methods and Interfaces

This document provides a complete API reference for the `memblocks` library with practical usage examples.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [MemBlocksClient](#memblocksclient)
3. [UserManager](#usermanager)
4. [BlockManager](#blockmanager)
5. [SessionManager](#sessionmanager)
6. [ChatEngine](#chatengine)
7. [CoreMemoryService](#corememoryservice)
8. [SemanticMemoryService](#semanticmemoryservice)
9. [Transparency Layer](#transparency-layer)
10. [Data Models](#data-models)

---

## Quick Start

```python
import asyncio
from memblocks import MemBlocksClient, MemBlocksConfig

async def main():
    # Create client (reads from .env automatically)
    client = MemBlocksClient(MemBlocksConfig())
    
    # User + block setup
    user = await client.users.get_or_create_user("alice")
    block = await client.blocks.create_block("alice", "Work Memory")
    
    # Get block-scoped chat engine
    engine = client.get_chat_engine(block)
    session = await engine.sessions.create_session("alice", block.meta_data.id)
    
    # Chat
    result = await engine.chat.send_message(session["session_id"], "Hello!")
    print(result["response"])
    
    await client.close()

asyncio.run(main())
```

---

## MemBlocksClient

The main entry point for the library. Wire all dependencies and access services.

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
| `users` | `UserManager` | User CRUD operations |
| `blocks` | `BlockManager` | Memory block lifecycle |
| `sessions` | `SessionManager` | Chat session management |
| `core` | `CoreMemoryService` | Core memory operations |
| `event_bus` | `EventBus` | Pub/sub for internal events |
| `operation_log` | `OperationLog` | Database write log |
| `retrieval_log` | `RetrievalLog` | Memory retrieval log |
| `processing_history` | `ProcessingHistory` | Pipeline run history |

### Methods

#### `get_chat_engine(block: MemoryBlock) -> _BlockChatEngine`

Create a chat engine scoped to a specific memory block.

```python
block = await client.blocks.create_block("alice", "Work Memory")
engine = client.get_chat_engine(block)

# Access chat and session managers
result = await engine.chat.send_message(session_id, "Hello!")
session = await engine.sessions.create_session("alice", block.meta_data.id)
```

#### `subscribe(event_name: str, callback: Callable) -> None`

Subscribe to internal library events.

```python
def on_pipeline_done(payload):
    print(f"Pipeline completed: {payload['task_id']}")

client.subscribe("on_pipeline_completed", on_pipeline_done)
```

#### `close() -> None`

Gracefully close all connections.

```python
await client.close()
```

---

## UserManager

Manage user accounts. Accessed via `client.users`.

### Methods

#### `create_user(user_id: str, metadata: dict = None) -> Dict[str, Any]`

Create a new user (idempotent).

```python
user = await client.users.create_user("alice", {"role": "admin"})
print(user["user_id"])  # "alice"
```

#### `get_user(user_id: str) -> Optional[Dict[str, Any]]`

Retrieve a user by ID.

```python
user = await client.users.get_user("alice")
if user:
    print(user["block_ids"])  # List of block IDs
```

#### `list_users() -> List[Dict[str, Any]]`

List all users.

```python
users = await client.users.list_users()
for u in users:
    print(u["user_id"])
```

#### `get_or_create_user(user_id: str) -> Dict[str, Any]`

Get existing user or create if not found.

```python
user = await client.users.get_or_create_user("alice")
```

---

## BlockManager

Manage memory blocks. Accessed via `client.blocks`.

### Methods

#### `create_block(user_id, name, description="", ...) -> MemoryBlock`

Create a new memory block with optional Qdrant collections and MongoDB core memory.

```python
block = await client.blocks.create_block(
    user_id="alice",
    name="Work Memory",
    description="Professional context and project details",
    create_semantic=True,   # Create Qdrant collection for semantic memories
    create_core=True,       # Create MongoDB document for core memory
    create_resource=False,  # Create Qdrant collection for resources
)

print(block.meta_data.id)           # "block_xxx..."
print(block.semantic_collection)    # "block_xxx_semantic"
print(block.core_memory_block_id)   # "block_xxx..."
```

#### `get_block(block_id: str) -> Optional[MemoryBlock]`

Load a memory block by ID.

```python
block = await client.blocks.get_block("block_abc123")
if block:
    print(block.name)
```

#### `get_user_blocks(user_id: str) -> List[MemoryBlock]`

List all blocks for a user.

```python
blocks = await client.blocks.get_user_blocks("alice")
for b in blocks:
    print(f"{b.name}: {b.description}")
```

#### `delete_block(block_id: str, user_id: str) -> bool`

Delete a memory block.

```python
success = await client.blocks.delete_block("block_abc123", "alice")
```

---

## SessionManager

Manage chat sessions. Accessed via `client.sessions` (global) or `engine.sessions` (block-scoped).

### Methods

#### `create_session(user_id: str, block_id: str) -> Dict[str, Any]`

Create a new chat session attached to a block.

```python
session = await client.sessions.create_session(
    user_id="alice",
    block_id="block_abc123"
)
print(session["session_id"])  # "session_xxx..."
```

#### `get_session(session_id: str) -> Optional[Dict[str, Any]]`

Retrieve session metadata.

```python
session = await client.sessions.get_session("session_xxx")
print(session["block_id"])
```

#### `attach_block(session_id: str, block_id: str) -> None`

Attach or switch the block for a session.

```python
await client.sessions.attach_block("session_xxx", "block_yyy")
```

#### `detach_block(session_id: str) -> None`

Remove block attachment from a session.

```python
await client.sessions.detach_block("session_xxx")
```

#### `get_attached_block(session_id: str) -> Optional[str]`

Get the block ID attached to a session.

```python
block_id = await client.sessions.get_attached_block("session_xxx")
```

#### `add_message(session_id: str, role: str, content: str) -> None`

Append a message to session history (usually called automatically by ChatEngine).

```python
await client.sessions.add_message("session_xxx", "user", "Hello!")
await client.sessions.add_message("session_xxx", "assistant", "Hi there!")
```

#### `get_messages(session_id: str, limit: int = 100) -> List[Dict]`

Get message history.

```python
messages = await client.sessions.get_messages("session_xxx")
for msg in messages:
    print(f"{msg['role']}: {msg['content']}")
```

#### `get_message_count(session_id: str) -> int`

Count messages in a session.

```python
count = await client.sessions.get_message_count("session_xxx")
```

#### `clear_messages(session_id: str) -> None`

Clear all messages from a session.

```python
await client.sessions.clear_messages("session_xxx")
```

---

## ChatEngine

Handle conversational turns with memory integration. Accessed via `engine.chat` from a block-scoped engine.

### Methods

#### `send_message(session_id: str, user_message: str) -> Dict[str, Any]`

Process a user message and return an AI response.

**What it does:**
1. Retrieves relevant semantic memories
2. Loads core memory
3. Builds context-rich system prompt
4. Calls LLM for response
5. Persists messages
6. Triggers background pipeline when window is full

```python
result = await engine.chat.send_message(
    session_id="session_xxx",
    user_message="I'm working on a Python project using FastAPI."
)

print(result["response"])
# "That sounds interesting! FastAPI is a great choice for..."

print(result["retrieved_context"])
# [{"content": "User is a Python developer", "type": "fact", ...}]
```

**Returns:**

```python
{
    "response": "Assistant's reply text",
    "retrieved_context": [
        {
            "content": "Memory content",
            "type": "fact" | "event" | "opinion",
            "confidence": 0.95,
            "keywords": ["keyword1", "keyword2"],
        },
        # ...
    ]
}
```

#### `get_chat_history(session_id: str, limit: int = 100) -> List[Dict]`

Get conversation history.

```python
history = await engine.chat.get_chat_history("session_xxx", limit=50)
for msg in history:
    print(f"{msg['role']}: {msg['content']}")
```

---

## CoreMemoryService

Manage persistent "facts about the user." Accessed via `client.core`.

Core memory consists of two sections:
- **Persona**: How the AI should behave
- **Human**: Stable facts about the user

### Methods

#### `get(block_id: str) -> Optional[CoreMemoryUnit]`

Retrieve core memory for a block.

```python
core = await client.core.get("block_abc123")
if core:
    print(f"Persona: {core.persona_content}")
    print(f"Human: {core.human_content}")
```

#### `update(block_id: str, messages: List[Dict], ...) -> CoreMemoryUnit`

Extract and save updated core memory from recent messages.

```python
# Usually called automatically by MemoryPipeline
messages = [{"role": "user", "content": "My name is Alice and I live in NYC."}]
updated = await client.core.update("block_abc123", messages)
```

#### `save(block_id: str, memory_unit: CoreMemoryUnit) -> bool`

Manually save core memory.

```python
from memblocks.models import CoreMemoryUnit

core = CoreMemoryUnit(
    persona_content="The AI is helpful and concise.",
    human_content="User is named Alice, lives in NYC, and works as an engineer."
)
await client.core.save("block_abc123", core)
```

#### `extract(messages: List[Dict], old_core_memory: CoreMemoryUnit = None, ...) -> CoreMemoryUnit`

Extract core memory without saving (LLM call only).

```python
new_core = await client.core.extract(
    messages=conversation_messages,
    old_core_memory=existing_core,
)
```

---

## SemanticMemoryService

Manage vector-searchable memories. Accessed internally via block-scoped ChatEngine.

### Methods

#### `extract(messages: List[Dict], ps1_prompt: str = PS1_SEMANTIC_PROMPT) -> List[SemanticMemoryUnit]`

Extract semantic memories from conversation (PS1 pipeline step).

```python
from memblocks.prompts import PS1_SEMANTIC_PROMPT

messages = [
    {"role": "user", "content": "I just finished my machine learning certification."},
    {"role": "assistant", "content": "Congratulations! What topics did it cover?"},
    {"role": "user", "content": "Mostly neural networks and NLP."},
]

memories = await semantic_service.extract(messages, PS1_SEMANTIC_PROMPT)
for mem in memories:
    print(f"[{mem.type}] {mem.content}")
    print(f"  Keywords: {mem.keywords}")
    print(f"  Confidence: {mem.confidence}")
```

#### `store(memory_unit: SemanticMemoryUnit) -> List[MemoryOperation]`

Store a memory with PS2 conflict resolution.

```python
operations = await semantic_service.store(memory)
for op in operations:
    print(f"{op.operation}: {op.content[:50]}...")
```

**Returns a list of operations:**

```python
[
    MemoryOperation(operation="ADD", content="..."),
    MemoryOperation(operation="UPDATE", memory_id="uuid", content="...", old_content="..."),
    MemoryOperation(operation="DELETE", memory_id="uuid", content="..."),
]
```

#### `extract_and_store(messages, ps1_prompt=..., min_confidence=0.0) -> List[SemanticMemoryUnit]`

Convenience: extract and store in one call.

```python
stored = await semantic_service.extract_and_store(
    messages=conversation,
    min_confidence=0.7,  # Only store high-confidence memories
)
```

#### `retrieve(query_texts: List[str], top_k: int = 5) -> List[List[SemanticMemoryUnit]]`

Retrieve semantically similar memories.

```python
results = await semantic_service.retrieve(
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
    print(f"Sources: {r.source}")
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
    print(f"Memories extracted: {run.extracted_semantic_count}")
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
| `on_message_processed` | After chat message processed |

---

## Data Models

### MemoryBlock

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
    content="User completed a machine learning certification covering neural networks and NLP.",
    type="event",
    source="conversation",
    confidence=0.95,
    memory_time="2024-01-15T10:30:00",
    entities=["machine learning", "certification", "neural networks", "NLP"],
    keywords=["ML certification", "neural networks", "NLP", "completed"],
    updated_at="2024-01-15T10:30:00",
    meta_data=MemoryUnitMetaData(usage=["2024-01-15T10:30:00"]),
)
```

### CoreMemoryUnit

```python
from memblocks import CoreMemoryUnit

core = CoreMemoryUnit(
    persona_content="The AI is helpful, concise, and focuses on technical accuracy.",
    human_content="User is named Alice, a software engineer in NYC who is learning machine learning.",
)
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
    
    # --- Setup ---
    user = await client.users.get_or_create_user("alice")
    block = await client.blocks.create_block(
        user_id="alice",
        name="Personal Assistant",
        description="General-purpose memory for daily tasks"
    )
    
    # --- Chat Session ---
    engine = client.get_chat_engine(block)
    session = await engine.sessions.create_session("alice", block.meta_data.id)
    
    # --- Conversation ---
    messages = [
        "Hi, I'm Alice. I work as a software engineer.",
        "I'm currently learning machine learning.",
        "My favorite framework is PyTorch.",
    ]
    
    for msg in messages:
        result = await engine.chat.send_message(session["session_id"], msg)
        print(f"Assistant: {result['response']}\n")
    
    # --- Inspect Memory ---
    core = await client.core.get(block.meta_data.id)
    print("=== Core Memory ===")
    print(f"Persona: {core.persona_content}")
    print(f"Human: {core.human_content}")
    
    # --- Transparency ---
    print("\n=== Operations ===")
    for op in client.operation_log.get_entries(limit=5):
        print(f"{op.operation_type}: {op.payload_summary}")
    
    await client.close()

asyncio.run(main())
```

---

## Next Steps

- [Setup Guide](./01_SETUP_GUIDE.md) — Installation and configuration
- [Deep Technical Overview](./03_TECHNICAL_OVERVIEW.md) — Architecture and data flow
