---
phase: 03
slug: retrieve-tools
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (via memblocks_lib) |
| **Config file** | none — Wave 0 installs in mcp_server/tests |
| **Quick run command** | `pytest mcp_server/tests/ -x -q` |
| **Full suite command** | `pytest mcp_server/tests/ -v` |
| **Estimated runtime** | ~30-60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest mcp_server/tests/ -x -q`
- **After every plan wave:** Run `pytest mcp_server/tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | RETR-01 | integration | `pytest mcp_server/tests/ -x -q` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | RETR-02 | integration | `pytest mcp_server/tests/ -x -q` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | RETR-03 | integration | `pytest mcp_server/tests/ -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `mcp_server/tests/test_retrieve_tools.py` — integration tests for all three retrieve tools
- [ ] `mcp_server/tests/conftest.py` — shared fixtures (MemBlocksClient mock, active block setup)
- [ ] `pytest` install — ensure pytest is available in mcp_server environment

*Note: Retrieval tools require live MongoDB and Qdrant instances. Consider testcontainers or mock-based tests for tool wrapper logic.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Verify formatted output for LLM injection | RETR-01 | Requires live LLM to validate format quality | Run tool, inspect returned string format matches `to_prompt_string()` template |

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

