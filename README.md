# MemBlocks

> Modular Memory Management System for LLMs with intelligent retrieval and context organization

![Architecture](docs/assets/memBlocks_diagram1.png)

## Overview

MemBlocks is a sophisticated memory management system designed to solve the context problem in LLM applications. Instead of sending entire chat histories or using basic RAG, MemBlocks provides modular, intelligent memory management that thinks like humans organize information.

### The Problem

LLMs lose context over time. Current solutions either:
- Send full chat histories (expensive, hits token limits)
- Use basic RAG (treats all memory the same, creates noise)
- Lack organization (can't separate work from personal, or share team knowledge)

### The Solution

MemBlocks introduces **memory blocks as cartridges** - attachable, detachable, shareable memory spaces with intelligent retrieval:

- **Modular Memory Blocks**: Like game cartridges - swap contexts on demand
- **Layered Memory Types**: Core, Semantic, Episodic, and Resources - each optimized
- **Intelligent Retrieval**: LLM-powered query understanding with multi-strategy search
- **Team Collaboration**: Share memory blocks across team members
- **Source Transparency**: Know where every piece of context comes from

## Features

### Memory Architecture

Each memory block contains four distinct types of memory:

- **Core Memory**: Always-present essential facts (persona, user preferences)
- **Semantic Memory**: Timestamped facts and events (knowledge base)
- **Episodic Memory**: Conversation summaries (session history)
- **Resources**: Chunked documents (uploaded PDFs, guides, manuals)

### Intelligent Retrieval System

Not just vector search - a multi-stage intelligent system:

1. **Query Understanding**: LLM extracts intent, entities, and temporal context
2. **Section Routing**: Different searches for facts vs conversations vs documents
3. **Parallel Retrieval**: Search all relevant sections simultaneously
4. **Intelligent Reranking**: Considers recency, source, and entity matches
5. **Budget-Aware Assembly**: Fit context within token limits with diversity

### Three Ways to Use MemBlocks

1. **Python Library**: Build memory-enhanced apps programmatically
2. **REST API**: Access via FastAPI backend (for web apps, mobile, etc.)
3. **MCP Server**: Integrate with AI assistants (Claude Desktop, OpenCode, Cline)

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- UV package manager ([install guide](https://github.com/astral-sh/uv))

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd MemBlocks
   ```

2. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys (Groq, OpenRouter, Cohere, etc.)
   ```

3. **Install dependencies**
   ```bash
   uv sync --all-packages
   ```

4. **Start infrastructure**
   ```bash
   docker-compose up -d
   ```
   
   This starts:
   - Qdrant (vector database) on port 6333
   - Ollama (embeddings) on port 11434

### Usage

#### Option 1: Python Library

```python
from memblocks import MemBlocksClient

# Initialize
client = MemBlocksClient()

# Create memory block
block = await client.create_block(
    name="Work Projects",
    description="Memory for work-related projects"
)

# Add memory
await client.add_semantic_memory(
    block_id=block.id,
    content="Project deadline is March 25, 2024"
)

# Query memory
results = await client.query(
    block_id=block.id,
    query="When is the project deadline?",
    top_k=5
)

print(results[0].content)  # "Project deadline is March 25, 2024"
```

See [Library Documentation](docs/LIBRARY.md) for complete API reference.

#### Option 2: REST API

```bash
# Start backend
cd backend
uvicorn src.api.main:app --reload
```

API documentation available at: `http://localhost:8000/docs`

See [API Documentation](docs/API.md) for endpoint reference.

#### Option 3: MCP Server

For AI assistants like Claude Desktop or OpenCode:

```json
{
  "mcpServers": {
    "memblocks": {
      "command": "uv",
      "args": ["run", "--directory", "mcp_server", "memblocks-mcp"],
      "env": {
        "MEMBLOCKS_USER_ID": "your_user_id"
      }
    }
  }
}
```

See [MCP Server Guide](docs/MCP_SERVER.md) for setup instructions.

## Project Structure

```
MemBlocks/
├── memblocks_lib/      # Core Python library
│   ├── src/memblocks/  # Library source code
│   └── pyproject.toml  # Library dependencies
├── backend/            # FastAPI REST API
│   ├── src/api/        # API routes and models
│   └── pyproject.toml  # API dependencies
├── mcp_server/         # MCP server for AI assistants
│   ├── server.py       # MCP server implementation
│   ├── cli.py          # CLI for block management
│   └── pyproject.toml  # MCP dependencies
├── frontend/           # React web interface (optional)
├── tests/              # Integration tests
├── docs/               # Comprehensive documentation
│   ├── ARCHITECTURE.md # System design and concepts
│   ├── DEPLOYMENT.md   # Docker and deployment guide
│   ├── API.md          # REST API reference
│   ├── MCP_SERVER.md   # MCP server usage
│   └── LIBRARY.md      # Python library API
├── docker-compose.yml  # Infrastructure services
├── .env.example        # Environment configuration template
└── pyproject.toml      # Workspace configuration
```

## Documentation

- **[Architecture Overview](docs/ARCHITECTURE.md)** - Core concepts and system design
- **[Python Library API](docs/LIBRARY.md)** - Programmatic usage reference
- **[REST API](docs/API.md)** - Backend endpoint documentation
- **[MCP Server Guide](docs/MCP_SERVER.md)** - AI assistant integration
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Docker setup and production deployment

## Key Concepts

### Memory Blocks as Cartridges

Think of memory blocks like game cartridges or USB drives:
- **Swap contexts**: Switch between work, personal, learning blocks
- **Share knowledge**: Team blocks visible to all members
- **Keep separate**: Work never mixes with personal memories
- **Reduce noise**: Only search relevant blocks

### Multi-Layered Memory

Different memory types need different strategies:

| Type | Purpose | Strategy |
|------|---------|----------|
| **Core** | Always present | No search needed |
| **Semantic** | Facts & events | Entity + temporal search |
| **Episodic** | Conversation history | Session-based retrieval |
| **Resources** | Documents | Chunk-based semantic search |

### Intelligent vs Basic RAG

**Basic RAG**:
- Dump everything in one vector DB
- Embed query, return top results
- Hope for the best

**MemBlocks**:
- Understands query intent with LLM
- Routes to appropriate memory sections
- Searches with section-specific strategies
- Reranks for quality (recency, source, entities)
- Tags results with source transparency

## Configuration

Key environment variables (see `.env.example` for complete list):

```bash
# LLM Providers (choose one or more)
GROQ_API_KEY=your_groq_key
OPENROUTER_API_KEY=your_openrouter_key

# Vector Database
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Embeddings
OLLAMA_BASE_URL=http://localhost:11434

# Reranking (improves retrieval quality)
COHERE_API_KEY=your_cohere_key

# Authentication (for backend API)
CLERK_PUBLISHABLE_KEY=your_clerk_key
CLERK_SECRET_KEY=your_clerk_secret
```

## Examples

### Example 1: Personal AI Assistant with Memory

```python
# Create separate blocks for different contexts
work_block = await client.create_block(name="Work")
personal_block = await client.create_block(name="Personal")

# Work conversation - stores in work block
await session.add_message(role="user", content="Meeting is at 2pm tomorrow")
# Automatically extracts: "meeting at 2pm tomorrow" → work_block

# Personal conversation - stores in personal block
await session.add_message(role="user", content="Dinner reservation at 7pm")
# Automatically extracts: "dinner at 7pm" → personal_block

# Later queries only search relevant context
work_results = await client.query(work_block.id, "when is the meeting?")
# Doesn't search personal memories - no noise!
```

### Example 2: Team Knowledge Base

```python
# Shared team block
team_block = await client.create_block(
    name="Engineering Team Docs",
    shared_with=["user2", "user3", "user4"]
)

# Anyone on team can add knowledge
await client.add_semantic_memory(
    block_id=team_block.id,
    content="AWS credentials are in 1Password under 'Production Access'"
)

# Everyone sees the same knowledge
results = await client.query(team_block.id, "where are AWS credentials?")
# Returns: "AWS credentials are in 1Password..."
```

### Example 3: Document Q&A System

```python
# Upload documentation
doc_block = await client.create_block(name="API Documentation")

await client.upload_resource(
    block_id=doc_block.id,
    file_path="./api_guide.pdf"
)

# Automatically chunks, embeds, and stores

# Query documentation
results = await client.query(
    block_id=doc_block.id,
    query="How do I authenticate API requests?",
    top_k=3
)

# Returns relevant chunks with source citations
for result in results:
    print(f"{result.content}")
    print(f"Source: {result.metadata['filename']}, Page {result.metadata['page']}")
```

## Why MemBlocks?

### vs Mem0/MemGPT
They have one memory pool. We have **modular blocks** with internal organization.

### vs Zep
They focus on session memory. We separate **facts, conversations, and documents** into distinct sections.

### vs Standard RAG
We don't just search - we **extract intent**, route intelligently, search differently per section, and **rerank**.

### vs MIRIX
Similar active retrieval concept, but we add **modularity (blocks)** and **section-specific optimization**.

## Development

### Running Tests

```bash
# All tests
uv run pytest tests/

# Specific test file
uv run pytest tests/test_hybrid.py

# With coverage
uv run pytest --cov=memblocks_lib tests/
```

### Project Development

See [docs/development/](docs/development/) for:
- Token tracking implementation plan
- Recent library changes and rationale
- Architecture decisions

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

[Your License Here - e.g., MIT]

## Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)
- **Documentation**: See [docs/](docs/) folder

---

**Built for better LLM memory management** - because context matters.
