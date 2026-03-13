---
status: testing
phase: phase-2
source: phase-2-01-SUMMARY.md, phase-2-02-SUMMARY.md
started: 2026-03-13T10:35:00Z
updated: 2026-03-13T10:40:00Z
---

## Current Test

number: 5
name: [testing complete]
expected: |
awaiting: 

## Tests

### 1. Store to Semantic Memory
expected: Run memblocks_store_semantic with plain text (e.g., "I love coding in Python"). Tool should extract facts using PS1, resolve any conflicts with PS2, and store to semantic memory. Returns JSON with success message and semantic fact count.
result: issue
reported: "Returns count: 0 and empty operations array. Facts not being stored."
severity: blocker

### 2. Store to Core Memory
expected: Run memblocks_store_to_core with plain text (e.g., "My name is John and I prefer dark mode"). Tool should use LLM to extract relevant core memories, merge with existing core memory, and save updated core. Returns JSON with success message, persona preview, and human preview.
result: issue
reported: "Returns empty persona_preview and human_preview. Core memory not being updated."
severity: blocker

### 3. Combined Store (Both Memories)
expected: Run memblocks_store with plain text. Tool should store to both semantic AND core memory in sequence. Returns combined JSON result showing success from both operations.
result: issue
reported: "Both semantic (count: 0) and core (empty previews) return empty results."
severity: blocker

### 4. Active Block Validation
expected: Run any store tool WITHOUT an active block set. Tool should return error indicating no active block is set.
result: issue
reported: "Tool executes without active block and returns success message with empty data instead of error."
severity: major

## Summary

total: 4
passed: 0
issues: 4
pending: 0
skipped: 0

## Gaps

- truth: "Store to semantic memory extracts and stores facts, returns count > 0"
  status: failed
  reason: "User reported: Returns count: 0 and empty operations array. Facts not being stored."
  severity: blocker
  test: 1
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "Store to core memory updates and returns previews"
  status: failed
  reason: "User reported: Returns empty persona_preview and human_preview. Core memory not being updated."
  severity: blocker
  test: 2
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "Combined store stores to both memories and returns combined results"
  status: failed
  reason: "User reported: Both semantic (count: 0) and core (empty previews) return empty results."
  severity: blocker
  test: 3
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

- truth: "Store tools validate active block before processing"
  status: failed
  reason: "User reported: Tool executes without active block and returns success message with empty data instead of error."
  severity: major
  test: 4
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
