# Codebase Concerns

**Analysis Date:** 2026-03-12

## Tech Debt

**Hardcoded LLM Model Names in Backend Config:**
- Issue: Model names are hardcoded in `backend/src/api/dependencies.py` instead of reading from environment variables
- Files: `backend/src/api/dependencies.py` (lines 11-36)
- Impact: Developers must edit code to change models; deployments may use unexpected models
- Fix approach: Read model/temperature settings from environment variables or config file

**Deprecated Code Still Present:**
- Issue: Old code in `deprecated/` folder includes `main.py`, `vector_db_old/`, and `models_old/` directories
- Files: `deprecated/main.py`, `deprecated/vector_db_old/`, `deprecated/models_old/`
- Impact: Confusion about which code is active; potential import errors if deprecated paths are accidentally used
- Fix approach: Remove deprecated folder entirely or clearly mark as deleted

**TODO Not Addressed:**
- Issue: `#TODO make needed processes BG thread, and remove this function` found in deprecated code
- Files: `deprecated/main.py` (line 83)
- Impact: Low - code is already deprecated
- Fix approach: No action needed if deprecated folder is removed

## Known Bugs

**Silent Error Handling in Storage Layer:**
- Issue: All exceptions in Qdrant adapter return empty lists `[]` instead of propagating errors
- Files: `memblocks_lib/src/memblocks/storage/qdrant.py` (lines 283, 328, 381, 409, 441, 524)
- Symptoms: Retrieval operations fail silently; callers receive empty results without knowing if the error was "no results" or "database unavailable"
- Trigger: Any Qdrant connection error or query failure
- Workaround: Check logs for error messages; implement retry logic

**Silent Error Handling in MongoDB Adapter:**
- Issue: Similar pattern - returns `None` or `[]` on exceptions
- Files: `memblocks_lib/src/memblocks/storage/mongo.py` (lines 79, 284, 440)
- Trigger: MongoDB connection issues
- Workaround: Monitor logs

## Security Considerations

**Hardcoded Model Names with Placeholder Values:**
- Risk: `openai/gpt-oss-20b` and `openai/gpt-oss-120b` appear to be placeholder/fake model names
- Files: `backend/src/api/dependencies.py` (lines 17, 22, 29, 33)
- Current mitigation: None - these will fail at runtime if Groq doesn't recognize them
- Recommendations: Replace with actual valid model names from Groq's catalog

**CORS Not Environment-Configurable:**
- Risk: CORS origins are hardcoded in FastAPI app
- Files: `backend/src/api/main.py` (line 36)
- Current mitigation: Allows only localhost development ports
- Recommendations: Make CORS origins configurable via environment variable for production deployments

**No API Key Validation at Startup:**
- Risk: Application starts without validating that required API keys are present
- Files: `backend/src/api/dependencies.py`, `memblocks_lib/src/memblocks/config.py`
- Current mitigation: Errors occur when services are actually used
- Recommendations: Add startup validation that fails fast if required keys are missing

## Performance Bottlenecks

**Multiple LLM Provider Instances Created:**
- Problem: `MemBlocksClient.__init__` creates 5 separate LLM provider instances (conversation, ps1, ps2, retrieval, core, summary)
- Files: `memblocks_lib/src/memblocks/client.py` (lines 220-258)
- Cause: Each task type gets its own provider, even if they share the same backend
- Improvement path: Implement provider pooling or lazy initialization for providers that share settings

**LRU Cache on Client Initialization:**
- Problem: `@lru_cache` in `backend/src/api/dependencies.py` holds onto the client instance indefinitely
- Files: `backend/src/api/dependencies.py` (lines 8, 40)
- Cause: Cache is never cleared; connections remain open
- Improvement path: Implement proper connection lifecycle management or use dependency injection with cleanup

## Fragile Areas

**Broad Exception Handling:**
- Files: `memblocks_lib/src/memblocks/storage/qdrant.py`, `memblocks_lib/src/memblocks/storage/mongo.py`, `memblocks_lib/src/memblocks/services/*.py`
- Why fragile: Catching `Exception` without specific handling makes debugging difficult; real errors are masked as empty results
- Safe modification: Add specific exception types; log errors before returning defaults; consider raising instead of returning empty values for critical operations

**Deprecated Directory Structure:**
- Files: `deprecated/` directory contains full copy of old implementation
- Why fragile: Import statements or relative paths might accidentally reference deprecated modules
- Safe modification: Remove deprecated folder or move to separate repository

## Scaling Limits

**MongoDB Service Disabled:**
- Current capacity: MongoDB is commented out in docker-compose.yml
- Limit: Cannot persist user data, blocks, or sessions to MongoDB - only Qdrant vector storage works
- Scaling path: Uncomment MongoDB service in `docker-compose.yml` and configure connection

**Single Qdrant Connection:**
- Current capacity: One QdrantClient instance per adapter
- Limit: No connection pooling for high-throughput scenarios
- Scaling path: Implement connection pooling or use Qdrant's built-in replication features

## Dependencies at Risk

**FastAPI/Uvicorn:**
- Risk: No version pins in `pyproject.toml` visible
- Impact: Breaking changes in new versions could break the API
- Migration plan: Add version constraints to dependencies

## Missing Critical Features

**Missing Test Coverage:**
- Problem: Only 2 test files exist (`tests/test_hybrid.py`, `memblocks_lib/test_cohere_reranker.py`)
- Blocks: Cannot verify correctness of core functionality; regression detection impossible
- Priority: High

**No Rate Limiting:**
- Problem: API endpoints have no rate limiting
- Blocks: Vulnerable to abuse; no protection against LLM API quota exhaustion
- Priority: Medium

**No Input Validation:**
- Problem: API request models may not validate all inputs (e.g., user_id, block_id formats)
- Blocks: Potential injection or malformed data issues
- Priority: Medium

## Test Coverage Gaps

**Core Services Untested:**
- What's not tested: `BlockManager`, `SessionManager`, `CoreMemoryService`, `SemanticMemoryService`
- Files: `memblocks_lib/src/memblocks/services/block_manager.py`, `session_manager.py`, `core_memory.py`, `semantic_memory.py`
- Risk: Memory extraction, conflict resolution, and summary generation are critical but untested
- Priority: High

**Storage Layer Tests:**
- What's not tested: MongoDB adapter, Qdrant adapter operations
- Files: `memblocks_lib/src/memblocks/storage/mongo.py`, `qdrant.py`
- Risk: Data persistence failures could go undetected
- Priority: High

**Integration Tests Limited:**
- What's not tested: Full pipeline from API request through memory processing to response
- Risk: End-to-end failures would only be caught in manual testing
- Priority: Medium

---

*Concerns audit: 2026-03-12*
