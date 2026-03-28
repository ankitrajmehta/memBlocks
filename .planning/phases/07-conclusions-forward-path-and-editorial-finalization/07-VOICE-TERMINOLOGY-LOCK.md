# Phase 07 Voice and Terminology Lock

This lock file defines canonical wording and narrative constraints for final report normalization.

## Canonical Terminology Glossary

| Canonical Term | Meaning / Usage Scope |
| --- | --- |
| MemBlocks | Project/system name used in narrative references |
| MemBlocksClient | Primary integration surface at library core |
| library-first architecture | Architecture framing where shared library core is central and interfaces are consumers |
| Core Memory | Persistent high-priority memory section |
| Semantic Memory | Structured extracted memory section with metadata-aware retrieval |
| Recursive Summary | Compressed continuity section for conversation state |
| supporting interface | Non-central surface (CLI, MCP, backend, frontend) consuming shared core |
| evidence-grounded validation | Validation phrasing tied to concrete artifacts and traceability |

## Prohibited Alternatives (Synonym Drift)

| Canonical Term | Prohibited Alternatives |
| --- | --- |
| MemBlocks | Memory Blocks (as primary product name), MemoryBlocks |
| library-first architecture | monolithic memory pool as final architecture, system center is MCP, MCP-centered architecture |
| MemBlocksClient | client orchestrator only, wrapper utility (when used to downplay architectural centrality) |
| Semantic Memory | Event and Factual Memory (for shipped implementation naming), event/factual section |
| supporting interface | architecture center (when referring to CLI/MCP/backend/frontend surfaces) |
| evidence-grounded validation | generic testing claims, unbounded performance claims |

## Voice Rules

1. Use a **formal technical** register in all updated sections.
2. Keep claims **evidence-grounded**; tie assertions to implemented artifacts or documented behavior.
3. Maintain **moderate assertiveness**: clear outcomes without universal or absolute claims.
4. Acknowledge boundaries succinctly where clarification-sensitive or unresolved items remain.
5. Preserve meaning with minimal-change edits; normalize wording without introducing new factual claims.

## Section Coverage Checklist

- [x] Methodology
- [x] Results
- [x] Discussion
- [x] Testing/Evaluation/Validation
- [x] Conclusion
- [x] Limitations/Future
- [x] Appendix
