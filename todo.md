# memBlocks Refactoring Todo List

## Phase 1: UV Workspace Setup ✅ COMPLETE
- [x] Task 1.1: Create `memblocks_lib` package skeleton
- [x] Task 1.2: Create `backend` package skeleton
- [x] Task 1.3: Update root `pyproject.toml` to UV workspace

## Phase 2: Move Pure Data Models ✅ COMPLETE
- [x] Task 2.1: Create `models/block.py` (from `models/container.py`)
- [x] Task 2.2: Create `models/memory.py` (from `models/sections.py`)
- [x] Task 2.3: Create `models/units.py` (from `models/units.py`)
- [x] Task 2.4: Create `models/llm_outputs.py` (from `llm/output_models.py`)
- [x] Task 2.5: Create `models/__init__.py` with re-exports

## Phase 3: Move Prompts ✅ COMPLETE
- [x] Task 3.1: Create `prompts/__init__.py` (from `prompts.py`)

## Phase 4: Create Config Module ✅ COMPLETE
- [x] Task 4.1: Create `config.py` (MemBlocksConfig)

## Phase 5: Refactor Storage Adapters ✅ COMPLETE
- [x] Task 5.1: Create `storage/embeddings.py`
- [x] Task 5.2: Create `storage/mongo.py`
- [x] Task 5.3: Create `storage/qdrant.py`
- [x] Task 5.4: Create `storage/__init__.py`

## Phase 6: Create Abstract LLM Interface + Groq Implementation ✅ COMPLETE
- [x] Task 6.1: Create `llm/base.py` — LLMProvider ABC
- [x] Task 6.2: Create `llm/groq_provider.py`
- [x] Task 6.3: Create `llm/__init__.py`

## Phase 7: Extract Services from Models ✅ COMPLETE
- [x] Task 7.1: Create `services/semantic_memory.py` (SemanticMemoryService)
- [x] Task 7.2: Create `services/core_memory.py` (CoreMemoryService)
- [x] Task 7.3: Create `services/memory_pipeline.py` (MemoryPipeline) — Bug Fix 4: `pass` stub fully implemented
- [x] Task 7.4: Create `services/chat_engine.py` (ChatEngine)
- [x] Task 7.5: Create `services/block_manager.py` (BlockManager)
- [x] Task 7.6: Create `services/user_manager.py` (UserManager)
- [x] Task 7.7: Create `services/session_manager.py` (SessionManager — now persists to MongoDB)
- [x] Task 7.8: Create `services/__init__.py`
- [x] Task 7.9: Create `services/transparency.py` (OperationLog, RetrievalLog, ProcessingHistory, EventBus — Phase-9 stubs)

## Phase 8: Build MemBlocksClient ⏳ NEXT
- [ ] Task 8.1: Create `client.py`
- [ ] Task 8.2: Update `__init__.py` with public exports

## Phase 9: Add Transparency & Observability Layer
- [ ] Task 9.1: Create transparency models (`models/transparency.py`)
- [ ] Task 9.2: Implement log classes in `services/transparency.py` (replace stubs)
- [ ] Task 9.3: Wire transparency into storage adapters and services
- [ ] Task 9.4: Wire EventBus into MemBlocksClient

## Phase 10: Restructure Backend
- [ ] Task 10.1: Create `backend/src/api/dependencies.py`
- [ ] Task 10.2: Update `backend/src/api/main.py`
- [ ] Task 10.3: Update all routers
- [ ] Task 10.4: Move API request models

## Phase 11: Move CLI to Backend
- [ ] Task 11.1: Create `backend/src/cli/main.py`
- [ ] Task 11.2: Add CLI entry point to `backend/pyproject.toml`

## Phase 12: Cleanup & Final Verification
- [ ] Task 12.1: Remove old root-level source files
- [ ] Task 12.2: Update root `pyproject.toml`
- [ ] Task 12.3: Run full import verification
- [ ] Task 12.4: Run end-to-end integration test
- [ ] Task 12.5: Verify frontend still works
- [ ] Task 12.6: Remove `services/background_utils.py`
- [ ] Task 12.7: Migrate existing MongoDB data

---

## Notes
- Estimated Total Phases: 13
- Estimated Total Tasks: ~45
- Pre-requisites: All infrastructure services running (`docker-compose up -d`)
- LSP errors (pydantic, pydantic-settings "could not be resolved") are **false positives** — LSP not configured for the new venv. All imports verified working via `uv run python`.
