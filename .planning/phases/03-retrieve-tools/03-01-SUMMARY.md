---
phase: "03"
plan: "01"
subsystem: mcp-server
tags: [fastmcp, retrieval, memory, mcp-tools]

# Dependency graph
requires:
  - phase: "02"
    provides: "Store tools (memblocks_store, memblocks_store_semantic, memblocks_store_to_core)"
provides:
  - "Three MCP retrieval tools: combined, core-only, semantic-only"
  - "Formatted context strings ready for LLM injection"
affects: [agents, cli, downstream-phases]

# Tech tracking
tech-stack:
  added: []
  patterns: [mcp-tool-pattern, retrieval-pattern]

key-files:
  created: []
  modified: [mcp_server/server.py]

key-decisions:
  - "Reused RetrieveInput model for both combined and semantic retrieval"
  - "Core retrieval takes no params - returns full content"

patterns-established:
  - "MCP tool pattern: validate active block → get block → call method → return formatted result"

requirements-completed: [RETR-01, RETR-02, RETR-03]

# Metrics
duration: 3min
completed: 2026-03-14
---

# Phase 03 Plan 01: Retrieve Tools Summary

**Three MCP retrieval tools for combined, core-only, and semantic-only memory retrieval, formatted for LLM injection**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-14T00:00:00Z
- **Completed:** 2026-03-14T00:03:00Z
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments
- Added `memblocks_retrieve` - combined retrieval from core + semantic with query
- Added `memblocks_retrieve_core` - core-only retrieval, returns full core memory (no query)
- Added `memblocks_retrieve_semantic` - semantic-only retrieval with query
- All tools return formatted strings via `to_prompt_string()` for direct LLM injection

## Task Commits

Each task was committed atomically:

1. **Tasks 1-3: All three retrieval tools** - `ffb8b0f` (feat)

**Plan metadata:** (to be added by final commit)

## Files Created/Modified
- `mcp_server/server.py` - Added 144 lines with three new MCP tools

## Decisions Made
- Reused `RetrieveInput` Pydantic model for both combined and semantic-only retrieval (query field)
- Core retrieval takes no input parameters since it returns full content
- All tools follow existing MCP pattern: validate active block → get block → call retrieval method → return formatted result

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Retrieval tools complete for Phase 3
- Ready for Phase 3 Plan 02 or next phase

---
*Phase: 03-retrieve-tools*
*Completed: 2026-03-14*
