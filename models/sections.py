from pydantic import BaseModel, Field, model_validator
from config import settings
from prompts import PS1_SEMANTIC_PROMPT, CORE_MEMORY_PROMPT
from models.units import (
    SemanticMemoryUnit,
    CoreMemoryUnit,
    ResourceMemoryUnit,
    MemoryUnitMetaData,
)
from typing import Literal, Optional, Any, List, Dict
from concurrent.futures import ThreadPoolExecutor
from vector_db.vector_db_manager import VectorDBManager
from vector_db.mongo_manager import mongo_manager
from llm.llm_manager import llm_manager
from llm.output_models import SemanticMemoriesOutput, CoreMemoryOutput
import asyncio
from datetime import datetime
import json
from qdrant_client.models import ScoredPoint
from prompts import PS2_MEMORY_UPDATE_PROMPT
from llm.output_models import PS2MemoryUpdateOutput


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
        ps1_prompt: str = PS1_SEMANTIC_PROMPT,
    ) -> List[SemanticMemoryUnit]:
        """
        PS1: Extract structured semantic memories from conversation using LangChain.

        This extracts memories but does NOT store them - gives you control
        over filtering, validation, or modification before storage.

        Args:
            messages: List of conversation messages with 'role' and 'content'
            ps1_prompt: Custom PS1 prompt (optional, uses default if None)

        Returns:
            List of extracted SemanticMemoryUnit instances (not yet stored)
        """

        # Format conversation
        conversation_text = "\n".join(
            [f"{msg['role'].upper()}: {msg['content']}" for msg in messages]
        )

        user_input = f"""Conversation to analyze:

{conversation_text}

Extract structured semantic memories. Analyze each significant piece of information."""

        try:
            # Create LangChain structured output chain
            chain = llm_manager.create_structured_chain(
                system_prompt=ps1_prompt,
                pydantic_model=SemanticMemoriesOutput,
                temperature=settings.llm_semantic_extraction_temperature,
            )

            # Execute chain
            result = await chain.ainvoke({"input": user_input})

            current_time = datetime.now().isoformat()

            extracted_memories = []

            for memory_item in result.memories:
                # Build enriched embedding text (PS1 enhancement)
                embedding_text = f"""{memory_item.content}
Keywords: {", ".join(memory_item.keywords)}
Entities: {", ".join(memory_item.entities)}""".strip()

                memory_unit = SemanticMemoryUnit(
                    content=memory_item.content,
                    type=memory_item.type,
                    source="conversation",
                    confidence=memory_item.confidence,
                    memory_time=(current_time if memory_item.type == "event" else None),
                    entities=memory_item.entities,
                    updated_at=current_time,
                    meta_data=MemoryUnitMetaData(usage=[current_time]),
                    keywords=memory_item.keywords,
                    embedding_text=embedding_text,
                )

                extracted_memories.append(memory_unit)

            return extracted_memories

        except Exception as e:
            print(f"⚠️ Failed to extract semantic memories: {e}")
            return []

    async def extract_and_store_memories(
        self,
        messages: List[Dict[str, str]],
        ps1_prompt: str = PS1_SEMANTIC_PROMPT,
        min_confidence: float = 0.0,
    ) -> List[SemanticMemoryUnit]:
        """
        Convenience method: Extract AND store semantic memories in one call.

        For more control (filtering, validation), use extract_semantic_memories()
        followed by manual store_memory() calls.

        Args:
            messages: List of conversation messages with 'role' and 'content'
            ps1_prompt: Custom PS1 prompt (optional, uses default if None)
            min_confidence: Only store memories with confidence >= this threshold

        Returns:
            List of extracted and stored SemanticMemoryUnit instances
        """

        # Extract memories
        memories = await self.extract_semantic_memories(messages, ps1_prompt)

        # Filter by confidence if needed
        if min_confidence > 0.0:
            memories = [m for m in memories if m.confidence >= min_confidence]

        # Store all filtered memories
        for memory in memories:
            await self.store_memory(memory)

        return memories

    # ========================================================================
    # STORAGE - Uses enriched embedding_text
    # ========================================================================

    async def store_memory(self, memory_unit: SemanticMemoryUnit) -> bool:
        """Store a memory with conflict resolution (PS2).

        PS2 Enhancement:
        1. Retrieve semantically similar existing memories
        2. Use LLM to decide ADD/UPDATE/DELETE operations
        3. Execute operations atomically

        Args:
            memory_unit: The new memory unit to store

        Returns:
            bool: True if operations completed successfully
        """

        embedder = VectorDBManager.get_embedder()
        current_time = datetime.now().isoformat()

        # Step 1: Embed the new memory for similarity search
        text_to_embed = (
            memory_unit.embedding_text
            if memory_unit.embedding_text
            else memory_unit.content
        )
        new_memory_vector = embedder.embed_text(text_to_embed)

        # Step 2: Retrieve top-k similar existing memories
        similar_results = VectorDBManager.retrieve_from_vector(
            self.collection_name, new_memory_vector, top_k=5
        )

        # Step 3: Format inputs for PS2 prompt
        new_memory_dict = memory_unit.model_dump()
        new_memory_dict["updated_at"] = current_time

        # Build existing memories list and create ID mapping (int -> real Qdrant ID)
        # This prevents LLM hallucination with long UUIDs
        existing_memories_list = []
        id_mapping = {}  # Maps simple int ID to real Qdrant point ID

        for idx, point in enumerate(similar_results):
            if isinstance(point, ScoredPoint):
                # Use simple integer ID for LLM
                simple_id = str(idx)
                # Map back to real Qdrant ID
                id_mapping[simple_id] = point.id

                # Ensure simple ID takes priority over any 'id' in payload
                existing_mem = {**point.payload, "id": simple_id}
                existing_memories_list.append(existing_mem)

        # If no similar memories exist, just ADD directly
        if not existing_memories_list:
            payload = memory_unit.model_dump()
            success = VectorDBManager.store_vector(
                self.collection_name, new_memory_vector, payload
            )
            if success:
                print(
                    f"✓ Added new memory (no similar existing): {memory_unit.content[:60]}..."
                )
            return success

        # Step 4: Call PS2 LLM for conflict resolution
        try:
            # Create structured chain
            chain = llm_manager.create_structured_chain(
                system_prompt=PS2_MEMORY_UPDATE_PROMPT,
                pydantic_model=PS2MemoryUpdateOutput,
                temperature=settings.llm_memory_update_temperature,
            )

            user_input = f"""
                NEW MEMORY:
                {json.dumps(new_memory_dict, indent=2, default=str)}

                EXISTING MEMORIES:
                {json.dumps(existing_memories_list, indent=2, default=str)}
                """

            result = await chain.ainvoke({"input": user_input})

        except Exception as e:
            print(f"⚠️ PS2 conflict resolution failed: {e}")
            # Fallback: Just ADD the memory without conflict resolution
            print(f"   Fallback: Adding memory without conflict check")
            payload = memory_unit.model_dump()
            return VectorDBManager.store_vector(
                self.collection_name, new_memory_vector, payload
            )

        # Step 5: Execute operations based on LLM decisions
        operations_performed = []

        # 5a. Handle new memory operation
        if result.new_memory_operation.operation == "ADD":
            payload = memory_unit.model_dump()
            success = VectorDBManager.store_vector(
                self.collection_name, new_memory_vector, payload
            )
            if success:
                operations_performed.append("ADD new memory")
                print(f"✓ Added new memory: {memory_unit.content[:60]}...")
        else:
            operations_performed.append(
                f"NONE (new): {result.new_memory_operation.reason or 'Redundant'}"
            )
            print(f" Skipped new memory (redundant)")

        # 5b. Handle existing memory operations
        for op in result.existing_memory_operations:
            # Map simple ID back to real Qdrant point ID
            real_id = id_mapping.get(op.id)
            if not real_id:
                print(f" Warning: Could not map ID {op.id} to real Qdrant ID, skipping")
                continue

            if op.operation == "UPDATE":
                # Update the ID in the updated_memory dict to real Qdrant ID
                op.updated_memory["id"] = real_id

                # Re-embed the updated memory content
                updated_unit = SemanticMemoryUnit(**op.updated_memory)
                updated_text = (
                    updated_unit.embedding_text
                    if updated_unit.embedding_text
                    else updated_unit.content
                )
                updated_vector = embedder.embed_text(updated_text)

                # Remove 'id' from payload since Qdrant stores it separately
                payload_without_id = {
                    k: v for k, v in op.updated_memory.items() if k != "id"
                }

                # Upsert with real Qdrant ID
                success = VectorDBManager.store_vector(
                    self.collection_name,
                    updated_vector,
                    payload_without_id,
                    point_id=real_id,
                )
                if success:
                    operations_performed.append(f"UPDATE {real_id[:8]}...")
                    print(
                        f"Updated memory {real_id[:8]}...: {updated_unit.content[:60]}..."
                    )

            elif op.operation == "DELETE":
                success = VectorDBManager.delete_vector(self.collection_name, real_id)
                if success:
                    operations_performed.append(f"DELETE {real_id[:8]}...")
                    print(f"Deleted memory {real_id[:8]}...")

            else:  # NONE
                operations_performed.append(f"NONE {real_id[:8]}...")

        print(f"   Operations: {', '.join(operations_performed)}")
        return True

    # ========================================================================
    # RETRIEVAL
    # ========================================================================

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
    Stored in MongoDB (not Qdrant) as it's always retrieved in full, no vector search needed.
    """

    type: Literal["core"] = Field(
        default="core", description="Type of the memory section."
    )
    block_id: str = Field(
        ..., description="ID of the memory block this core memory belongs to"
    )

    @model_validator(mode="before")
    @classmethod
    def validate_from_string(cls, value: Any) -> Any:
        """Allow initialization from a string (block_id) or dict."""
        if isinstance(value, str):
            return {"block_id": value}
        return value

    async def create_new_core_memory(
        self,
        messages: List[Dict[str, str]],
        old_core_memory: Optional[CoreMemoryUnit] = None,
        core_creation_prompt: str = CORE_MEMORY_PROMPT,
    ) -> CoreMemoryUnit:
        """
        Create updated CoreMemoryUnit from conversation messages and old core memory.

        Uses LangChain to generate replacement persona and human paragraphs.

        Args:
            messages: Recent conversation messages
            old_core_memory: Previous core memory (if any)
            core_creation_prompt: System prompt for core memory extraction

        Returns:
            New CoreMemoryUnit with updated persona and human content
        """
        # Format conversation
        conversation_text = "\n".join(
            [f"{msg['role'].upper()}: {msg['content']}\n" for msg in messages]
        )

        # Format old core memory
        old_persona = old_core_memory.persona_content if old_core_memory else ""
        old_human = old_core_memory.human_content if old_core_memory else ""

        user_input = f"""Current Core Memory:
PERSONA: {old_persona}
HUMAN: {old_human}

Recent Conversation:
{conversation_text}

Generate updated core memory paragraphs that incorporate new stable facts."""

        try:
            # Create LangChain structured output chain
            chain = llm_manager.create_structured_chain(
                system_prompt=core_creation_prompt,
                pydantic_model=CoreMemoryOutput,
                temperature=settings.llm_core_extraction_temperature,
            )

            # Execute chain
            result = await chain.ainvoke({"input": user_input})

            return CoreMemoryUnit(
                persona_content=result.persona_content,
                human_content=result.human_content,
            )

        except Exception as e:
            print(f"⚠️ Failed to extract core memory: {e}")
            # Return old core memory or empty if extraction fails
            if old_core_memory:
                return old_core_memory
            return CoreMemoryUnit(persona_content="", human_content="")

    async def store_memory(self, memory_unit: CoreMemoryUnit) -> bool:
        """
        Store CoreMemoryUnit in MongoDB, replacing previous version.

        Args:
            memory_unit: The core memory unit to store

        Returns:
            bool: True if storage was successful
        """
        try:
            await mongo_manager.save_core_memory(
                block_id=self.block_id,
                persona_content=memory_unit.persona_content,
                human_content=memory_unit.human_content,
            )
            return True
        except Exception as e:
            print(f"⚠️ Failed to store core memory: {e}")
            return False

    async def get_memories(self) -> Optional[CoreMemoryUnit]:
        """
        Retrieve core memory from MongoDB.

        Core memories should always be loaded for the LLM context.

        Returns:
            CoreMemoryUnit instance or None if not found
        """
        try:
            doc = await mongo_manager.get_core_memory(self.block_id)
            if doc:
                return CoreMemoryUnit(
                    persona_content=doc.get("persona_content", ""),
                    human_content=doc.get("human_content", ""),
                )
            return None
        except Exception as e:
            print(f"⚠️ Failed to retrieve core memory: {e}")
            return None


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
