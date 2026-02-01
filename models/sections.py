from pydantic import BaseModel, Field, model_validator
from models.units import SemanticMemoryUnit, CoreMemoryUnit, ResourceMemoryUnit
from typing import Literal, Optional, Any
from concurrent.futures import ThreadPoolExecutor
from vector_db.vector_db_manager import VectorDBManager


class SemanticMemorySection(BaseModel):
    """A section representing semantic memory."""

    type: Literal["semantic"] = Field(
        default="semantic", description="Type of the memory section."
    )
    collection_name: str = Field(
        description="qDrant collection that stores SemanticMemoryUnit instances"
    )

    @model_validator(mode="before")
    @classmethod
    def validate_from_string(cls, value: Any) -> Any:
        """Allow initialization from a string (collection name) or dict."""
        if isinstance(value, str):
            return {"collection_name": value}
        return value

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
        """Retrieve top_k similar SemanticMemoryUnit instances based on the query text.

        Args:
            query_texts (list[str]): The texts to query against stored memories.
            top_k (int): Number of top similar memories to retrieve.
        Returns:
            list: List of retrieved SemanticMemoryUnit instances.
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
        vector = embedder.embed_text(memory_unit.content)
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
                if memory.content not in seen_contents:
                    seen_contents.add(memory.content)
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

    def store_memory(self, memory_unit: ResourceMemoryUnit) -> bool:
        """Store a ResourceMemoryUnit in the corresponding collection.

        PS1 Enhancement: Uses enriched embedding_text if available for better resource retrieval.

        Args:
            memory_unit (ResourceMemoryUnit): The memory unit to store.
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

    def retrive_memories_single_query(self, query_text: str, top_k: int = 5) -> list:
        """Retrieve top_k similar ResourceMemoryUnit instances based on a single query text.

        Args:
            query_text (str): The text to query against stored memories.
            top_k (int): Number of top similar memories to retrieve.
        Returns:
            list: List of retrieved ResourceMemoryUnit instances.
        """
        embedder = VectorDBManager.get_embedder()
        query_vector = embedder.embed_text(query_text)

        results = VectorDBManager.retrieve_from_vector(
            self.collection_name, query_vector, top_k
        )
        return [ResourceMemoryUnit(**hit.payload) for hit in results]

    def retrieve_memories(self, query_texts: list[str], top_k: int = 5) -> list:
        """Retrieve top_k similar ResourceMemoryUnit instances based on the query texts.

        Args:
            query_texts (list[str]): The texts to query against stored memories.
            top_k (int): Number of top similar memories to retrieve.
        Returns:
            list: List of lists of retrieved ResourceMemoryUnit instances (one list per query).
        """
        embedder = VectorDBManager.get_embedder()

        query_vectors = embedder.embed_documents(query_texts)

        def _search(vector: list) -> list[ResourceMemoryUnit]:
            results = VectorDBManager.retrieve_from_vector(
                self.collection_name, vector, top_k
            )
            return [ResourceMemoryUnit(**hit.payload) for hit in results]

        with ThreadPoolExecutor(max_workers=min(10, len(query_vectors))) as executor:
            grouped_results = list(executor.map(_search, query_vectors))

        # remove duplicates across different query results
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
    ) -> list[ResourceMemoryUnit]:
        """Search memories based on payload filter.

        Useful for filtering by resource type (chat_transcript, uploaded_doc, extraction)
        or by decay status for time-sensitive extractions.

        Args:
            filter_query (dict): The filter query to apply on payload.
            top_k (int): Number of top similar memories to retrieve.
        Returns:
            list: List of retrieved ResourceMemoryUnit instances.
        """
        # results = VectorDBManager.retrieve_with_filter(self.collection_name, filter_query, top_k)
        # return [ResourceMemoryUnit(**hit.payload) for hit in results]
        pass

    def retrieve_by_resource_type(
        self, resource_type: str, top_k: int = 10
    ) -> list[ResourceMemoryUnit]:
        """Retrieve resources filtered by their type.

        Args:
            resource_type (str): Type of resource ('chat_transcript', 'uploaded_doc', 'extraction')
            top_k (int): Number of resources to retrieve.
        Returns:
            list: List of retrieved ResourceMemoryUnit instances.
        """
        filter_query = {"resource_type": resource_type}
        return self.search_in_payload(filter_query, top_k)

    def retrieve_chat_transcripts(
        self, chat_id: Optional[str] = None, top_k: int = 10
    ) -> list[ResourceMemoryUnit]:
        """Retrieve complete chat transcripts.

        Args:
            chat_id (str, optional): Specific chat ID to retrieve. If None, retrieves recent transcripts.
            top_k (int): Number of transcripts to retrieve.
        Returns:
            list: List of retrieved ResourceMemoryUnit instances containing chat transcripts.
        """
        if chat_id:
            filter_query = {"resource_type": "chat_transcript", "chat_id": chat_id}
        else:
            filter_query = {"resource_type": "chat_transcript"}
        return self.search_in_payload(filter_query, top_k)
