import asyncio
from datetime import datetime
from typing import List, Dict, Optional
import json
from groq import Groq
from dotenv import load_dotenv

from models.units import SemanticMemoryUnit, MemoryUnitMetaData
from vector_db.mem_block_setup import MemBlockQdrantManager

load_dotenv()

client = Groq()
MODEL = "llama-3.1-8b-instant"


class ChatSession:
    """
    Chat session with memory management, recursive summarization, and memory extraction.
    
    Features:
    - Maintains sliding window of 10 messages
    - Triggers summary & memory extraction at 8 messages
    - Flushes to last 3 messages after processing
    - Retrieves relevant memories for each query
    - Attaches memories and recursive summary to context
    """
    
    def __init__(self, user_id: str, session_description: str = "Chat session memories"):
        self.user_id = user_id
        self.message_history: List[Dict[str, str]] = []  # {"role": "user/assistant", "content": "..."}
        self.recursive_summary: str = ""
        
        # Initialize memory block
        self.memory_manager = MemBlockQdrantManager()
        self.memory_block = self.memory_manager.create_memory_block(
            name=f"ChatSessionBlock_{user_id}",
            description=session_description,
            user_id=user_id
        )
        
        print(f"✅ Chat session initialized for user: {user_id}")
    
    async def _generate_recursive_summary(self, messages: List[Dict[str, str]]) -> str:
        """Generate recursive summary of conversation using Groq."""
        
        system_prompt = """You are a conversation summarizer. Create a concise recursive summary that:
1. Builds upon the previous summary (if any)
2. Captures key topics, decisions, and important information
3. Maintains temporal context
4. Is concise but comprehensive

Return ONLY the summary text, no JSON or formatting."""

        # Format conversation for summarization
        conversation_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}" 
            for msg in messages
        ])
        
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
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_completion_tokens=1024,
                top_p=1
            )
        )
        
        return completion.choices[0].message.content.strip()
    
    async def _extract_semantic_memories(self, messages: List[Dict[str, str]]) -> List[SemanticMemoryUnit]:
        """Extract semantic memories (event & factual) from conversation using Groq."""
        
        system_prompt = """You are a memory extraction engine. Extract semantic memories from conversations.

Focus on:
1. FACTUAL memories: Facts about people, places, things, preferences
2. EVENT memories: Things that happened, decisions made, actions taken

Return ONLY valid JSON array without markdown formatting.

Schema:
[
  {
    "content": "Clear, standalone memory statement",
    "type": "factual" or "event",
    "entities": ["entity1", "entity2"],
    "tags": ["tag1", "tag2"],
    "confidence": 0.0 to 1.0
  }
]

Rules:
- Each memory should be self-contained and clear
- Extract entities (people, places, organizations, concepts)
- Add relevant tags for categorization
- Confidence based on clarity and importance
- Skip small talk and pleasantries"""

        # Format conversation
        conversation_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}" 
            for msg in messages
        ])
        
        user_prompt = f"""Conversation:
{conversation_text}

Extract semantic memories as JSON array:"""

        loop = asyncio.get_event_loop()
        completion = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                max_completion_tokens=2048,
                top_p=1
            )
        )
        
        raw_response = completion.choices[0].message.content.strip()
        
        # Strip markdown code fences if present
        if raw_response.startswith("```"):
            raw_response = raw_response.split("```")[1]
            if raw_response.startswith("json"):
                raw_response = raw_response[4:]
        raw_response = raw_response.strip()
        
        try:
            memories_data = json.loads(raw_response)
            
            # Convert to SemanticMemoryUnit objects
            memory_units = []
            current_time = datetime.now().isoformat()
            
            for mem in memories_data:
                unit = SemanticMemoryUnit(
                    content=mem.get("content", ""),
                    type=mem.get("type", "factual"),
                    source="conversation",
                    confidence=mem.get("confidence", 0.8),
                    memory_time=current_time,
                    entities=mem.get("entities", []),
                    tags=mem.get("tags", []),
                    updated_at=current_time,
                    meta_data=MemoryUnitMetaData(usage=[current_time])
                )
                memory_units.append(unit)
            
            return memory_units
            
        except json.JSONDecodeError as e:
            print(f"⚠️ Failed to parse memories JSON: {e}")
            print(f"Raw response: {raw_response}")
            return []
    
    async def _process_memory_window(self):
        """
        Process conversation when 8 messages reached:
        1. Generate recursive summary
        2. Extract semantic memories
        3. Store memories
        4. Flush history to last 3 messages
        """
        print(f"\n🔄 Processing memory window ({len(self.message_history)} messages)...")
        
        # Run summary and extraction in parallel
        summary_task = self._generate_recursive_summary(self.message_history)
        memories_task = self._extract_semantic_memories(self.message_history)
        
        new_summary, new_memories = await asyncio.gather(summary_task, memories_task)
        
        # Update recursive summary
        self.recursive_summary = new_summary
        print(f"✅ Recursive summary updated ({len(new_summary)} chars)")
        
        # Store extracted memories
        if new_memories:
            print(f"💾 Storing {len(new_memories)} semantic memories...")
            for memory in new_memories:
                self.memory_block.semantic_memories.store_memory(memory)
            print(f"✅ Memories stored successfully")
        else:
            print("ℹ️ No new memories extracted")
        
        # Flush history to last 3 messages
        self.message_history = self.message_history[-2:]
        print(f"🗑️ Flushed history, keeping last {len(self.message_history)} messages")
    
    def _retrieve_relevant_memories(self, query: str, top_k: int = 5) -> List[str]:
        """Retrieve relevant semantic memories for the query."""
        
        results = self.memory_block.semantic_memories.retrieve_memories(
            query_texts=[query],
            top_k=top_k
        )
        
        # Format memories for context
        formatted_memories = []
        for memory in results[0]:
            formatted_memories.append(
                f"[{memory.type.upper()}] {memory.content} "
                f"(entities: {', '.join(memory.entities)}, confidence: {memory.confidence:.2f})"
            )
        
        return formatted_memories
    
    def _build_system_prompt(self, retrieved_memories: List[str]) -> str:
        """Build system prompt with memories and recursive summary."""
        
        base_prompt = "You are a helpful AI assistant with access to conversation history and memories."
        
        context_parts = [base_prompt]
        
        # Add recursive summary if exists
        if self.recursive_summary:
            context_parts.append(f"\n<CONVERSATION_SUMMARY>\n{self.recursive_summary}\n</CONVERSATION_SUMMARY>")
        
        # Add retrieved memories if exist
        if retrieved_memories:
            memories_text = "\n".join([f"- {mem}" for mem in retrieved_memories])
            context_parts.append(f"\n<RELEVANT_MEMORIES>\n{memories_text}\n</RELEVANT_MEMORIES>")
        
        context_parts.append("\nUse the above context to provide informed, contextual responses.")
        
        return "\n".join(context_parts)
    
    async def send_message(self, user_message: str) -> str:
        """
        Send a message and get response.
        
        Process:
        1. Retrieve relevant memories
        2. Build context with memories + recursive summary
        3. Add to message history
        4. Get LLM response
        5. Check if memory processing needed (8 messages)
        """
        
        # Retrieve relevant memories for this query
        print(f"\n🔍 Retrieving memories for: '{user_message[:50]}...'")
        retrieved_memories = self._retrieve_relevant_memories(user_message)
        print(f"📚 Retrieved {len(retrieved_memories)} relevant memories")
        
        # Build system prompt with context
        system_prompt = self._build_system_prompt(retrieved_memories)
        
        # Add user message to history
        self.message_history.append({"role": "user", "content": user_message})
        
        # Build messages for API call (system + recent history + current query)
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.message_history)
        
        # Get response from Groq
        loop = asyncio.get_event_loop()
        completion = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.7,
                max_completion_tokens=1024,
                top_p=1
            )
        )
        
        assistant_response = completion.choices[0].message.content
        
        # Add assistant response to history
        self.message_history.append({"role": "assistant", "content": assistant_response})
        
        # Check if we need to process memory window
        if len(self.message_history) >= 2:
            await self._process_memory_window()
        
        return assistant_response
    
    def print_status(self):
        """Print current session status."""
        print(f"\n{'='*60}")
        print(f"📊 SESSION STATUS")
        print(f"{'='*60}")
        print(f"Message History: {len(self.message_history)} messages")
        print(f"Recursive Summary: {'Yes' if self.recursive_summary else 'No'} "
              f"({len(self.recursive_summary)} chars)" if self.recursive_summary else "")
        print(f"Memory Block ID: {self.memory_block.meta_data.id}")
        print(f"{'='*60}\n")


async def interactive_chat_demo():
    """Interactive chat demo with memory management."""
    
    print("\n" + "="*60)
    print("🚀 CHAT SESSION WITH MEMORY PIPELINE")
    print("="*60)
    print("Commands:")
    print("  - Type your message to chat")
    print("  - 'status' to see session status")
    print("  - 'exit' or 'quit' to end session")
    print("="*60 + "\n")
    
    # Initialize session
    session = ChatSession(
        user_id="demo_user",
        session_description="Interactive chat demo with memory extraction"
    )
    
    while True:
        try:
            # Get user input
            user_input = input("\n💬 You: ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.lower() in ['exit', 'quit']:
                print("\n👋 Ending session. Goodbye!")
                break
            
            if user_input.lower() == 'status':
                session.print_status()
                continue
            
            # Send message and get response
            response = await session.send_message(user_input)
            print(f"\n🤖 Assistant: {response}")
            
        except KeyboardInterrupt:
            print("\n\n👋 Session interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


async def automated_demo():
    """Automated demo with predefined messages to test memory extraction."""
    
    print("\n" + "="*60)
    print("🤖 AUTOMATED DEMO - Memory Extraction Test")
    print("="*60 + "\n")
    
    session = ChatSession(
        user_id="test_user",
        session_description="Automated demo testing memory extraction"
    )
    
    # Predefined conversation that should trigger memory extraction
    demo_messages = [
        "Hi! My name is Alex and I live in San Francisco.",
        "I work as a software engineer at TechCorp.",
        "I'm currently working on a machine learning project focused on NLP.",
        "My team lead is Sarah Johnson, she's been very helpful.",
        "We're planning to deploy the model by March 15th.",
        "I love hiking in my free time, especially in Yosemite.",
        "Yesterday, I attended a conference on AI safety in Berkeley.",
        "The keynote speaker was Dr. Emily Chen, she talked about responsible AI.",
        # This should trigger memory processing
        "What do you know about me so far?",
        "Tell me about my work project.",
    ]
    
    for i, message in enumerate(demo_messages, 1):
        print(f"\n{'─'*60}")
        print(f"Message {i}/{len(demo_messages)}")
        print(f"{'─'*60}")
        print(f"💬 User: {message}")
        
        response = await session.send_message(message)
        print(f"🤖 Assistant: {response}")
        
        # Small delay for readability
        await asyncio.sleep(1)
    
    # Show final status
    session.print_status()


async def main():
    """Main entry point - choose demo mode."""
    
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "auto":
        await automated_demo()
    else:
        await interactive_chat_demo()


if __name__ == "__main__":
    asyncio.run(main())
