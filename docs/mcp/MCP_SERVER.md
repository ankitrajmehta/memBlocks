# MemBlocks MCP Server

MemBlocks provides a Model Context Protocol (MCP) server that enables AI assistants like Claude Desktop, OpenCode, and other MCP-compatible clients to interact with your memory system.

## What is MCP?

The Model Context Protocol (MCP) is a standardized way for AI assistants to access external tools and data sources. With MemBlocks MCP server, your AI assistant can:

- Create and manage memory blocks
- Store and retrieve memories
- Query your knowledge base
- Maintain context across conversations

---

## Quick Start

### Prerequisites

- Python 3.11+
- UV package manager installed
- Docker running (for Qdrant and Ollama)
- MCP-compatible client (Claude Desktop, OpenCode, Cline, etc.)

### Installation

1. **Install project dependencies**:
   ```bash
   uv sync --all-packages
   ```

2. **Install MCP server package** (optional but recommended):
   ```bash
   uv pip install -e mcp_server
   ```

3. **Verify installation**:
   ```bash
   memblocks-mcp --help
   memblocks-cli --help
   ```

   If commands aren't found, use UV to run them:
   ```bash
   uv run memblocks-mcp --help
   uv run memblocks-cli --help
   ```

---

## Configuration

### For OpenCode CLI

Add to your `opencode.json` (or create it in your project root):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "memblocks": {
      "type": "local",
      "command": ["uv", "run", "python", "-m", "mcp_server.server"],
      "environment": {
        "MEMBLOCKS_USER_ID": "your_user_id"
      },
      "enabled": true
    }
  }
}
```

**Important**: Replace `"your_user_id"` with your actual user ID (from MemBlocks backend registration).

### For Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "memblocks": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/MemBlocks/mcp_server", "memblocks-mcp"],
      "env": {
        "MEMBLOCKS_USER_ID": "your_user_id"
      }
    }
  }
}
```

### For Cline (VS Code Extension)

Add to Cline's MCP settings:

```json
{
  "mcpServers": {
    "memblocks": {
      "command": "uv",
      "args": ["run", "python", "-m", "mcp_server.server"],
      "cwd": "/path/to/MemBlocks",
      "env": {
        "MEMBLOCKS_USER_ID": "your_user_id"
      }
    }
  }
}
```

---

## CLI Commands

MemBlocks provides a CLI for managing the active memory block outside of AI assistant interactions.

### View User Info

```bash
memblocks-cli whoami
```

Shows your current user ID.

### List Memory Blocks

```bash
memblocks-cli list-blocks
```

Lists all memory blocks accessible to your user.

### Set Active Block

```bash
memblocks-cli set-block <block_id>
```

Sets which memory block the MCP server should use for subsequent operations.

### Get Active Block

```bash
memblocks-cli get-block
```

Shows the currently active memory block ID.

### Lock/Unlock MCP

```bash
memblocks-cli lock
memblocks-cli unlock
```

Prevents the MCP server from switching blocks (useful during focused work sessions).

---

## Available MCP Tools

When connected to an AI assistant, the following tools become available:

### Memory Block Management

#### `create_memory_block`
Creates a new memory block.

**Parameters**:
- `name` (string): Block name
- `description` (string, optional): Block description
- `tags` (array, optional): Tags for organization

**Example**:
```
AI: I'll create a memory block for your ML project.
[calls create_memory_block with name="ML Project" description="Memory for machine learning project"]
```

#### `list_memory_blocks`
Lists all accessible memory blocks.

**Parameters**: None

**Returns**: List of blocks with IDs, names, and metadata

#### `get_memory_block`
Gets details of a specific memory block.

**Parameters**:
- `block_id` (string): The block ID

#### `set_active_block`
Sets which block to use for subsequent operations.

**Parameters**:
- `block_id` (string): The block ID to activate

#### `delete_memory_block`
Deletes a memory block and all its contents.

**Parameters**:
- `block_id` (string): Block ID to delete

---

### Memory Operations

#### `store_semantic_memory`
Stores a fact or piece of information in semantic memory.

**Parameters**:
- `content` (string): The information to store
- `metadata` (object, optional): Additional context (source, entities, etc.)

**Example**:
```
User: Remember that the API key expires on March 25.
AI: [calls store_semantic_memory with content="API key expires on March 25, 2024"]
```

#### `store_episodic_memory`
Stores a conversation summary in episodic memory.

**Parameters**:
- `summary` (string): Summary of the conversation
- `key_points` (array): Important points discussed

#### `update_core_memory`
Updates the always-present core memory (persona and human profile).

**Parameters**:
- `persona` (string, optional): AI persona/behavior description
- `human` (string, optional): User profile/preferences

**Example**:
```
User: I prefer Python over JavaScript.
AI: [calls update_core_memory with human="Prefers Python for development"]
```

#### `upload_resource`
Uploads a document to the resources section (chunked and embedded).

**Parameters**:
- `file_path` (string): Path to the document
- `metadata` (object, optional): Document metadata

---

### Retrieval Operations

#### `query_memory`
Searches across all memory types for relevant information.

**Parameters**:
- `query` (string): The search query
- `top_k` (integer, optional): Number of results (default: 5)
- `include_sections` (array, optional): Which sections to search

**Returns**: Relevant memories with source tags

**Example**:
```
User: What did we discuss about the API?
AI: [calls query_memory with query="API discussion"]
AI: Based on our previous conversation, we discussed that the API key expires on March 25.
```

#### `get_core_memory`
Retrieves the current core memory (always included in context).

**Parameters**: None

**Returns**: Persona and human profile

#### `list_semantic_memories`
Lists semantic memories with optional filters.

**Parameters**:
- `limit` (integer): Max results
- `tags` (array, optional): Filter by tags

#### `list_episodic_memories`
Lists conversation summaries.

**Parameters**:
- `limit` (integer): Max results
- `recent_days` (integer, optional): Only from last N days

---

### Background Tools (Non-Blocking)

Some tools run in the background to avoid slowing down conversation:

#### `store_semantic_memory_bg`
Same as `store_semantic_memory` but doesn't block the response.

#### `store_episodic_memory_bg`
Same as `store_episodic_memory` but doesn't block the response.

**Use case**: AI can continue responding while memory is being stored in the background.

---

## Shared State Management

### Active Block State

The CLI and MCP server share state through a file:

```
~/.config/memblocks/active_block.json
```

**Contents**:
```json
{
  "user_id": "user_123",
  "block_id": "block_abc",
  "mcp_locked": false,
  "last_updated": "2024-03-15T10:30:00Z"
}
```

**Fields**:
- `user_id`: Current user ID
- `block_id`: Active memory block ID
- `mcp_locked`: Whether block switching is locked
- `last_updated`: Timestamp of last update

### Why This Matters

- Set a block via CLI: `memblocks-cli set-block block_abc`
- AI assistant automatically uses that block for all operations
- Lock prevents accidental block switching during focused sessions
- Persists across AI assistant restarts

---

## Usage Examples

### Example 1: Project-Specific Memory

```bash
# Create a memory block for a project
memblocks-cli list-blocks  # Find or create a block

# Set it as active
memblocks-cli set-block block_project_x

# Lock it to prevent switching
memblocks-cli lock

# Now use AI assistant normally
# All memories stored/retrieved from "Project X" block
```

### Example 2: Multi-Context Switching

```bash
# Morning: Work mode
memblocks-cli set-block block_work

# Ask AI about work projects
# Memories stored in work block

# Evening: Personal mode
memblocks-cli set-block block_personal

# Ask AI about personal topics
# Completely separate memory space
```

### Example 3: Team Collaboration

```bash
# Set team block (shared with colleagues)
memblocks-cli set-block block_team_docs

# AI assistant can now:
# - Access team-shared knowledge
# - Add information visible to whole team
# - Keep personal blocks separate
```

---

## Testing Your Setup

### 1. Verify MCP Server Starts

```bash
uv run python -m mcp_server.server
```

Should start without errors. Press Ctrl+C to stop.

### 2. Test CLI Commands

```bash
# Check user ID
memblocks-cli whoami

# List blocks
memblocks-cli list-blocks

# Set a block (use actual block ID from list)
memblocks-cli set-block <block_id>

# Verify it's set
memblocks-cli get-block
```

### 3. Test MCP Integration

In your AI assistant:

```
User: List my memory blocks
AI: [Should show your blocks via MCP tool call]

User: Remember that my favorite color is blue
AI: [Should store in semantic memory]

User: What's my favorite color?
AI: [Should retrieve from memory: "Your favorite color is blue"]
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'mcp_server'"

**Solution**:
```bash
uv pip install -e mcp_server
```

### "Command not found: memblocks-cli"

**Solution**: Use UV to run directly:
```bash
uv run memblocks-cli --help
```

Or ensure your UV virtual environment scripts are on `PATH`.

### MCP Server Not Connecting

**Check**:
1. Is Docker running? (Qdrant and Ollama needed)
2. Is `MEMBLOCKS_USER_ID` set correctly in config?
3. Check MCP server logs for errors
4. Verify `.env` file has correct API keys

### Active Block Not Persisting

**Check**:
1. Does `~/.config/memblocks/` directory exist?
2. Do you have write permissions?
3. Run `memblocks-cli get-block` to verify state file

### Memory Not Being Retrieved

**Check**:
1. Is a block set as active? (`memblocks-cli get-block`)
2. Does the block have memories? (Check via backend API)
3. Are Qdrant and Ollama services running? (`docker-compose ps`)

---

## Advanced Configuration

### Custom State File Location

Set environment variable:

```bash
export MEMBLOCKS_STATE_PATH=/custom/path/active_block.json
```

### Multiple User Profiles

Create separate state files for different users:

```bash
# User 1
MEMBLOCKS_STATE_PATH=~/.config/memblocks/user1.json memblocks-cli whoami

# User 2
MEMBLOCKS_STATE_PATH=~/.config/memblocks/user2.json memblocks-cli whoami
```

### Custom MCP Server Port

Edit `mcp_server/server.py` to change the default port (if needed for your MCP client).

---

## MCP Server Architecture

```
┌─────────────────┐
│  AI Assistant   │
│ (Claude/OpenCode)│
└────────┬────────┘
         │ MCP Protocol
         ▼
┌─────────────────┐
│  MCP Server     │
│  (server.py)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ MemBlocks Lib   │
│  (Client API)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Infrastructure │
│ Qdrant/Ollama   │
└─────────────────┘
```

**Flow**:
1. AI assistant calls MCP tool
2. MCP server validates and processes request
3. Calls MemBlocks library API
4. Library interacts with vector DB and LLMs
5. Results returned through MCP to AI assistant

---

## Additional Resources

- [Architecture Overview](../ARCHITECTURE.md)
- [Library Setup Guide](../memblockslib_docs/01_SETUP_GUIDE.md)
- [Library Methods and Interfaces](../memblockslib_docs/02_METHODS_AND_INTERFACES.md)
- [Backend REST API](../backend/API.md)
- [Deployment Guide](../backend/DEPLOYMENT.md)
- [MCP Protocol Specification](https://spec.modelcontextprotocol.io/)

---

**Questions or issues?** Open a GitHub issue or check existing discussions.
