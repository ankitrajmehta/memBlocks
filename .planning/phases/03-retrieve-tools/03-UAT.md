---
status: complete
phase: 03-retrieve-tools
source: [03-01-SUMMARY.md]
started: 2026-03-14T00:00:00Z
updated: 2026-03-14T22:25:37Z
---

## Current Test

[testing complete]

## Tests

### 1. Combined Retrieval (memblocks_retrieve)
expected: Call memblocks_retrieve with a query string. The tool returns a formatted string containing relevant memories from BOTH core and semantic sources, ready for LLM injection. No error about missing active block.
result: pass

### 2. Core-Only Retrieval (memblocks_retrieve_core)
expected: Call memblocks_retrieve_core with NO query parameter. The tool returns a formatted string with the FULL core memory contents of the active block. Response includes persona and human sections if populated.
result: pass

### 3. Semantic-Only Retrieval (memblocks_retrieve_semantic)
expected: Call memblocks_retrieve_semantic with a query string. The tool returns a formatted string with ONLY semantically relevant memories (no core memory content) for the active block.
result: pass

### 4. Error Handling — No Active Block
expected: With no active block set, calling any retrieve tool returns a clear error message (e.g., "No active block" or similar) rather than crashing or returning garbled output.
result: pass

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
