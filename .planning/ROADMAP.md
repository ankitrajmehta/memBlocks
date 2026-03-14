# Roadmap: MemBlocks

## Milestones

- ✅ **v1.0 Foundation** — Pre-GSD (shipped, existing codebase)
- ✅ **v1.1 MCP Server** — Phases 1–4 (COMPLETE)

## Phases

<details>
<summary>✅ v1.0 Foundation — SHIPPED (pre-GSD, existing codebase)</summary>

Full Python library, FastAPI backend, React frontend, CLI, multi-provider LLM support, transparency layer. No GSD phase tracking (predates milestone system).

</details>

### ✅ v1.1 MCP Server (Complete)

**Milestone Goal:** Any AI agent connected to MemBlocks can store and retrieve the right memory from the right block at the right time, with conflict resolution and source transparency.

- [x] **Phase 1: Foundation** — MCP server scaffold, singleton client, active block state, block management tools
- [x] **Phase 2.01: Store Semantic & Core** — Semantic store (PS1+PS2) and core store (LLM update) tools
- [x] **Phase 2.02: Store Combined** — Combined store tool for single-call semantic+core
- [x] **Phase 3: Retrieve Tools** — Semantic retrieve, core retrieve, and combined retrieve via MCP
- [x] **Phase 4: CLI + Resources** — Block-switching CLI commands and MCP agent-readable resources

## Phase Details

### Phase 1: Foundation
**Goal**: A working MCP server that agents can connect to, list blocks, and create blocks — with graceful error handling when no active block is set
**Depends on**: Nothing (first phase)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05, BLCK-01, BLCK-02
**Success Criteria** (what must be TRUE):
  1. Agent connects to the MCP server via stdio and receives the tool list without errors
  2. Agent calls `memblocks_list_blocks` and receives all blocks for the configured user, including which is active
  3. Agent calls `memblocks_create_block` and a new block appears in subsequent list calls
  4. Any tool call made when no active block is set returns a clear error message — server does not crash
  5. Running `memblocks-mcp` from the command line starts the server (entry point registered in pyproject.toml)
**Plans**: TBD

### Phase 2: Store Tools
**Goal**: Agent can persist facts and knowledge into the active memory block via three store paths — semantic-only, core-only, and combined
**Depends on**: Phase 1
**Requirements**: STOR-01, STOR-02, STOR-03
**Success Criteria** (what must be TRUE):
  1. Agent calls `memblocks_store_semantic` with a plain text fact; the fact appears in subsequent vector search results (PS1 extraction + PS2 conflict resolution ran)
  2. Agent calls `memblocks_store_to_core` with a plain text fact; core memory is updated and the change is visible on next core retrieval
  3. Agent calls `memblocks_store` with a plain text fact; the fact persists in both semantic and core memory in a single call
**Plans**: phase-2-01-PLAN.md, phase-2-02-PLAN.md

### Phase 3: Retrieve Tools
**Goal**: Agent can retrieve the right context from the active memory block — combined, core-only, or semantic-only — formatted and ready for LLM injection
**Depends on**: Phase 1
**Requirements**: RETR-01, RETR-02, RETR-03
**Success Criteria** (what must be TRUE):
  1. Agent calls `memblocks_retrieve` with a query string; returned string contains relevant memories from both core and semantic sources, formatted for direct LLM injection
  2. Agent calls `memblocks_retrieve_core` with no query; returned string contains the full core memory contents of the active block
  3. Agent calls `memblocks_retrieve_semantic` with a query string; returned string contains only semantically relevant memories (no core) for the active block
**Plans**: 03-01-PLAN.md — Retrieve tools implementation

### Phase 4: CLI + Resources
**Goal**: User can switch the active block from the terminal, and agents can read block context and tool documentation without making a tool call
**Depends on**: Phases 1, 2, 3
**Requirements**: CLI-01, CLI-02, RES-01, RES-02
**Success Criteria** (what must be TRUE):
  1. User runs `memblocks set-block <block_id>` in the terminal; subsequent MCP tool calls operate on the new block
  2. User runs `memblocks get-block` and sees the current active block name and ID
  3. Agent reads the `memblocks://active-block` MCP resource and receives the current block name, ID, and description without calling any tool
  4. Agent reads the `memblocks://tools` MCP resource and receives a human-readable usage guide listing all available tools, their purpose, and when to use each
**Plans**: 2 plans

Plans:
- [x] 04-01-PLAN.md — CLI commands: `memblocks set-block` and `memblocks get-block` (Complete: 2026-03-14)
- [x] 04-02-PLAN.md — MCP resources: `memblocks://active-block` and `memblocks://tools` (Complete: 2026-03-14)

## Progress

**Execution Order:** 1 → 2 → 3 → 4

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.1 | 1/1 | Complete | 2026-03-12 |
| 2. Store Tools | v1.1 | 2/2 | Complete | 2026-03-13 |
| 3. Retrieve Tools | v1.1 | 1/1 | Complete | 2026-03-14 |
| 4. CLI + Resources | v1.1 | 2/2 | Complete | 2026-03-14 |

---
*Roadmap created: 2026-03-12*
*Last updated: 2026-03-14*
