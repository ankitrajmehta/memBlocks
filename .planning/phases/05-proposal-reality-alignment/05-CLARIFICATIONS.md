# Phase 5: Clarification Guardrail Tracker

**Created:** 2026-03-19
**Phase:** 05-proposal-reality-alignment
**Linked from:** 05-ALIGNMENT-MATRIX.md

## Workflow Rules

1. **Trigger**: Any edit requiring assumptions or ambiguous interpretation must request clarification before wording is finalized.
2. **Tagging**: Each clarification item gets a unique `[CLARIFY-REQ:XXX]` tag.
3. **Linkage**: Matrix row references clarify ID via `Clarify ID` column.
4. **Fallback**: If clarification is not received in-session, original report text remains unchanged for that segment.
5. **Status Tracking**: Open → Asked In-Session → Resolved → Applied (or Fallback Applied)

---

## Open Items

### [CLARIFY-REQ:001]

**Segment:** Abstract (para 2) — "recursive memory evolution mechanism"
**Matrix Row:** #5
**Current Wording:** "A recursive memory evolution mechanism updates and refines stored knowledge while maintaining coherence and avoiding redundancy."
**Issue:** The exact scope of "evolution" needs verification against shipped implementation.
**Requested Clarification:**
- Does the shipped system implement recursive memory evolution across all memory types, or only within specific sections (Core/Episodic)?
- Is "evolution" triggered automatically, or is it capacity-threshold based?

---

### [CLARIFY-REQ:002]

**Segment:** Abstract (para 2) — "privacy-preserving multi-user collaboration"
**Matrix Row:** #6
**Current Wording:** "MemBlocks supports dynamic context switching, user-controlled memory exposure, and privacy-preserving multi-user collaboration."
**Issue:** MCP server documentation indicates single-user per instance (MEMBLOCKS_USER_ID env var). Extent of multi-user support unclear.
**Requested Clarification:**
- Is multi-user collaboration planned for shipped system, or is it future work?
- If implemented, how is privacy preserved across users?

---

### [CLARIFY-REQ:003]

**Segment:** Section 1.2 Problem Statement — "weak support for collaborative memory, where some information must be shared among users while other data remains private"
**Matrix Row:** #13
**Current Wording:** "weak support for collaborative memory, where some information must be shared among users while other data remains private"
**Issue:** MCP is single-user. Library architecture supports user_id per block. Actual multi-user implementation unclear.
**Requested Clarification:**
- Should collaborative memory mention be removed or reworded to reflect single-user MCP scope?
- Or is collaborative sharing planned for a future milestone?

---

### [CLARIFY-REQ:004]

**Segment:** Section 1.3 Objectives, Objective 6 — "support multi-user collaboration, allowing shared memory blocks while maintaining private user blocks"
**Matrix Row:** #20
**Current Wording:** "support multi-user collaboration, allowing shared memory blocks while maintaining private user blocks"
**Issue:** Extent of multi-user block sharing implementation unknown.
**Requested Clarification:**
- Is this objective fulfilled, partially fulfilled, or deferred to future work?
- If partially fulfilled, what is the current implementation boundary?

---

### [CLARIFY-REQ:005]

**Segment:** Section 3.3 System Architecture — "The Sliding Window Manager maintains immediate conversational context"
**Matrix Row:** #30
**Current Wording:** "The Sliding Window Manager maintains immediate conversational context by storing recent message exchanges. This component implements a bounded buffer that retains the last N messages..."
**Issue:** Session-based chat has sliding window. MCP context: agents pass only important facts, no session pipeline.
**Requested Clarification:**
- Should the sliding window description apply to both CLI (session-based) and MCP contexts?
- Or should it be scoped specifically to the CLI application?
- Is the MCP behavior (no session pipeline) documented anywhere that should be referenced?

---

## Asked In-Session

*(To be populated during Phase 5 execution)*

| Clarify ID | Date Asked | Response Due | Status |
|------------|------------|--------------|--------|
| — | — | — | — |

---

## Resolution Log

*(To be populated as clarifications are received)*

### [CLARIFY-REQ:001]

| Field | Value |
|-------|-------|
| **Resolved** | TBD |
| **Resolution** | — |
| **Outcome** | Applied / Fallback Applied |
| **Notes** | — |

### [CLARIFY-REQ:002]

| Field | Value |
|-------|-------|
| **Resolved** | TBD |
| **Resolution** | — |
| **Outcome** | Applied / Fallback Applied |
| **Notes** | — |

### [CLARIFY-REQ:003]

| Field | Value |
|-------|-------|
| **Resolved** | TBD |
| **Resolution** | — |
| **Outcome** | Applied / Fallback Applied |
| **Notes** | — |

### [CLARIFY-REQ:004]

| Field | Value |
|-------|-------|
| **Resolved** | TBD |
| **Resolution** | — |
| **Outcome** | Applied / Fallback Applied |
| **Notes** | — |

### [CLARIFY-REQ:005]

| Field | Value |
|-------|-------|
| **Resolved** | TBD |
| **Resolution** | — |
| **Outcome** | Applied / Fallback Applied |
| **Notes** | — |

---

## Fallback Behavior

Per Phase 5 context decisions: **if clarification is not received in-session, leave original report text unchanged for that segment and carry the clarification item as open.**

This ensures no assumption-based wording is introduced without explicit confirmation.

---

## Summary

| Category | Count |
|----------|-------|
| Total Clarifications | 5 |
| Open | 5 |
| Asked In-Session | 0 |
| Resolved (Applied) | 0 |
| Resolved (Fallback Applied) | 0 |

---

## Usage Instructions for Downstream Editing

1. Before finalizing wording for any `[CLARIFY-REQ:XXX]` tagged segment:
   - Check if clarification is resolved in this tracker
   - If Resolved: Apply clarified wording
   - If Open: Request clarification via user interaction
   - If deadline passed without response: Apply fallback (keep original wording)

2. After receiving clarification:
   - Log in Resolution Log section
   - Update matrix row status
   - Proceed with edited wording

3. At Phase 5 closeout:
   - All CLARIFY segments must have resolution status
   - Unresolved items documented as open for Phase 6/7 handling

---
*Tracker created: 2026-03-19*
*Drift rules per 05-CONTEXT.md*
