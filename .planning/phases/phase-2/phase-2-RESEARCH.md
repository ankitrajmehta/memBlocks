# Phase 2: Store Tools - Research

**Researched:** 2026-03-13
**Domain:** MCP server tools for memory persistence
**Confidence:** HIGH

## Summary

Phase 2 adds three store tools to the MemBlocks MCP server: `memblocks_store_semantic`, `memblocks_store_to_core`, and `memblocks_store`. These tools enable agents to persist facts and knowledge into the active memory block through different pathways.

The MemBlocks library already provides all necessary infrastructure:
- **SemanticMemoryService** handles PS1 extraction (LLM structured output from messages) and PS2 conflict resolution (vector similarity + LLM decision for ADD/UPDATE/DELETE)
- **CoreMemoryService** handles core memory extraction and updates via LLM

The implementation approach mirrors Phase 1: accept plain text input, wrap as message format ` [{"role": "user", "content": text}]`, then call the appropriate library methods.

**Primary recommendation:** Implement three FastMCP tools that wrap the existing SemanticMemoryService and CoreMemoryService methods, following the same error-handling and active-block patterns established in Phase 1.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastmcp | 3.1.0 | MCP server framework | Official Python SDK from PrefectHQ |
| memblocks | (library) | Memory management | Existing project library |
| pydantic | (transitive) | Input validation | FastMCP dependency |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| qdrant | (via memblocks) | Vector storage for semantic memories | Not directly accessed - via SemanticMemoryService |
| mongodb | (via memblocks) | Core memory storage | Not directly accessed - via CoreMemoryService |

---

## Architecture Patterns

### Recommended Project Structure

```
mcp_server/
├── __init__.py          # Package marker
├── state.py             # Active block state (Phase 1)
├── server.py            # MCP tools (Phase 1 + Phase 2)
└── pyproject.toml       # Package config
```

### Pattern 1: FastMCP Tool with Block Access

**What:** Tool functions that access the active block via client and perform operations

**When to use:** All store tools require the active block context

**Example:**
```python
@mcp.tool(name="memblocks_store_semantic")
async def memblocks_store_semantic(params: StoreSemanticInput, ctx: Context) -> str:
    """Store a fact to semantic memory."""
    client: MemBlocksClient = ctx.request_context.lifespan_context["client"]
    block_id, error = _active_block_id_or_error()
    if error:
        return json.dumps({"error": error})
    
    block = await client.get_block(block_id)
    if not block:
        return json.dumps({"error": f"Block {block_id} not found"})
    
    # Wrap plain text as messages for PS1 extraction
    messages = [{"role": "user", "content": params.fact}]
    extracted = await block._semantic.extract(messages)
    
    # Store each extracted memory with PS2 conflict resolution
    for memory in extracted:
        await block._semantic.store(memory)
    
    return json.dumps({"message": "Stored to semantic memory", "count": len(extracted)})
```

### Pattern 2: Message Wrapping for LLM Extraction

**What:** Plain text input wrapped as ` [{"role": "user", "content": text}]` before calling extraction

**When to use:** Both semantic and core memory extraction require message format

**Why:** Minimal change to existing LLM pipelines - matches Phase 1 decision

**Source:** STATE.md - "Plain text input wrapped as `[{"role": "user", "content": text}]` — minimal change to existing LLM pipelines"

### Pattern 3: Core Memory Update Pipeline

**What:** Get existing core, extract new from messages, save updated version

**When to use:** STOR-02 and STOR-03 for core memory

**Example:**
```python
# Get existing core memory
old_core = await block._core.get(block.core_memory_block_id or block.id)

# Extract new from wrapped messages
messages = [{"role": "user", "content": text}]
new_core = await block._core.extract(messages, old_core)

# Save updated version
await block._core.save(block.core_memory_block_id or block.id, new_core)
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Semantic extraction (PS1) | Custom LLM prompts and parsing | `SemanticMemoryService.extract()` | Already implements PS1_SEMANTIC_PROMPT with structured output |
| Conflict resolution (PS2) | Vector similarity logic | `SemanticMemoryService.store()` | Handles retrieval, LLM decision, and atomic storage |
| Core memory updates | Manual string concatenation | `CoreMemoryService.update()` | Implements CORE_MEMORY_PROMPT with persona/human split |
| Vector storage | Direct Qdrant calls | Via SemanticMemoryService | Handles sparse vectors, metadata, ID mapping |

**Key insight:** The MemBlocks library is specifically designed for memory extraction, conflict resolution, and storage. Custom implementations would miss edge cases around confidence thresholds, memory time handling, and atomic operations.

---

## Common Pitfalls

### Pitfall 1: Missing Block Reference to Services

**What goes wrong:** Block object provides access to `_semantic` and `_core` services, but these are private (underscore-prefixed)

**Why it happens:** The Block class exposes retrieval methods but not the underlying service methods directly

**How to avoid:** Access via `block._semantic` and `block._core` (note: these are internal APIs but the only way to use the store pipeline)

**Warning signs:** "Block has no attribute 'semantic'" errors

### Pitfall 2: Wrong Collection/Block ID for Core Memory

**What goes wrong:** Core memory not persisting or retrieving empty content

**Why it happens:** Using `block.id` instead of `block.core_memory_block_id` for core operations

**How to avoid:** Use `block.core_memory_block_id or block.id` pattern (matches existing code in Block.retrieve())

**Warning signs:** Core memory appears empty after store, or overwrites wrong block

### Pitfall 3: Not Handling Empty Extraction Results

**What goes wrong:** Tool returns success but nothing was stored

**Why it happens:** PS1 extraction may return no memories if input is not informative enough

**How to avoid:** Return the number of memories extracted/stored in response

**Warning signs:** User expects memory stored but retrieval returns nothing

### Pitfall 4: Blocking Async Operations

**What goes wrong:** Server hangs or errors

**Why it happens:** Calling async library methods without await

**How to avoid:** Ensure all MemBlocksClient, SemanticMemoryService, and CoreMemoryService calls are awaited

---

## Code Examples

### Example 1: Semantic Store (STOR-01)

```python
# Source: memblocks_lib/src/memblocks/services/semantic_memory.py (lines 124-187, 193-424)
from memblocks.models.units import SemanticMemoryUnit, MemoryUnitMetaData
from datetime import datetime, timezone

async def store_semantic(block, fact: str) -> dict:
    """Store a fact to semantic memory with PS1 + PS2 pipeline."""
    # Step 1: Wrap plain text as messages for PS1 extraction
    messages = [{"role": "user", "content": fact}]
    
    # Step 2: PS1 - Extract semantic memories from the fact
    extracted_memories = await block._semantic.extract(messages)
    
    # Step 3: PS2 - Store each with conflict resolution
    operations = []
    for memory in extracted_memories:
        ops = await block._semantic.store(memory)
        operations.extend(ops)
    
    return {
        "extracted": len(extracted_memories),
        "operations": [op.model_dump() for op in operations]
    }
```

### Example 2: Core Store (STOR-02)

```python
# Source: memblocks_lib/src/memblocks/services/core_memory.py (lines 176-196)

async def store_to_core(block, fact: str) -> dict:
    """Update core memory with a new fact."""
    # Step 1: Get existing core memory (if any)
    core_block_id = block.core_memory_block_id or block.id
    old_core = await block._core.get(core_block_id)
    
    # Step 2: Wrap plain text as messages for extraction
    messages = [{"role": "user", "content": fact}]
    
    # Step 3: Extract updated core memory (LLM combines old + new)
    new_core = await block._core.extract(messages, old_core)
    
    # Step 4: Save the updated core memory
    await block._core.save(core_block_id, new_core)
    
    return {
        "persona": new_core.persona_content[:100] + "...",
        "human": new_core.human_content[:100] + "...",
        "message": "Core memory updated"
    }
```

### Example 3: Combined Store (STOR-03)

```python
async def store_combined(block, fact: str) -> dict:
    """Store to both semantic and core memory."""
    # Run both pipelines - semantic first, then core
    semantic_result = await store_semantic(block, fact)
    core_result = await store_to_core(block, fact)
    
    return {
        "semantic": semantic_result,
        "core": core_result,
        "message": "Stored to both semantic and core memory"
    }
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Session.add() with full conversation | Direct fact storage via MCP tools | v1.1 MCP Server | Agents can push distilled facts without full history |
| Manual core memory editing | LLM-driven core memory updates | v1.1 MCP Server | Core memory stays consistent via LLM extraction |
| Vector-only storage | PS1 extraction + PS2 conflict resolution | Pre-existing in library | Prevents duplicate/conflicting memories |

**Deprecated/outdated:**
- Direct Qdrant/MongoDB writes — should go through library services for proper PS1/PS2 processing

---

## Open Questions

1. **Should store tools return transparency data (operations performed)?**
   - What we know: SemanticMemoryService.store() returns List[MemoryOperation] with ADD/UPDATE/DELETE
   - What's unclear: Whether agents need this detail or just success/failure
   - Recommendation: Return operation summary in response for debugging

2. **What confidence threshold for storing semantic memories?**
   - What we know: SemanticMemoryService.extract() returns memories with confidence scores
   - What's unclear: Whether to filter low-confidence extractions before storing
   - Recommendation: Store all for now; add threshold parameter if needed

3. **Error handling during partial failures?**
   - What we know: Combined store runs semantic then core
   - What's unclear: What happens if semantic succeeds but core fails?
   - Recommendation: Return error status for whichever step fails; semantic commits are atomic per memory

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| STOR-01 | Agent can store a fact to semantic memory via `memblocks_store_semantic`, which accepts plain text, runs LLM extraction (PS1) and conflict resolution (PS2) | SemanticMemoryService.extract() + store() implement full PS1+PS2 pipeline |
| STOR-02 | Agent can update core memory via `memblocks_store_to_core`, which accepts plain text, wraps it as a message, and runs LLM core memory update | CoreMemoryService.update() implements full extract+save pipeline |
| STOR-03 | Agent can store to both semantic and core memory in one call via `memblocks_store`, which runs both pipelines sequentially | Sequential execution of STOR-01 and STOR-02 logic |

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (inherited from memblocks_lib) |
| Config file | pyproject.toml (root) |
| Quick run command | `pytest tests/ -x -v` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STOR-01 | Semantic store with PS1+PS2 | integration | Run MCP tool + verify vector retrieval | ❌ Needs creation |
| STOR-02 | Core store with LLM update | integration | Run MCP tool + verify core retrieval | ❌ Needs creation |
| STOR-03 | Combined store | integration | Run MCP tool + verify both retrievals | ❌ Needs creation |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q` (fast subset)
- **Per wave merge:** `pytest tests/ -v` (full suite)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_store_tools.py` — integration tests for all three store tools
- [ ] `tests/conftest.py` — shared fixtures (may reuse from existing tests)

---

## Sources

### Primary (HIGH confidence)
- `memblocks_lib/src/memblocks/client.py` - MemBlocksClient interface, service wiring
- `memblocks_lib/src/memblocks/services/semantic_memory.py` - PS1 extraction (lines 124-187), PS2 storage (lines 193-424)
- `memblocks_lib/src/memblocks/services/core_memory.py` - Core memory update pipeline (lines 176-196)
- `memblocks_lib/src/memblocks/services/block.py` - Block class with service access via `_semantic`, `_core`
- `mcp_server/server.py` - Phase 1 FastMCP tools pattern

### Secondary (MEDIUM confidence)
- STATE.md - Project decisions (message wrapping pattern)
- ROADMAP.md - Phase 2 requirements and success criteria

### Tertiary (LOW confidence)
- None required - primary sources provide complete implementation guidance

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - FastMCP 3.1.0 confirmed from Phase 1 summary
- Architecture: HIGH - Existing patterns in server.py and service classes provide clear template
- Pitfalls: HIGH - Based on actual library API inspection

**Research date:** 2026-03-13
**Valid until:** 2026-04-13 (30 days for stable library API)
