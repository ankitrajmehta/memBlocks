# MemBlocks

## What This Is

MemBlocks is a modular memory management library and platform that lets AI agents and users maintain multiple independent, organized memory spaces ("blocks"). Each block contains layered memory types — core (always-on facts), semantic (searchable knowledge), and resources (documents) — retrieved through intelligent, intent-aware search. It is designed for personal use, team collaboration, and AI agent integration.

## Core Value

Any AI agent connected to MemBlocks can store and retrieve the right memory from the right block at the right time, with conflict resolution and source transparency.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- ✓ Core memory extraction from conversation via LLM — v1.0 (existing)
- ✓ Semantic memory extraction (PS1) + conflict resolution (PS2) — v1.0 (existing)
- ✓ Hybrid vector search (dense + SPLADE) with query expansion, HyDE, and Cohere reranking — v1.0 (existing)
- ✓ Block management (create, list, retrieve by user) — v1.0 (existing)
- ✓ Session-based chat loop with memory window + recursive summary — v1.0 (existing)
- ✓ FastAPI REST backend with Clerk auth — v1.0 (existing)
- ✓ React frontend (workspace + chat interface) — v1.0 (existing)
- ✓ CLI for interactive memory chat — v1.0 (existing)
- ✓ Multi-provider LLM support (Groq, Gemini, OpenRouter) — v1.0 (existing)
- ✓ Transparency layer (event bus, operation log, retrieval log, LLM usage tracking) — v1.0 (existing)

### Active

<!-- Current scope. Building toward these. -->

- [ ] MCP server that exposes MemBlocks memory to AI agents via the Model Context Protocol
- [ ] CLI commands to set, view, and switch the active memory block for the MCP server
- [ ] store_semantic: accept plain text, run LLM extraction (PS1) + PS2 conflict resolution
- [ ] store_to_core: accept plain text, wrap as message, run LLM core memory update
- [ ] store: combined store to both core and semantic
- [ ] retrieve_semantic: query semantic memory from active block
- [ ] retrieve_core: retrieve full core memory from active block
- [ ] retrieve: query both core and semantic, return combined context
- [ ] memblocks_list_blocks: MCP tool to list user's blocks
- [ ] memblocks_create_block: MCP tool to create a new block
- [ ] MCP resources exposing tool usage documentation to connected agents

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Session / memory window / recursive summary in MCP context — agents pass only important facts, not full conversations; no session pipeline needed
- OAuth / multi-user MCP — single configured user per MCP server instance; simplicity first
- HTTP transport for MCP — stdio is sufficient for local AI agent clients (Claude Desktop, etc.)
- Resource memory (documents/PDFs) in MCP tools — resource memory is a stub in the library; deferred

## Context

- **Existing library**: `memblocks_lib/src/memblocks/` — full Python library with `MemBlocksClient` as the single entry point
- **Existing CLI**: `backend/src/cli/main.py` — interactive chat loop using the library; demonstrates how to initialize client, select blocks, and run the memory pipeline
- **Key services**: `SemanticMemoryService.extract_and_store()` and `CoreMemoryService.update()` are the core store paths
- **Key gap**: Current `extract()` and `update()` expect `List[Dict[str, str]]` (role/content messages); MCP will wrap plain text as `[{"role": "user", "content": text}]`
- **Active block state**: Shared JSON state file on disk; CLI writes it, MCP server reads it per request
- **Stack**: Python, FastMCP (MCP Python SDK), stdio transport

## Constraints

- **Tech stack**: Python — must use the existing `memblocks` library; no new language runtimes
- **MCP framework**: FastMCP (Python MCP SDK) — standard, well-documented, compatible with all major MCP clients
- **Single user**: MCP server is single-user; user_id configured via env var or config
- **No session pipeline**: MCP tools bypass session/memory_window/MemoryPipeline.run() entirely

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Plain text input wrapped as `[{"role": "user", "content": text}]` | Minimal change to existing LLM pipelines; extract() and update() already handle single-message inputs | — Pending |
| Shared state file for active block | Simple, robust, no IPC complexity; CLI and MCP server are separate processes | — Pending |
| stdio transport | Standard for local MCP integrations; works with Claude Desktop, Cursor, and most MCP clients out of the box | — Pending |
| FastMCP framework | Official Python SDK; auto-generates schemas from docstrings; minimal boilerplate | — Pending |

---
*Last updated: 2026-03-12 — Milestone v1.1 MCP Server started*
