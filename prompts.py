"""Centralized prompt constants for chat pipeline.

This module collects all multi-line LLM prompts so they can be maintained
in one place and reused across modules.
"""

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
  • Examples: "Redis", "LRU caching", "RAM optimization", "40% reduction", "Sarah"
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
   - Write exactly ONE sentence that captures:
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
   - Extract key entities: people, places, technologies, tools, concepts
   - Focus on nouns and proper nouns important for retrieval

Output format (JSON only):

{
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "context": "One sentence description",
  "type": "fact | event | opinion",
  "entities": ["entity1", "entity2"]
}"""

# TODO: Get rid during resource redesign
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


CORE_MEMORY_PROMPT = """
You are a core memory extractor. You have been given the present know core information, and a list
of user messages.
Extract stable, enduring facts about the user from this conversation and rewrite the core information

Human Content is the information about the user that should be stored in core memory.
Persona content is the information about how the assistant should interact with the user. 

Focus ONLY on:
- User's name, location, occupation
- Lasting preferences (communication style, interests, dislikes)
- Important relationships (family, colleagues mentioned by name)
- Self-identifying attributes

Do NOT extract:
- Temporary events or plans
- Opinions that may change
- Specific projects (those go to semantic memory)

If no core memories found, return dict with empty str"""


SUMMARY_SYSTEM_PROMPT = """You are a conversation summarizer. Create a concise recursive summary that:
1. Builds upon the previous summary (if any)
2. Captures key topics, decisions, and important information
3. Maintains temporal context
4. Is concise but comprehensive

Return ONLY the summary text, no JSON or formatting."""


ASSISTANT_BASE_PROMPT = """You are a helpful AI assistant with access to persistent memory.

When using context:
- Synthesize information rather than repeating it
- If semantic memories and resources overlap, cite the resource as primary source
- Provide concise, informed responses based on available context"""
