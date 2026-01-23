from datetime import datetime
import time

from models.units import SemanticMemoryUnit, MemoryUnitMetaData
from vector_db.mem_block_setup import MemBlockQdrantManager


def build_block_store_retrieve() -> None:
    manager = MemBlockQdrantManager()
    
    # Time block creation
    start = time.time()
    block = manager.create_memory_block(
        description="Personal semantic memories",
        user_id="user_123"
    )
    block_time = time.time() - start
    print(f"Block creation time: {block_time:.2f}s")

    semantic_unit = SemanticMemoryUnit(
        content="User attended the AI conference in San Francisco.",
        type="event",
        source="user",
        confidence=0.95,
        memory_time="2023-11-15T10:00:00",
        entities=["AI conference", "San Francisco"],
        tags=["conference", "AI"],
        updated_at=datetime.now().isoformat(),
        meta_data=MemoryUnitMetaData(usage=[datetime.now().isoformat()])
    )

    # Time memory storage
    start = time.time()
    block.semantic_memories.store_memory(semantic_unit)
    store_time = time.time() - start
    print(f"Memory storage time: {store_time:.2f}s")

    # Time memory retrieval
    start = time.time()
    results = block.semantic_memories.retrieve_memories(
        query_texts=["AI conference in San Francisco", "good weather in New York", "technology trends in 2024"],
        top_k=1
    )
    retrieve_time = time.time() - start
    print(f"Memory retrieval time: {retrieve_time:.2f}s")

    print("Retrieved semantic memories:")
    for i in results:
            print(f"- {i}")


def main():
    build_block_store_retrieve()


if __name__ == "__main__":
    main()
