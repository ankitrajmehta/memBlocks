# Phase 3: Retrieve Tools - Research

**Researched:** 2026-03-14
**Domain:** MCP Server retrieval tools (semantic + core memory retrieval)
**Confidence:** HIGH

## Summary

The MemBlocks library already provides all three retrieval methods required by the MCP server:
1. `block.retrieve(query)` - Combined (core + semantic) retrieval
2. `block.core_retrieve()` - Core-only retrieval (no query needed)
3. `block.semantic_retrieve(query)` - Semantic-only retrieval (query-based)

These return `RetrievalResult` objects with a `.to_prompt_string()` method that formats memories for direct LLM injection. The MCP server needs to expose these as three MCP tools that:
- Check for active block (using existing `_active_block_id_or_error()` helper)
- Get the block via `client.get_block(block_id)`
- Call the appropriate retrieval method
- Return the formatted string

**Primary recommendation:** Implement three MCP tools (`memblocks_retrieve`, `memblocks_retrieve_core`, `memblocks_retrieve_semantic`) that wrap the library's existing `Block` retrieval methods and return formatted strings.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RETR-01 | Combined retrieve (core + semantic) with query string, formatted for LLM injection | Library provides `block.retrieve(query)` → `RetrievalResult.to_prompt_string()` |
| RETR-02 | Core-only retrieve with no query, full content | Library provides `block.core_retrieve()` → `RetrievalResult.to_prompt_string()` |
| RETR-03 | Semantic-only retrieve with query string, relevant memories only | Library provides `block.semantic_retrieve(query)` → `RetrievalResult.to_prompt_string()` |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| MemBlocks library | Latest | Retrieval via `Block` methods | Already installed, provides full pipeline |
| FastMCP | >=3.1.0 | MCP tool definitions | Used for all existing tools |
| Pydantic | Latest | Input validation models | Used for all existing store tools |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| RetrievalResult | N/A | Container returned by library | Wrapped in Block, accessed via block.retrieve() |
| to_prompt_string() | N/A | Formats for LLM injection | Always called on RetrievalResult for return value |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Library retrieval | Custom vector search | Library handles query enhancement, hybrid search, reranking - hand-rolling would miss these |
| to_prompt_string() | Custom formatting | Library format tested with LLM prompts, consistent with other agents |

**Installation:**
```bash
# Already installed via memblocks dependency
# No additional packages needed
```

## Architecture Patterns

### Recommended Project Structure
```
mcp_server/
├── server.py              # Add 3 new tools here (lines ~566-750)
├── state.py               # Existing - active block management
└── pyproject.toml         # Existing - no changes needed
```

### Pattern 1: Retrieval Tool Structure
**What:** Each retrieval tool follows the same pattern as store tools
**When to use:** For all three retrieve tools

```python
# Source: Adapted from store tools in server.py (lines 290-565)
# Pattern for retrieve tools

# 1. Input model (optional - semantic needs query, core does not)
class RetrieveInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    query: str = Field(
        ...,
        description="Query string to find relevant memories",
        min_length=1,
    )

# 2. MCP tool definition
@mcp.tool(
    name="memblocks_retrieve",
    annotations={...},
)
async def memblocks_retrieve(params: RetrieveInput, ctx: Context) -> str:
    """Tool description..."""
    logger.info(f"memblocks_retrieve: query={params.query[:80]!r}")
    
    # 3. Get client from context
    client: MemBlocksClient = ctx.request_context.lifespan_context["client"]
    
    # 4. Check active block (same helper as store tools)
    block_id, error = _active_block_id_or_error()
    if error:
        return json.dumps({"error": error})
    
    # 5. Get block
    block = await client.get_block(block_id)
    if block is None:
        return json.dumps({"error": f"Block '{block_id}' not found."})
    
    # 6. Call retrieval method
    result = await block.retrieve(params.query)
    
    # 7. Format for LLM injection
    return result.to_prompt_string()
```

### Pattern 2: Core-Only (No Query)
**What:** Core retrieval takes no query parameter
**When to use:** For `memblocks_retrieve_core`

```python
# Source: Adapted from block.py (lines 101-111)
# Core-only has no query parameter

@mcp.tool(...)
async def memblocks_retrieve_core(ctx: Context) -> str:
    # ... same setup as above ...
    result = await block.core_retrieve()  # No query argument
    return result.to_prompt_string()
```

### Pattern 3: Semantic-Only
**What:** Semantic retrieval takes a query
**When to use:** For `memblocks_retrieve_semantic`

```python
# Source: Adapted from block.py (lines 113-124)
# Semantic-only is query-based

@mcp.tool(...)
async def memblocks_retrieve_semantic(params: RetrieveInput, ctx: Context) -> str:
    # ... same setup as above ...
    result = await block.semantic_retrieve(params.query)  # Query required
    return result.to_prompt_string()
```

### Anti-Patterns to Avoid
- **Hand-rolling vector search:** The library handles query enhancement, hybrid (dense+sparse) search, and Cohere re-ranking. Hand-rolling would miss these optimizations.
- **Direct service access:** Use `block.retrieve()`, not `block._semantic.retrieve()` directly - the Block wrapper ensures proper result formatting.
- **Returning JSON for LLM context:** The success criteria specify returning "formatted context ready for LLM injection" - this means plain text from `to_prompt_string()`, not JSON with metadata.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Query enhancement | Custom query expansion | `block.retrieve()` uses library's `_enhance_query()` | Library handles single-call expansion + hypothetical paragraphs |
| Hybrid search | Pure dense vectors | Library's `_retrieve_with_hybrid()` | Library supports SPLADE sparse vectors for better recall |
| Re-ranking | LLM-based ranking | Library's Cohere reranker | Faster and more accurate per documentation |
| Result formatting | Custom string building | `RetrievalResult.to_prompt_string()` | Tested format, consistent across all retrieval types |

**Key insight:** The library's retrieval pipeline is significantly more sophisticated than storage. It includes query enhancement, hybrid dense+sparse search, and Cohere re-ranking. Using the library ensures best-in-class retrieval quality.

## Common Pitfalls

### Pitfall 1: Empty Results When No Memories Match
**What goes wrong:** Retrieval returns empty string if no semantic memories match the query and core is empty
**Why it happens:** Vector search returns nothing when no memories are similar enough to query
**How to avoid:** Document this behavior; callers should check if result is empty and handle gracefully
**Warning signs:** Agent gets empty context for queries outside stored memory scope

### Pitfall 2: Wrong Block When Active Block Not Set
**What goes wrong:** Error returned instead of memories
**Why it happens:** `_active_block_id_or_error()` returns error when no active block
**How to avoid:** Already handled by existing helper function - same pattern as store tools
**Warning signs:** Error message returned: "No active block is set"

### Pitfall 3: Formatting Mismatch with LLM Expectations
**What goes wrong:** Returned text doesn't include relevant metadata
**Why it happens:** `to_prompt_string()` formats for LLM but may miss specific use cases
**How to avoid:** Library's format tested with LLM prompts - use as-is unless specific needs arise
**Warning signs:** LLM doesn't utilize retrieved context effectively

### Pitfall 4: Query Without Meaningful Content
**What goes wrong:** Semantic retrieval returns irrelevant results for vague queries
**Why it happens:** Query enhancement helps but can't fix fundamentally vague queries
**How to avoid:** Document that specific queries return better results
**Warning signs:** Agent uses generic queries like "everything" or "what do you know"

## Code Examples

### Combined Retrieve (RETR-01)
```python
# Source: memblocks_lib/src/memblocks/services/block.py (lines 84-99)
async def retrieve(self, query: str) -> RetrievalResult:
    """
    Retrieve all available memory types relevant to *query*.
    Combines core memory (always fetched in full) with semantic memories (vector-searched).
    """
    core, semantic = await self._fetch_core_and_semantic(query)
    return RetrievalResult(core=core, semantic=semantic, resource=[])

# MCP tool usage:
result = await block.retrieve(query)
return result.to_prompt_string()
```

### Core-Only Retrieve (RETR-02)
```python
# Source: memblocks_lib/src/memblocks/services/block.py (lines 101-111)
async def core_retrieve(self) -> RetrievalResult:
    """
    Retrieve only the core memory for this block.
    Core memory is always fetched in full — no query needed.
    """
    core = await self._core.get(self.core_memory_block_id or self.id)
    return RetrievalResult(core=core, semantic=[], resource=[])

# MCP tool usage:
result = await block.core_retrieve()
return result.to_prompt_string()
```

### Semantic-Only Retrieve (RETR-03)
```python
# Source: memblocks_lib/src/memblocks/services/block.py (lines 113-124)
async def semantic_retrieve(self, query: str) -> RetrievalResult:
    """
    Retrieve only semantic memories relevant to *query* via vector search.
    """
    semantic = await self._fetch_semantic(query)
    return RetrievalResult(core=None, semantic=semantic, resource=[])

# MCP tool usage:
result = await block.semantic_retrieve(query)
return result.to_prompt_string()
```

### Format Output (All Three)
```python
# Source: memblocks_lib/src/memblocks/models/retrieval.py (lines 42-108)
# Returns formatted string like:
"""
<Core Memory>
[PERSONA]
{persona_content}
[HUMAN]
{human_content}
</Core Memory>

<Semantic Memories>
[EVENT] {memory.content}
 Memory Updated at: {memory.updated_at}
 | Event occurance time: {memory.memory_time} 

[FACT] {memory.content}
 Memory Updated at: {memory.updated_at}
</Semantic Memories>
"""
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Direct vector retrieval | Query enhancement + hybrid search + reranking | Library v1.x | Significantly improved recall and precision |
| Single dense vectors | Dense + SPLADE sparse hybrid | Library config | Better handling of rare terms |
| LLM-based reranking | Cohere reranker API | Library v1.x | Faster, more accurate reranking |

**Deprecated/outdated:**
- Direct `_semantic.retrieve()` calls: Should use `block.retrieve()` for proper result formatting
- Custom formatting: Use `to_prompt_string()` for consistency

## Open Questions

1. **What should happen when retrieval returns empty?**
   - What we know: `to_prompt_string()` returns empty string, no error
   - What's unclear: Should MCP tool return empty string or a message?
   - Recommendation: Return empty string (matches library behavior) - callers can check `is_empty()`

2. **Should retrieval include resource memories?**
   - What we know: Resource memories are a stub, always empty
   - What's unclear: Future implementation may change this
   - Recommendation: Document that resource memories return empty for now

3. **How many semantic results to retrieve?**
   - What we know: Library has `retrieval_top_k` config (default 5)
   - What's unclear: Whether this default is optimal for MCP use
   - Recommendation: Use library defaults initially, expose as config if needed

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (not yet configured in project) |
| Config file | None detected - needs Wave 0 setup |
| Quick run command | `pytest tests/ -x` (once configured) |
| Full suite command | `pytest tests/` (once configured) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RETR-01 | Combined retrieve returns formatted context | unit | N/A - requires MongoDB/Qdrant | ❌ |
| RETR-02 | Core-only retrieve returns full core content | unit | N/A - requires MongoDB | ❌ |
| RETR-03 | Semantic-only returns relevant memories | unit | N/A - requires Qdrant | ❌ |

### Sampling Rate
- **Per task commit:** N/A - integration tests require infrastructure
- **Per wave merge:** Full test suite
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] Test directory `tests/` does not exist in mcp_server
- [ ] No pytest.ini or conftest.py configured
- [ ] No test files for MCP tools
- [ ] Framework install: Not yet configured

**Note:** Retrieval tools require live MongoDB and Qdrant instances. Consider:
- Integration tests with testcontainers
- Mock-based unit tests for tool wrapper logic
- Or document as requiring full infrastructure to test

## Sources

### Primary (HIGH confidence)
- `memblocks_lib/src/memblocks/services/block.py` - Block retrieval methods (lines 84-140)
- `memblocks_lib/src/memblocks/models/retrieval.py` - RetrievalResult.format_string() (lines 42-108)
- `mcp_server/server.py` - Existing tool patterns (lines 290-565)

### Secondary (MEDIUM confidence)
- `memblocks_lib/src/memblocks/services/semantic_memory.py` - Retrieval pipeline details (lines 707-819)
- `memblocks_lib/src/memblocks/services/core_memory.py` - Core retrieval (lines 146-170)

### Tertiary (LOW confidence)
- None - all sources from library codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Library already provides all required methods
- Architecture: HIGH - Follows existing store tool patterns exactly
- Pitfalls: MEDIUM - Library handles most edge cases internally

**Research date:** 2026-03-14
**Valid until:** 90 days - Retrieval API is stable in library
