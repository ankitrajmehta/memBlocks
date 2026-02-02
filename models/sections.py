from pydantic import BaseModel, Field, model_validator
from prompts import PS1_SEMANTIC_PROMPT
from models.units import (
    SemanticMemoryUnit,
    CoreMemoryUnit,
    ResourceMemoryUnit,
    MemoryUnitMetaData,
)
from typing import Literal, Optional, Any, List, Dict
from concurrent.futures import ThreadPoolExecutor
from vector_db.vector_db_manager import VectorDBManager
import asyncio
from datetime import datetime
import json


class SemanticMemorySection(BaseModel):
    """A section representing semantic memory with PS1 enhancement."""

    type: Literal["semantic"] = Field(
        default="semantic", description="Type of the memory section."
    )
    collection_name: str = Field(
        description="qDrant collection that stores SemanticMemoryUnit instances"
    )

    @model_validator(mode="before")
    @classmethod
    def validate_from_string(cls, value: Any) -> Any:
        """Allow initialization from a string (collection name) or dict.

        Example initializations:
            semantic_mem = SemanticMemorySection(collection_name="ok_collection")
            semantic_mem = SemanticMemorySection({"collection_name": "ojha_collection"})
            semantic_mem: SemanticMemorySection = "mojja_collection"
        """
        if isinstance(value, str):
            return {"collection_name": value}
        return value

    # ========================================================================
    # PS1 EXTRACTION - Separated from storage for flexibility
    # ========================================================================

    async def extract_semantic_memories(
        self,
        messages: List[Dict[str, str]],
        client,  # Groq/OpenAI client
        model: str = "llama-3.1-8b-instant",
        ps1_prompt: str = PS1_SEMANTIC_PROMPT,
    ) -> List[SemanticMemoryUnit]:
        """
        PS1: Extract structured semantic memories from conversation.

        This extracts memories but does NOT store them - gives you control
        over filtering, validation, or modification before storage.

        Args:
            messages: List of conversation messages with 'role' and 'content'
            client: LLM client (Groq, OpenAI, etc.)
            model: Model name to use
            ps1_prompt: Custom PS1 prompt (optional, uses default if None)

        Returns:
            List of extracted SemanticMemoryUnit instances (not yet stored)
        """

        # Format conversation
        conversation_text = "\n".join(
            [f"{msg['role'].upper()}: {msg['content']}" for msg in messages]
        )

        user_prompt = f"""Conversation to analyze:

{conversation_text}

Extract structured semantic memories following the JSON format specified in the system prompt."""

        # Call LLM for extraction
        loop = asyncio.get_event_loop()
        completion = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": ps1_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
                max_completion_tokens=2048,
                response_format={"type": "json_object"},
            ),
        )

        raw_response = completion.choices[0].message.content.strip()

        try:
            ps1_data = json.loads(raw_response)
            current_time = datetime.now().isoformat()

            # Handle both single memory and array of memories
            memories_list = (
                ps1_data.get("memories", [ps1_data])
                if "memories" in ps1_data
                else [ps1_data]
            )

            extracted_memories = []

            for mem_data in memories_list:
                # Build enriched embedding text (PS1 enhancement)
                # Merged keywords now include both categorical tags and key terms
                embedding_text = f"""{mem_data.get('content', '')}
Keywords: {', '.join(mem_data.get('keywords', []))}
Entities: {', '.join(mem_data.get('entities', []))}""".strip()

                memory_unit = SemanticMemoryUnit(
                    content=mem_data.get("content", ""),
                    type=mem_data.get("type", "factual"),
                    source="conversation",
                    confidence=mem_data.get("confidence", 0.8),
                    memory_time=(
                        mem_data.get("memory_time", current_time)
                        if mem_data.get("type") == "event"
                        else None
                    ),
                    entities=mem_data.get("entities", []),
                    updated_at=current_time,
                    meta_data=MemoryUnitMetaData(usage=[current_time]),
                    keywords=mem_data.get("keywords", []),
                    embedding_text=embedding_text,
                )

                extracted_memories.append(memory_unit)

            return extracted_memories

        except json.JSONDecodeError as e:
            print(f"⚠️ Failed to parse PS1 semantic JSON: {e}")
            return []

    async def extract_and_store_memories(
        self,
        messages: List[Dict[str, str]],
        client,  # Groq/OpenAI client
        model: str = "llama-3.1-8b-instant",
        ps1_prompt: str = PS1_SEMANTIC_PROMPT,
        min_confidence: float = 0.0,
    ) -> List[SemanticMemoryUnit]:
        """
        Convenience method: Extract AND store semantic memories in one call.

        For more control (filtering, validation), use extract_semantic_memories()
        followed by manual store_memory() calls.

        Args:
            messages: List of conversation messages with 'role' and 'content'
            client: LLM client (Groq, OpenAI, etc.)
            model: Model name to use
            ps1_prompt: Custom PS1 prompt (optional, uses default if None)
            min_confidence: Only store memories with confidence >= this threshold

        Returns:
            List of extracted and stored SemanticMemoryUnit instances
        """

        # Extract memories
        memories = await self.extract_semantic_memories(
            messages, client, model, ps1_prompt
        )

        # Filter by confidence if needed
        if min_confidence > 0.0:
            memories = [m for m in memories if m.confidence >= min_confidence]

        # Store all filtered memories
        for memory in memories:
            self.store_memory(memory)

        return memories

    # ========================================================================
    # STORAGE - Uses enriched embedding_text
    # ========================================================================

    def store_memory(self, memory_unit: SemanticMemoryUnit) -> bool:
        """Store a SemanticMemoryUnit in the corresponding collection.

        PS1 Enhancement: Uses enriched embedding_text if available for better retrieval.

        Args:
            memory_unit (SemanticMemoryUnit): The memory unit to store.
        Returns:
            bool: True if storage was successful, False otherwise.
        """
        embedder = VectorDBManager.get_embedder()

        # PS1: Use enriched embedding_text if available, otherwise fall back to content
        text_to_embed = (
            memory_unit.embedding_text
            if memory_unit.embedding_text
            else memory_unit.content
        )

        vector = embedder.embed_text(text_to_embed)
        payload = memory_unit.model_dump()
        return VectorDBManager.store_vector(self.collection_name, vector, payload)

    # ========================================================================
    # RETRIEVAL
    # ========================================================================

    def retrive_memories_single_query(self, query_text: str, top_k: int = 5) -> list:
        """Retrieve top_k similar SemanticMemoryUnit instances based on a single query text.

        Args:
            query_text (str): The text to query against stored memories.
            top_k (int): Number of top similar memories to retrieve.
        Returns:
            list: List of retrieved SemanticMemoryUnit instances.
        """
        embedder = VectorDBManager.get_embedder()
        query_vector = embedder.embed_text(query_text)

        results = VectorDBManager.retrieve_from_vector(
            self.collection_name, query_vector, top_k
        )
        return [SemanticMemoryUnit(**hit.payload) for hit in results]

    def retrieve_memories(self, query_texts: list[str], top_k: int = 5) -> list:
        """Retrieve top_k similar SemanticMemoryUnit instances based on query texts.

        Args:
            query_texts (list[str]): The texts to query against stored memories.
            top_k (int): Number of top similar memories to retrieve.
        Returns:
            list: List of lists of retrieved SemanticMemoryUnit instances (one list per query).
        """
        embedder = VectorDBManager.get_embedder()

        query_vectors = embedder.embed_documents(query_texts)

        def _search(vector: list) -> list[SemanticMemoryUnit]:
            results = VectorDBManager.retrieve_from_vector(
                self.collection_name, vector, top_k
            )
            return [SemanticMemoryUnit(**hit.payload) for hit in results]

        with ThreadPoolExecutor(max_workers=min(10, len(query_vectors))) as executor:
            grouped_results = list(executor.map(_search, query_vectors))

        # Remove duplicates across different query results
        seen_contents = set()
        deduplicated_results = []

        for result_group in grouped_results:
            unique_group = []
            for memory in result_group:
                if memory.content not in seen_contents:
                    seen_contents.add(memory.content)
                    unique_group.append(memory)
            deduplicated_results.append(unique_group)

        return deduplicated_results

    def search_in_payload(
        self, filter_query: dict, top_k: int = 5
    ) -> list[SemanticMemoryUnit]:
        """Search memories based on payload filter.

        Args:
            filter_query (dict): The filter query to apply on payload.
            top_k (int): Number of top similar memories to retrieve.
        Returns:
            list: List of retrieved SemanticMemoryUnit instances.
        """
        # results = VectorDBManager.retrieve_with_filter(self.collection_name, filter_query, top_k)
        # return [SemanticMemoryUnit(**hit.payload) for hit in results]
        pass


class CoreMemorySection(BaseModel):
    """A section representing core memory.

    Core Memory stores high-priority, persistent information that should always remain
    visible to the agent when engaging with the user. Divided into two primary blocks:
    - persona: encodes the identity, tone, or behavior profile of the agent
    - human: stores enduring facts about the user (name, preferences, self-identifying attributes)

    Examples: "User's name is David", "User enjoys Japanese cuisine", "Agent is helpful and concise"

    Should be passed to answering LLM each single time and kept fairly optimized and short.
    When memory size exceeds 90% of capacity, triggers a controlled rewrite process.
    """

    type: Literal["core"] = Field(
        default="core", description="Type of the memory section."
    )
    collection_name: str = Field(
        description="qDrant collection that stores CoreMemoryUnit instances"
    )

    @model_validator(mode="before")
    @classmethod
    def validate_from_string(cls, value: Any) -> Any:
        """Allow initialization from a string (collection name) or dict."""
        if isinstance(value, str):
            return {"collection_name": value}
        return value

    def store_memory(self, memory_unit: CoreMemoryUnit) -> bool:
        """Store a CoreMemoryUnit in the corresponding collection.

        Args:
            memory_unit (CoreMemoryUnit): The memory unit to store.
        Returns:
            bool: True if storage was successful, False otherwise.
        """
        embedder = VectorDBManager.get_embedder()
        # Combine persona and human content for embedding
        combined_content = f"{memory_unit.persona_content} {memory_unit.human_content}"
        vector = embedder.embed_text(combined_content)
        payload = memory_unit.model_dump()
        return VectorDBManager.store_vector(self.collection_name, vector, payload)

    def retrive_memories_single_query(self, query_text: str, top_k: int = 5) -> list:
        """Retrieve top_k similar CoreMemoryUnit instances based on a single query text.

        Args:
            query_text (str): The text to query against stored memories.
            top_k (int): Number of top similar memories to retrieve.
        Returns:
            list: List of retrieved CoreMemoryUnit instances.
        """
        embedder = VectorDBManager.get_embedder()
        query_vector = embedder.embed_text(query_text)

        results = VectorDBManager.retrieve_from_vector(
            self.collection_name, query_vector, top_k
        )
        return [CoreMemoryUnit(**hit.payload) for hit in results]

    def retrieve_memories(self, query_texts: list[str], top_k: int = 5) -> list:
        """Retrieve top_k similar CoreMemoryUnit instances based on the query texts.

        Args:
            query_texts (list[str]): The texts to query against stored memories.
            top_k (int): Number of top similar memories to retrieve.
        Returns:
            list: List of lists of retrieved CoreMemoryUnit instances (one list per query).
        """
        embedder = VectorDBManager.get_embedder()

        query_vectors = embedder.embed_documents(query_texts)

        def _search(vector: list) -> list[CoreMemoryUnit]:
            results = VectorDBManager.retrieve_from_vector(
                self.collection_name, vector, top_k
            )
            return [CoreMemoryUnit(**hit.payload) for hit in results]

        with ThreadPoolExecutor(max_workers=min(10, len(query_vectors))) as executor:
            grouped_results = list(executor.map(_search, query_vectors))

        # Remove duplicates across different query results
        seen_contents = set()
        deduplicated_results = []

        for result_group in grouped_results:
            unique_group = []
            for memory in result_group:
                # Use combined content for deduplication
                combined_content = f"{memory.persona_content} {memory.human_content}"
                if combined_content not in seen_contents:
                    seen_contents.add(combined_content)
                    unique_group.append(memory)
            deduplicated_results.append(unique_group)

        return deduplicated_results

    def search_in_payload(
        self, filter_query: dict, top_k: int = 5
    ) -> list[CoreMemoryUnit]:
        """Search memories based on payload filter.

        Args:
            filter_query (dict): The filter query to apply on payload.
            top_k (int): Number of top similar memories to retrieve.
        Returns:
            list: List of retrieved CoreMemoryUnit instances.
        """
        # results = VectorDBManager.retrieve_with_filter(self.collection_name, filter_query, top_k)
        # return [CoreMemoryUnit(**hit.payload) for hit in results]
        pass

    def get_all_memories(self) -> list[CoreMemoryUnit]:
        """Retrieve all core memories (persona and human blocks).

        Core memories should always be loaded for the LLM context.

        Returns:
            list: List of all CoreMemoryUnit instances.
        """
        # This should retrieve all memories without limit for passing to LLM
        # Implementation depends on VectorDBManager's capability to retrieve all
        pass

    def check_capacity_threshold(self, threshold: float = 0.9) -> bool:
        """Check if memory size exceeds the specified capacity threshold.

        Args:
            threshold (float): Capacity threshold (default 0.9 for 90%)
        Returns:
            bool: True if threshold exceeded, False otherwise.
        """
        # Implementation to check if memory needs rewriting
        pass


class ResourceMemorySection(BaseModel):
    """A section representing resource memory.

    Resource Memory stores read-only reference materials not modified by the agent:
    - Complete chat transcripts for all chats
    - User uploaded documents
    - Agent-identified important extractions from conversations (decaying with time)

    These resources serve as contextual references that can be retrieved when needed
    but are not actively maintained or updated by the agent during conversations.
    """

    type: Literal["resource"] = Field(
        default="resource", description="Type of the memory section."
    )
    collection_name: str = Field(
        description="qDrant collection that stores ResourceMemoryUnit instances"
    )

    @model_validator(mode="before")
    @classmethod
    def validate_from_string(cls, value: Any) -> Any:
        """Allow initialization from a string (collection name) or dict."""
        if isinstance(value, str):
            return {"collection_name": value}
        return value

    # def store_memory(self, memory_unit: ResourceMemoryUnit) -> bool:
    #     """Store a ResourceMemoryUnit in the corresponding collection.

    #     PS1 Enhancement: Uses enriched embedding_text if available for better resource retrieval.

    #     Args:
    #         memory_unit (ResourceMemoryUnit): The memory unit to store.
    #     Returns:
    #         bool: True if storage was successful, False otherwise.
    #     """
    #     embedder = VectorDBManager.get_embedder()

    #     # PS1: Use enriched embedding_text if available, otherwise fall back to content
    #     text_to_embed = (
    #         memory_unit.embedding_text
    #         if memory_unit.embedding_text
    #         else memory_unit.content
    #     )

    #     vector = embedder.embed_text(text_to_embed)
    #     payload = memory_unit.model_dump()
    #     return VectorDBManager.store_vector(self.collection_name, vector, payload)

    # def retrive_memories_single_query(self, query_text: str, top_k: int = 5) -> list:
    #     """Retrieve top_k similar ResourceMemoryUnit instances based on a single query text.

    #     Args:
    #         query_text (str): The text to query against stored memories.
    #         top_k (int): Number of top similar memories to retrieve.
    #     Returns:
    #         list: List of retrieved ResourceMemoryUnit instances.
    #     """
    #     embedder = VectorDBManager.get_embedder()
    #     query_vector = embedder.embed_text(query_text)

    #     results = VectorDBManager.retrieve_from_vector(
    #         self.collection_name, query_vector, top_k
    #     )
    #     return [ResourceMemoryUnit(**hit.payload) for hit in results]

    # def retrieve_memories(self, query_texts: list[str], top_k: int = 5) -> list:
    #     """Retrieve top_k similar ResourceMemoryUnit instances based on the query texts.

    #     Args:
    #         query_texts (list[str]): The texts to query against stored memories.
    #         top_k (int): Number of top similar memories to retrieve.
    #     Returns:
    #         list: List of lists of retrieved ResourceMemoryUnit instances (one list per query).
    #     """
    #     embedder = VectorDBManager.get_embedder()

    #     query_vectors = embedder.embed_documents(query_texts)

    #     def _search(vector: list) -> list[ResourceMemoryUnit]:
    #         results = VectorDBManager.retrieve_from_vector(
    #             self.collection_name, vector, top_k
    #         )
    #         return [ResourceMemoryUnit(**hit.payload) for hit in results]

    #     with ThreadPoolExecutor(max_workers=min(10, len(query_vectors))) as executor:
    #         grouped_results = list(executor.map(_search, query_vectors))

    #     # Remove duplicates across different query results
    #     seen_contents = set()
    #     deduplicated_results = []

    #     for result_group in grouped_results:
    #         unique_group = []
    #         for memory in result_group:
    #             if memory.content not in seen_contents:
    #                 seen_contents.add(memory.content)
    #                 unique_group.append(memory)
    #         deduplicated_results.append(unique_group)

    #     return deduplicated_results

    # def search_in_payload(
    #     self, filter_query: dict, top_k: int = 5
    # ) -> list[ResourceMemoryUnit]:
    #     """Search memories based on payload filter.

    #     Useful for filtering by resource type (chat_transcript, uploaded_doc, extraction)
    #     or by decay status for time-sensitive extractions.

    #     Args:
    #         filter_query (dict): The filter query to apply on payload.
    #         top_k (int): Number of top similar memories to retrieve.
    #     Returns:
    #         list: List of retrieved ResourceMemoryUnit instances.
    #     """
    #     # results = VectorDBManager.retrieve_with_filter(self.collection_name, filter_query, top_k)
    #     # return [ResourceMemoryUnit(**hit.payload) for hit in results]
    #     pass

    # def retrieve_by_resource_type(
    #     self, resource_type: str, top_k: int = 10
    # ) -> list[ResourceMemoryUnit]:
    #     """Retrieve resources filtered by their type.

    #     Args:
    #         resource_type (str): Type of resource ('document', 'image', 'video', 'audio', 'link', 'extracted')
    #         top_k (int): Number of resources to retrieve.
    #     Returns:
    #         list: List of retrieved ResourceMemoryUnit instances.
    #     """
    #     filter_query = {"resource_type": resource_type}
    #     return self.search_in_payload(filter_query, top_k)

    # def retrieve_chat_transcripts(
    #     self, chat_id: Optional[str] = None, top_k: int = 10
    # ) -> list[ResourceMemoryUnit]:
    #     """Retrieve complete chat transcripts.

    #     Args:
    #         chat_id (str, optional): Specific chat ID to retrieve. If None, retrieves recent transcripts.
    #         top_k (int): Number of transcripts to retrieve.
    #     Returns:
    #         list: List of retrieved ResourceMemoryUnit instances containing chat transcripts.
    #     """
    #     if chat_id:
    #         filter_query = {"resource_type": "chat_transcript", "chat_id": chat_id}
    #     else:
    #         filter_query = {"resource_type": "chat_transcript"}
    #     return self.search_in_payload(filter_query, top_k)
