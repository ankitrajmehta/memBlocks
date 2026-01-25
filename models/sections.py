from pydantic import BaseModel, Field, model_validator
from .units import SemanticMemoryUnit, CoreMemoryUnit, ResourceMemoryUnit
from typing import Literal, Optional, Any
from concurrent.futures import ThreadPoolExecutor
from vector_db.vector_db_manager import VectorDBManager

class SemanticMemorySection(BaseModel):
    """A section representing semantic memory."""
    type: Literal["semantic"] = Field(default="semantic", description="Type of the memory section.")
    collection_name: str = Field(description="qDrant collection that stores SemanticMemoryUnit instances")

    @model_validator(mode='before')
    @classmethod
    def validate_from_string(cls, value: Any) -> Any:
        """Allow initialization from a string (collection name) or dict.
        Example initializations:
            semantic_mem = SemanticMemorySection(collection_name="ok_collection")
            semantic_mem = SemanticMemorySection({"collection_name": "ojha_collection"})
            semantic_mem: SemanticMemorySection = "mojja_collection" 
        """
        if isinstance(value, str):
            return {'collection_name': value}
        return value
    
    def store_memory(self, memory_unit: SemanticMemoryUnit) -> bool:
        """Store a SemanticMemoryUnit in the corresponding collection.
        
        Args:
            memory_unit (SemanticMemoryUnit): The memory unit to store.
        """
        embedder = VectorDBManager.get_embedder()
        vector = embedder.embed_text(memory_unit.content)
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

        results = VectorDBManager.retrieve_from_vector(self.collection_name, query_vector, top_k)
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
            results = VectorDBManager.retrieve_from_vector(self.collection_name, vector, top_k)
            return [SemanticMemoryUnit(**hit.payload) for hit in results]

        with ThreadPoolExecutor(max_workers=min(10, len(query_vectors))) as executor:
            grouped_results = list(executor.map(_search, query_vectors))

        # TODO: remove duplicates across different query results

        return grouped_results
    
    def search_in_payload(self, filter_query: dict, top_k: int = 5)-> list[SemanticMemoryUnit]:
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
    """A section representing core memory."""
    type: Literal["core"] = Field(default="core", description="Type of the memory section.")
    collection_name: str = Field(description="qDrant collection that stores CoreMemoryUnit instances")

    @model_validator(mode='before')
    @classmethod
    def validate_from_string(cls, value: Any) -> Any:
        """Allow initialization from a string (collection name) or dict."""
        if isinstance(value, str):
            return {'collection_name': value}
        return value

class ResourceMemorySection(BaseModel):
    """A section representing resource memory."""
    type: Literal["resource"] = Field(default="resource", description="Type of the memory section.")
    collection_name: str = Field(description="qDrant collection that stores ResourceMemoryUnit instances")

    @model_validator(mode='before')
    @classmethod
    def validate_from_string(cls, value: Any) -> Any:
        """Allow initialization from a string (collection name) or dict."""
        if isinstance(value, str):
            return {'collection_name': value}
        return value
