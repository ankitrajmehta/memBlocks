"""Centralized prompt constants for chat pipeline.

This module collects all multi-line LLM prompts so they can be maintained
in one place and reused across modules.
"""

# TODO: change prompt so it can produce multiple memories from the conversation instead of just one. Each memory should be minimal and focused on a single topic or fact.
# TODO: add more examples to the prompt to help guide the model's output.
PS1_SEMANTIC_PROMPT = """You are a memory extraction specialist. Your task is to analyze user interactions and extract structured information for long-term memory storage and retrieval.

Your output will be used for:
- Semantic search via vector embeddings
- Linking related memories across time
- Evolving and refining knowledge as new information arrives

Extract the following components:

1. **Keywords** (3-6 items)
   - Identify concrete, retrieval-effective terms
   - Prioritize: technical nouns, specific actions, domain entities, constraints
   - Exclude: generic verbs ("use", "make", "do"), conversational filler, speaker names
   - Order by importance (most salient first)
   - Ensure keywords are semantically rich for embedding generation
   
   Examples:
   Good Keywords examples: ["neural networks", "backpropagation", "gradient descent"]
   Bad Keywords examples: ["AI", "learning", "things"]

2. **content** (exactly ONE sentence)
   - Capture: primary topic, user's intent/goal, and information status (new/refinement/continuation)
   - Write in a way that allows future updates as related memories emerge
   - Be specific and actionable
   
   Examples:
   Good content Examples: "User is exploring transformer architecture optimization techniques to reduce inference latency in production environments"
   Bad content Examples: "User asked about AI stuff"

3. **Type** (one of: fact | event | opinion)
   - **fact**: Objective, verifiable information or established knowledge
   - **event**: Time-bound occurrence, past action, or planned activity
   - **opinion**: Subjective preference, belief, or perspective
   
   Examples:
   - "Python uses garbage collection" → fact
   - "Had meeting with John yesterday about API redesign" → event
   - "I prefer functional programming over OOP" → opinion

4. **Entities** (2-8 items)
   - Extract: proper nouns, technologies, tools, frameworks, people, organizations, domain concepts
   - Focus on retrieval-critical entities that establish context
   - Include version numbers or specific identifiers when mentioned
   
   Examples:
   Good Entities Examples: ["React 18", "PostgreSQL", "AWS Lambda", "Docker"]
   Bad Entities Examples: ["thing", "stuff", "it"]

**Critical Guidelines:**
- Output ONLY valid JSON, no additional text or explanation
- Ensure all fields are present
- Keywords and entities should have NO overlap with generic stopwords
- content must be a complete, grammatically correct sentence
- Type must be exactly one of: fact, event, opinion

**Output Format:**
{{
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "content": "Single sentence capturing domain, intent, and information status",
  "type": "fact",
  "entities": ["entity1", "entity2", "entity3"]
  "confidence" : "A score between 0 and 1"
}}

**Content to analyze:**
"""

# TODO: add more examples to the prompt to help guide the model's output.
# TODO: change prompt so it keeps old_core as far as possible and only updates it with new must have information from the conversation
  # Should not act like recursive summary. If no new info, return old_core as it is. Dont not delete any information unless invalidated by new conversation.
  # TODO: conflict management -> keep old memory as far as possible and only update it with new must have information from the conversation. Append also only if new information is added.
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


SUMMARY_SYSTEM_PROMPT = """
You are a conversation summarizer.

Create a concise recursive summary that:
1. Incrementally builds upon the previous summary (if exists), preserving earlier information unless explicitly corrected by new content
2. Captures key topics, decisions, constraints, and important factual information
3. Maintains temporal ordering and cause–effect relationships where relevant
4. Avoids speculation, interpretation, or introducing new information
5. Remains concise while retaining all critical context

Do NOT:
- Include casual or irrelevant dialogue
- Remove previously summarized information unless it is clearly contradicted

Output format (JSON only):
{{
  "summary": "Your concise recursive summary here"
}}

"""

# TODO: take reference from https://github.com/mem0ai/mem0/blob/main/mem0/configs/prompts.py#L175 & L405 for conflict management prompt
PS2_SEMANTIC_PROMPT = """
You are an AI Memory Resolution and Evolution Agent.

Your responsibility is to maintain a long-term, structured memory store by
carefully integrating new information without destroying historical knowledge.

You will analyze ONE proposed new memory (mn) together with its top-k
semantically related existing memories and produce a conservative memory
transition plan.
---

### SYMBOL GLOSSARY (IMPORTANT)

* mn: Proposed new memory (not yet stored)
* Xi: Natural language content of a memory (atomic statement)
* Gi: Tags / semantic labels associated with a memory
* type: One of {fact, event, opinion}
* confidence: Float in [0.0, 1.0] indicating epistemic confidence
* entities: Canonical named entities referenced in the memory

  * active: currently valid
  * archived: historically valid but superseded
  * invalid: determined to be incorrect

---

### CORE PRINCIPLES (MUST FOLLOW)

* Never delete memories; use **ARCHIVE** or **INVALIDATE**
* FACT memories are immutable relative to EVENT or OPINION
* OPINIONS may coexist with contradictions
* Contradictions must be handled explicitly
* All updates must be **field-scoped and additive** where possible
* `confidence_delta` must be small (|Δ| ≤ 0.1) and justified by new evidence

---

### NEW MEMORY PROPOSAL (mn)

* Xi: {Xi}
* Gi: {Gi}
* type: {type}
* confidence: {confidence}
* entities: {entities}
* memory_time: {memory_time}
* source: {source}

**Note:** mn is NOT yet stored.

---

### CANDIDATE EXISTING MEMORIES

{candidate_memories}


Each candidate includes:

* memory_id
* Xi
* Gi
* type
* confidence
* entities
* status
* memory_time
* updated_at

---

### DECISION OBJECTIVES

1. Decide whether mn should be:

   * **STORED** as a new memory, or
   * **MERGED** into a single existing memory

2. For EACH candidate existing memory, decide **exactly ONE** action:

   * NOOP
   * UPDATE (refinement only, no semantic overwrite)
   * ARCHIVE (superseded but historically valid)
   * INVALIDATE (clearly incorrect)

---

### CONTRADICTION RULES

* **FACT vs FACT**
  Prefer higher confidence, newer, and better-sourced memory.
  The weaker memory must be ARCHIVED or INVALIDATED.

* **EVENT vs FACT**
  FACT is immutable; EVENT may be archived or refined.

* **OPINION**
  May coexist with contradictions; do not invalidate unless clearly erroneous.

---

### OUTPUT FORMAT (JSON ONLY)

{{
  "new_memory_decision": {
    "operation": "STORE | MERGE",
    "merge_target_memory_id": null,
    "final_type": "fact | event | opinion",
    "final_confidence": 0.0,
    "final_entities": [],
    "initial_status": "active"
  },

  "existing_memory_updates": [
    {
      "memory_id": "",
      "action": "NOOP | UPDATE | ARCHIVE | INVALIDATE",
      "field_updates": {
        "Xi_append": null,
        "Gi_add": [],
        "entities_add": [],
        "confidence_delta": null
      }
    }
  ]
}}

"""


ASSISTANT_BASE_PROMPT = """You are a helpful AI assistant with access to persistent memory.

When using context:
- Synthesize information rather than repeating it
- If semantic memories and resources overlap, cite the resource as primary source
- Provide concise, informed responses based on available context"""


