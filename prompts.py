"""Centralized prompt constants for chat pipeline.

This module collects all multi-line LLM prompts so they can be maintained
in one place and reused across modules.
"""

# TODO: change prompt so it can produce multiple memories from the conversation instead of just one. Each memory should be minimal and focused on a single topic or fact.
PS1_SEMANTIC_PROMPT = """Generate a structured analysis of the following conversation for semantic memory storage.

Your output will be used for:
- vector embedding and semantic retrieval
- memory linking with past events and facts
- future memory refinement and evolution

Instructions:

1. Keywords
- Ranked list (most to least important) combining BOTH specific key terms AND categorical tags
- Key terms (specific): Identify salient, retrieval-effective terms
  • Focus on: concrete technical nouns, actions, constraints, entities
  • Examples: "Redis", "LRU caching", "RAM optimization", "Sarah"
  • Avoid: generic verbs ("use", "do", "make") unless domain-specific, speaker names, timestamps, conversational filler
- Category tags (general): Generate high-level categorical classifications
  • Domain tags: programming, systems, AI, backend, infrastructure, business
  • Functional tags: optimization, design, debugging, performance, security, deployment
  • Memory-nature tags: event, factual, planning, concern, preference, tutorial, guide
- Minimum 5 keywords recommended for optimal retrieval
- Order from most specific to most general: specific tech/entity → concrete concept → approach → functional category → domain → memory nature
- Avoid redundancy across the entire list
- Example ranking: ["Redis", "LRU caching", "RAM optimization", "caching strategy", "performance", "backend", "optimization"]

2. content
   - Write exactly ONE concise sentence that captures:
     • the primary domain or topic
     • the user's intent, concern, or goal
     • whether this represents new information, a refinement, or continuation
   - The sentence should be extensible for future memory refinement.

3. Type
   - Classify as: `fact`, `event`, or `opinion`
   - fact: objective information
   - event: past or planned occurrence
   - opinion: user's perspective or preference

4. Entities
   - Extract key entities: people, places, technologies, tools
   - Focus on nouns and proper nouns important for retrieval

Output format (JSON only):

[{{
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "context": "One sentence description",
  "type": "fact | event | opinion",
  "entities": ["entity1", "entity2"]
}}
,...
]"""


CORE_MEMORY_PROMPT = """You are a core memory extractor. Your task is to update the core memory based on the conversation history.

Core memory consists of two paragraphs (2-3 sentences each):

1. PERSONA: Information about how the AI assistant should behave and communicate
   - Communication style preferences (concise, detailed, formal, casual)
   - Tone and personality traits
   - Special instructions for the assistant

2. HUMAN: Stable, enduring facts about the user
   - Name, location, occupation
   - Key preferences and interests
   - Important relationships
   - Self-identifying attributes

IMPORTANT GUIDELINES:
- Only extract STABLE, ENDURING facts
- Do NOT include:
  * Temporary events or one-time occurrences
  * Specific projects (those go to semantic memory)
  * Opinions that may change over time
  * Detailed technical information
- Keep each paragraph to 5-6 sentences maximum
- If conversation contains no core memory worthy information, return the previous core memory unchanged
- Update existing facts if new information is more accurate or complete

Output format:
{{
  "persona_content": "2-3 sentence paragraph about assistant behavior",
  "human_content": "5-6 sentence paragraph about user facts"
}}"""


SUMMARY_SYSTEM_PROMPT = """You are a conversation summarizer. Create a concise recursive summary that:
1. Builds upon the previous summary (if any)
2. Captures key topics, decisions, and important information
3. Maintains temporal context
4. Is concise but comprehensive

Output format (JSON only):
{{
  "summary": "Your concise summary text here"
}}"""


ASSISTANT_BASE_PROMPT = """You are a helpful AI assistant with access to persistent memory.

When using context:
- Synthesize information rather than repeating it
- If semantic memories and resources overlap, cite the resource as primary source
- Provide concise, informed responses based on available context"""
