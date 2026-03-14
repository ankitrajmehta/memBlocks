---
phase: 2
slug: store-tools
status: planned
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-13
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (inherited from memblocks_lib) |
| **Config file** | pyproject.toml (root) |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | STOR-01 | integration | `pytest tests/ -x -q -k "store_semantic"` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | STOR-02 | integration | `pytest tests/ -x -q -k "store_core"` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 2 | STOR-03 | integration | `pytest tests/ -x -q -k "store_combined"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_store_tools.py` — integration tests for all three store tools
- [ ] `tests/conftest.py` — shared fixtures (may reuse from existing tests)

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Verify fact appears in vector search results | STOR-01 | Requires live Qdrant instance | Run store tool, then query vector DB for the fact |
| Verify core memory updated | STOR-02 | Requires live MongoDB instance | Run store tool, then retrieve core memory |

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
