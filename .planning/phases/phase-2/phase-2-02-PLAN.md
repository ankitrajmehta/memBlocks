---
phase: phase-2
plan: 02
type: execute
wave: 2
depends_on: [phase-2-01]
files_modified: [mcp_server/server.py]
autonomous: true
requirements: [STOR-03]

must_haves:
  truths:
    - "Agent calls memblocks_store with plain text; fact is stored in both semantic and core memory"
    - "Tool returns combined results from both pipelines"
  artifacts:
    - path: "mcp_server/server.py"
      provides: "memblocks_store combined tool"
      exports: ["memblocks_store"]
  key_links:
    - from: "memblocks_store"
      to: "block._semantic + block._core"
      via: "sequential async calls"
      pattern: "_semantic.*_core|_core.*_semantic"
---

<objective>
Implement the combined store tool: `memblocks_store` (STOR-03). This tool accepts plain text and stores to both semantic and core memory in a single call by running both pipelines sequentially.

Purpose: Give agents a convenient single operation to persist facts to both memory systems without making two separate tool calls.

Output: One new MCP tool in server.py
</objective>

<execution_context>
@C:/Users/Lenovo/.config/opencode/get-shit-done/workflows/execute-plan.md
@C:/Users/Lenovo/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/phase-2/phase-2-01-PLAN.md
@mcp_server/server.py

# Key context from Plan 01:
# - memblocks_store_semantic uses block._semantic.extract() + store()
# - memblocks_store_to_core uses block._core.get() + extract() + save()
# - Both wrap plain text as [{"role": "user", "content": fact}]
# - Both use _active_block_id_or_error() for active block validation
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add memblocks_store tool (STOR-03)</name>
  <files>mcp_server/server.py</files>
  <behavior>
    - Input: plain text fact (string)
    - Runs semantic storage pipeline (PS1 extraction + PS2 conflict resolution)
    - Runs core memory update pipeline (LLM extraction + save)
    - Returns JSON with results from both operations
    - Returns error if no active block
  </behavior>
  <action>
Create `StoreInput` Pydantic model with:
- fact: str (..., description="The fact or knowledge to store in both semantic and core memory", min_length=1)

Create `@mcp.tool(name="memblocks_store")` async function:
1. Get client from ctx.request_context.lifespan_context
2. Call _active_block_id_or_error() - return error if no active block
3. Get block via client.get_block(block_id) - return error if not found
4. Wrap params.fact as messages = [{"role": "user", "content": params.fact}]

# Semantic pipeline (same as memblocks_store_semantic):
5. extracted = await block._semantic.extract(messages)  # PS1
6. semantic_operations = []
7. For each memory in extracted:
   ops = await block._semantic.store(memory)  # PS2
   semantic_operations.extend(ops)

# Core pipeline (same as memblocks_store_to_core):
8. core_block_id = block.core_memory_block_id or block.id
9. old_core = await block._core.get(core_block_id)
10. new_core = await block._core.extract(messages, old_core)
11. await block._core.save(core_block_id, new_core)

# Return combined result:
12. Return json.dumps with:
{
  "message": "Stored to both semantic and core memory",
  "semantic": {"count": len(extracted), "operations": [...]},
  "core": {"updated": true, "persona_preview": new_core.persona_content[:100], "human_preview": new_core.human_content[:100]}
}

Use the same tool annotations pattern as existing tools
  </action>
  <verify>
    <automated>python -c "import ast; ast.parse(open('mcp_server/server.py').read())" && echo "Syntax OK"</automated>
  </verify>
  <done>Tool registered in server.py, accepts plain text, runs both semantic and core pipelines, returns combined result</done>
</task>

</tasks>

<verification>
- [ ] Tool is registered with FastMCP
- [ ] Uses _active_block_id_or_error() for active block validation
- [ ] Wraps plain text as messages before both extractions
- [ ] Runs PS1+PS2 for semantic (block._semantic.extract + store)
- [ ] Runs LLM update for core (block._core.get + extract + save)
- [ ] Returns combined JSON result from both operations
</verification>

<success_criteria>
- STOR-03: Agent can call `memblocks_store` with plain text, and the fact persists in both semantic and core memory in a single call
</success_criteria>

<output>
After completion, create `.planning/phases/phase-2/phase-2-02-SUMMARY.md`
</output>
