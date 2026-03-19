## Plan: Token Usage & Timing Tracking in the Transparency Layer

### Context Summary

The codebase has a clean transparency layer with 3 log types (`OperationLog`, `RetrievalLog`, `ProcessingHistory`) and a `PipelineRunEntry` model. LLM calls happen in 5 distinct call sites, all using LangChain's `chain.ainvoke()` with `include_raw=False` (meaning token metadata is discarded). Token tracking needs to be added **without** changing the LLMProvider interface or services' call patterns.

The key design question is: **where do we intercept LLM calls to capture token usage?**

---

### Design Decision: Interception via LLMProvider Wrapper

Rather than modifying each call site (messy, repeated code), the cleanest approach is to change `include_raw=True` in each provider's `create_structured_chain()` and wrap the chain to extract token metadata before returning the parsed result. The providers then call a shared `LLMUsageTracker` after each invocation.

Each provider gets a reference to a `LLMUsageTracker` (a new class), which collects stats per-task-type and per-block.

---

### New Data Model: `LLMCallRecord` & `LLMUsageSummary`

**In `models/transparency.py`**, add:

```python
class LLMCallType(str, Enum):
    PS1_EXTRACTION     = "ps1_extraction"
    PS2_CONFLICT       = "ps2_conflict"
    RETRIEVAL          = "retrieval"          # query expansion + HyDE
    CORE_MEMORY        = "core_memory"
    SUMMARY            = "summary"
    CONVERSATION       = "conversation"

class LLMCallRecord(BaseModel):
    """A single recorded LLM API call with usage statistics."""
    timestamp: datetime
    call_type: LLMCallType
    block_id: Optional[str]           # which block this call was for
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: float                 # wall-clock ms for the call
    success: bool
    error: Optional[str] = None

class LLMUsageSummary(BaseModel):
    """Aggregated stats per call type."""
    call_type: LLMCallType
    request_count: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_latency_ms: float
    avg_latency_ms: float
```

**In `models/block.py`**, add a `llm_usage` field to `MemoryBlockMetaData`:

```python
llm_usage: Dict[str, Any] = Field(
    default_factory=dict,
    description="Aggregated LLM token usage and timing per call type for this block."
)
```

This stores a snapshot of `LLMUsageSummary` per call type, updated after each pipeline run.

---

### New Service: `LLMUsageTracker` in `services/transparency.py`

A new thread-safe class alongside the existing 4:

```python
class LLMUsageTracker:
    """Thread-safe tracker for LLM call counts, token usage, and latency.
    
    Tracks across all call types globally (since a client may serve multiple blocks),
    and also maintains per-block aggregates.
    """
    
    def record(self, record: LLMCallRecord) -> None: ...
    
    def get_records(self, 
                    call_type: Optional[LLMCallType] = None,
                    block_id: Optional[str] = None,
                    limit: int = 100) -> List[LLMCallRecord]: ...
    
    def get_summary(self) -> Dict[LLMCallType, LLMUsageSummary]: ...
    
    def get_block_summary(self, block_id: str) -> Dict[LLMCallType, LLMUsageSummary]: ...
    
    def get_totals(self) -> LLMUsageSummary: ...  # grand totals across all types
    
    def clear(self) -> None: ...
```

---

### Changes to LLM Providers

Each provider's `create_structured_chain()` will:
1. Switch to `include_raw=True` to get the raw LangChain response (with `usage_metadata`)
2. Wrap the chain in a thin async callable that times the call, extracts tokens from `raw["raw"].usage_metadata`, records the `LLMCallRecord`, then returns the parsed result

Each provider needs two new constructor params:
- `usage_tracker: Optional[LLMUsageTracker]`
- `call_type: Optional[LLMCallType]`  ← set at construction time by `_build_provider` in `client.py`

The `chat()` method similarly wraps `llm.ainvoke()` with timing + token extraction.

---

### Changes to `client.py`

```python
self.llm_usage: LLMUsageTracker = LLMUsageTracker()

# Pass tracker + call_type when building providers:
_ps1_llm = _build_provider(llm_settings.for_task("ps1_semantic_extraction"), config,
                            usage_tracker=self.llm_usage, call_type=LLMCallType.PS1_EXTRACTION)
_ps2_llm = _build_provider(llm_settings.for_task("ps2_conflict_resolution"), config,
                            usage_tracker=self.llm_usage, call_type=LLMCallType.PS2_CONFLICT)
# ... etc
```

Add a `get_llm_usage()` convenience method.

---

### Block-level Storage

**Option A (per-run snapshot in `PipelineRunEntry`)**: Extend `PipelineRunEntry` with a `llm_usage: Dict[str, LLMUsageSummary]` field populated at pipeline completion. This requires the pipeline to query the tracker for records since the run started and summarize them.

**Option B (persisted in MongoDB block doc)**: After each pipeline run completes, update the block's MongoDB document with cumulative per-block token usage. The `MemoryBlockMetaData.llm_usage` field holds this.

**Recommendation: Both.** Option A captures per-run details in the in-memory transparency log. Option B persists cumulative totals alongside the block in MongoDB so they survive restarts.

---

### Files to Modify

| File | Change |
|---|---|
| `models/transparency.py` | Add `LLMCallType`, `LLMCallRecord`, `LLMUsageSummary` |
| `models/block.py` | Add `llm_usage: Dict` to `MemoryBlockMetaData` |
| `services/transparency.py` | Add `LLMUsageTracker` class |
| `llm/base.py` | No change to interface; add optional `usage_tracker` + `call_type` convention in docstring |
| `llm/groq_provider.py` | Accept `usage_tracker`, `call_type`, `block_id_getter`; wrap chain + chat with timing/token capture |
| `llm/gemini_provider.py` | Same as Groq |
| `llm/openrouter_provider.py` | Same as Groq |
| `client.py` | Instantiate `LLMUsageTracker`, pass to `_build_provider`; add `get_llm_usage()` |
| `services/memory_pipeline.py` | After pipeline completes, store per-run usage snapshot in `PipelineRunEntry` |
| `storage/mongo.py` | Add `update_block_llm_usage(block_id, usage_dict)` method |
| `services/block.py` / `block_manager.py` | After pipeline run, call `update_block_llm_usage` to persist totals |

---

### Token Extraction Details (per provider)

LangChain's `include_raw=True` returns `{"raw": AIMessage, "parsed": <PydanticObj>}`.  
`AIMessage.usage_metadata` has `{"input_tokens": int, "output_tokens": int, "total_tokens": int}`.  
This works for Groq, Gemini, and OpenRouter (all via LangChain).

For `chat()`, the `response` is already an `AIMessage` — so `response.usage_metadata` is available directly today.

---

### Questions for you before I proceed:

1. **Block-level persistence**: Should the `llm_usage` be stored in MongoDB (persisted across restarts, viewable via the existing API), or just kept in-memory in `LLMUsageTracker`? Or both as I recommended?

2. **`block_id` tracking**: The LLM providers are stateless and don't inherently know which block a call is for. The best way to associate a call with a block is to pass `block_id` at call time. This would require adding an optional `block_id` param to `chain.ainvoke()` calls (or a context-var approach). Which do you prefer?
   - **Option A**: Pass `block_id` as a context variable (thread-local/asyncio `contextvars`) set by the service before each call — no signature changes
   - **Option B**: Add `block_id: Optional[str]` param to the LLM call wrapper, requiring minor changes to each `ainvoke` call site in the 5 services

3. **`conversation` LLM call type**: The `chat()` calls (the main conversation turn) are made by the *user's own code*, not by the library's pipeline. Should the tracker track those too, or only the library-internal calls (PS1, PS2, retrieval, core, summary)?

4. **Backend API exposure**: Should the new `llm_usage` data be exposed via a new or existing REST endpoint in the `backend/` API?
