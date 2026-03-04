# Merge Plan: `feature/embedding-retrieval-test` → `feat/query_exp_and_re-ranking`

## Background

Two branches diverged from common ancestor commit `13d7b7b` and each added independent
new capabilities:

| Branch | What it added |
|---|---|
| `feature/embedding-retrieval-test` | SPLADE sparse-vector hybrid search (dense + SPLADE via Qdrant native RRF), BM25-style keyword/entity scroll, `fastembed` integration. **Accidentally pushed to an old branch.** |
| `feat/query_exp_and_re-ranking` | Query expansion, HyDE (Hypothetical Document Embeddings), LLM-based re-ranking, `GeminiLLMProvider`, structured PS2 memory model, full logger migration, config cleanup. **The correct new branch.** |

The embedding branch **removed** the sparse/hybrid infrastructure when transitioning to the
query-expansion approach. Both features must coexist in the final merge:

- **SPLADE hybrid** (dense + sparse via Qdrant native RRF) becomes the *retrieval backend*
- **Query expansion + HyDE + LLM re-ranking** remain layered on top

**Merge target:** `feat/query_exp_and_re-ranking` (survives; the embedding branch is cherry-picked into it)

---

## Pre-Merge State Summary

### Commits unique to `feature/embedding-retrieval-test` (since `13d7b7b`)

```
57d3c15  fixed dependencies issues
03b8b48  feat: Introduce an LLM manager with centralized Pydantic config for Groq and Gemini, alongside integration tests
00d9b0e  feat: Added entity/keyword search using bm25
2bae9e8  gemini llm as an option
```

### Commits unique to `feat/query_exp_and_re-ranking` (since `13d7b7b`)

```
f3697fa  query exp and re-ranking
5a0a550  big efficiency boost in number of tokens for PS2
3a3c5d7  minor changes
4ae23d9  cli updates
e8d526e  Merge branch 'refactor/complete-rework' (x3)
3907886  Updated docs
fa8454d  switched from print statements to logger
...      (13 commits total back to common ancestor)
```

---

## Files Changed in the Diff (`feature/embedding-retrieval-test` vs `feat/query_exp_and_re-ranking`)

44 files total. Categorised by action required:

| Category | Files | Action |
|---|---|---|
| Core library — must merge | `storage/embeddings.py`, `storage/qdrant.py`, `services/semantic_memory.py`, `config.py`, `memblocks_lib/pyproject.toml` | Merge both sets of changes |
| Core library — query branch wins | `models/llm_outputs.py`, `models/units.py`, `models/transparency.py`, `prompts/__init__.py`, `services/session.py`, `services/memory_pipeline.py`, `services/block.py`, `services/block_manager.py`, `services/core_memory.py`, `services/session_manager.py`, `services/user_manager.py`, `services/transparency.py`, `client.py`, `__init__.py`, `llm/__init__.py`, `llm/groq_provider.py`, `llm/gemini_provider.py` (new), `logger/__init__.py` (new) | Already on target branch — no action |
| Tests — bring from embedding branch | `tests/test_hybrid.py`, `tests/test_llm_integration.py` | Port with minor updates |
| Docs — bring from embedding branch | `HYBRID_SEARCH_README.md` | Cherry-pick (optional, for reference) |
| Root/workspace | `pyproject.toml` (root), `uv.lock` | Re-lock after dep change |
| Backend/frontend | `backend/src/api/main.py`, `backend/src/api/routers/memory.py`, `backend/src/cli/main.py`, `frontend/` | Query branch versions are correct — no action |
| Deprecated/legacy | `deprecated/config.py`, `deprecated/llm_old/llm_manager.py`, `deprecated/vector_db_old/vector_db_manager.py` | Low priority; embedding-branch versions of llm_manager are superseded by `GeminiLLMProvider` |
| Removed from query branch (intentionally) | `.agent/workflows/run-backend.md`, `tests/test_hybrid.py` (old location `test_hybrid.py` at root), `gemini_model_list.py` | Keep deleted on target |

---

## Detailed Step-by-Step Implementation

---

### Step 1 — `memblocks_lib/pyproject.toml`

**Why:** The query branch removed `fastembed` when it dropped SPLADE support. We need it back.

**Current state on `feat/query_exp_and_re-ranking`:**
```toml
dependencies = [
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "motor>=3.0",
    "qdrant-client>=1.7",
    "langchain>=0.1",
    "langchain-groq>=0.1",
    "langchain-core>=0.1",
    "httpx>=0.25",
    "requests>=2.32",
    "openinference-instrumentation-langchain>=0.1.4",
    "arize-otel>=0.7.0",
    "langchain-google-genai>=4.2.1",
]
```

**Change:** Add `"fastembed>=0.7.4"` to the dependencies list.

**Result:**
```toml
dependencies = [
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "motor>=3.0",
    "qdrant-client>=1.7",
    "langchain>=0.1",
    "langchain-groq>=0.1",
    "langchain-core>=0.1",
    "httpx>=0.25",
    "requests>=2.32",
    "openinference-instrumentation-langchain>=0.1.4",
    "arize-otel>=0.7.0",
    "langchain-google-genai>=4.2.1",
    "fastembed>=0.7.4",
]
```

**Note:** The root `pyproject.toml` stays as-is (query branch cleaned it up correctly — no
workspace-level deps, just workspace members). Do NOT re-add `fastembed` there.

---

### Step 2 — `memblocks_lib/src/memblocks/config.py`

**Why:** The query branch removed `sparse_embeddings_model` (used by `EmbeddingProvider` to
initialise the SPLADE model). We also need a new `retrieval_enable_sparse` toggle so users
can disable SPLADE without touching code.

**Current state on `feat/query_exp_and_re-ranking`:** The `Ollama / Embeddings` section has
only `embeddings_model`. The `Memory pipeline behaviour` section has `memory_window_limit` and
`keep_last_n`. A full `Retrieval Configuration` section exists with query-expansion and
re-ranking flags.

**Changes — two additions:**

**2a.** Under `# Ollama / Embeddings`, after `embeddings_model`, add:

```python
sparse_embeddings_model: str = Field(
    "prithivida/Splade_PP_en_v1",
    validation_alias="SPARSE_EMBEDDINGS_MODEL",
    description="SPLADE model used by fastembed for sparse vector generation.",
)
```

**2b.** Under `# Retrieval Configuration`, after the last existing retrieval flag
(`retrieval_enable_reranking`), add:

```python
retrieval_enable_sparse: bool = Field(
    True,
    validation_alias="RETRIEVAL_ENABLE_SPARSE",
    description=(
        "Enable SPLADE sparse vector hybrid search (dense + sparse via Qdrant RRF). "
        "When False, falls back to pure dense vector search."
    ),
)
```

**Nothing else changes in this file.**

---

### Step 3 — `memblocks_lib/src/memblocks/storage/embeddings.py`

**Why:** The query branch removed sparse embedding support entirely. We restore it in a way that
is consistent with the query branch's code style (uses `logger`, not `print`).

**Current state on `feat/query_exp_and_re-ranking`:**
```python
import requests
from concurrent.futures import ThreadPoolExecutor
from typing import List, TYPE_CHECKING

from memblocks.logger import get_logger

if TYPE_CHECKING:
    from memblocks.config import MemBlocksConfig

logger = get_logger(__name__)
```

`__init__` only sets `self._model`, `self._base_url`, `self._endpoint`.

**Changes:**

**3a. Extend imports:**

```python
# Change:
from typing import List, TYPE_CHECKING
# To:
from typing import Any, Dict, List, TYPE_CHECKING

# Add below existing imports, before TYPE_CHECKING block:
from fastembed.sparse.sparse_text_embedding import SparseTextEmbedding
```

**3b. Extend `__init__`:**

After `self._endpoint = f"{config.ollama_base_url}/api/embeddings"`, add:

```python
# Sparse (SPLADE) embedder — initialised lazily to avoid startup cost
# when retrieval_enable_sparse is False. The actual model download
# (~200 MB) only happens on first call to embed_sparse_text().
self._sparse_model: str = config.sparse_embeddings_model
self._sparse_embedder: Optional[SparseTextEmbedding] = None
```

> **Design note:** The embedding branch initialised `SparseTextEmbedding` eagerly in
> `__init__`, which triggers a ~200 MB model download on every cold start even if sparse
> retrieval is disabled. The merged version uses lazy initialisation: the embedder is only
> created on the first sparse call. This is safer and cheaper when
> `RETRIEVAL_ENABLE_SPARSE=False`.

**3c. Add a private helper `_get_sparse_embedder()`:**

```python
def _get_sparse_embedder(self) -> SparseTextEmbedding:
    """Lazily initialise and return the SPLADE sparse embedder."""
    if self._sparse_embedder is None:
        logger.debug("Initialising SPLADE sparse embedder: %s", self._sparse_model)
        self._sparse_embedder = SparseTextEmbedding(model_name=self._sparse_model)
    return self._sparse_embedder
```

**3d. Add `embed_sparse_text()` method (after `get_dimension()`):**

```python
def embed_sparse_text(self, text: str) -> Dict[str, Any]:
    """
    Embed a single text string into a sparse vector using SPLADE via fastembed.

    Args:
        text: Text to embed.

    Returns:
        Dictionary with 'indices' (List[int]) and 'values' (List[float])
        for the sparse vector. Returns empty dicts on failure.
    """
    embedder = self._get_sparse_embedder()
    embeddings = list(embedder.embed([text]))
    if not embeddings:
        return {"indices": [], "values": []}
    sparse_obj = embeddings[0]
    return {
        "indices": sparse_obj.indices.tolist(),
        "values": sparse_obj.values.tolist(),
    }
```

**3e. Add `embed_sparse_documents()` method (after `embed_sparse_text()`):**

```python
def embed_sparse_documents(self, texts: List[str]) -> List[Dict[str, Any]]:
    """
    Embed multiple texts into sparse vectors using SPLADE via fastembed.

    fastembed handles batching natively — no ThreadPoolExecutor needed.

    Args:
        texts: List of texts to embed.

    Returns:
        List of dicts, each with 'indices' and 'values'. Same order as input.
    """
    embedder = self._get_sparse_embedder()
    embeddings = list(embedder.embed(texts))
    return [
        {
            "indices": sparse_obj.indices.tolist(),
            "values": sparse_obj.values.tolist(),
        }
        for sparse_obj in embeddings
    ]
```

**3f. Update `Optional` import** — the lazy `_sparse_embedder` field is typed
`Optional[SparseTextEmbedding]`, so `Optional` must be in the `typing` import.

Final import line:
```python
from typing import Any, Dict, List, Optional, TYPE_CHECKING
```

---

### Step 4 — `memblocks_lib/src/memblocks/storage/qdrant.py`

**Why:** The query branch removed the Qdrant sparse/hybrid infrastructure. We restore it
cleanly in the query-branch code style (uses `logger`, not `print`; uses arrow `→` in
docstrings). We also remove the incomplete `hybrid_retrieve()` stub that was added in the
query branch as a placeholder.

**Current state on `feat/query_exp_and_re-ranking`:** `qdrant.py` imports only
`Distance, Filter, PointIdsList, PointStruct, VectorParams` from `qdrant_client.models`.
`create_collection()` does NOT create a sparse vector config. `store_vector()` does NOT
accept a `sparse_vector` parameter. A placeholder `hybrid_retrieve()` stub with `pass`
exists. No `retrieve_hybrid()` or `retrieve_by_keywords_and_entities()` methods exist.

**Changes:**

**4a. Extend imports from `qdrant_client.models`:**

```python
# Change:
from qdrant_client.models import (
    Distance,
    Filter,
    PointIdsList,
    PointStruct,
    VectorParams,
)
# To:
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FusionQuery,
    MatchAny,
    PointIdsList,
    PointStruct,
    Prefetch,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)
```

**4b. Update `create_collection()`:**

Inside the `self._client.create_collection(...)` call, add `sparse_vectors_config`:

```python
self._client.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(
        size=resolved_size,
        distance=Distance.COSINE,
    ),
    sparse_vectors_config={
        "text-sparse": SparseVectorParams(),
    },
)
```

> **Important:** `"text-sparse"` is the named sparse vector slot inside Qdrant. All
> `store_vector()` calls that pass a `sparse_vector` will use the same name `"text-sparse"`.
> `retrieve_hybrid()` uses `using="text-sparse"` in the sparse prefetch. These must be
> consistent.

**4c. Update `store_vector()` signature and body:**

Add optional `sparse_vector` parameter and the conditional vector-packing logic:

```python
def store_vector(
    self,
    collection_name: str,
    vector: List[float],
    payload: Dict[str, Any],
    point_id: Optional[str] = None,
    sparse_vector: Optional[Dict[str, Any]] = None,   # <-- new
) -> bool:
    """
    Upsert a single vector into a collection.

    Args:
        collection_name: Target Qdrant collection.
        vector: Dense embedding vector.
        payload: Metadata stored alongside the vector.
        point_id: Optional explicit UUID string ID. Auto-generated if None.
        sparse_vector: Optional dict with 'indices' and 'values' for SPLADE.
                       When provided, the point is stored with both a dense
                       (unnamed default) and a sparse ('text-sparse') vector,
                       enabling hybrid RRF retrieval via retrieve_hybrid().

    Returns:
        True if successful, False otherwise.
    """
    try:
        resolved_id = point_id or str(uuid4())

        if sparse_vector:
            packed_vector = {
                "": vector,  # unnamed slot = default dense vector
                "text-sparse": SparseVector(
                    indices=sparse_vector.get("indices", []),
                    values=sparse_vector.get("values", []),
                ),
            }
        else:
            packed_vector = vector

        self._client.upsert(
            collection_name=collection_name,
            points=[
                PointStruct(
                    id=resolved_id,
                    vector=packed_vector,
                    payload=payload,
                )
            ],
            wait=False,
        )
        self._record_op(
            collection_name,
            "upsert",
            document_id=resolved_id,
            payload_summary=f"store vector in {collection_name}",
        )
        return True
    except Exception as e:
        self._record_op(
            collection_name,
            "upsert",
            success=False,
            error=str(e),
            payload_summary=f"store vector in {collection_name}",
        )
        logger.error("Error storing vector in '%s': %s", collection_name, e)
        return False
```

**4d. Add `retrieve_hybrid()` method** (after `retrieve_from_vector()`, replacing the stub):

```python
def retrieve_hybrid(
    self,
    collection_name: str,
    dense_query_vector: List[float],
    sparse_query_vector: Dict[str, Any],
    top_k: int = 5,
) -> list:
    """
    Hybrid retrieval combining dense semantic search and SPLADE sparse search
    via Qdrant's native Reciprocal Rank Fusion (RRF).

    How it works:
    1. Prefetch top_k*2 results using the dense vector (cosine similarity).
    2. Prefetch top_k*2 results using the SPLADE sparse vector.
    3. Fuse both result sets using RRF and return the top_k fused results.

    Args:
        collection_name: Source Qdrant collection.
        dense_query_vector: Dense embedding from nomic-embed-text (or similar).
        sparse_query_vector: Dict with 'indices' and 'values' from SPLADE
                             (output of EmbeddingProvider.embed_sparse_text()).
        top_k: Number of final results to return after fusion.

    Returns:
        List of ScoredPoint objects, ranked by RRF fusion score.
    """
    try:
        sparse_vec = SparseVector(
            indices=sparse_query_vector.get("indices", []),
            values=sparse_query_vector.get("values", []),
        )
        results = self._client.query_points(
            collection_name=collection_name,
            prefetch=[
                Prefetch(
                    query=dense_query_vector,
                    using="",            # unnamed slot = default dense vector
                    limit=top_k * 2,
                ),
                Prefetch(
                    query=sparse_vec,
                    using="text-sparse", # named sparse vector slot
                    limit=top_k * 2,
                ),
            ],
            query=FusionQuery(fusion="rrf"),
            limit=top_k,
        )
        return results.points
    except Exception as e:
        logger.error("Error in hybrid retrieval from '%s': %s", collection_name, e)
        return []
```

**4e. Add `retrieve_by_keywords_and_entities()` method** (after `retrieve_hybrid()`):

```python
def retrieve_by_keywords_and_entities(
    self,
    collection_name: str,
    keywords: List[str],
    entities: List[str],
    top_k: int = 10,
) -> list:
    """
    Scroll the collection for points whose payload 'keywords' or 'entities'
    arrays contain any of the supplied terms (OR / 'should' logic).

    Used as a supplementary/benchmarking path alongside vector retrieval.
    No vector computation required — pure payload filtering.

    Args:
        collection_name: Source Qdrant collection.
        keywords: Lowercased keyword strings extracted from the query.
        entities: Lowercased entity strings extracted from the query.
        top_k: Maximum number of matching points to return.

    Returns:
        List of Record objects (qdrant_client types).
    """
    if not keywords and not entities:
        return []

    try:
        should_conditions = []
        if keywords:
            should_conditions.append(
                FieldCondition(
                    key="keywords",
                    match=MatchAny(any=[k.lower() for k in keywords if k.strip()]),
                )
            )
        if entities:
            should_conditions.append(
                FieldCondition(
                    key="entities",
                    match=MatchAny(any=[e.lower() for e in entities if e.strip()]),
                )
            )

        payload_filter = Filter(should=should_conditions)
        points, _ = self._client.scroll(
            collection_name=collection_name,
            scroll_filter=payload_filter,
            limit=top_k,
            with_vectors=False,
            with_payload=True,
        )
        return points
    except Exception as e:
        logger.error(
            "Error in keyword/entity scroll on '%s': %s", collection_name, e
        )
        return []
```

**4f. Remove the stub `hybrid_retrieve()` method and inner `QueryObject` class** that exists in
the query branch. It was a placeholder (body is `pass`) and is entirely superseded by
`retrieve_hybrid()`.

The stub to remove:
```python
class QueryObject:
    query_vector: List[float]
    keywords: List[str]
    entities: List[str]

def hybrid_retrieve(self, query_objects: List[QueryObject], top_k: int = 5) -> list:
    """..."""
    # TODO: implement
    pass
```

---

### Step 5 — `memblocks_lib/src/memblocks/services/semantic_memory.py`

This is the largest and most critical change. The query branch has a clean async
pipeline; we extend it to use SPLADE in the storage and retrieval paths.

**Current state on `feat/query_exp_and_re-ranking`:**
- `store()` calls `self._qdrant.store_vector(collection, vector, payload)` — no sparse vector
- `_retrieve_with_vectors()` (private helper) calls `self._qdrant.retrieve_from_vector()` per query
- `retrieve()` is `async` and orchestrates expansion → HyDE → `_retrieve_with_vectors` → rerank

**Changes:**

**5a. Extend imports at the top of the file:**

```python
# Add to the stdlib imports (currently only `import json`):
import re
import string

# Extend typing import — add Tuple (Set is already present):
from typing import Any, Dict, List, Optional, Set, Tuple, TYPE_CHECKING
```

**5b. Update `store()` — add SPLADE sparse vector to all write paths:**

The `store()` method has 4 places where `self._qdrant.store_vector()` is called:

1. **No-similar-memories ADD** (early return path)
2. **PS2 fallback ADD** (exception handler)
3. **PS2 decision ADD** (normal path)
4. **PS2 decision UPDATE** (existing memory update)

For each, embed sparse alongside dense and pass through.

After `new_vector = self._embeddings.embed_text(text_to_embed)`, add:

```python
new_sparse_vector = (
    self._embeddings.embed_sparse_text(text_to_embed)
    if self._config.retrieval_enable_sparse
    else None
)
```

Then for every `self._qdrant.store_vector(self._collection, new_vector, payload)` call,
change to:

```python
self._qdrant.store_vector(
    self._collection, new_vector, payload, sparse_vector=new_sparse_vector
)
```

For the UPDATE path (where `updated_vector` is computed from `updated_text`), add:

```python
updated_sparse_vector = (
    self._embeddings.embed_sparse_text(updated_text)
    if self._config.retrieval_enable_sparse
    else None
)
```

And pass `sparse_vector=updated_sparse_vector` to its `store_vector()` call.

> **Why this matters:** Qdrant stores the sparse vector alongside the dense vector in the same
> point. On retrieval, `retrieve_hybrid()` can then issue a prefetch against both vector slots
> and fuse the results with RRF. Points stored without a sparse vector will simply not score in
> the sparse leg — they degrade gracefully to dense-only results.

**5c. Add `_extract_query_terms()` static method** (copy from embedding branch, unchanged):

Place this method between `extract_and_store()` and the retrieval section (before
`_expand_query()`):

```python
@staticmethod
def _extract_query_terms(query: str) -> Tuple[List[str], List[str]]:
    """
    Lightweight extraction of keywords and entity candidates from a raw
    query string using only Python stdlib (re, string).

    Strategy:
    - keywords: lowercased, punctuation-stripped tokens with stopwords removed.
    - entities: sequences of consecutive Title-Case words (named entity candidates).

    No external NLP libraries required.

    Args:
        query: Raw query text from the user.

    Returns:
        (keywords, entities) — both are lists of lowercase strings.
    """
    _STOPWORDS = {
        "a", "an", "and", "are", "as", "at", "be", "been", "but", "by",
        "did", "do", "does", "for", "from", "had", "has", "have", "he",
        "her", "him", "his", "how", "i", "if", "in", "is", "it", "its",
        "just", "me", "my", "no", "not", "of", "on", "or", "our", "she",
        "so", "that", "the", "their", "them", "then", "there", "they",
        "this", "to", "too", "up", "us", "was", "we", "what", "when",
        "where", "which", "who", "will", "with", "you", "your",
    }
    clean = query.translate(str.maketrans("", "", string.punctuation))
    tokens = clean.lower().split()
    keywords = [t for t in tokens if t and t not in _STOPWORDS and len(t) > 2]
    entity_pattern = re.compile(r"\b[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*\b")
    entities = [e.lower() for e in entity_pattern.findall(query) if len(e) > 2]
    return keywords, entities
```

**5d. Replace `_retrieve_with_vectors()` with `_retrieve_with_hybrid()`:**

The query branch has `_retrieve_with_vectors()` which calls `retrieve_from_vector()` per
query in a thread pool. We replace it (or rename it) so it uses hybrid retrieval when sparse
is enabled, falling back to dense-only when disabled.

**Remove** the existing `_retrieve_with_vectors()` method and **replace** it with:

```python
def _retrieve_with_hybrid(
    self,
    query_texts: List[str],
    top_k: int,
) -> Tuple[List[SemanticMemoryUnit], Set[str]]:
    """
    Retrieve memories for multiple query texts using hybrid (dense + SPLADE)
    or pure-dense search depending on config.retrieval_enable_sparse.

    Runs all queries in parallel via ThreadPoolExecutor, then deduplicates
    results by memory_id across all query groups.

    Args:
        query_texts: List of query strings (original + expanded + hypothetical).
        top_k: Number of results to retrieve per query.

    Returns:
        Tuple of (deduplicated_memories, set_of_seen_memory_ids).
    """
    logger.debug(
        "Retrieving with %d query variations, top_k=%d, sparse=%s",
        len(query_texts),
        top_k,
        self._config.retrieval_enable_sparse,
    )

    query_vectors = self._embeddings.embed_documents(query_texts)

    if self._config.retrieval_enable_sparse:
        query_sparse_vectors = self._embeddings.embed_sparse_documents(query_texts)

        def _hybrid_search(
            args: Tuple[List[float], Dict[str, Any]],
        ) -> List[SemanticMemoryUnit]:
            dense_vec, sparse_vec = args
            results = self._qdrant.retrieve_hybrid(
                self._collection, dense_vec, sparse_vec, top_k
            )
            memories = []
            for hit in results:
                try:
                    memories.append(
                        SemanticMemoryUnit(**hit.payload, memory_id=str(hit.id))
                    )
                except Exception:
                    pass
            return memories

        with ThreadPoolExecutor(max_workers=min(10, len(query_vectors))) as executor:
            grouped_results = list(
                executor.map(_hybrid_search, zip(query_vectors, query_sparse_vectors))
            )
    else:
        def _dense_search(dense_vec: List[float]) -> List[SemanticMemoryUnit]:
            results = self._qdrant.retrieve_from_vector(
                self._collection, dense_vec, top_k
            )
            memories = []
            for hit in results:
                try:
                    memories.append(
                        SemanticMemoryUnit(**hit.payload, memory_id=str(hit.id))
                    )
                except Exception:
                    pass
            return memories

        with ThreadPoolExecutor(max_workers=min(10, len(query_vectors))) as executor:
            grouped_results = list(executor.map(_dense_search, query_vectors))

    # De-duplicate by memory_id across all query groups
    seen_ids: Set[str] = set()
    deduplicated: List[SemanticMemoryUnit] = []
    for group in grouped_results:
        for memory in group:
            if memory.memory_id and memory.memory_id not in seen_ids:
                seen_ids.add(memory.memory_id)
                deduplicated.append(memory)

    logger.debug(
        "Hybrid retrieval: %d unique memories from %d query vectors",
        len(deduplicated),
        len(query_vectors),
    )
    return deduplicated, seen_ids
```

**5e. Update `retrieve()` to call `_retrieve_with_hybrid()` instead of `_retrieve_with_vectors()`:**

In the `retrieve()` method body, change:

```python
# Old:
retrieved_memories, seen_ids = self._retrieve_with_vectors(
    all_query_texts, top_k_per_query
)

# New:
retrieved_memories, seen_ids = self._retrieve_with_hybrid(
    all_query_texts, top_k_per_query
)
```

**5f. Update `retrieval_method` in `RetrievalEntry`:**

In the `retrieve()` transparency-logging block, make `retrieval_method` dynamic:

```python
retrieval_method=(
    "hybrid_enhanced"
    if self._config.retrieval_enable_sparse
    else "vector_enhanced"
),
```

**5g. Update the class docstring** to reflect both capabilities:

```
- Enhanced vector retrieval with SPLADE hybrid search, query expansion,
  hypothetical paragraphs, and LLM-based re-ranking
```

---

### Step 6 — Tests

**6a. `tests/test_hybrid.py`**

Bring this file from `feature/embedding-retrieval-test`. It requires two fixes for
compatibility with the query branch:

**Fix 1:** `MemoryUnitMetaData` no longer has `Parent_Memory_ids`. Remove that field from
all `MemoryUnitMetaData(...)` constructor calls in the test:

```python
# Old:
meta_data=MemoryUnitMetaData(
    usage=[], status="active", Parent_Memory_ids=[], message_ids=[]
),
# New:
meta_data=MemoryUnitMetaData(usage=[], status="active", message_ids=[]),
```

**Fix 2:** `block.retrieve()` now returns a `RetrievalResult` with `.semantic` as a
`List[SemanticMemoryUnit]`. The test already uses `context.semantic` — this is fine. No
change needed for the retrieval assertions.

**Fix 3:** Transparency log access — the test calls
`client.get_retrieval_log().get_last_retrieval()`. Verify this API still exists on the query
branch's `MemBlocksClient`. If not, update to use the correct method.

**6b. `tests/test_llm_integration.py`**

This test in the embedding branch depends on the old root-level `config.py` and
`llm/llm_manager.py` (both in `deprecated/` territory). It **does not** use the new
`memblocks_lib` structure. Do **not** port it as-is — it would be dead weight. Options:

- **Skip** — the LLM integration is already tested implicitly through `test_hybrid.py` which
  exercises the full pipeline including the LLM calls.
- **Rewrite** (future task) — write a new `tests/test_llm_providers.py` that tests
  `GroqLLMProvider` and `GeminiLLMProvider` directly using the `memblocks_lib` API.

Recommended: **skip for now**, document as a follow-up task.

---

### Step 7 — `uv.lock`

After step 1 modifies `memblocks_lib/pyproject.toml`:

```bash
uv lock
```

This regenerates `uv.lock` to include `fastembed>=0.7.4` and all its transitive
dependencies. The lock file will grow by several hundred lines (fastembed pulls in numpy,
scipy, huggingface-hub, etc.).

Run from the workspace root (where `pyproject.toml` with `[tool.uv.workspace]` lives).

---

### Step 8 — Verification

After all code changes, verify the implementation is internally consistent:

**8a. Import check (no services running needed):**

```bash
cd memblocks_lib
uv run python -c "
from memblocks.config import MemBlocksConfig
from memblocks.storage.embeddings import EmbeddingProvider
from memblocks.storage.qdrant import QdrantAdapter
from memblocks.services.semantic_memory import SemanticMemoryService
print('All imports OK')
"
```

**8b. Config field check:**

```bash
uv run python -c "
from memblocks.config import MemBlocksConfig
c = MemBlocksConfig()
print('sparse_embeddings_model:', c.sparse_embeddings_model)
print('retrieval_enable_sparse:', c.retrieval_enable_sparse)
print('retrieval_enable_query_expansion:', c.retrieval_enable_query_expansion)
print('retrieval_enable_reranking:', c.retrieval_enable_reranking)
"
```

**8c. Sparse embedder instantiation (fastembed model download on first run):**

```bash
uv run python -c "
from memblocks.config import MemBlocksConfig
from memblocks.storage.embeddings import EmbeddingProvider
config = MemBlocksConfig()
ep = EmbeddingProvider(config)
result = ep.embed_sparse_text('test sentence about memory')
print('Sparse indices:', result['indices'][:5])
print('Sparse values:', result['values'][:5])
print('SPLADE OK')
"
```

**8d. Full hybrid test (requires Qdrant + Ollama running):**

```bash
uv run python tests/test_hybrid.py
```

Expected output includes:
- `Retrieved N memories via hybrid_enhanced` or similar in transparency log
- Memories ranked by RRF fusion score

---

## Architecture of the Final Merged Retrieval Pipeline

```
block.retrieve(query) / block.semantic_retrieve(query)
        │
        ▼
SemanticMemoryService.retrieve([query])
        │
        ├─── 1. _expand_query(query)
        │         └── LLM generates N alternative query formulations
        │
        ├─── 2. _generate_hypothetical_paragraphs(query)   [HyDE]
        │         └── LLM generates M hypothetical answer paragraphs
        │
        ├─── 3. _retrieve_with_hybrid(original + expanded + hypothetical)
        │         ├── embed_documents()        → dense vectors (Ollama)
        │         ├── embed_sparse_documents() → SPLADE sparse vectors (fastembed)  [NEW]
        │         └── ThreadPoolExecutor:
        │               └── per query: retrieve_hybrid(dense, sparse, top_k)       [NEW]
        │                     ├── Qdrant Prefetch: dense cosine (top_k*2)
        │                     ├── Qdrant Prefetch: SPLADE sparse (top_k*2)
        │                     └── FusionQuery(fusion="rrf") → ranked merged results
        │         └── De-duplicate by memory_id across all query groups
        │
        └─── 4. _rerank_memories(query, deduplicated_results)
                  └── LLM scores each memory for relevance, returns ranked list
```

```
block._semantic.store(memory_unit)
        │
        ├── embed_text(content)          → dense vector
        ├── embed_sparse_text(content)   → SPLADE sparse vector   [NEW]
        │
        ├── retrieve_from_vector(dense, top_k=5)  [for PS2 conflict check, dense-only]
        │
        └── store_vector(collection, dense, payload, sparse_vector=sparse)  [NEW]
              └── PointStruct(
                    vector={"": dense, "text-sparse": SparseVector(...)},
                    payload=memory_dict
                  )
```

---

## Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | **Existing Qdrant collections lack `text-sparse` config** — created before this merge, so they don't have the sparse vector slot. `retrieve_hybrid()` will error or silently degrade. | High (any existing data) | Medium | `retrieve_hybrid()` wraps in try/except and falls back to `[]` gracefully. Dense results from `retrieve_from_vector()` are still used as the fallback for the expansion path. For full hybrid recall, collections must be **dropped and recreated** (the sparse vector config is set at collection creation time, not patchable). |
| 2 | **SPLADE model download on first use (~200 MB)** | Certain | Low | Expected behaviour — same as the embedding branch. `fastembed` caches the model in `~/.cache/fastembed`. Document in setup guide. |
| 3 | **`fastembed` import at module level causes issues in environments where it's not installed** | Low (it's in deps) | Medium | Import is at module level in `embeddings.py`. If `fastembed` is not installed, Python will raise `ImportError` on import of `EmbeddingProvider`. The `pyproject.toml` addition (Step 1) prevents this for properly managed environments. |
| 4 | **`store_vector()` with named vectors (`{"": dense, "text-sparse": sparse}`) breaks on collections without `sparse_vectors_config`** | Medium (old collections) | Low | The `if sparse_vector:` guard means if `RETRIEVAL_ENABLE_SPARSE=False`, the old `PointStruct(vector=dense)` path is used unchanged. Old collections are only at risk if sparse is enabled — which correctly requires recreating them anyway (Risk 1). |
| 5 | **`using=""` for the dense vector in `retrieve_hybrid()` requires the collection to use unnamed `VectorParams`** | Low | High | `create_collection()` uses `vectors_config=VectorParams(...)` (unnamed). This creates the default unnamed dense vector slot accessed by `using=""`. This is consistent. Only breaks if someone creates a collection using named vectors (`vectors_config={"name": VectorParams(...)}`), which is not done anywhere in this codebase. |
| 6 | **`test_hybrid.py` uses removed `Parent_Memory_ids` field** | Certain | Low | Step 6a fix removes the field from test constructor calls. |
| 7 | **Thread safety of lazy SPLADE embedder initialisation** | Low | Low | `_get_sparse_embedder()` does not use a lock. `embed_sparse_documents()` is called from within a `ThreadPoolExecutor`. Multiple threads could race to initialise `self._sparse_embedder`. Worst case: the model is loaded twice and one result is discarded. `SparseTextEmbedding.__init__` is idempotent. Add a lock if this becomes an issue. |
| 8 | **LLM re-ranking makes retrieve() significantly slower** | Certain | Medium | Already present in the query branch — not introduced by this merge. Can be disabled via `RETRIEVAL_ENABLE_RERANKING=False`. |

---

## Environment Variable Reference (complete set after merge)

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER_NAME` | `groq` | LLM provider: `groq` or `gemini` |
| `GROQ_API_KEY` | — | Groq API key |
| `GEMINI_API_KEY` | — | Google Gemini API key |
| `LLM_MODEL` | `meta-llama/llama-4-maverick-17b-128e-instruct` | Model name |
| `LLM_CONVO_TEMPERATURE` | `0.7` | Temperature for conversational LLM calls |
| `LLM_SEMANTIC_EXTRACTION_TEMPERATURE` | `0.0` | Temperature for PS1 extraction |
| `LLM_CORE_EXTRACTION_TEMPERATURE` | `0.0` | Temperature for core memory extraction |
| `LLM_RECURSIVE_SUMMARY_GEN_TEMPERATURE` | `0.3` | Temperature for summary generation |
| `LLM_MEMORY_UPDATE_TEMPERATURE` | `0.0` | Temperature for PS2 conflict resolution |
| `MONGODB_CONNECTION_STRING` | — | MongoDB URI |
| `MONGODB_DATABASE_NAME` | `memblocks_v2` | MongoDB database name |
| `MONGO_COLLECTION_USERS` | `users` | Users collection name |
| `MONGO_COLLECTION_BLOCKS` | `memory_blocks` | Blocks collection name |
| `MONGO_COLLECTION_CORE_MEMORIES` | `core_memories` | Core memories collection name |
| `QDRANT_HOST` | `localhost` | Qdrant host |
| `QDRANT_PORT` | `6333` | Qdrant port |
| `QDRANT_PREFER_GRPC` | `True` | Use gRPC for Qdrant |
| `SEMANTIC_COLLECTION_TEMPLATE` | `{block_id}_semantic` | Qdrant collection name template |
| `RESOURCE_COLLECTION_TEMPLATE` | `{block_id}_resource` | Qdrant collection name template |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API base URL |
| `EMBEDDINGS_MODEL` | `nomic-embed-text` | Dense embedding model (Ollama) |
| `SPARSE_EMBEDDINGS_MODEL` | `prithivida/Splade_PP_en_v1` | SPLADE model (fastembed) **(new)** |
| `MEMORY_WINDOW` | `10` | Messages before pipeline triggers |
| `KEEP_LAST_N` | `4` | Messages kept after flush |
| `RETRIEVAL_NUM_QUERY_EXPANSIONS` | `3` | LLM-generated query variants |
| `RETRIEVAL_NUM_HYPOTHETICAL_PARAGRAPHS` | `2` | HyDE hypothetical paragraphs |
| `RETRIEVAL_TOP_K_PER_QUERY` | `5` | Results per query variation |
| `RETRIEVAL_FINAL_TOP_K` | `10` | Results returned after re-ranking |
| `RETRIEVAL_ENABLE_QUERY_EXPANSION` | `True` | Enable LLM query expansion |
| `RETRIEVAL_ENABLE_HYPOTHETICAL_PARAGRAPHS` | `True` | Enable HyDE |
| `RETRIEVAL_ENABLE_RERANKING` | `True` | Enable LLM re-ranking |
| `RETRIEVAL_ENABLE_SPARSE` | `True` | Enable SPLADE hybrid search **(new)** |
| `ARIZE_SPACE_ID` | — | Arize monitoring space ID (optional) |
| `ARIZE_API_KEY` | — | Arize monitoring API key (optional) |
| `ARIZE_PROJECT_NAME` | `memBlocks` | Arize project name |

---

## Files Modified Summary

| File | Change Type | Steps |
|---|---|---|
| `memblocks_lib/pyproject.toml` | Add dep | 1 |
| `memblocks_lib/src/memblocks/config.py` | Add 2 fields | 2 |
| `memblocks_lib/src/memblocks/storage/embeddings.py` | Add sparse methods | 3 |
| `memblocks_lib/src/memblocks/storage/qdrant.py` | Add hybrid methods, update store/create | 4 |
| `memblocks_lib/src/memblocks/services/semantic_memory.py` | Add sparse to store(), replace retrieval helper, add query terms extractor | 5 |
| `tests/test_hybrid.py` | Port from embedding branch, fix `Parent_Memory_ids` | 6 |
| `uv.lock` | Regenerate | 7 |

**Files NOT touched (already correct on target branch):**
- All `services/` except `semantic_memory.py`
- All `models/`
- All `prompts/`
- `llm/` (including new `gemini_provider.py`)
- `logger/`
- `client.py`
- `backend/`
- `frontend/`
- Root `pyproject.toml`

---

## Execution Checklist

- [x] Step 1: Add `fastembed>=0.7.4` to `memblocks_lib/pyproject.toml`
- [x] Step 2a: Add `sparse_embeddings_model` field to `config.py`
- [x] Step 2b: Add `retrieval_enable_sparse` field to `config.py`
- [x] Step 3a: Extend `typing` imports in `embeddings.py` (`Any`, `Dict`, `Optional`)
- [x] Step 3b: Add `fastembed` import in `embeddings.py`
- [x] Step 3c: Add `self._sparse_model` and `self._sparse_embedder = None` to `EmbeddingProvider.__init__`
- [x] Step 3d: Add `_get_sparse_embedder()` method
- [x] Step 3e: Add `embed_sparse_text()` method
- [x] Step 3f: Add `embed_sparse_documents()` method
- [x] Step 4a: Add sparse-related imports to `qdrant.py`
- [x] Step 4b: Add `sparse_vectors_config` to `create_collection()`
- [x] Step 4c: Add `sparse_vector` param and conditional packing to `store_vector()`
- [x] Step 4d: Add `retrieve_hybrid()` method
- [x] Step 4e: Add `retrieve_by_keywords_and_entities()` method
- [x] Step 4f: Remove stub `hybrid_retrieve()` and inner `QueryObject` class
- [x] Step 5a: Add `re`, `string`, `Tuple` imports to `semantic_memory.py`
- [x] Step 5b: Add sparse vector generation and passing in all 4 `store_vector()` calls in `store()`
- [x] Step 5c: Add `_extract_query_terms()` static method
- [x] Step 5d: Replace `_retrieve_with_vectors()` with `_retrieve_with_hybrid()`
- [x] Step 5e: Update `retrieve()` to call `_retrieve_with_hybrid()`
- [x] Step 5f: Update `retrieval_method` in `RetrievalEntry` to be dynamic
- [x] Step 5g: Update class docstring
- [x] Step 6: Port `tests/test_hybrid.py` with `Parent_Memory_ids` fix
- [x] Step 7: Run `uv lock`
- [x] Step 8a: Import check (no services)
- [x] Step 8b: Config field check
- [ ] Step 8c: SPLADE embedder instantiation test
- [ ] Step 8d: Full hybrid end-to-end test (requires Qdrant + Ollama)
