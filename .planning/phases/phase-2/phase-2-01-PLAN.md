---
phase: phase-2
plan: 01
type: execute
wave: 1
depends_on: [phase-1-01]
files_modified: [mcp_server/server.py]
autonomous: true
requirements: [STOR-01, STOR-02]

must_haves:
  truths:
    - "Agent calls memblocks_store_semantic with plain text; fact is stored in semantic memory"
    - "Agent calls memblocks_store_to_core with plain text; core memory is updated"
    - "Both tools return clear success/error messages as JSON"
  artifacts:
    - path: "mcp_server/server.py"
      provides: "memblocks_store_semantic and memblocks_store_to_core tools"
      exports: ["memblocks_store_semantic", "memblocks_store_to_core"]
  key_links:
    - from: "memblocks_store_semantic"
      to: "block._semantic.extract() + store()"
      via: "async calls with wrapped messages"
      pattern: "_semantic\\.(extract|store)"
    - from: "memblocks_store_to_core"
      to: "block._core.get() + extract() + save()"
      via: "async calls with wrapped messages"
      pattern: "_core\\.(get|extract|save)"
---

<objective>
Implement two store tools: `memblocks_store_semantic` (STOR-01) and `memblocks_store_to_core` (STOR-02). Both tools accept plain text, wrap it as messages, and use the MemBlocks library's PS1/PS2 pipelines for semantic storage or LLM-driven core memory updates.

Purpose: Give agents the ability to persist facts to semantic memory (with extraction + conflict resolution) and to core memory (with LLM update) as separate operations.

Output: Two new MCP tools in server.py
</objective>

<execution_context>
@C:/Users/Lenovo/.config/opencode/get-shit-done/workflows/execute-plan.md
@C:/Users/Lenovo/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/phase-1/phase-1-01-SUMMARY.md
@mcp_server/server.py

# Key patterns from Phase 1:
# - FastMCP tool with @mcp.tool() decorator
# - Pydantic input model with Field descriptions
# - _active_block_id_or_error() helper for active block validation
# - ctx.request_context.lifespan_context["client"] for MemBlocksClient access
# - Return json.dumps() with result/error
</context>

<interfaces>
<!-- Key interfaces from memblocks library that this plan uses -->

From block._semantic:
```python
async def extract(messages: list[dict]) -> list[SemanticMemoryUnit]:
    """PS1: Extract semantic memories from messages using LLM"""
    
async def store(memory: SemanticMemoryUnit) -> list[MemoryOperation]:
    """PS2: Store memory with conflict resolution. Returns operations (ADD/UPDATE/DELETE)"""
```

From block._core:
```python
async def get(block_id: str) -> CoreMemory | None:
    """Get existing core memory"""

async def extract(messages: list[dict], old_core: CoreMemory | None) -> CoreMemory:
    """Extract updated core memory by combining old + new messages via LLM"""

async def save(block_id: str, core: CoreMemory) -> None:
    """Save updated core memory"""
```

Helper pattern from Phase 1:
```python
def _active_block_id_or_error() -> tuple[str | None, str | None]:
    """Returns (block_id, None) on success or (None, error_message) if not set."""
```
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add memblocks_store_semantic tool (STOR-01)</name>
  <files>mcp_server/server.py</files>
  <behavior>
    - Input: plain text fact (string)
    - Wraps text as [{"role": "user", "content": fact}]
    - Calls block._semantic.extract(messages) for PS1
    - Calls block._semantic.store(memory) for each extracted memory for PS2
    - Returns JSON with message and count of memories stored
    - Returns error if no active block
  </behavior>
  <action>
Create `StoreSemanticInput` Pydantic model with:
- fact: str (..., description="The fact or knowledge to store in semantic memory", min_length=1)

Create `@mcp.tool(name="memblocks_store_semantic")` async function:
1. Get client from ctx.request_context.lifespan_context
2. Call _active_block_id_or_error() - return error if no active block
3. Get block via client.get_block(block_id) - return error if not found
4. Wrap params.fact as messages = [{"role": "user", "content": params.fact}]
5. Call await block._semantic.extract(messages) (PS1 extraction)
6. For each extracted memory, call await block._semantic.store(memory) (PS2 conflict resolution)
7. Return json.dumps with {"message": "Stored to semantic memory", "count": len(extracted), "operations": [...]}

Use the same tool annotations pattern as existing tools (title, readOnlyHint, etc.)
  </action>
  <verify>
    <automated>python -c "import ast; ast.parse(open('mcp_server/server.py').read())" && echo "Syntax OK"</automated>
  </verify>
  <done>Tool registered in server.py, accepts plain text, runs PS1+PS2, returns count of stored memories</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add memblocks_store_to_core tool (STOR-02)</name>
  <files>mcp_server/server.py</files>
  <behavior>
    - Input: plain text fact (string)
    - Wraps text as [{"role": "user", "content": fact}]
    - Gets existing core memory via block._core.get(core_block_id)
    - Extracts new core via block._core.extract(messages, old_core)
    - Saves updated core via block._core.save(core_block_id, new_core)
    - Returns JSON with message confirming update
    - Returns error if no active block
  </behavior>
  <action>
Create `StoreToCoreInput` Pydantic model with:
- fact: str (..., description="The fact or knowledge to add/update in core memory", min_length=1)

Create `@mcp.tool(name="memblocks_store_to_core")` async function:
1. Get client from ctx.request_context.lifespan_context
2. Call _active_block_id_or_error() - return error if no active block
3. Get block via client.get_block(block_id) - return error if not found
4. Determine core_block_id = block.core_memory_block_id or block.id
5. Get existing core: old_core = await block._core.get(core_block_id)
6. Wrap params.fact as messages = [{"role": "user", "content": params.fact}]
7. Extract new core: new_core = await block._core.extract(messages, old_core)
8. Save updated core: await block._core.save(core_block_id, new_core)
9. Return json.dumps with {"message": "Core memory updated", "persona_preview": new_core.persona_content[:100], "human_preview": new_core.human_content[:100]}

Use the same tool annotations pattern as existing tools
  </action>
  <verify>
    <automated>python -c "import ast; ast.parse(open('mcp_server/server.py').read())" && echo "Syntax OK"</automated>
  </verify>
  <done>Tool registered in server.py, accepts plain text, runs LLM core update, returns confirmation with preview</done>
</task>

</tasks>

<verification>
- [ ] Both tools are registered with FastMCP
- [ ] Both tools use _active_block_id_or_error() for active block validation
- [ ] Both tools wrap plain text as messages before extraction
- [ ] Semantic tool uses block._semantic.extract() + store()
- [ ] Core tool uses block._core.get() + extract() + save()
- [ ] Both return JSON strings with appropriate success/error responses
</verification>

<success_criteria>
- STOR-01: Agent can call `memblocks_store_semantic` with plain text, and PS1 extraction + PS2 conflict resolution runs
- STOR-02: Agent can call `memblocks_store_to_core` with plain text, and core memory is updated via LLM
</success_criteria>

<output>
After completion, create `.planning/phases/phase-2/phase-2-01-SUMMARY.md`
</output>
