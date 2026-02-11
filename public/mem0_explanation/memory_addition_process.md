# Mem0 Memory Addition Process: A Deep Dive

This document details the internal lifecycle of the `Memory.add()` operation in Mem0. It explains how raw user messages are transformed into structured managed memories, handling conflicts and updates along the way.

## 1. Input Processing & Normalization

The process begins when `add()` is called with a message.

**Function**: `Memory.add()` in `mem0/memory/main.py`

### 1.1 Standardization
Mem0 first normalizes input into a list of message dictionaries:
*   **String Input**: `"I like cats"` → `[{"role": "user", "content": "I like cats"}]`
*   **Dict Input**: `{"role": "user", "content": "..."}` → Wrapped in a list.
*   **List Input**: Kept as is.

### 1.2 Vision Processing
If `enable_vision` is true in the config, `parse_vision_messages` is called.
*   **Logic**: It scans for `image_url` types in the content.
*   **Action**: Calls an LLM (using `get_image_description`) to generate a text description of the image.
*   **Result**: The image content is replaced by its text description for downstream processing.

---

## 2. Fact Extraction (The "Analyzer")

The core goal here is to distill "noisy" conversation into "clean" facts.

**Condition**: This step runs only if `infer=True` (default). If `infer=False`, the raw message is just stored directly.

### 2.1 Prompt Selection
The system decides *which* side of the conversation to memorize based on `_should_use_agent_memory_extraction`.

*   **User Memory (Default)**:
    *   **Prompt**: `USER_MEMORY_EXTRACTION_PROMPT`
    *   **Goal**: Extract facts about the *User* (User's likes, name, plans).
    *   **Constraint**: *Strictly ignores* Assistant/System messages to prevent hallucinating user facts from the bot's own words.
*   **Agent Memory**:
    *   **Trigger**: If `agent_id` is present AND messages contain `role: assistant`.
    *   **Prompt**: `AGENT_MEMORY_EXTRACTION_PROMPT`
    *   **Goal**: Extract facts about the *Agent* (Agent's persona, capabilities, traits).
    *   **Constraint**: *Strictly ignores* User messages.

### 2.2 Execution
*   **Input**: The normalized conversation history.
*   **Multiple Memories**: The LLM is instructed to extract *all* relevant facts. This means a single message like "I'm Alice and I love pizza" will result in two distinct facts: `["Name is Alice", "Loves pizza"]`.
*   **Output (JSON)**: `{"facts": ["User likes sci-fi movies", "User lives in Tokyo"]}`

---

## 3. Context Retrieval (The "Recall")

Before storing the new facts, Mem0 checks if it already knows about them to avoid duplication or contradictions.

1.  **Iterative Search**: For *each* newly extracted fact, the system generates an embedding and searches the `vector_store`.
2.  **Aggregation**: It collects all unique "Old Memories" found for any of the new facts.
3.  **Scope**: Uses `user_id`, `agent_id`, or `run_id` to ensure we only look at relevant history.
4.  **Result**: An aggregated list of "Old Memories" semantically related to the batch of new facts.

---

## 4. Function Calling (The "Decider")

This is the brain of the operation. Mem0 uses an LLM to decide how to reconcile the *New Facts* with the *Old Memories*.

**Prompt**: `DEFAULT_UPDATE_MEMORY_PROMPT`

### 4.1 The Input to LLM
The LLM is presented with:
1.  **Existing Memory**: A list of `{"id": "...", "text": "..."}` that were retrieved in step 3.
2.  **New Facts**: The list of facts extracted in step 2.

### 4.2 The Decision Logic
The LLM must output a JSON list of actions. It chooses one of four operations for each fact:

*   **`ADD`**: The fact is completely new.
    *   *Example*: Old: `[]`, New: `"My name is Alice"` -> **Action: ADD**
*   **`UPDATE`**: The fact refines or changes an existing memory.
    *   *Example*: Old: `"Likes swimming"`, New: `"Loves swimming in the ocean"` -> **Action: UPDATE** (Preserves the stored ID).
*   **`DELETE`**: The fact contradicts an old memory (explicit correction).
    *   *Example*: Old: `"Likes cats"`, New: `"I actually hate cats now"` -> **Action: DELETE**
*   **`NONE`**: The fact is already known or irrelevant.
    *   *Example*: Old: `"Name is Alice"`, New: `"I am Alice"` -> **Action: NONE**

---

## 5. Storage Execution (The "Writer")

Based on the LLM's decisions, `Memory.add` executes the changes.

### 5.1 Handling `ADD`
*   **Action**: `_create_memory`
*   **Process**:
    1.  Generate new UUID.
    2.  Embed the memory text.
    3.  Insert into **Vector Store**.
    4.  Insert row into **SQLite History** (Event: `ADD`).

### 5.2 Handling `UPDATE`
*   **Action**: `_update_memory`
*   **Process**:
    1.  Use the *existing ID* (critical for continuity).
    2.  Re-embed the updated text.
    3.  Update record in **Vector Store**.
    4.  Insert row into **SQLite History** (Event: `UPDATE`, includes `old_memory` and `new_memory`).

### 5.3 Handling `DELETE`
*   **Action**: `_delete_memory`
*   **Process**:
    1.  Remove vector by ID from **Vector Store**.
    2.  Insert row into **SQLite History** (Event: `DELETE`).

### 5.4 Handling `NONE`
*   **Action**: No-op.
*   **Special Case**: If `agent_id` or `run_id` changed but the content is the same, it might just update the metadata (session IDs) in the vector store without changing the memory text.
