# MemBlocks Library Changes

The following changes were made to the `memblocks_lib` and its configuration to support real-time context saving and cross-session memory retention:

## 1. Added Manual Memory `flush()` Method
**File Modified:** `memblocks_lib/src/memblocks/services/session.py`

**Change:** 
Added a new `flush()` asynchronous method to the `Session` class. By default, the library only triggers the `MemoryPipeline` automatically when the `memory_window_limit` (e.g., 10 messages) is reached. If a user ended a session early (e.g., by clicking "New Chat" after just 2 messages), those messages were orphaned, and semantic/core memories were never extracted. 

The `flush()` method allows the backend to force the pipeline to process however many messages are currently in the window before abandoning the session, ensuring zero context loss.

```python
async def flush(self) -> str:
    """
    Manually trigger the memory pipeline for all current messages in the window,
    even if the window size has not reached the limit.
    ...
    """
```

## 2. Updated `MEMORY_WINDOW` Configuration
**File Modified:** `.env` (Project root)

**Change:**
Added `MEMORY_WINDOW=2` to the environment variables.

**Why:**
The `MemBlocksConfig` model strictly controls how many messages accumulate before memory extraction occurs. The default is 10. By setting it to 2 (1 user message + 1 AI response = 1 conversational turn), the memory pipeline is now instructed to run and extract semantic facts, update core memories, and generate a recursive summary **after every single turn**. 

This, combined with running the persistence tasks in FastAPI `BackgroundTasks`, ensures that the right-side Analytics Panel and the vector database update instantly in the background on every interaction without slowing down the chat UI.
