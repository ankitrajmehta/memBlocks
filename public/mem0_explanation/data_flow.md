# Mem0 Data Flow Architecture

This document provides a deep dive into the data flow of the Mem0 library, tracing how user messages are processed, stored, and retrieved.

## 1. High-Level Overview

The core of Mem0 interactions happens through the `Memory` class (synchronous) or `AsyncMemory` class (asynchronous).

**Key Components:**
*   **Memory Client (`Memory`/`AsyncMemory`)**: The main entry point. Orchestrates the workflow.
*   **LLM (`LlmFactory`)**: Used for extracting facts and determining memory updates (e.g., GPT-4).
*   **Embedder (`EmbedderFactory`)**: Converts text into vector embeddings (e.g., OpenAI text-embedding-3).
*   **Vector Store (`VectorStoreFactory`)**: Stores the actual memories and their embeddings (e.g., Qdrant, Chroma).
*   **History DB (`SQLiteManager`)**: Attributes a local SQLite database to track the history of all memory changes (ADD, UPDATE, DELETE).
*   **Graph Store (`GraphStoreFactory`)**: (Optional) Stores relationships between entities.

---

## 2. The "Add" Flow (Storing Memories)

This process converts a raw user interaction into structured, stored memories.

**Entry Point**: `Memory.add(messages, user_id=..., ...)` in `mem0/mem0/memory/main.py`.

### Step 2.1: Initialization & Validation
1.  **Metadata Construction**: `_build_filters_and_metadata` creates a metadata dictionary containing `user_id`, `agent_id`, and `run_id`.
2.  **Input Normalization**: `messages` are converted to a list of dictionaries (standard format).
3.  **Vision Processing**: If enabled, `parse_vision_messages` processes any images using the LLM.

### Step 2.2: Parallel Execution
The `add` method spins up threads (or async tasks) to write to storage systems in parallel:
1.  **Vector Store**: `_add_to_vector_store` (Primary flow)
2.  **Graph Store**: `_add_to_graph` (If enabled)

### Step 2.3: Vector Store Processing (`_add_to_vector_store`)

This is where the intelligence happens. It splits into two paths based on the `infer` flag.

#### Path A: `infer=False` (Direct Storage)
If you just want to dump data without processing:
1.  **Embed**: The full message content is embedded directly (`self.embedding_model.embed`).
2.  **Store**: Calls `_create_memory`.

#### Path B: `infer=True` (Intelligent Memory) - *The Default*
1.  **Fact Extraction**:
    *   The system constructs a prompt using `get_fact_retrieval_messages`.
    *   **LLM Call**: `self.llm.generate_response` is called to extract specific facts from the conversation.
    *   *Result*: A list of clear, standalone facts (e.g., "User likes tennis").

2.  **Context Retrieval**:
    *   For *each* extracted fact, the system embeds it.
    *   **Vector Search**: It searches the existing `vector_store` for similar, existing memories to check for contradictions or updates.

3.  **Action Determination (Deduplication/Evolution)**:
    *   The system creates a "function calling" prompt using `get_update_memory_messages`.
    *   **LLM Call**: It sends the *new facts* and the *existing related memories* to the LLM.
    *   The LLM decides on a list of actions:
        *   **`ADD`**: Create a new memory.
        *   **`UPDATE`**: Modify an existing memory (e.g., "User likes tennis" -> "User loves tennis").
        *   **`DELETE`**: Remove an outdated memory.
        *   **`NONE`**: No change needed.

4.  **Execution**:
    *   The system iterates through the LLM's decided actions and calls the respective internal methods:
        *   `_create_memory`
        *   `_update_memory`
        *   `_delete_memory`

---

## 3. Internal CRUD Operations

These methods handle the low-level interactions with the Vector Store and History DB.

### `_create_memory(data, ...)`
1.  **Embed**: Generates vector embedding for `data` (if not already present).
2.  **ID Generation**: Creates a new UUID.
3.  **Vector Store Insert**: Calls `self.vector_store.insert` to save the vector and payload.
4.  **History Log**: Calls `self.db.add_history` to write an "ADD" event to the local SQLite `history` table.

### `_update_memory(memory_id, data, ...)`
1.  **Retrieve**: Fetches the existing memory to preserve metadata.
2.  **Embed**: Generates new vector for the updated `data`.
3.  **Vector Store Update**: Calls `self.vector_store.update`.
4.  **History Log**: Writes an "UPDATE" event to SQLite, recording both `old_memory` and `new_memory`.

### `_delete_memory(memory_id)`
1.  **Retrieve**: Fetches the memory to log what is being deleted.
2.  **Vector Store Delete**: Calls `self.vector_store.delete`.
3.  **History Log**: Writes a "DELETE" event to SQLite.

---

## 4. The "Search" Flow (Retrieval)

**Entry Point**: `Memory.search(query, user_id=..., ...)`

1.  **Filter Construction**: Builds filters based on `user_id`, etc. Handles advanced operators (gt, lt, etc.) via `_process_metadata_filters`.
2.  **Parallel Search**:
    *   **Vector Search** (`_search_vector_store`):
        *   Embeds the `query`.
        *   Calls `self.vector_store.search`.
        *   Filters results by score `threshold`.
    *   **Graph Search** (If enabled).
3.  **Reranking** (Optional): If a `reranker` is configured, it re-orders the results for better relevance.
4.  **Format**: Returns a Clean list of results.

---

## 5. File Map

| Component | File Path | Responsibility |
| :--- | :--- | :--- |
| **Main Entry** | `mem0/mem0/memory/main.py` | `Memory` class. Orchestrates Add/Search/Get logic. |
| **History DB** | `mem0/mem0/memory/storage.py` | `SQLiteManager`. Manages the `history` table for audit logs. |
| **Vector Base** | `mem0/mem0/vector_stores/base.py` | Defines the interface (`insert`, `search`, `delete`, `update`) for all vector stores. |
| **Vector Impl** | `mem0/mem0/vector_stores/*.py` | Concrete implementations (e.g., `qdrant.py`, `chroma.py`). |
| **LLM Base** | `mem0/mem0/llms/base.py` | Defines interface for LLM interactions. |
| **LLM Impl** | `mem0/mem0/llms/*.py` | Concrete wrappers (e.g., `openai.py`) calling external APIs. |
| **Embedder** | `mem0/mem0/embeddings/*.py` | Handles text-to-vector conversion. |
