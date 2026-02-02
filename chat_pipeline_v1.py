"""
Modularized Chat Session with Semantic Memory Pipeline
======================================================

Features:
- PS1-enhanced semantic memory extraction (integrated in sections.py)
- Recursive summarization for context compression
- Sliding window management
- Simplified pipeline focusing on semantic memories only

Memory extraction is now handled by SemanticMemorySection class.
"""

import asyncio
from datetime import datetime
from typing import List, Dict
from groq import Groq
from dotenv import load_dotenv

from models.units import SemanticMemoryUnit
from vector_db.mem_block_setup import MemBlockQdrantManager
from prompts import SUMMARY_SYSTEM_PROMPT, ASSISTANT_BASE_PROMPT

load_dotenv()

# LLM Configuration
client = Groq()
MODEL = "llama-3.3-70b-versatile"


class ChatSession:
    """
    Modularized chat session with PS1-enhanced semantic memory pipeline.

    Memory Architecture:
    - Semantic: PS1 extraction (events, facts, opinions) - retrieved per query
    - Recursive Summary: Compressed conversation history
    - Sliding Window: Last 2 messages kept in history

    The heavy lifting of memory extraction is now in SemanticMemorySection.extract_and_store_memories()
    """

    def __init__(
        self,
        user_id: str,
        session_description: str = "Chat session memories",
        memory_window: int = 10,
        keep_last_n: int = 4,
    ):
        """
        Initialize chat session.

        Args:
            user_id: Unique user identifier
            session_description: Description of the memory block
            memory_window: Number of messages before triggering memory processing
            keep_last_n: Number of recent messages to keep after flushing
        """
        self.user_id = user_id
        self.memory_window = memory_window
        self.keep_last_n = keep_last_n

        # Message history and summary
        self.message_history: List[Dict[str, str]] = []
        self.recursive_summary: str = ""

        # Initialize memory block
        self.memory_manager = MemBlockQdrantManager()
        self.memory_block = self.memory_manager.create_memory_block(
            name=f"ChatSession_{user_id}",
            description=session_description,
            user_id=user_id,
        )

        print(f"✅ Chat session initialized for user: {user_id}")
        print(f"   Memory Block ID: {self.memory_block.meta_data.id}")
        print(f"   Memory Window: {memory_window} messages")

    # ========================================================================
    # RECURSIVE SUMMARY
    # ========================================================================

    async def _generate_recursive_summary(
        self, messages: List[Dict[str, str]], system_prompt: str = SUMMARY_SYSTEM_PROMPT
    ) -> str:
        """
        Generate recursive summary of conversation.

        Combines previous summary with new messages to create updated summary.
        """

        conversation_text = "\n".join(
            [f"{msg['role'].upper()}: {msg['content']}" for msg in messages]
        )

        user_prompt = f"""Previous Summary:
{self.recursive_summary if self.recursive_summary else "None"}

Recent Conversation:
{conversation_text}

Generate an updated recursive summary:"""

        loop = asyncio.get_event_loop()
        completion = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_completion_tokens=512,
                top_p=1,
            ),
        )

        return completion.choices[0].message.content.strip()

    # ========================================================================
    # MEMORY WINDOW PROCESSING
    # ========================================================================

    async def _process_memory_window(self):
        """
        Complete memory processing pipeline when message window threshold is reached.

        Steps:
        1. Extract semantic memories using PS1 (via SemanticMemorySection)
        2. (Optional: Filter/validate before storing)
        3. Store memories in vector DB
        4. Generate recursive summary
        5. Flush message history to last N messages
        """
        print(f"\n{'='*70}")
        print(f"🔄 MEMORY PROCESSING PIPELINE")
        print(f"{'='*70}")
        print(f"Processing {len(self.message_history)} messages...")

        # APPROACH 1: Extract then store separately (more control)
        semantic_memories = (
            await self.memory_block.semantic_memories.extract_semantic_memories(
                messages=self.message_history, client=client, model=MODEL
            )
        )

        print(f"   ✓ Extracted {len(semantic_memories)} semantic memories")

        # STEP 3: Store filtered memories
        print(f"\n💾 STEP 3: Storing Memories")
        for mem in semantic_memories:
            self.memory_block.semantic_memories.store_memory(mem)
        print(f"   ✓ Stored {len(semantic_memories)} memories in vector DB")

        # Alternative: Use extract_and_store_memories() for one-liner
        # semantic_memories = await self.memory_block.semantic_memories.extract_and_store_memories(
        #     messages=self.message_history,
        #     client=client,
        #     model=MODEL,
        #     min_confidence=0.7  # Built-in filtering
        # )

        # STEP 4: Generate Recursive Summary
        print(f"\n📊 STEP 4: Recursive Summary")
        new_summary = await self._generate_recursive_summary(self.message_history)
        self.recursive_summary = new_summary
        print(f"   ✓ Summary updated ({len(new_summary)} chars)")

        # STEP 5: Flush History
        print(f"\n🗑️  STEP 5: Flushing Message History")
        print(f"   Before: {len(self.message_history)} messages")
        self.message_history = self.message_history[-self.keep_last_n :]
        print(
            f"   After: {len(self.message_history)} messages (kept last {self.keep_last_n})"
        )
        print(f"   💡 Old messages are now stored as structured memories!")

        print(f"\n{'='*70}")
        print(f"✅ PIPELINE COMPLETE")
        print(f"{'='*70}\n")

    # ========================================================================
    # RETRIEVAL
    # ========================================================================

    def _retrieve_semantic_memories(
        self, query: str, top_k: int = 5
    ) -> List[SemanticMemoryUnit]:
        """
        Retrieve relevant semantic memories for the query.

        Args:
            query: User query text
            top_k: Number of top memories to retrieve

        Returns:
            List of relevant SemanticMemoryUnit instances
        """
        results = self.memory_block.semantic_memories.retrieve_memories(
            [query], top_k=top_k
        )
        return results[0] if results else []

    # ========================================================================
    # CONTEXT BUILDING
    # ========================================================================

    def _build_system_prompt(
        self,
        semantic_memories: List[SemanticMemoryUnit],
        base_prompt: str = ASSISTANT_BASE_PROMPT,
    ) -> str:
        """
        Build system prompt with semantic memories and recursive summary.

        Args:
            semantic_memories: Retrieved semantic memories

        Returns:
            Complete system prompt string
        """

        parts = [base_prompt]

        # Add recursive summary
        if self.recursive_summary:
            parts.append(
                f"\n<CONVERSATION_SUMMARY>\n{self.recursive_summary}\n</CONVERSATION_SUMMARY>"
            )

        # Add semantic memories (with PS1 enrichment)
        if semantic_memories:
            semantic_text = "\n\n".join(
                [
                    f"[{mem.type.upper()}] {mem.content}\n"
                    f"  Keywords: {', '.join(mem.keywords[:5])}\n"
                    f"  Embedding: {mem.embedding_text[:100]}"
                    for mem in semantic_memories
                ]
            )
            parts.append(f"\n<SEMANTIC_MEMORY>\n{semantic_text}\n</SEMANTIC_MEMORY>")

        return "\n".join(parts)

    # ========================================================================
    # CHAT INTERFACE
    # ========================================================================

    async def send_message(self, user_message: str) -> str:
        """
        Process user message and generate response with memory augmentation.

        Args:
            user_message: User's input message

        Returns:
            Assistant's response
        """

        print(f"\n{'─'*70}")
        print(f"💬 Processing message...")
        print(f"{'─'*70}")

        # Retrieve relevant semantic memories
        print(f"🔍 Retrieving semantic memories...")
        semantic_memories = self._retrieve_semantic_memories(user_message, top_k=5)
        print(f"   📚 Retrieved: {len(semantic_memories)} memories")

        # Build system prompt with context
        system_prompt = self._build_system_prompt(semantic_memories)

        # Add user message to history
        self.message_history.append({"role": "user", "content": user_message})

        # Build messages for LLM
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.message_history)

        # Get response
        loop = asyncio.get_event_loop()
        completion = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.7,
                max_completion_tokens=1024,
                top_p=1,
            ),
        )

        assistant_response = completion.choices[0].message.content

        # Add assistant response to history
        self.message_history.append(
            {"role": "assistant", "content": assistant_response}
        )

        # Process memory window if threshold reached
        if len(self.message_history) >= self.memory_window:
            await self._process_memory_window()

        return assistant_response

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def print_status(self):
        """Print current session status."""
        print(f"\n{'='*60}")
        print(f"📊 SESSION STATUS")
        print(f"{'='*60}")
        print(f"User: {self.user_id}")
        print(f"Memory Block: {self.memory_block.meta_data.id}")
        print(f"Message History: {len(self.message_history)} messages")
        print(f"Memory Window: {self.memory_window} messages")
        print(f"Recursive Summary: {'Yes' if self.recursive_summary else 'No'}")
        if self.recursive_summary:
            print(f"  ({len(self.recursive_summary)} chars)")
        print(f"{'='*60}\n")


# ============================================================================
# DEMO
# ============================================================================


async def demo_semantic_pipeline():
    """Demo showing the modularized semantic memory pipeline."""

    print("\n" + "=" * 70)
    print("🚀 MODULARIZED SEMANTIC MEMORY PIPELINE DEMO")
    print("=" * 70)
    print("Features:")
    print("  - PS1 extraction integrated in SemanticMemorySection")
    print("  - Recursive summarization for context")
    print("  - Sliding window management")
    print("  - Clean, modular architecture")
    print("=" * 70 + "\n")

    # Initialize session
    session = ChatSession(
        user_id="demo_user",
        session_description="Semantic memory demo",
        memory_window=8,
        keep_last_n=2,
    )

    # Sample conversation
    messages = [
        "Hi! My name is Alex and I prefer short, concise answers.",
        "I live in San Francisco and work as a software engineer.",
        "Yesterday I attended an AI safety conference at Stanford.",
        "The keynote was about alignment research and value learning.",
        "I'm planning to implement LRU caching in our production system.",
        "The current system uses 2GB of RAM and we need to reduce it by 40%.",
        "My colleague Sarah suggested using Redis for distributed caching.",
        "We scheduled the migration for March 15th during low-traffic hours.",
    ]

    # Process messages
    for i, msg in enumerate(messages, 1):
        print(f"\n{'─'*70}")
        print(f"Message {i}/{len(messages)}")
        print(f"{'─'*70}")
        print(f"💬 User: {msg}")

        response = await session.send_message(msg)
        print(f"🤖 Assistant: {response}")

        await asyncio.sleep(0.5)

    # Test memory retrieval
    print(f"\n{'─'*70}")
    print(f"TESTING MEMORY RETRIEVAL")
    print(f"{'─'*70}")

    final_response = await session.send_message(
        "Can you remind me about the caching project I mentioned?"
    )
    print(f"🤖 Assistant: {final_response}")

    # Show session status
    session.print_status()


if __name__ == "__main__":
    asyncio.run(demo_semantic_pipeline())
