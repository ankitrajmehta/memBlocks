---
phase: 4
slug: cli-resources
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (via mcp_server/tests) |
| **Config file** | none — Wave 0 creates mcp_server/tests/test_cli_resources.py |
| **Quick run command** | `pytest mcp_server/tests/test_cli_resources.py -x -q` |
| **Full suite command** | `pytest mcp_server/tests/ -v` |
| **Estimated runtime** | ~10-20 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest mcp_server/tests/test_cli_resources.py -x -q`
- **After every plan wave:** Run `pytest mcp_server/tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 0 | CLI-01, CLI-02 | unit | `pytest mcp_server/tests/test_cli_resources.py -x -q` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | CLI-01, CLI-02 | unit | `pytest mcp_server/tests/test_cli_resources.py -x -q -k "cli or set_block or get_block"` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 1 | RES-01 | unit | `python -c "from mcp_server.server import mcp; import asyncio; rs=asyncio.run(mcp.list_resources()); assert 'memblocks://active-block' in [str(r.uri) for r in rs]"` | ✅ | ⬜ pending |
| 04-02-02 | 02 | 1 | RES-02 | unit | `python -c "from mcp_server.server import mcp; import asyncio; rs=asyncio.run(mcp.list_resources()); uris=[str(r.uri) for r in rs]; assert 'memblocks://tools' in uris"` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `mcp_server/tests/test_cli_resources.py` — stubs for CLI-01, CLI-02, RES-01, RES-02 (created by Plan 04-01 Task 1)
- [ ] `mcp_server/tests/conftest.py` — shared fixtures with `tmp_state_file` monkeypatch (if not existing)

*Wave 0 task is Plan 04-01 Task 1 ("Wave 0 — Test scaffold for Phase 4"). Must run before Task 2 within Plan 04-01.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `memblocks set-block <id>` writes state and MCP reads it | CLI-01 | Requires live MCP server + real block ID | Run `memblocks set-block <id>`, then call `memblocks_list_blocks` and verify `is_active: true` for that block |
| `memblocks get-block` shows correct name+ID | CLI-02 | Requires real state file on disk | Run `memblocks set-block <id>` then `memblocks get-block`, verify output matches |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
