"""
Complete Chat Session with Memory Pipeline + Deduplication
===========================================================

Features:
- PS1 for Semantic Memories (events, facts, opinions)
- Modified PS1 for Resource Memories (documents, images, links)
- Simple extraction for Core Memories (user profile, preferences)
- Cross-memory-type deduplication to prevent context overlap
- Recursive summarization
- Sliding window management
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import json
from groq import Groq
from dotenv import load_dotenv
import uuid

from models.units import SemanticMemoryUnit, CoreMemoryUnit, ResourceMemoryUnit, MemoryUnitMetaData
from vector_db.mem_block_setup import MemBlockQdrantManager

load_dotenv()

client = Groq()
MODEL = "llama-3.1-8b-instant"


# ============================================================================
# PS1: STRUCTURED NOTE CONSTRUCTION FOR SEMANTIC MEMORIES
# ============================================================================

PS1_SEMANTIC_PROMPT = """Generate a structured analysis of the following conversation for semantic memory storage.

Your output will be used for:
- vector embedding and semantic retrieval
- memory linking with past events and facts
- future memory refinement and evolution

Instructions:

1. Keywords
   - Identify the most salient and retrieval-effective keywords.
   - Focus on concrete technical nouns, actions, constraints, and entities.
   - Avoid generic verbs (e.g., "use", "do", "make") unless they carry domain-specific meaning.
   - Do NOT include speaker names, timestamps, or conversational filler.
   - At least 3 keywords, ordered from most to least important.

2. Context
   - Write exactly ONE sentence that captures:
     • the primary domain or topic
     • the user's intent, concern, or goal
     • whether this represents new information, a refinement, or continuation
   - The sentence should be extensible for future memory refinement.

3. Tags
   - Generate high-level categorical tags including:
     • domain tags (e.g., programming, systems, AI)
     • functional tags (e.g., optimization, design, debugging)
     • memory-nature tags (e.g., event, factual, planning, concern)
   - At least 3 tags, avoid redundancy.

4. Type
   - Classify as: `fact`, `event`, or `opinion`
   - fact: objective information
   - event: past or planned occurrence
   - opinion: user's perspective or preference

5. Entities
   - Extract key entities: people, places, technologies, tools, concepts
   - Focus on nouns and proper nouns important for retrieval

Output format (JSON only):

{
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "context": "One sentence description",
  "tags": ["tag1", "tag2", "tag3"],
  "type": "fact | event | opinion",
  "entities": ["entity1", "entity2"]
}"""


# ============================================================================
# MODIFIED PS1: FOR RESOURCE MEMORIES (documents, images, links)
# ============================================================================

PS1_RESOURCE_PROMPT = """Analyze this resource content for memory storage and retrieval.

The resource could be a document, image description, video transcript, or web link.

IMPORTANT: Extract information ONLY from the resource content itself, NOT from any surrounding context.

Instructions:

1. Keywords
   - Extract key terms that make this resource findable
   - Focus on: main topics, technologies, names, concepts mentioned IN the resource
   - At least 3 keywords

2. Context
   - ONE sentence describing:
     • what the resource is about (based ONLY on its content)
     • its purpose or type (guide, reference, tutorial, etc.)
   - Do NOT mention user projects or plans

3. Tags
   - Categorize with tags like:
     • resource type (document, guide, reference, tutorial)
     • domain (programming, business, personal)
     • topics covered
   - At least 3 tags

4. Entities
   - Named entities: people, companies, products, tools mentioned IN the resource
   - Important for finding this resource later

Output format (JSON only):

{
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "context": "One sentence about the resource content",
  "tags": ["tag1", "tag2", "tag3"],
  "entities": ["entity1", "entity2"]
}"""


# ============================================================================
# SIMPLE CORE MEMORY EXTRACTION
# ============================================================================

CORE_MEMORY_PROMPT = """Extract stable, enduring facts about the user from this conversation.

Focus ONLY on:
- User's name, location, occupation
- Lasting preferences (communication style, interests, dislikes)
- Important relationships (family, colleagues mentioned by name)
- Self-identifying attributes

Do NOT extract:
- Temporary events or plans
- Opinions that may change
- Specific projects (those go to semantic memory)

Output format (JSON array):

[
  {"content": "User's name is Alex"},
  {"content": "User prefers concise, direct communication"},
  {"content": "User is a software engineer"}
]

If no core memories found, return empty array: []"""


class ChatSession:
    """
    Complete chat session with PS1-enhanced memory pipeline and deduplication.
    
    Memory Architecture:
    - Semantic: PS1 extraction (events, facts, opinions) - retrieved per query
    - Core: Simple extraction (stable user facts) - always injected
    - Resource: Modified PS1 (uploaded files) - retrieved on demand
    
    Deduplication: Prevents semantic overlap between memory types
    """
    
    def __init__(self, user_id: str, session_description: str = "Chat session memories"):
        self.user_id = user_id
        self.message_history: List[Dict[str, str]] = []
        self.recursive_summary: str = ""
        
        # Initialize memory block
        self.memory_manager = MemBlockQdrantManager()
        self.memory_block = self.memory_manager.create_memory_block(
            name=f"ChatSession_{user_id}",
            description=session_description,
            user_id=user_id
        )
        
        print(f"✅ Chat session initialized for user: {user_id}")
        print(f"   Memory Block ID: {self.memory_block.meta_data.id}")
    
    # ========================================================================
    # SEMANTIC MEMORY: PS1 EXTRACTION
    # ========================================================================
    
    async def _ps1_extract_semantic_memories(
        self, 
        messages: List[Dict[str, str]]
    ) -> List[SemanticMemoryUnit]:
        """
        PS1: Extract structured semantic memories from conversation.
        
        Returns SemanticMemoryUnits with enriched PS1 fields.
        """
        
        # Format conversation
        conversation_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}" 
            for msg in messages
        ])
        
        user_prompt = f"""Conversation to analyze:

{conversation_text}

Extract structured semantic memories:"""

        loop = asyncio.get_event_loop()
        completion = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": PS1_SEMANTIC_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                max_completion_tokens=2048,
                response_format={"type": "json_object"}
            )
        )
        
        raw_response = completion.choices[0].message.content.strip()
        
        try:
            ps1_data = json.loads(raw_response)
            
            # Create SemanticMemoryUnit with PS1 enrichment
            current_time = datetime.now().isoformat()
            
            # Build enriched embedding text (PS1 Step 2)
            embedding_text = f"""{conversation_text}

Keywords: {', '.join(ps1_data.get('keywords', []))}
Tags: {', '.join(ps1_data.get('tags', []))}
Context: {ps1_data.get('context', '')}
Entities: {', '.join(ps1_data.get('entities', []))}""".strip()
            
            memory_unit = SemanticMemoryUnit(
                content=conversation_text[:500],  # Truncate for storage
                type=ps1_data.get('type', 'fact'),
                source="conversation",
                confidence=0.8,
                memory_time=current_time,
                entities=ps1_data.get('entities', []),
                tags=ps1_data.get('tags', []),
                updated_at=current_time,
                meta_data=MemoryUnitMetaData(usage=[current_time]),
                # PS1 fields
                keywords=ps1_data.get('keywords', []),
                context_sentence=ps1_data.get('context', ''),
                embedding_text=embedding_text
            )
            
            return [memory_unit]
            
        except json.JSONDecodeError as e:
            print(f"⚠️ Failed to parse PS1 semantic JSON: {e}")
            return []
    
    # ========================================================================
    # CORE MEMORY: SIMPLE EXTRACTION
    # ========================================================================
    
    async def _extract_core_memories(
        self,
        messages: List[Dict[str, str]]
    ) -> List[CoreMemoryUnit]:
        """
        Simple extraction of stable user facts.
        No PS1 needed - core memories are always injected, not retrieved.
        """
        
        conversation_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}" 
            for msg in messages
        ])
        
        user_prompt = f"""Conversation:

{conversation_text}

Extract core memories:"""

        loop = asyncio.get_event_loop()
        completion = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": CORE_MEMORY_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                max_completion_tokens=1024,
                response_format={"type": "json_object"}
            )
        )
        
        raw_response = completion.choices[0].message.content.strip()
        
        # Handle both array and object responses
        try:
            parsed = json.loads(raw_response)
            
            # If it's wrapped in an object, extract the array
            if isinstance(parsed, dict):
                # Try common keys
                core_memories_data = (
                    parsed.get('core_memories') or 
                    parsed.get('memories') or 
                    parsed.get('items') or
                    []
                )
            else:
                core_memories_data = parsed
            
            # Convert to CoreMemoryUnit objects
            core_units = []
            for item in core_memories_data:
                if isinstance(item, dict) and 'content' in item:
                    core_units.append(CoreMemoryUnit(content=item['content']))
                elif isinstance(item, str):
                    core_units.append(CoreMemoryUnit(content=item))
            
            return core_units
            
        except json.JSONDecodeError as e:
            print(f"⚠️ Failed to parse core memory JSON: {e}")
            return []
    
    # ========================================================================
    # RESOURCE MEMORY: MODIFIED PS1 FOR UPLOADED FILES
    # ========================================================================
    
    async def _ps1_extract_resource_memory(
        self,
        content: str,
        resource_type: str,
        resource_link: str
    ) -> ResourceMemoryUnit:
        """
        Modified PS1: Extract structured metadata for uploaded resources.
        
        IMPORTANT: Extracts info ONLY from resource content, not user context.
        
        Args:
            content: Extracted text from document/image/file
            resource_type: Type of resource (document, image, link, etc.)
            resource_link: Path or URL to resource
        """
        
        user_prompt = f"""Resource Type: {resource_type}

Content:
{content[:2000]}

Analyze this resource (extract info ONLY from the content above):"""

        loop = asyncio.get_event_loop()
        completion = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": PS1_RESOURCE_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                max_completion_tokens=1024,
                response_format={"type": "json_object"}
            )
        )
        
        raw_response = completion.choices[0].message.content.strip()
        
        try:
            ps1_data = json.loads(raw_response)
            
            # Build enriched embedding text
            embedding_text = f"""{content[:500]}

Resource Type: {resource_type}
Keywords: {', '.join(ps1_data.get('keywords', []))}
Tags: {', '.join(ps1_data.get('tags', []))}
Context: {ps1_data.get('context', '')}
Entities: {', '.join(ps1_data.get('entities', []))}""".strip()
            
            resource_unit = ResourceMemoryUnit(
                content=content[:500],  # Summary
                resource_type=resource_type,
                resource_link=resource_link,
                # PS1 fields
                keywords=ps1_data.get('keywords', []),
                tags=ps1_data.get('tags', []),
                entities=ps1_data.get('entities', []),
                context_sentence=ps1_data.get('context', ''),
                embedding_text=embedding_text
            )
            
            return resource_unit
            
        except json.JSONDecodeError as e:
            print(f"⚠️ Failed to parse PS1 resource JSON: {e}")
            # Fallback: create basic resource unit
            return ResourceMemoryUnit(
                content=content[:500],
                resource_type=resource_type,
                resource_link=resource_link
            )
    
    # ========================================================================
    # RECURSIVE SUMMARY
    # ========================================================================
    
    async def _generate_recursive_summary(self, messages: List[Dict[str, str]]) -> str:
        """Generate recursive summary of conversation."""
        
        system_prompt = """You are a conversation summarizer. Create a concise recursive summary that:
1. Builds upon the previous summary (if any)
2. Captures key topics, decisions, and important information
3. Maintains temporal context
4. Is concise but comprehensive

Return ONLY the summary text, no JSON or formatting."""

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
    
    # ========================================================================
    # DEDUPLICATION LOGIC
    # ========================================================================
    
    def _calculate_keyword_overlap(
        self,
        keywords1: List[str],
        keywords2: List[str]
    ) -> float:
        """
        Calculate Jaccard similarity between two keyword sets.
        
        Returns:
            float: Overlap ratio (0.0 to 1.0)
        """
        if not keywords1 or not keywords2:
            return 0.0
        
        set1 = set(k.lower() for k in keywords1)
        set2 = set(k.lower() for k in keywords2)
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_entity_overlap(
        self,
        entities1: List[str],
        entities2: List[str]
    ) -> float:
        """
        Calculate entity overlap between two memory units.
        
        Returns:
            float: Overlap ratio (0.0 to 1.0)
        """
        if not entities1 or not entities2:
            return 0.0
        
        set1 = set(e.lower() for e in entities1)
        set2 = set(e.lower() for e in entities2)
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def _are_memories_duplicate(
        self,
        mem1_keywords: List[str],
        mem1_entities: List[str],
        mem2_keywords: List[str],
        mem2_entities: List[str],
        keyword_threshold: float = 0.5,
        entity_threshold: float = 0.4
    ) -> bool:
        """
        Determine if two memories are duplicates based on keyword and entity overlap.
        
        Args:
            mem1_keywords: Keywords from first memory
            mem1_entities: Entities from first memory
            mem2_keywords: Keywords from second memory
            mem2_entities: Entities from second memory
            keyword_threshold: Minimum overlap for keywords (default 0.5 = 50%)
            entity_threshold: Minimum overlap for entities (default 0.4 = 40%)
        
        Returns:
            bool: True if memories are considered duplicates
        """
        keyword_overlap = self._calculate_keyword_overlap(mem1_keywords, mem2_keywords)
        entity_overlap = self._calculate_entity_overlap(mem1_entities, mem2_entities)
        
        # Consider duplicate if EITHER threshold exceeded
        # (high keyword overlap OR high entity overlap)
        is_duplicate = (
            keyword_overlap >= keyword_threshold or 
            entity_overlap >= entity_threshold
        )
        
        return is_duplicate
    
    def _deduplicate_across_types(
        self,
        semantic_memories: List[SemanticMemoryUnit],
        resource_memories: List[ResourceMemoryUnit]
    ) -> Tuple[List[SemanticMemoryUnit], List[ResourceMemoryUnit]]:
        """
        Remove duplicate information across semantic and resource memories.
        
        Strategy:
        - Resources are considered "authoritative" (primary sources)
        - Remove semantic memories that overlap significantly with resources
        - Keep all resources (user uploaded them for a reason)
        
        Args:
            semantic_memories: Retrieved semantic memories
            resource_memories: Retrieved resource memories
        
        Returns:
            Tuple of (filtered_semantic, all_resources)
        """
        if not resource_memories:
            # No resources, return all semantic memories
            return semantic_memories, resource_memories
        
        print(f"\n🔍 Deduplication Check:")
        print(f"   Semantic memories: {len(semantic_memories)}")
        print(f"   Resource memories: {len(resource_memories)}")
        
        filtered_semantic = []
        removed_count = 0
        
        for sem_mem in semantic_memories:
            is_duplicate = False
            
            for res_mem in resource_memories:
                # Check overlap
                if self._are_memories_duplicate(
                    mem1_keywords=sem_mem.keywords or [],
                    mem1_entities=sem_mem.entities or [],
                    mem2_keywords=res_mem.keywords or [],
                    mem2_entities=res_mem.entities or [],
                    keyword_threshold=0.5,  # 50% keyword overlap
                    entity_threshold=0.4    # 40% entity overlap
                ):
                    is_duplicate = True
                    removed_count += 1
                    print(f"   ⚠️  Removing semantic memory (overlaps with resource):")
                    print(f"       Semantic: {sem_mem.keywords[:3]}...")
                    print(f"       Resource: {res_mem.keywords[:3]}...")
                    break
            
            if not is_duplicate:
                filtered_semantic.append(sem_mem)
        
        print(f"   ✓ Kept {len(filtered_semantic)} semantic memories")
        print(f"   ✓ Removed {removed_count} duplicate semantic memories")
        
        return filtered_semantic, resource_memories
    
    # ========================================================================
    # MEMORY WINDOW PROCESSING
    # ========================================================================
    
    async def _process_memory_window(self):
        """
        Complete pipeline when 8 messages reached:
        
        1. PS1: Extract semantic memories (events, facts, opinions)
        2. Simple: Extract core memories (stable user facts)
        3. Store both in respective collections
        4. Generate recursive summary
        5. Flush message history to last 2 messages
        """
        print(f"\n{'='*70}")
        print(f"🔄 MEMORY PROCESSING PIPELINE")
        print(f"{'='*70}")
        print(f"Processing {len(self.message_history)} messages...")
        
        # STEP 1: PS1 Semantic Memory Extraction
        print(f"\n📝 STEP 1: PS1 Semantic Memory Extraction")
        semantic_memories = await self._ps1_extract_semantic_memories(self.message_history)
        print(f"   ✓ Extracted {len(semantic_memories)} semantic memories")
        
        if semantic_memories:
            for i, mem in enumerate(semantic_memories, 1):
                print(f"\n   Semantic Memory {i}:")
                print(f"   - Type: {mem.type}")
                print(f"   - Keywords: {mem.keywords}")
                print(f"   - Context: {mem.context_sentence[:80]}...")
                print(f"   - Tags: {mem.tags}")
                print(f"   - Entities: {mem.entities}")
        
        # STEP 2: Simple Core Memory Extraction
        print(f"\n🎯 STEP 2: Core Memory Extraction")
        core_memories = await self._extract_core_memories(self.message_history)
        print(f"   ✓ Extracted {len(core_memories)} core memories")
        
        if core_memories:
            for i, mem in enumerate(core_memories, 1):
                print(f"   - {mem.content}")
        
        # STEP 3: Store Memories
        print(f"\n💾 STEP 3: Storing Memories")
        
        for mem in semantic_memories:
            self.memory_block.semantic_memories.store_memory(mem)
        print(f"   ✓ Stored {len(semantic_memories)} semantic memories")
        
        for mem in core_memories:
            self.memory_block.core_memories.store_memory(mem)
        print(f"   ✓ Stored {len(core_memories)} core memories")
        
        # STEP 4: Generate Recursive Summary
        print(f"\n📊 STEP 4: Recursive Summary")
        new_summary = await self._generate_recursive_summary(self.message_history)
        self.recursive_summary = new_summary
        print(f"   ✓ Summary updated ({len(new_summary)} chars)")
        
        # STEP 5: Flush History
        print(f"\n🗑️  STEP 5: Flushing Message History")
        self.message_history = self.message_history[-2:]
        print(f"   ✓ Kept last {len(self.message_history)} messages")
        
        print(f"\n{'='*70}")
        print(f"✅ PIPELINE COMPLETE")
        print(f"{'='*70}\n")
    
    # ========================================================================
    # RETRIEVAL WITH DEDUPLICATION
    # ========================================================================
    
    def _retrieve_semantic_memories(self, query: str, top_k: int = 5) -> List[SemanticMemoryUnit]:
        """Retrieve relevant semantic memories."""
        results = self.memory_block.semantic_memories.retrieve_memories([query], top_k=top_k)
        return results[0] if results else []
    
    def _retrieve_resource_memories(self, query: str, top_k: int = 3) -> List[ResourceMemoryUnit]:
        """Retrieve relevant resource memories."""
        results = self.memory_block.resource_memories.retrieve_memories([query], top_k=top_k)
        return results[0] if results else []
    
    def _get_all_core_memories(self) -> List[CoreMemoryUnit]:
        """Get all core memories (always injected in context)."""
        # For now, retrieve top 10 (in production, implement get_all_memories())
        results = self.memory_block.core_memories.retrieve_memories(["user profile"], top_k=10)
        return results[0] if results else []
    
    # ========================================================================
    # CONTEXT BUILDING
    # ========================================================================
    
    def _build_system_prompt(
        self,
        semantic_memories: List[SemanticMemoryUnit],
        core_memories: List[CoreMemoryUnit],
        resource_memories: List[ResourceMemoryUnit]
    ) -> str:
        """Build system prompt with all memory types."""
        
        base_prompt = """You are a helpful AI assistant with access to persistent memory.

When using context:
- Synthesize information rather than repeating it
- If semantic memories and resources overlap, cite the resource as primary source
- Provide concise, informed responses based on available context"""
        
        parts = [base_prompt]
        
        # Core memories (always present)
        if core_memories:
            core_text = "\n".join([f"- {mem.content}" for mem in core_memories])
            parts.append(f"\n<CORE_MEMORY>\n{core_text}\n</CORE_MEMORY>")
        
        # Recursive summary
        if self.recursive_summary:
            parts.append(f"\n<CONVERSATION_SUMMARY>\n{self.recursive_summary}\n</CONVERSATION_SUMMARY>")
        
        # Semantic memories (retrieved, deduplicated)
        if semantic_memories:
            semantic_text = "\n\n".join([
                f"[{mem.type.upper()}] {mem.content[:200]}...\n"
                f"  Keywords: {', '.join(mem.keywords[:5])}\n"
                f"  Context: {mem.context_sentence}\n"
                f"  Tags: {', '.join(mem.tags[:5])}"
                for mem in semantic_memories
            ])
            parts.append(f"\n<SEMANTIC_MEMORIES>\n{semantic_text}\n</SEMANTIC_MEMORIES>")
        
        # Resource memories (retrieved)
        if resource_memories:
            resource_text = "\n\n".join([
                f"[{mem.resource_type.upper()}] {mem.content[:200]}...\n"
                f"  Keywords: {', '.join(mem.keywords[:5])}\n"
                f"  Context: {mem.context_sentence}\n"
                f"  Source: {mem.resource_link}"
                for mem in resource_memories
            ])
            parts.append(f"\n<RESOURCES>\n{resource_text}\n</RESOURCES>")
        
        return "\n".join(parts)
    
    # ========================================================================
    # MAIN CHAT INTERFACE
    # ========================================================================
    
    async def send_message(self, user_message: str) -> str:
        """
        Send message and get response.
        
        Flow:
        1. Retrieve semantic memories (facts, events)
        2. Get all core memories (always injected)
        3. Optionally retrieve resources
        4. DEDUPLICATE across memory types
        5. Build context
        6. Get LLM response
        7. Check if memory processing needed (8 messages)
        """
        
        # Retrieve memories
        print(f"\n🔍 Retrieving memories for: '{user_message[:50]}...'")
        
        semantic_memories = self._retrieve_semantic_memories(user_message, top_k=5)
        core_memories = self._get_all_core_memories()
        
        # Check if user mentions files/documents
        mentions_resource = any(word in user_message.lower() for word in 
            ['document', 'file', 'upload', 'pdf', 'image', 'guide', 'resource'])
        resource_memories = []
        if mentions_resource:
            resource_memories = self._retrieve_resource_memories(user_message, top_k=3)
        
        print(f"   📚 Semantic (before dedup): {len(semantic_memories)}")
        print(f"   🎯 Core: {len(core_memories)}")
        print(f"   📎 Resources: {len(resource_memories)}")
        
        # DEDUPLICATION: Remove semantic memories that overlap with resources
        if semantic_memories and resource_memories:
            semantic_memories, resource_memories = self._deduplicate_across_types(
                semantic_memories,
                resource_memories
            )
            print(f"   📚 Semantic (after dedup): {len(semantic_memories)}")
        
        # Build system prompt
        system_prompt = self._build_system_prompt(
            semantic_memories,
            core_memories,
            resource_memories
        )
        
        # Add to history
        self.message_history.append({"role": "user", "content": user_message})
        
        # Build messages
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
                top_p=1
            )
        )
        
        assistant_response = completion.choices[0].message.content
        
        # Add to history
        self.message_history.append({"role": "assistant", "content": assistant_response})
        
        # Process memory window if threshold reached
        if len(self.message_history) >= 8:
            await self._process_memory_window()
        
        return assistant_response
    
    # ========================================================================
    # FILE UPLOAD INTERFACE
    # ========================================================================
    
    async def upload_file(
        self,
        file_path: str,
        resource_type: str,
        content: Optional[str] = None
    ) -> str:
        """
        Upload a file and extract resource memory.
        
        Args:
            file_path: Path to the file
            resource_type: Type (document, image, video, audio, link)
            content: Extracted text content (if None, will try to extract)
        
        Returns:
            Resource ID
        """
        
        print(f"\n📎 Uploading resource: {file_path}")
        print(f"   Type: {resource_type}")
        
        # If content not provided, extract it
        if content is None:
            # In production, implement actual file reading
            content = f"Extracted content from {file_path}"
            print(f"   ⚠️  Using placeholder content (implement file extraction)")
        
        # Extract resource memory with modified PS1
        resource_memory = await self._ps1_extract_resource_memory(
            content,
            resource_type,
            file_path
        )
        
        # Store
        success = self.memory_block.resource_memories.store_memory(resource_memory)
        
        if success:
            print(f"   ✅ Resource stored successfully")
            print(f"      Keywords: {resource_memory.keywords}")
            print(f"      Tags: {resource_memory.tags}")
            print(f"      Context: {resource_memory.context_sentence[:80]}...")
            return f"resource_{uuid.uuid4().hex[:8]}"
        else:
            print(f"   ❌ Failed to store resource")
            return None
    
    # ========================================================================
    # STATUS
    # ========================================================================
    
    def print_status(self):
        """Print current session status."""
        print(f"\n{'='*60}")
        print(f"📊 SESSION STATUS")
        print(f"{'='*60}")
        print(f"User: {self.user_id}")
        print(f"Memory Block: {self.memory_block.meta_data.id}")
        print(f"Message History: {len(self.message_history)} messages")
        print(f"Recursive Summary: {'Yes' if self.recursive_summary else 'No'}")
        if self.recursive_summary:
            print(f"  ({len(self.recursive_summary)} chars)")
        print(f"{'='*60}\n")


# ============================================================================
# DEMO
# ============================================================================

async def demo_with_deduplication():
    """Demo showing deduplication in action."""
    
    print("\n" + "="*70)
    print("🚀 MEMORY PIPELINE WITH DEDUPLICATION DEMO")
    print("="*70)
    print("Features:")
    print("  - PS1 for Semantic Memories")
    print("  - Modified PS1 for Resources")
    print("  - Simple Core Memory extraction")
    print("  - Cross-type deduplication")
    print("="*70 + "\n")
    
    session = ChatSession(
        user_id="demo_user",
        session_description="Deduplication demo"
    )
    
    # Conversation
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
    
    for i, msg in enumerate(messages, 1):
        print(f"\n{'─'*70}")
        print(f"Message {i}/{len(messages)}")
        print(f"{'─'*70}")
        print(f"💬 User: {msg}")
        
        response = await session.send_message(msg)
        print(f"🤖 Assistant: {response}")
        
        await asyncio.sleep(0.5)
    
    # Upload a resource (PURE content, no user project mention)
    print(f"\n{'─'*70}")
    print(f"FILE UPLOAD")
    print(f"{'─'*70}")
    
    resource_id = await session.upload_file(
        file_path="/documents/redis_caching_guide.pdf",
        resource_type="document",
        content="""
Redis Caching Guide - Complete Reference

Chapter 1: Introduction to Redis
Redis is an open-source, in-memory data structure store used as a database, 
cache, and message broker. It supports various data structures including 
strings, hashes, lists, sets, and sorted sets.

Chapter 2: Caching Strategies
Redis implements several eviction policies for cache management:
- LRU (Least Recently Used): Removes least recently accessed items
- LFU (Least Frequently Used): Removes least frequently accessed items
- Random: Removes random items when memory limit reached
- TTL-based: Removes items based on expiration time

Chapter 3: Memory Optimization
Techniques for reducing memory footprint:
- Use appropriate data structures
- Set memory limits with maxmemory directive
- Configure eviction policies
- Monitor memory usage with INFO command
- Use Redis persistence for data durability

Chapter 4: Production Deployment
Best practices for production environments:
- Connection pooling for efficiency
- Cluster setup for high availability
- Monitoring and alerting
- Backup and recovery strategies
- Security configurations
"""
    )
    
    # Test retrieval with deduplication
    print(f"\n{'─'*70}")
    print(f"TESTING RETRIEVAL WITH DEDUPLICATION")
    print(f"{'─'*70}")
    
    final_response = await session.send_message(
        "Can you remind me about my caching project and find that Redis guide I uploaded?"
    )
    print(f"🤖 Assistant: {final_response}")
    
    # Show status
    session.print_status()


if __name__ == "__main__":
    asyncio.run(demo_with_deduplication())