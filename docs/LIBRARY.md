# MemBlocks Python Library

The MemBlocks Python library provides a programmatic interface for building memory-enhanced LLM applications with modular, intelligent memory management.

## Installation

### As Part of Workspace

```bash
# From repository root
uv sync --all-packages
```

### As Standalone Package

```bash
uv pip install -e memblocks_lib
```

---

## Quick Start

### Basic Usage

```python
import asyncio
from memblocks import MemBlocksClient
from memblocks.config import MemBlocksConfig

async def main():
    # Initialize client
    config = MemBlocksConfig()
    client = MemBlocksClient(config=config)
    
    # Create a memory block
    block = await client.create_block(
        name="My Project",
        description="Memory for my ML project"
    )
    
    print(f"Created block: {block.id}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Core Concepts

### MemBlocksClient

The main entry point for all library operations.

```python
from memblocks import MemBlocksClient
from memblocks.config import MemBlocksConfig

# Create with default config (reads from .env)
client = MemBlocksClient()

# Or with custom config
config = MemBlocksConfig(
    qdrant_host="localhost",
    qdrant_port=6333,
    ollama_base_url="http://localhost:11434"
)
client = MemBlocksClient(config=config)
```

### Memory Blocks

Memory blocks are isolated memory spaces with four sections:

1. **Core Memory**: Always-present context (persona, user profile)
2. **Semantic Memory**: Facts and events with timestamps
3. **Episodic Memory**: Conversation summaries
4. **Resources**: Chunked documents

---

## API Reference

### Block Management

#### Create Block

```python
from memblocks.models.block import MemoryBlock

block = await client.create_block(
    name="Work Projects",
    description="Memory for work-related information",
    tags=["work", "projects"]
)

# Returns: MemoryBlock object
print(block.id)  # "block_abc123"
print(block.name)  # "Work Projects"
```

#### List Blocks

```python
blocks = await client.list_blocks(
    skip=0,
    limit=10,
    tags=["work"]  # Optional filter
)

for block in blocks:
    print(f"{block.name}: {block.id}")
```

#### Get Block

```python
block = await client.get_block(block_id="block_abc123")

print(block.core_memory)  # CoreMemory object
print(block.metadata)  # Block metadata
```

#### Update Block

```python
updated_block = await client.update_block(
    block_id="block_abc123",
    name="Updated Name",
    description="New description",
    tags=["work", "ai"]
)
```

#### Delete Block

```python
await client.delete_block(block_id="block_abc123")
```

---

### Memory Storage

#### Add Semantic Memory

```python
from datetime import datetime

memory = await client.add_semantic_memory(
    block_id="block_abc123",
    content="Project deadline is March 25, 2024",
    metadata={
        "source": "user_provided",
        "category": "event_factual",
        "entities": ["project", "deadline"],
        "timestamp": datetime.now().isoformat()
    }
)

print(memory.id)  # Memory ID
print(memory.vector_id)  # Vector database ID
```

#### Add Episodic Memory

```python
from memblocks.models.memory import EpisodicMemory

episodic = await client.add_episodic_memory(
    block_id="block_abc123",
    summary="Discussed project timeline and deliverables",
    messages=[
        {"role": "user", "content": "When is the deadline?"},
        {"role": "assistant", "content": "March 25, 2024"}
    ],
    metadata={
        "session_id": "session_123",
        "key_points": ["timeline", "deliverables"]
    }
)
```

#### Update Core Memory

```python
core = await client.update_core_memory(
    block_id="block_abc123",
    persona="Professional AI assistant specialized in project management",
    human="Software engineer, prefers Python, works on ML projects"
)

print(core.persona)
print(core.human)
```

#### Upload Resource (Document)

```python
resource = await client.upload_resource(
    block_id="block_abc123",
    file_path="./docs/api_guide.pdf",
    metadata={
        "type": "documentation",
        "category": "technical"
    }
)

print(f"Created {resource.chunks_count} chunks from document")
```

---

### Memory Retrieval

#### Query Memories

```python
from memblocks.models.retrieval import RetrievalRequest

# Simple query
results = await client.query(
    block_id="block_abc123",
    query="What is the project deadline?",
    top_k=5
)

for result in results:
    print(f"[{result.section}] {result.content}")
    print(f"Score: {result.score}, Source: {result.metadata['source']}")
```

#### Advanced Query

```python
from memblocks.models.retrieval import RetrievalRequest, SectionType

# Query specific sections only
request = RetrievalRequest(
    query="project deadline",
    block_ids=["block_abc123"],
    sections=[SectionType.SEMANTIC, SectionType.EPISODIC],
    top_k=10,
    rerank=True,
    include_metadata=True
)

results = await client.retrieve(request)

# Results are already reranked and filtered
for result in results.results:
    print(f"{result.content} (relevance: {result.rerank_score})")
```

#### Get Semantic Memories

```python
memories = await client.get_semantic_memories(
    block_id="block_abc123",
    limit=20,
    tags=["important"]  # Optional filter
)
```

#### Get Episodic Memories

```python
episodes = await client.get_episodic_memories(
    block_id="block_abc123",
    limit=10,
    recent_days=7  # Only last 7 days
)
```

#### Get Core Memory

```python
core = await client.get_core_memory(block_id="block_abc123")

print("Persona:", core.persona)
print("Human:", core.human)
```

---

### Conversational Memory (Session-Based)

#### Create Session

```python
from memblocks.services.session import Session

session = await client.create_session(
    block_id="block_abc123",
    memory_window_limit=2  # Process every 2 messages
)
```

#### Add Messages to Session

```python
# User message
await session.add_message(
    role="user",
    content="What is the project deadline?"
)

# AI response
await session.add_message(
    role="assistant",
    content="Based on our discussion, the deadline is March 25, 2024."
)

# Memory pipeline automatically runs after memory_window_limit reached
```

#### Manual Flush

```python
# Force memory processing even if window not full
summary = await session.flush()

print(f"Processed: {summary}")
```

#### Session with Retrieval

```python
# Start session
session = await client.create_session(block_id="block_abc123")

# User asks question
user_query = "What's the deadline?"

# Retrieve relevant context
context = await client.query(
    block_id="block_abc123",
    query=user_query,
    top_k=5
)

# Build prompt with context
prompt = f"""
Context from memory:
{context}

User question: {user_query}
"""

# Get LLM response
response = await client.chat(prompt)

# Add to session
await session.add_message(role="user", content=user_query)
await session.add_message(role="assistant", content=response)
```

---

### Configuration

#### MemBlocksConfig

```python
from memblocks.config import MemBlocksConfig

config = MemBlocksConfig(
    # Vector Database
    qdrant_host="localhost",
    qdrant_port=6333,
    qdrant_api_key=None,  # For cloud Qdrant
    
    # Embeddings
    ollama_base_url="http://localhost:11434",
    embedding_model="nomic-embed-text",
    
    # LLM Providers
    groq_api_key="your_key",
    openrouter_api_key="your_key",
    
    # Reranking
    cohere_api_key="your_key",
    
    # Memory Processing
    memory_window_limit=2,  # Messages before pipeline runs
    
    # Retrieval
    default_top_k=5,
    enable_reranking=True
)
```

#### Environment Variables

The library reads from environment variables by default:

```bash
# .env file
QDRANT_HOST=localhost
QDRANT_PORT=6333
OLLAMA_BASE_URL=http://localhost:11434
GROQ_API_KEY=your_key
COHERE_API_KEY=your_key
MEMORY_WINDOW=2
```

---

### LLM Configuration

#### Task-Specific LLM Settings

```python
from memblocks.llm.task_settings import LLMTaskSettings, TaskType

# Configure different models for different tasks
settings = LLMTaskSettings()

settings.configure_task(
    task=TaskType.SEMANTIC_EXTRACTION,
    provider="groq",
    model="llama-3.1-70b-versatile",
    temperature=0.0
)

settings.configure_task(
    task=TaskType.CONVERSATION,
    provider="openrouter",
    model="anthropic/claude-3.5-sonnet",
    temperature=0.7
)

# Use in client
client = MemBlocksClient(config=config, llm_settings=settings)
```

#### Available Task Types

- `SEMANTIC_EXTRACTION`: Extract facts from conversations
- `CONFLICT_RESOLUTION`: Resolve conflicting memories
- `CORE_MEMORY`: Update core memory
- `EPISODIC_SUMMARY`: Generate conversation summaries
- `QUERY_EXPANSION`: Expand user queries for retrieval
- `CONVERSATION`: General chat

---

### Transparency & Monitoring

#### Get Operation Logs

```python
logs = await client.get_operation_logs(
    block_id="block_abc123",
    limit=50
)

for log in logs:
    print(f"[{log.timestamp}] {log.operation}: {log.duration_ms}ms")
```

#### Get Retrieval Logs

```python
retrievals = await client.get_retrieval_logs(
    block_id="block_abc123",
    limit=20
)

for retrieval in retrievals:
    print(f"Query: {retrieval.query}")
    print(f"Results: {retrieval.results_count}")
    print(f"Latency: {retrieval.latency_ms}ms")
```

#### Get LLM Usage Statistics

```python
usage = await client.get_llm_usage(block_id="block_abc123")

print(f"Total requests: {usage.total_requests}")
print(f"Total tokens: {usage.total_tokens}")
print(f"Estimated cost: ${usage.estimated_cost_usd}")

# By operation type
for task, stats in usage.by_task.items():
    print(f"{task}: {stats.requests} requests, {stats.total_tokens} tokens")
```

---

## Advanced Usage

### Custom Vector Store

```python
from memblocks.storage.vector_store import QdrantVectorStore

# Custom Qdrant configuration
vector_store = QdrantVectorStore(
    host="custom-host",
    port=6333,
    api_key="custom_key",
    collection_name="my_memories"
)

client = MemBlocksClient(vector_store=vector_store)
```

### Custom Embeddings

```python
from memblocks.embeddings import OllamaEmbeddings

# Custom embedding model
embeddings = OllamaEmbeddings(
    base_url="http://localhost:11434",
    model="mxbai-embed-large"
)

client = MemBlocksClient(embeddings=embeddings)
```

### Batch Operations

```python
# Batch add semantic memories
memories = [
    {"content": "Fact 1", "metadata": {"source": "user"}},
    {"content": "Fact 2", "metadata": {"source": "user"}},
    {"content": "Fact 3", "metadata": {"source": "user"}}
]

results = await client.batch_add_semantic_memories(
    block_id="block_abc123",
    memories=memories
)

print(f"Added {len(results)} memories")
```

### Memory Pipeline Customization

```python
from memblocks.services.memory_pipeline import MemoryPipeline

# Custom pipeline configuration
pipeline = MemoryPipeline(
    client=client,
    enable_semantic_extraction=True,
    enable_core_memory_updates=True,
    enable_episodic_summary=True,
    min_messages_for_summary=4
)

# Run pipeline manually
result = await pipeline.process_messages(
    block_id="block_abc123",
    messages=conversation_history
)

print(f"Extracted {len(result.semantic_facts)} facts")
print(f"Summary: {result.episodic_summary}")
```

---

## Examples

### Example 1: Building a Chatbot with Memory

```python
import asyncio
from memblocks import MemBlocksClient

async def chatbot():
    client = MemBlocksClient()
    
    # Create or use existing block
    block = await client.create_block(name="Chatbot Memory")
    
    # Create session
    session = await client.create_session(
        block_id=block.id,
        memory_window_limit=2
    )
    
    while True:
        # Get user input
        user_input = input("You: ")
        if user_input.lower() == "quit":
            await session.flush()  # Save final memories
            break
        
        # Retrieve relevant context
        context = await client.query(
            block_id=block.id,
            query=user_input,
            top_k=3
        )
        
        # Build prompt with context
        context_str = "\n".join([r.content for r in context])
        prompt = f"Context:\n{context_str}\n\nUser: {user_input}\n\nAssistant:"
        
        # Get response (use your LLM here)
        response = await client.chat(prompt)
        
        # Add to session (automatic memory extraction)
        await session.add_message(role="user", content=user_input)
        await session.add_message(role="assistant", content=response)
        
        print(f"Bot: {response}")

asyncio.run(chatbot())
```

### Example 2: Document Q&A System

```python
async def document_qa():
    client = MemBlocksClient()
    
    # Create block for documents
    block = await client.create_block(name="Documentation")
    
    # Upload documents
    await client.upload_resource(
        block_id=block.id,
        file_path="./user_manual.pdf"
    )
    
    await client.upload_resource(
        block_id=block.id,
        file_path="./api_docs.pdf"
    )
    
    # Query documents
    query = "How do I authenticate with the API?"
    
    results = await client.query(
        block_id=block.id,
        query=query,
        top_k=5
    )
    
    # Display results
    print("Relevant sections:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result.content}")
        print(f"   Source: {result.metadata['filename']}")
        print(f"   Relevance: {result.score:.2f}")

asyncio.run(document_qa())
```

### Example 3: Multi-User Memory Management

```python
async def multi_user_app():
    client = MemBlocksClient()
    
    users = {
        "user1": await client.create_block(name="User 1 Memory"),
        "user2": await client.create_block(name="User 2 Memory")
    }
    
    # User 1 adds memory
    await client.add_semantic_memory(
        block_id=users["user1"].id,
        content="I prefer dark mode"
    )
    
    # User 2 adds memory
    await client.add_semantic_memory(
        block_id=users["user2"].id,
        content="I prefer light mode"
    )
    
    # Retrieve user-specific preferences
    for user_id, block in users.items():
        prefs = await client.query(
            block_id=block.id,
            query="user preferences",
            top_k=5
        )
        print(f"{user_id} preferences: {prefs[0].content if prefs else 'None'}")

asyncio.run(multi_user_app())
```

---

## Testing

### Run Tests

```bash
# From repository root
uv run pytest tests/

# Specific test file
uv run pytest tests/test_hybrid.py

# With coverage
uv run pytest --cov=memblocks_lib tests/
```

---

## Additional Resources

- [Architecture Overview](./ARCHITECTURE.md)
- [REST API Documentation](./API.md)
- [MCP Server Guide](./MCP_SERVER.md)
- [Deployment Guide](./DEPLOYMENT.md)

---

**For library issues or feature requests, please open a GitHub issue.**
