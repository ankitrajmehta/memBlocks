# Appendix Extract Set (Hybrid Strategy)

## Prompt Artifacts

### PS1\_SEMANTIC\_PROMPT (extract)

```python
PS1_SEMANTIC_PROMPT = """
You are a memory extraction specialist. Your task is to analyze a batch of user messages and extract structured semantic information for long-term memory storage and retrieval.

Your input is a list of messages from a conversation. Each message may contain multiple distinct pieces of information. You must:

- Extract **all** distinct semantic memory blocks from the conversation.
- Create a JSON object with a single key `"memories"` containing a list of these memory blocks.
- Each memory block must be **ATOMIC**: focused on a single, standalone fact, event, or opinion.
- Each memory must be **UNIQUE WITHIN THE EXTRACTION BATCH**: If multiple messages mention the same information, extract it ONLY ONCE with the most complete version.
- Memories must be **SELF-CONTAINED**: readable and meaningful without referring to other memories.

### Each Memory Block JSON should contain:

1. **keywords** (3–6 items)
2. **content** (exactly ONE sentence)
3. **type** (one of: fact | event | opinion)
4. **entities** (2–8 items)
5. **confidence**
6. **memory_time** (ISO 8601 string or null)

### Critical Guidelines:

- Output **ONLY valid JSON**, no extra text.
- The root object must be { "memories": [ ... ] }.
- Ensure **all fields are present** in every memory object.
- **ATOMIC EXTRACTION**: Each memory must capture ONE distinct piece of information.
"""
```

### PS2\_MEMORY\_UPDATE\_PROMPT (extract)

```python
PS2_MEMORY_UPDATE_PROMPT = """
You are an AI Memory Conflict Resolution Agent. Your task is to intelligently deduplicate and integrate newly extracted memories with existing semantically similar memories in the knowledge store.

You will receive:
1. **New Memory**: A complete SemanticMemoryUnit with all fields
2. **Existing Memories**: List of similar memories already stored, each with their ID and all fields

## Operations

### For New Memory (independent decision):
- **ADD**: Store as new memory (novel information)
- **NONE**: Discard (redundant, already covered by existing)

### For Each Existing Memory:
- **UPDATE**: Merge new info into existing (refinement, extension)
- **DELETE**: Remove (contradicted by new memory, or superseded)
- **NONE**: No change needed

## OUTPUT FORMAT (JSON ONLY):
{
  "new_memory_operation": {
    "operation": "ADD" | "NONE",
    "reason": "Explanation for decision"
  },
  "existing_memory_operations": [
    {
      "id": "0",
      "operation": "UPDATE" | "DELETE" | "NONE",
      "updated_memory": { ... },
      "reason": "Explanation"
    }
  ]
}
"""
```

## Core Data Models

### MemoryBlockMetaData / MemoryBlock (extract)

```python
class MemoryBlockMetaData(BaseModel):
    id: str = Field(..., description="Unique identifier for the memory block.")
    created_at: str = Field(..., description="ISO 8601 formatted timestamp when the block was created.")
    updated_at: str = Field(..., description="ISO 8601 formatted timestamp when the block was last updated.")
    usage: Optional[List[str]] = Field([], description="ISO 8601 timestamps of when this block was accessed.")
    user_id: Optional[str] = Field(None, description="Identifier for the user associated with this block.")
    llm_usage: Dict[str, Any] = Field(default_factory=dict)


class MemoryBlock(BaseModel):
    meta_data: MemoryBlockMetaData = Field(...)
    name: str = Field(..., description="Human-readable name of the memory block.")
    description: str = Field(...)
    semantic_collection: Optional[str] = Field(None)
    core_memory_block_id: Optional[str] = Field(None)
    resource_collection: Optional[str] = Field(None)
    is_active: bool = Field(False)
```

### Semantic/Core/Resource section models (extract)

```python
class SemanticMemoryData(BaseModel):
    type: Literal["semantic"] = Field(default="semantic")
    collection_name: str = Field(...)


class CoreMemoryData(BaseModel):
    type: Literal["core"] = Field(default="core")
    block_id: str = Field(...)


class ResourceMemoryData(BaseModel):
    type: Literal["resource"] = Field(default="resource")
    collection_name: str = Field(...)
```

### LLM structured outputs (extract)

```python
class SemanticExtractionOutput(BaseModel):
    keywords: List[str]
    content: str
    type: str
    entities: List[str]
    confidence: float
    memory_time: Optional[str] = None


class PS2MemoryUpdateOutput(BaseModel):
    new_memory_operation: PS2NewMemoryOperation
    existing_memory_operations: List[PS2ExistingMemoryOperation] = Field(default_factory=list)


class QueryEnhancementOutput(BaseModel):
    expanded_queries: List[str]
    hypothetical_paragraphs: List[str]
```

## API Request Models

### Backend API request contracts (extract)

```python
class CreateBlockRequest(BaseModel):
    name: str = Field(..., description="Human-readable block name")
    description: str = Field("", description="Optional block description")
    create_semantic: bool = Field(True, description="Create semantic Qdrant collection")
    create_core: bool = Field(True, description="Initialise core memory document")
    create_resource: bool = Field(False, description="Create resource Qdrant collection")


class ChatRequest(BaseModel):
    message: str = Field(..., description="User's message text")


class SearchMemoriesRequest(BaseModel):
    query: str = Field(..., description="Search query text")
    top_k: int = Field(5, description="Number of results to return")
```

## Placeholder Entries

### Placeholder: End-to-end MCP tool-call transcript package

Pending packaging state: representative, redacted MCP interaction logs are not yet consolidated into a stable appendix-ready artifact bundle.

### Placeholder: Validation snapshot bundle (library/CLI/MCP cross-surface)

Pending packaging state: repeatable validation snapshot outputs are planned but not yet packaged into a single reproducible appendix artifact.
