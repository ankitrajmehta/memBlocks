# MILESTONES.md

## v1.0 — Foundation (Existing)

**Status:** Shipped (existing codebase, pre-GSD)
**Last Phase:** 0 (no GSD phases — code predates milestone tracking)

### What Shipped

- Full `memblocks` Python library with `MemBlocksClient` entry point
- Core memory service: LLM extraction, MongoDB persistence, full retrieval
- Semantic memory service: PS1 extraction, PS2 conflict resolution, hybrid vector search (dense + SPLADE), query expansion, HyDE, Cohere reranking
- Block management: create, list, get by user
- Session management: memory window, recursive summary, MemoryPipeline
- FastAPI REST backend with Clerk authentication
- React frontend (landing + workspace with chat, memory viewer, block manager, analytics)
- CLI: interactive memory chat loop
- Multi-provider LLM support: Groq, Gemini, OpenRouter
- Transparency layer: EventBus, OperationLog, RetrievalLog, ProcessingHistory, LLMUsageTracker

---

*Milestone log initialized: 2026-03-12*
