from datetime import datetime
import time

from models.units import (
    SemanticMemoryUnit,
    CoreMemoryUnit,
    ResourceMemoryUnit,
    MemoryUnitMetaData,
)
from vector_db.mem_block_setup import MemBlockQdrantManager


def build_block_store_retrieve() -> None:
    manager = MemBlockQdrantManager()

    # Time block creation
    start = time.time()
    block = manager.create_memory_block(
        name="TestBlock", description="Personal semantic memories", user_id="user_123"
    )
    block_time = time.time() - start
    print(f"Block creation time: {block_time:.2f}s")

    # ========== SEMANTIC MEMORY ==========
    print("\n" + "=" * 60)
    print("SEMANTIC MEMORY SECTION")
    print("=" * 60)

    semantic_unit = SemanticMemoryUnit(
        content="User attended the AI conference in San Francisco.",
        type="event",
        source="user",
        confidence=0.95,
        memory_time="2023-11-15T10:00:00",
        entities=["AI conference", "San Francisco"],
        tags=["conference", "AI"],
        updated_at=datetime.now().isoformat(),
        meta_data=MemoryUnitMetaData(usage=[datetime.now().isoformat()]),
    )

    # Time semantic memory storage
    start = time.time()
    block.semantic_memories.store_memory(semantic_unit)
    store_time = time.time() - start
    print(f"Semantic memory storage time: {store_time:.2f}s")

    # Time semantic memory retrieval
    start = time.time()
    semantic_results = block.semantic_memories.retrieve_memories(
        query_texts=[
            "AI conference in San Francisco",
            "good weather in New York",
            "technology trends in 2024",
        ],
        top_k=3,
    )
    retrieve_time = time.time() - start
    print(f"Semantic memory retrieval time: {retrieve_time:.2f}s")

    print("Retrieved semantic memories:")
    for query_results in semantic_results:
        for memory in query_results:
            print(f"  - {memory.content}")

    # ========== CORE MEMORY ==========
    print("\n" + "=" * 60)
    print("CORE MEMORY SECTION")
    print("=" * 60)

    core_unit = CoreMemoryUnit(
        persona_content="You are a helpful AI assistant.",
        human_content="User's name is David. User prefers concise responses and likes Japanese cuisine.",
    )

    # Time core memory storage
    start = time.time()
    block.core_memories.store_memory(core_unit)
    store_time = time.time() - start
    print(f"Core memory storage time: {store_time:.2f}s")

    # Time core memory retrieval
    start = time.time()
    core_results = block.core_memories.retrieve_memories(
        query_texts=["user preferences", "user name", "food likes"], top_k=3
    )
    retrieve_time = time.time() - start
    print(f"Core memory retrieval time: {retrieve_time:.2f}s")

    print("Retrieved core memories:")
    for query_results in core_results:
        for memory in query_results:
            print(f"  - Persona: {memory.persona_content}")
            print(f"  - Human: {memory.human_content}")

    # ========== RESOURCE MEMORY ==========
    # print("\n" + "=" * 60)
    # print("RESOURCE MEMORY SECTION")
    # print("=" * 60)

    # resource_unit = ResourceMemoryUnit(
    #     content="API Documentation: REST endpoints include /api/users, /api/projects, /api/tasks with full CRUD operations.",
    #     resource_type="document",
    #     resource_link="docs/api-reference.pdf",
    # )

    # # Time resource memory storage
    # start = time.time()
    # block.resource_memories.store_memory(resource_unit)
    # store_time = time.time() - start
    # print(f"Resource memory storage time: {store_time:.2f}s")

    # # Time resource memory retrieval
    # start = time.time()
    # resource_results = block.resource_memories.retrieve_memories(
    #     query_texts=["API documentation", "REST endpoints", "user guides"], top_k=3
    # )
    # retrieve_time = time.time() - start
    # print(f"Resource memory retrieval time: {retrieve_time:.2f}s")

    # print("Retrieved resource memories:")
    # for query_results in resource_results:
    #     for memory in query_results:
    #         print(f"  - {memory.content}")
    #         print(f"    Type: {memory.resource_type}, Link: {memory.resource_link}")

    # ========== SUMMARY ==========
    print("\n" + "=" * 60)
    print("MEMORY BLOCK SUMMARY")
    print("=" * 60)
    print(f"Block ID: {block.meta_data.id}")
    print(f"Block Name: {block.name}")
    print(f"Block Description: {block.description}")
    print(f"\nSections:")
    print(
        f"  - Semantic Memories Collection: {block.semantic_memories.collection_name}"
    )
    print(f"  - Core Memories Collection: {block.core_memories.collection_name}")
    # print(
    #     f"  - Resource Memories Collection: {block.resource_memories.collection_name}"
    # )

def main():
    build_block_store_retrieve()
    build_block_store_retrieve()

if __name__ == "__main__":
    main()
