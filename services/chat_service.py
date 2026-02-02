"""Chat service with memory integration."""

import asyncio
from typing import List, Dict, Optional
from datetime import datetime

from models.container import MemoryBlock
from models.units import SemanticMemoryUnit, CoreMemoryUnit
from llm.llm_manager import llm_manager
from llm.output_models import SummaryOutput
from prompts import SUMMARY_SYSTEM_PROMPT, ASSISTANT_BASE_PROMPT


class ChatService:
    """
    Chat service with memory augmentation.
    
    Handles:
    - Message history management
    - Memory extraction (semantic + core)
    - Recursive summarization
    - Context assembly for LLM
    """
    
    def __init__(
        self,
        memory_block: MemoryBlock,
        memory_window: int = 10,
        keep_last_n: int = 4
    ):
        """
        Initialize chat service.
        
        Args:
            memory_block: Attached memory block
            memory_window: Messages before triggering memory processing
            keep_last_n: Messages to keep after flushing
        """
        self.memory_block = memory_block
        self.memory_window = memory_window
        self.keep_last_n = keep_last_n
        
        # Session state
        self.message_history: List[Dict[str, str]] = []
        self.recursive_summary: str = ""
    
    # ========================================================================
    # MEMORY WINDOW PROCESSING
    # ========================================================================
    
    async def _process_memory_window(self):
        """
        Process memory window: extract semantic + core memories, generate summary, flush history.
        """
        print(f"\n{'='*70}")
        print(f"🔄 MEMORY PROCESSING PIPELINE")
        print(f"{'='*70}")
        print(f"Processing {len(self.message_history)} messages...")
        
        # STEP 1: Extract semantic memories
        if self.memory_block.semantic_memories:
            print(f"\n📝 STEP 1: Semantic Memory Extraction")
            semantic_memories = await self.memory_block.semantic_memories.extract_semantic_memories(
                messages=self.message_history
            )
            print(f"   ✓ Extracted {len(semantic_memories)} semantic memories")
            
            # Store memories
            for mem in semantic_memories:
                self.memory_block.semantic_memories.store_memory(mem)
            print(f"   ✓ Stored {len(semantic_memories)} memories")
        
        # STEP 2: Extract and update core memory
        if self.memory_block.core_memories:
            print(f"\n🧠 STEP 2: Core Memory Extraction")
            old_core = await self.memory_block.core_memories.get_memories()
            
            new_core = await self.memory_block.core_memories.create_new_core_memory(
                messages=self.message_history,
                old_core_memory=old_core
            )
            
            # Store updated core memory
            await self.memory_block.core_memories.store_memory(new_core)
            print(f"   ✓ Updated core memory")
            if new_core.persona_content:
                print(f"     Persona: {new_core.persona_content[:60]}...")
            if new_core.human_content:
                print(f"     Human: {new_core.human_content[:60]}...")
        
        # STEP 3: Generate recursive summary
        print(f"\n📊 STEP 3: Recursive Summary")
        new_summary = await self._generate_recursive_summary(self.message_history)
        self.recursive_summary = new_summary
        print(f"   ✓ Summary updated ({len(new_summary)} chars)")
        
        # STEP 4: Flush history
        print(f"\n🗑️  STEP 4: Flushing Message History")
        print(f"   Before: {len(self.message_history)} messages")
        self.message_history = self.message_history[-self.keep_last_n:]
        print(f"   After: {len(self.message_history)} messages (kept last {self.keep_last_n})")
        
        print(f"\n{'='*70}")
        print(f"✅ PIPELINE COMPLETE")
        print(f"{'='*70}\n")
    
    async def _generate_recursive_summary(
        self,
        messages: List[Dict[str, str]]
    ) -> str:
        """
        Generate recursive summary using LangChain.
        
        Args:
            messages: Recent conversation messages
            
        Returns:
            Updated summary
        """
        conversation_text = "\n".join(
            [f"{msg['role'].upper()}: {msg['content']}" for msg in messages]
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
                temperature=0.3
            )
            
            result = await chain.ainvoke({"input": user_input})
            return result.summary
            
        except Exception as e:
            print(f"⚠️ Failed to generate summary: {e}")
            return self.recursive_summary
    
    # ========================================================================
    # RETRIEVAL & CONTEXT BUILDING
    # ========================================================================
    
    def _retrieve_semantic_memories(
        self,
        query: str,
        top_k: int = 5
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
        base_prompt: str = ASSISTANT_BASE_PROMPT
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
            semantic_text = "\n\n".join([
                f"[{mem.type.upper()}] {mem.content}\n"
                f"  Keywords: {', '.join(mem.keywords[:5])}"
                for mem in semantic_memories
            ])
            parts.append(f"\n<SEMANTIC_MEMORY>\n{semantic_text}\n</SEMANTIC_MEMORY>")
        
        return "\n".join(parts)
    
    # ========================================================================
    # CHAT INTERFACE
    # ========================================================================
    
    async def send_message(self, user_message: str) -> str:
        """
        Process user message and generate response.
        
        Args:
            user_message: User's input
            
        Returns:
            Assistant's response
        """
        print(f"\n{'─'*70}")
        print(f"💬 Processing message...")
        print(f"{'─'*70}")
        
        # Retrieve memories
        print(f"🔍 Retrieving memories...")
        semantic_memories = self._retrieve_semantic_memories(user_message, top_k=5)
        core_memory = await self._get_core_memory()
        print(f"   📚 Semantic: {len(semantic_memories)} memories")
        print(f"   🧠 Core: {'Yes' if core_memory else 'No'}")
        
        # Build system prompt
        system_prompt = await self._build_system_prompt(semantic_memories, core_memory)
        
        # Add user message to history
        self.message_history.append({"role": "user", "content": user_message})
        
        # Build messages for LLM
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.message_history)
        
        # Get response using LangChain
        try:
            llm = llm_manager.get_chat_llm(temperature=0.7)
            response = await llm.ainvoke(messages)
            assistant_response = response.content
        except Exception as e:
            print(f"⚠️ LLM error: {e}")
            assistant_response = "I apologize, but I encountered an error processing your message."
        
        # Add assistant response to history
        self.message_history.append({"role": "assistant", "content": assistant_response})
        
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
        print(f"Block: {self.memory_block.meta_data.id}")
        print(f"Name: {self.memory_block.name}")
        print(f"Message History: {len(self.message_history)} messages")
        print(f"Memory Window: {self.memory_window} messages")
        print(f"Recursive Summary: {'Yes' if self.recursive_summary else 'No'}")
        if self.recursive_summary:
            print(f"  ({len(self.recursive_summary)} chars)")
        print(f"{'='*60}\n")
