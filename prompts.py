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
