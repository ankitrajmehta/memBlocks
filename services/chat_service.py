"""Chat service with memory integration and optimized background processing."""

import asyncio
from typing import List, Dict, Optional, Set, Any
from datetime import datetime
from enum import Enum

from config import settings
from models.container import MemoryBlock
from models.units import (
    SemanticMemoryUnit,
    CoreMemoryUnit,
    ProcessingEvent,
    MemoryOperation,
)
from llm.llm_manager import llm_manager
from llm.output_models import SummaryOutput
from prompts import SUMMARY_SYSTEM_PROMPT, ASSISTANT_BASE_PROMPT
import uuid


class TaskStatus(Enum):
    """Background task status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BackgroundTaskTracker:
    """Track background memory processing tasks."""

    def __init__(self):
        self.tasks: Dict[str, asyncio.Task] = {}
        self.status: Dict[str, TaskStatus] = {}
        self.results: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()

    def add_task(self, task_id: str, task: asyncio.Task):
        """Register a new background task (synchronous)."""
        self.tasks[task_id] = task
        self.status[task_id] = TaskStatus.RUNNING
        self.results[task_id] = {
            "started_at": datetime.now(),
            "completed_at": None,
            "error": None,
        }

    async def mark_completed(self, task_id: str, error: Optional[Exception] = None):
        """Mark task as completed or failed."""
        async with self._lock:
            # Safety check - task might not be registered yet due to race condition
            if task_id not in self.status:
                print(
                    f"⚠️ Warning: Attempting to mark unknown task as completed: {task_id}"
                )
                return

            if error:
                self.status[task_id] = TaskStatus.FAILED
                self.results[task_id]["error"] = str(error)
            else:
                self.status[task_id] = TaskStatus.COMPLETED
            self.results[task_id]["completed_at"] = datetime.now()

    async def cleanup_completed(self, max_age_seconds: int = 300):
        """Remove completed tasks older than max_age_seconds."""
        async with self._lock:
            now = datetime.now()
            to_remove = []

            for task_id, result in self.results.items():
                if result["completed_at"]:
                    age = (now - result["completed_at"]).total_seconds()
                    if age > max_age_seconds:
                        to_remove.append(task_id)

            for task_id in to_remove:
                self.tasks.pop(task_id, None)
                self.status.pop(task_id, None)
                self.results.pop(task_id, None)

    async def get_status(self) -> Dict:
        """Get current status of all tasks."""
        async with self._lock:
            return {
                "total_tasks": len(self.tasks),
                "running": sum(
                    1 for s in self.status.values() if s == TaskStatus.RUNNING
                ),
                "completed": sum(
                    1 for s in self.status.values() if s == TaskStatus.COMPLETED
                ),
                "failed": sum(
                    1 for s in self.status.values() if s == TaskStatus.FAILED
                ),
                "tasks": {
                    task_id: {"status": status.value, **self.results[task_id]}
                    for task_id, status in self.status.items()
                },
            }

    async def wait_all(self, timeout: Optional[float] = None):
        """Wait for all tasks to complete."""
        async with self._lock:
            running_tasks = [
                task
                for task_id, task in self.tasks.items()
                if self.status[task_id] == TaskStatus.RUNNING
            ]

        if running_tasks:
            try:
                await asyncio.wait(running_tasks, timeout=timeout)
            except asyncio.TimeoutError:
                print(f"⚠️ Timeout waiting for {len(running_tasks)} background tasks")


class ProcessingHistoryTracker:
    """Track memory processing events for the session."""

    def __init__(self):
        self.events: List[ProcessingEvent] = []
        self._lock = asyncio.Lock()

    async def add_event(self, event: ProcessingEvent):
        """Add a new processing event."""
        async with self._lock:
            self.events.append(event)

    async def get_events(self) -> List[ProcessingEvent]:
        """Get all processing events."""
        async with self._lock:
            return self.events.copy()

    async def clear(self):
        """Clear all events."""
        async with self._lock:
            self.events.clear()


class ChatService:
    """
    Chat service with memory augmentation and optimized background processing.

    Handles:
    - Message history management
    - Memory extraction (semantic + core)
    - Recursive summarization
    - Context assembly for LLM
    - Background task management
    """

    def __init__(
        self,
        memory_block: MemoryBlock,
        memory_window: int = 10,
        keep_last_n: int = 4,
        max_concurrent_processing: int = 1,
    ):
        """
        Initialize chat service.

        Args:
            memory_block: Attached memory block
            memory_window: Messages before triggering memory processing
            keep_last_n: Messages to keep after flushing
            max_concurrent_processing: Max concurrent memory processing tasks
        """
        self.memory_block = memory_block
        self.memory_window = memory_window
        self.keep_last_n = keep_last_n
        self.max_concurrent_processing = max_concurrent_processing

        # Session state
        self.message_history: List[Dict[str, str]] = []
        self.recursive_summary: str = ""

        # Background task management
        self.task_tracker = BackgroundTaskTracker()
        self.processing_history = ProcessingHistoryTracker()
        self._processing_semaphore = asyncio.Semaphore(max_concurrent_processing)
        self._processing_lock = (
            asyncio.Lock()
        )  # Prevent race conditions on memory window

        # Metrics
        self.metrics = {
            "total_messages": 0,
            "memory_windows_processed": 0,
            "last_processing_time": None,
        }

    # ========================================================================
    # MEMORY WINDOW PROCESSING
    # ========================================================================

    async def _process_memory_window(self, task_id: str):
        """
        Process memory window: extract semantic + core memories, generate summary, flush history.

        Args:
            task_id: Unique identifier for this processing task

        This runs in the background without blocking the chat response.
        """
        async with self._processing_semaphore:
            async with self._processing_lock:
                messages_to_process = self.message_history.copy()

            if not messages_to_process:
                return

            print(f"🔄 MEMORY PIPELINE START (Task: {task_id[:12]}...)")
            print(f"   Processing {len(messages_to_process)} messages...")

            all_operations: List[MemoryOperation] = []

            if self.memory_block.semantic_memories:
                print(f"   → STEP 1: Semantic Extraction...")
                semantic_memories = (
                    await self.memory_block.semantic_memories.extract_semantic_memories(
                        messages=messages_to_process
                    )
                )
                print(f"   ✓ Extracted {len(semantic_memories)} semantic memories")

                for mem in semantic_memories:
                    operations = await self.memory_block.semantic_memories.store_memory(
                        mem
                    )
                    if operations:
                        all_operations.extend(operations)
                print(f"   ✓ Stored {len(semantic_memories)} memories")

            if self.memory_block.core_memories:
                print(f"   → STEP 2: Core Memory Update...")
                old_core = await self.memory_block.core_memories.get_memories()

                new_core = await self.memory_block.core_memories.create_new_core_memory(
                    messages=messages_to_process, old_core_memory=old_core
                )

                await self.memory_block.core_memories.store_memory(new_core)
                print(f"   ✓ Updated core memory")

            print(f"   → STEP 3: Recursive Summary...")
            new_summary = await self._generate_recursive_summary(messages_to_process)

            async with self._processing_lock:
                self.recursive_summary = new_summary
            print(f"   ✓ Summary updated")

            print(f"   → STEP 4: Flushing History...")
            async with self._processing_lock:
                old_len = len(self.message_history)
                self.message_history = self.message_history[-self.keep_last_n :]
                print(f"   ✓ Flushed history ({old_len} → {len(self.message_history)})")

            if all_operations:
                event = ProcessingEvent(
                    event_id=f"evt_{uuid.uuid4().hex[:12]}",
                    timestamp=datetime.now().isoformat(),
                    messages_processed=len(messages_to_process),
                    operations=all_operations,
                )
                await self.processing_history.add_event(event)
                print(
                    f"   ✓ Recorded processing event with {len(all_operations)} operations"
                )

            self.metrics["memory_windows_processed"] += 1
            self.metrics["last_processing_time"] = datetime.now()

            print(f"✅ MEMORY PIPELINE COMPLETE (Task: {task_id[:12]}...)")

    async def _generate_recursive_summary(self, messages: List[Dict[str, str]]) -> str:
        """
        Generate recursive summary using LangChain.

        Args:
            messages: Recent conversation messages

        Returns:
            Updated summary
        """
        conversation_text = "\n".join(
            [f"{msg['role'].upper()}: {msg['content']}\n" for msg in messages]
        )

        user_input = f"""Previous Summary:
        {self.recursive_summary if self.recursive_summary else "None"}

        Recent Conversation:
        {conversation_text}

        Generate an updated recursive summary that incorporates the new conversation."""

        try:
            # Create chain
            chain = llm_manager.create_structured_chain(
                system_prompt=SUMMARY_SYSTEM_PROMPT,
                pydantic_model=SummaryOutput,
                temperature=settings.llm_recursive_summary_gen_temperature,
            )

            result = await chain.ainvoke({"input": user_input})
            return result.summary

        except Exception as e:
            print(f"⚠️ Failed to generate summary: {e}")
            return self.recursive_summary

    def _trigger_memory_processing(self):
        """
        Trigger background memory processing without blocking.

        Creates a background task and registers it with the tracker.
        """
        task_id = f"mem_proc_{uuid.uuid4()}"

        # Create wrapper that includes task tracking
        async def process_with_tracking():
            try:
                await self._process_memory_window(task_id)
                await self.task_tracker.mark_completed(task_id)
            except Exception as e:
                print(f"❌ Memory processing failed (Task: {task_id}): {e}")
                await self.task_tracker.mark_completed(task_id, error=e)

        # Create and register the task BEFORE starting it
        task = asyncio.create_task(process_with_tracking())
        self.task_tracker.add_task(task_id, task)

        # Add error handler for logging
        def on_done(t):
            if not t.cancelled() and t.exception():
                print(f"⚠️ Background memory processing uncaught error: {t.exception()}")

        task.add_done_callback(on_done)

        return task

    # ========================================================================
    # RETRIEVAL & CONTEXT BUILDING
    # ========================================================================

    def _retrieve_semantic_memories(
        self, query: str, top_k: int = 5
    ) -> List[SemanticMemoryUnit]:
        """Retrieve relevant semantic memories for query."""
        if not self.memory_block.semantic_memories:
            return []

        results = self.memory_block.semantic_memories.retrieve_memories(
            [query], top_k=top_k
        )
        return results[0] if results else []

    async def _get_core_memory(self) -> Optional[CoreMemoryUnit]:
        """Get core memory from block."""
        if not self.memory_block.core_memories:
            return None
        return await self.memory_block.core_memories.get_memories()

    async def _build_system_prompt(
        self,
        semantic_memories: List[SemanticMemoryUnit],
        core_memory: Optional[CoreMemoryUnit],
        base_prompt: str = ASSISTANT_BASE_PROMPT,
    ) -> str:
        """
        Build system prompt with all memory context.

        Args:
            semantic_memories: Retrieved semantic memories
            core_memory: Core memory (persona + human facts)
            base_prompt: Base assistant prompt

        Returns:
            Complete system prompt with tagged memory sections
        """
        parts = [base_prompt]

        # Add core memory (always present if exists)
        if core_memory and (core_memory.persona_content or core_memory.human_content):
            core_text = []
            if core_memory.persona_content:
                core_text.append(f"[PERSONA]\n{core_memory.persona_content}")
            if core_memory.human_content:
                core_text.append(f"[HUMAN]\n{core_memory.human_content}")

            parts.append(f"\n<CORE_MEMORY>\n{chr(10).join(core_text)}\n</CORE_MEMORY>")

        # Add recursive summary
        if self.recursive_summary:
            parts.append(
                f"\n<CONVERSATION_SUMMARY>\n{self.recursive_summary}\n</CONVERSATION_SUMMARY>"
            )

        # Add semantic memories
        if semantic_memories:
            semantic_text = "\n\n".join(
                [
                    f"[{mem.type.upper()}] {mem.content}\n"
                    f"  Keywords: {', '.join(mem.keywords[:5])}"
                    for mem in semantic_memories
                ]
            )
            parts.append(f"\n<SEMANTIC_MEMORY>\n{semantic_text}\n</SEMANTIC_MEMORY>")

        return "\n".join(parts)

    # ========================================================================
    # CHAT INTERFACE
    # ========================================================================

    async def send_message(self, user_message: str) -> Dict[str, Any]:
        """
        Process user message and generate response.

        Args:
            user_message: User's input

        Returns:
            Dict with 'response' and 'retrieved_context' keys
        """
        print(f"\n{'─' * 70}")
        print(f"💬 Processing message...")
        print(f"{'─' * 70}")

        print(f"🔍 Retrieving memories...")
        semantic_memories = self._retrieve_semantic_memories(user_message, top_k=5)
        core_memory = await self._get_core_memory()
        print(f"   📚 Semantic: {len(semantic_memories)} memories")
        print(f"   🧠 Core: {'Yes' if core_memory else 'No'}")

        system_prompt = await self._build_system_prompt(semantic_memories, core_memory)

        self.message_history.append({"role": "user", "content": user_message})
        self.metrics["total_messages"] += 1

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.message_history)

        try:
            llm = llm_manager.get_chat_llm(temperature=settings.llm_convo_temperature)
            response = await llm.ainvoke(messages)
            assistant_response = response.content
        except Exception as e:
            print(f"⚠️ LLM error: {e}")
            assistant_response = (
                "I apologize, but I encountered an error processing your message."
            )

        self.message_history.append(
            {"role": "assistant", "content": assistant_response}
        )

        if len(self.message_history) >= self.memory_window:
            print(
                f"\n🔄 Memory window threshold reached, triggering background processing..."
            )
            self._trigger_memory_processing()

        retrieved_context = [
            {
                "content": mem.content,
                "type": mem.type,
                "confidence": mem.confidence,
                "keywords": mem.keywords[:5] if mem.keywords else [],
            }
            for mem in semantic_memories
        ]

        return {"response": assistant_response, "retrieved_context": retrieved_context}

    # ========================================================================
    # UTILITIES & MANAGEMENT
    # ========================================================================

    async def get_processing_status(self) -> Dict:
        """Get status of background processing tasks."""
        return await self.task_tracker.get_status()

    async def wait_for_processing(self, timeout: Optional[float] = None):
        """
        Wait for all background memory processing to complete.

        Useful for graceful shutdown or testing.

        Args:
            timeout: Maximum time to wait in seconds
        """
        print(f"⏳ Waiting for background tasks to complete...")
        await self.task_tracker.wait_all(timeout=timeout)
        print(f"✅ All background tasks completed")

    async def cleanup_old_tasks(self, max_age_seconds: int = 300):
        """Clean up completed tasks older than max_age_seconds."""
        await self.task_tracker.cleanup_completed(max_age_seconds)

    def print_status(self):
        """Print current session status."""
        print(f"\n{'=' * 60}")
        print(f"📊 SESSION STATUS")
        print(f"{'=' * 60}")
        print(f"Block: {self.memory_block.meta_data.id}")
        print(f"Name: {self.memory_block.name}")
        print(f"Message History: {len(self.message_history)} messages")
        print(f"Memory Window: {self.memory_window} messages")
        print(f"Recursive Summary: {'Yes' if self.recursive_summary else 'No'}")
        if self.recursive_summary:
            print(f"  ({len(self.recursive_summary)} chars)")
        print(f"\n📈 METRICS")
        print(f"Total Messages: {self.metrics['total_messages']}")
        print(f"Memory Windows Processed: {self.metrics['memory_windows_processed']}")
        if self.metrics["last_processing_time"]:
            print(
                f"Last Processing: {self.metrics['last_processing_time'].strftime('%Y-%m-%d %H:%M:%S')}"
            )
        print(f"{'=' * 60}\n")

    async def print_task_status(self):
        """Print background task status."""
        status = await self.get_processing_status()
        print(f"\n{'=' * 60}")
        print(f"🔧 BACKGROUND TASK STATUS")
        print(f"{'=' * 60}")
        print(f"Total Tasks: {status['total_tasks']}")
        print(f"Running: {status['running']}")
        print(f"Completed: {status['completed']}")
        print(f"Failed: {status['failed']}")

        if status["tasks"]:
            print(f"\nTask Details:")
            for task_id, task_info in status["tasks"].items():
                print(f"\n  {task_id}:")
                print(f"    Status: {task_info['status']}")
                print(f"    Started: {task_info['started_at'].strftime('%H:%M:%S')}")
                if task_info["completed_at"]:
                    duration = (
                        task_info["completed_at"] - task_info["started_at"]
                    ).total_seconds()
                    print(
                        f"    Completed: {task_info['completed_at'].strftime('%H:%M:%S')} ({duration:.2f}s)"
                    )
                if task_info["error"]:
                    print(f"    Error: {task_info['error']}")

        print(f"{'=' * 60}\n")

    async def shutdown(self, timeout: float = 30.0):
        """
        Gracefully shutdown the chat service.

        Waits for background tasks to complete before shutdown.

        Args:
            timeout: Maximum time to wait for tasks to complete
        """
        print(f"\n🛑 Shutting down chat service...")
        await self.wait_for_processing(timeout=timeout)
        print(f"✅ Chat service shutdown complete")
