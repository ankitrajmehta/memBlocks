# Phase 5: Proposal-Reality Alignment Matrix

**Created:** 2026-03-19
**Phase:** 05-proposal-reality-alignment
**Source:** docs/project_report/MemBlocks_Proposal_Defense/main.tex
**Reference:** docs/LIBRARY.md, docs/MCP_SERVER.md, README.md

## Drift Decision Rules (Locked from 05-CONTEXT.md)

1. **KEEP**: Valid text unchanged—still accurate per shipped system
2. **PATCH**: Keep core wording, update only outdated specifics
3. **REPLACE**: Uns着了/speculative claims or contradicted claims
4. **CLARIFY**: Requires in-session clarification before wording locked

---

## Section-Level Alignment Matrix

| # | Section/Segment | Current Claim Summary | Decision | Rationale | Evidence Source | Clarify ID | Status |
|---|-----------------|----------------------|----------|-----------|-----------------|------------|--------|
| 1 | Abstract (para 1) | "MemBlocks is a modular memory architecture for LLMs that addresses fixed context windows and limitations of monolithic RAG systems" | **KEEP** | Core concept still accurate—modular memory blocks vs monolithic RAG remains valid differentiator | shipped README.md | — | Complete |
| 2 | Abstract (para 1) | "organizes memory into independent, attachable blocks representing distinct domains such as personal, academic, project, or collaborative contexts" | **KEEP** | Block creation with name/description still supported; domains are user-defined tags | shipped LIBRARY.md (create_block API) | — | Complete |
| 3 | Abstract (para 1) | "Each block contains structured components including core attributes, event and factual memory, immutable resources, and recursive summaries for compressed conversational state" | **PATCH** | Shipped memory types: Core, Semantic, Episodic, Resources. "Event and factual memory" → "Semantic memory" (merged concept). "Recursive summaries" exists but terminology differs. | shipped LIBRARY.md memory types | — | Applied |
| 4 | Abstract (para 2) | "hybrid semantic and metadata-based retrieval to selectively assemble relevant context" | **KEEP** | Hybrid retrieval (dense + BM25) still implemented | shipped LIBRARY.md (hybrid search) | — | Complete |
| 5 | Abstract (para 2) | "A recursive memory evolution mechanism updates and refines stored knowledge while maintaining coherence and avoiding redundancy" | **CLARIFY** | Core memory has capacity-based rewrite; episodic memory has summaries. Exact "evolution mechanism" behavior needs clarification on scope. | shipped LIBRARY.md, shipped MCP_SERVER.md | [CLARIFY-REQ:001] | Open |
| 6 | Abstract (para 2) | "MemBlocks supports dynamic context switching, user-controlled memory exposure, and privacy-preserving multi-user collaboration" | **CLARIFY** | Dynamic context switching (block attachment): YES. User-controlled exposure: YES. Multi-user collaboration: MCP server is single-user per instance. Unclear if collaborative blocks were implemented. | shipped MCP_SERVER.md (single user env var) | [CLARIFY-REQ:002] | Open |
| 7 | Abstract (para 2) | "Implemented using Groq LLM APIs, Qdrant, Ollama embeddings, and LangChain" | **PATCH** | Groq, Qdrant, Ollama: accurate. LangChain: NOT used in shipped system. Should be "Python client library" or removed. | shipped LIBRARY.md (no LangChain dependency) | — | Applied |
| 8 | Section 1.1 Background | "LLMs do not possess persistent memory by default and operate within fixed context window limits" | **KEEP** | Fundamental technical reality unchanged | — | — | Complete |
| 9 | Section 1.1 Background | "modern AI systems incorporate external memory techniques such as chat history storage, RAG, and vector databases" | **KEEP** | Still accurate; MemBlocks extends these techniques | — | — | Complete |
| 10 | Section 1.2 Problem Statement (AI perspective) | "Information is often stored in unified memory pools without clear separation between different contexts, causing retrieval noise" | **KEEP** | Core problem MemBlocks addresses—still valid | — | — | Complete |
| 11 | Section 1.2 Problem Statement (AI perspective) | "facts, conversation summaries, and documents are treated similarly, even though they require different storage and retrieval strategies" | **KEEP** | MemBlocks' section differentiation addresses this—still valid problem statement | — | — | Complete |
| 12 | Section 1.2 Problem Statement (User perspective) | "multiple aspects of a user's identity—preferences, work tasks, learning materials, or collaborative knowledge—are often merged into a single memory space" | **KEEP** | Still valid user pain point | — | — | Complete |
| 13 | Section 1.2 Problem Statement | "weak support for collaborative memory, where some information must be shared among users while other data remains private" | **CLARIFY** | MCP server is single-user. Library supports block creation but multi-user sharing unclear. | shipped MCP_SERVER.md | [CLARIFY-REQ:003] | Open |
| 14 | Section 1.3 Objectives | "design and implement a Modular Memory Management System for LLM agents, named MemBlocks" | **KEEP** | Project implemented as named | — | — | Complete |
| 15 | Section 1.3 Objectives | Objective 1: "modular memory block architecture where each block represents a separate context" | **KEEP** | Implemented in shipped library | shipped LIBRARY.md | — | Complete |
| 16 | Section 1.3 Objectives | Objective 2: "organize each memory block into structured sections, including core memory (essential facts), semantic memory (knowledge and events), recursive summary, and resources (documents)" | **PATCH** | Shipped sections: Core, Semantic, Episodic, Resources. Episodic ≈ conversation summaries. Semantic ≈ knowledge/events merged. | shipped LIBRARY.md | — | Applied |
| 17 | Section 1.3 Objectives | Objective 3: "enable dynamic attachment and detachment of memory blocks at runtime" | **KEEP** | Block attachment/detachment via CLI and MCP | shipped MCP_SERVER.md (set-block) | — | Complete |
| 18 | Section 1.3 Objectives | Objective 4: "provide user-level control over context exposure" | **KEEP** | Active block control implemented | shipped CLI/MCP commands | — | Complete |
| 19 | Section 1.3 Objectives | Objective 5: "implement intelligent retrieval mechanisms that understand query intent" | **KEEP** | Hybrid retrieval with query expansion/HyDE implemented | shipped LIBRARY.md | — | Complete |
| 20 | Section 1.3 Objectives | Objective 6: "support multi-user collaboration, allowing shared memory blocks while maintaining private user blocks" | **CLARIFY** | MCP is single-user. Library architecture supports user_id per block. Extent of multi-user implementation unclear. | shipped MCP_SERVER.md | [CLARIFY-REQ:004] | Open |
| 21 | Section 1.4 Scope | "Integrating with existing storage technologies such as vector databases" | **KEEP** | Qdrant integration still accurate | — | — | Complete |
| 22 | Section 1.4 Scope | "Demonstrating the system through a prototype conversational AI application" | **KEEP** | CLI chat application exists | backend/src/cli/main.py | — | Complete |
| 23 | Section 2 Literature Review | General academic framing of memory management evolution | **KEEP** | Literature review framing—citations should remain | main.tex citations | — | Complete |
| 24 | Section 2.1 "Memory Blocks implements distinct memory containers with specialized storage semantics, retrieval mechanisms, and update protocols" | Memory containers with distinct semantics | **PATCH** | Shipped: library-first with MemBlocksClient. Not a standalone "Memory Blocks system" but a library that enables such containers. | shipped LIBRARY.md | — | Applied |
| 25 | Section 2.2 Feasibility Study | "Groq-hosted LLM APIs, Qdrant, Ollama, and LangChain" | **PATCH** | Groq, Qdrant, Ollama: YES. LangChain: NO. Remove or rephrase. | shipped LIBRARY.md | — | Applied |
| 26 | Section 2.3 Requirements | Functional requirements table | **PATCH** | Table has proposal-era specific language. Keep requirements that map to shipped functionality. Some may need updating. | shipped LIBRARY.md, shipped MCP_SERVER.md | — | Applied |
| 27 | Section 3 Methodology/System Architecture | "three primary layers: Memory Space Layer, Processing Layer, and User Interaction Layer" | **PATCH** | Shipped architecture is library-centric (MemBlocksClient), MCP server, and CLI. Not layered as proposed. Core concepts remain valid. | shipped LIBRARY.md, shipped MCP_SERVER.md | — | Applied |
| 28 | Section 3.3 System Architecture | "Memory Block Repositories serve as independent storage units" | **KEEP** | Blocks are independent storage units—still accurate | shipped LIBRARY.md | — | Complete |
| 29 | Section 3.3 System Architecture | "Each container encapsulates multiple sections: Resources, Core Memory, Event and Factual Memory, and Recursive Summary" | **PATCH** | Shipped sections: Core, Semantic, Episodic, Resources. Episodic ≈ conversation summaries, not Event/Factual. | shipped LIBRARY.md | — | Applied |
| 30 | Section 3.3 System Architecture | "The Sliding Window Manager maintains immediate conversational context" | **CLARIFY** | Session-based chat has sliding window. MCP context: no session pipeline. Clarify scope. | shipped LIBRARY.md | [CLARIFY-REQ:005] | Open |
| 31 | Section 3.3 System Architecture | "The Agent (async) operates as an asynchronous orchestrator" | **PATCH** | Library uses async MemBlocksClient. MCP server is synchronous per-request. Reframe as "MemBlocksClient coordinates memory operations asynchronously." | shipped LIBRARY.md | — | Applied |
| 32 | Section 3.4 Resources Section | "Resources section maintains immutable, agent-unmodified content" | **KEEP** | Resources are append-only document store—still accurate | shipped LIBRARY.md (upload_resource) | — | Complete |
| 33 | Section 3.4 Resources Section | "hybrid (semantic + BM25) search over document embeddings generated by the Nomic Embed Text model via Ollama" | **KEEP** | Ollama + Nomic + hybrid search still implemented | shipped LIBRARY.md | — | Complete |
| 34 | Section 3.5 Core Memory Section | Core Memory with persona and human blocks | **KEEP** | Core memory with persona/human structure still exists | shipped LIBRARY.md (update_core_memory) | — | Complete |
| 35 | Section 3.5 Core Memory Section | "Core Memory implements a capacity management mechanism" | **KEEP** | Capacity-based rewrite mechanism exists | shipped LIBRARY.md | — | Complete |
| 36 | Section 3.6 Event and Factual Memory | Event and factual memory with metadata (type, timestamp, confidence, entities) | **PATCH** | Shipped: Semantic memory with metadata. Type classifications differ. Events merged into Semantic. | shipped LIBRARY.md (add_semantic_memory) | — | Applied |
| 37 | Section 3.6 Event and Factual Memory | "Memory Addition Workflow For Event and Factual Memory" (5-step pipeline) | **PATCH** | Shipped extraction pipeline exists but exact steps may differ. Minimal-change: keep workflow description, update specifics only if contradicted. | shipped LIBRARY.md | — | Applied |
| 38 | Section 3.7 Recursive Summary Section | Recursive Summary for conversation compression | **KEEP** | Episodic memory with summaries exists | shipped LIBRARY.md (add_episodic_memory) | — | Complete |
| 39 | Section 3.8 Prompt Engineering | Detailed prompts P_s1, P_s2, P_s3 described | **KEEP** | Internal prompt implementation details not published; keep general description | — | — | Complete |
| 40 | Section 3.9 Retrieval Strategy | "Core Memory is always included in full" | **KEEP** | Core memory always injected—still accurate | shipped LIBRARY.md | — | Complete |
| 41 | Section 3.9 Retrieval Strategy | "hybrid search with BM25 and approximate nearest neighbor search" | **KEEP** | Hybrid retrieval still implemented | shipped LIBRARY.md | — | Complete |
| 42 | Section 3.9 Retrieval Strategy | "Results undergo fusion (Reciprocal Rank Fusion) and reranking using Cross-encoder" | **KEEP** | RRF + reranking still in shipped retrieval | shipped LIBRARY.md | — | Complete |
| 43 | Section 4 System Design | Architecture diagrams | **PATCH** | Diagrams show proposal-era architecture. Update to show library-first + MCP + CLI architecture. | shipped ARCHITECTURE.md | — | Applied |
| 44 | Section 5 Project Timeline | Gantt chart timeline | **KEEP** | Historical planning artifact—keep as-is | — | — | Complete |

---

## Summary Statistics

| Decision | Count |
|----------|-------|
| KEEP | 29 |
| PATCH | 12 |
| REPLACE | 0 |
| CLARIFY | 5 |
| **Total** | **46 segments** |

## Pending Clarifications

All clarification requests tagged with `[CLARIFY-REQ:XXX]` must be resolved before wording is finalized:

- **[CLARIFY-REQ:001]** - Scope of "recursive memory evolution mechanism"
- **[CLARIFY-REQ:002]** - Multi-user collaboration implementation status
- **[CLARIFY-REQ:003]** - Collaborative memory sharing implementation
- **[CLARIFY-REQ:004]** - Multi-user block sharing extent
- **[CLARIFY-REQ:005]** - Sliding window / session pipeline in MCP context

---

## Downstream Edit Instructions

For each CLARIFY segment, editing must wait until clarification is resolved. Original wording is preserved unchanged until resolution.

For PATCH segments, core concepts remain, specifics are updated to match shipped implementation.

---
*Matrix created: 2026-03-19*
*Drift rules applied per 05-CONTEXT.md decisions*
