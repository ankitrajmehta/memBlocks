# MemBlocks - Refactored System Setup

## Overview

The memBlocks system has been refactored with:
- **LangChain** for structured LLM outputs
- **MongoDB** for user/block/core-memory persistence  
- **Modular services** for clean separation of concerns
- **Interactive CLI** for testing all features

## Architecture

```
memBlocks/
├── llm/                      # LangChain integration
│   ├── llm_manager.py        # ChatGroq singleton
│   └── output_models.py      # Pydantic schemas (SemanticExtractionOutput, CoreMemoryOutput, SummaryOutput)
│
├── vector_db/
│   ├── mongo_manager.py      # MongoDB async client (NEW)
│   ├── vector_db_manager.py  # Qdrant manager (existing)
│   └── embeddings.py         # Ollama embeddings (existing)
│
├── models/
│   ├── container.py          # MemoryBlock with save/load methods
│   ├── sections.py           # SemanticMemorySection, CoreMemorySection (refactored)
│   ├── units.py              # Memory unit models
│   └── extractions.py        # Extraction schemas
│
├── services/                 # Business logic layer (NEW)
│   ├── user_service.py       # User CRUD operations
│   ├── block_service.py      # Block creation, management, session handling
│   └── chat_service.py       # Chat with memory augmentation
│
├── main.py                   # Interactive CLI (NEW)
├── prompts.py                # LLM prompts
└── pyproject.toml            # Updated dependencies
```

## Key Changes

### 1. MongoDB Integration
- **Collections**:
  - `users`: User documents with `block_ids: []`
  - `blocks`: MemoryBlock metadata (stores Qdrant collection names for semantic/resource, block_id for core)
  - `core_memories`: Core memory paragraphs (persona_content, human_content)

### 2. LangChain Integration
- Replaced direct Groq API calls with `ChatGroq` + `PydanticOutputParser`
- Structured outputs for semantic extraction, core memory, and summaries
- Centralized LLM configuration in `llm_manager.py`

### 3. Core Memory
- **Stored in MongoDB** (not Qdrant - no vector search needed)
- **Replacement-based**: Each extraction generates NEW paragraphs that replace old ones
- **Two fields**: `persona_content` (AI behavior) and `human_content` (user facts)
- **Auto-extracted** during memory window flush

### 4. Memory Processing Pipeline
When message history reaches threshold (default 10 messages):
1. **Extract semantic memories** → store in Qdrant
2. **Extract/update core memory** → replace in MongoDB
3. **Generate recursive summary** → keep in memory
4. **Flush message history** → keep last N messages

### 5. Context Assembly
LLM receives:
```
<CORE_MEMORY>
[PERSONA] AI behavior preferences
[HUMAN] User facts
</CORE_MEMORY>

<CONVERSATION_SUMMARY>
Recursive summary of past conversation
</CONVERSATION_SUMMARY>

<SEMANTIC_MEMORY>
[EVENT] Specific occurrence...
[FACTUAL] General knowledge...
</SEMANTIC_MEMORY>
```

## Setup Instructions

### 1. Install Dependencies

```bash
# Install new packages
uv pip install langchain langchain-groq langchain-core motor

# Or sync from pyproject.toml
uv sync
```

### 2. Environment Variables

Add MongoDB connection string to `.env`:

```bash
GROQ_API_KEY=your_groq_key_here
MONGODB_CONNECTION_STRING=mongodb://localhost:27017
```

### 3. Start Infrastructure

```bash
docker-compose up -d --build
```

### 4. Run the CLI

```bash
uv run main.py
```

## CLI Usage

### Menu Options

1. **Select/Create User** - Switch between users or create new ones
2. **Create Memory Block** - Create a new memory block with semantic + core memory
3. **List My Blocks** - View all blocks for current user
4. **Start Chat Session** - Attach a block and begin chatting
5. **Chat** - Interactive chat with memory augmentation
6. **View Status** - See current user, session, and memory stats
7. **Exit** - Close the application

### Typical Workflow

```
1. CLI auto-creates "test_user" on startup
2. Create a memory block (e.g., "Personal Block")
3. Start chat session and select your block
4. Chat normally - memories are extracted automatically
5. Type 'status' in chat to see memory stats
6. After 10 messages, memory window flushes:
   - Semantic memories extracted and stored
   - Core memory updated
   - Summary generated
   - History trimmed
```

## Testing the System

### Test Scenario 1: Core Memory Extraction

```
User: Hi! My name is Alex and I prefer short, concise answers.
Assistant: [responds]

User: I live in San Francisco and work as a software engineer.
Assistant: [responds]

# After 10 messages, check core memory:
# HUMAN: "User's name is Alex, lives in San Francisco, and works as a software engineer."
# PERSONA: "Assistant should provide short, concise answers."
```

### Test Scenario 2: Semantic Memory Retrieval

```
User: I attended an AI conference at Stanford yesterday.
Assistant: [responds]

# ... 8 more messages to trigger memory flush ...

# Later in new session:
User: What conferences have I mentioned?
Assistant: [retrieves from semantic memory] You attended an AI conference at Stanford.
```

### Test Scenario 3: Block Management

```
# Create multiple blocks
1. Personal Life
2. Work Projects
3. Learning ML

# Switch between blocks by starting new chat sessions
# Each block maintains separate memories
```

## API/Service Usage (for Future Integration)

### User Service
```python
from services.user_service import user_service

# Create user
user = await user_service.create_user("user_123")

# Get user
user = await user_service.get_user("user_123")
```

### Block Service
```python
from services.block_service import block_service

# Create block
block = await block_service.create_block(
    user_id="user_123",
    name="My Block",
    description="Personal memories"
)

# Load block
block = await block_service.load_block("block_abc123")

# List user's blocks
blocks = await block_service.list_user_blocks("user_123")
```

### Chat Service
```python
from services.chat_service import ChatService

# Initialize
chat = ChatService(
    memory_block=block,
    memory_window=10,
    keep_last_n=4
)

# Send message
response = await chat.send_message("Hello!")

# Get status
chat.print_status()
```

## Modular Design Benefits

### For FastAPI Integration
```python
from fastapi import FastAPI
from services.chat_service import ChatService
from services.block_service import block_service

app = FastAPI()

@app.post("/chat")
async def chat(user_id: str, block_id: str, message: str):
    block = await block_service.load_block(block_id)
    chat_service = ChatService(block)
    response = await chat_service.send_message(message)
    return {"response": response}
```

### For MCP Server Integration
```python
from mcp import Server
from services.user_service import user_service
from services.block_service import block_service

server = Server("memblocks")

@server.tool()
async def create_memory_block(user_id: str, name: str):
    block = await block_service.create_block(user_id, name, "")
    return {"block_id": block.meta_data.id}
```

## Troubleshooting

### MongoDB Connection Error
```
ValueError: MONGODB_CONNECTION_STRING not found
```
**Solution**: Add `MONGODB_CONNECTION_STRING=mongodb://localhost:27017` to `.env`

### Groq API Error
```
ValueError: GROQ_API_KEY not found
```
**Solution**: Add `GROQ_API_KEY=...` to `.env`

### Qdrant Connection Error
```
ConnectionError: Could not connect to Qdrant
```
**Solution**: Start Qdrant: `docker run -p 6333:6333 qdrant/qdrant`

### Ollama Embedding Error
```
Failed to generate embeddings
```
**Solution**: 
1. Start Ollama: `docker run -p 11434:11434 ollama/ollama`
2. Pull model: `docker exec -it <container> ollama pull nomic-embed-text`

## Next Steps

1. **Test core memory extraction** - Chat for 10+ messages and verify persona/human facts
2. **Test semantic retrieval** - Mention facts, flush memory, then ask about them
3. **Create multiple blocks** - Test block switching and isolation
4. **Implement FastAPI endpoints** - Expose services via REST API
5. **Add MCP server** - Integrate with MCP protocol
6. **Implement resource memory** - Add document ingestion (currently stubbed)

## Migration from Old System

Old code preserved in:
- `main_old.py` - Original main file
- `chat_pipeline_v1.py` - Old chat pipeline (can be removed after testing)

New system is backwards-compatible with existing Qdrant collections for semantic memories.
