"""Test script for Cohere re-ranker integration.

This script tests the new Cohere-based re-ranking functionality to ensure
it works correctly with the existing semantic memory retrieval pipeline.
"""

import asyncio
import os
from pathlib import Path
from memblocks.services.reranker import CohereReranker
from memblocks.models.units import SemanticMemoryUnit

# Load environment variables from parent directory's .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded .env from: {env_path}")
except ImportError:
    print("python-dotenv not installed, relying on system environment variables")


async def test_cohere_reranker():
    """Test the CohereReranker with sample memories."""
    
    print("=" * 80)
    print("Testing Cohere Re-ranker Integration")
    print("=" * 80)
    
    # Create sample memories
    memories = [
        SemanticMemoryUnit(
            memory_id="1",
            content="User prefers Python for data science and machine learning projects.",
            type="opinion",
            keywords=["Python", "data science", "machine learning"],
            entities=["Python"],
            confidence=0.9,
            source="conversation",
            updated_at="2024-03-20T10:00:00Z",
            memory_time=None,
        ),
        SemanticMemoryUnit(
            memory_id="2",
            content="User completed a FastAPI project for building REST APIs last week.",
            type="event",
            keywords=["FastAPI", "REST API", "project"],
            entities=["FastAPI"],
            confidence=0.85,
            source="conversation",
            updated_at="2024-03-19T10:00:00Z",
            memory_time="2024-03-13T10:00:00Z",
        ),
        SemanticMemoryUnit(
            memory_id="3",
            content="User is learning Docker and Kubernetes for container orchestration.",
            type="fact",
            keywords=["Docker", "Kubernetes", "containers", "orchestration"],
            entities=["Docker", "Kubernetes"],
            confidence=0.8,
            source="conversation",
            updated_at="2024-03-18T10:00:00Z",
            memory_time=None,
        ),
        SemanticMemoryUnit(
            memory_id="4",
            content="User dislikes JavaScript frameworks because of their complexity.",
            type="opinion",
            keywords=["JavaScript", "frameworks", "complexity"],
            entities=["JavaScript"],
            confidence=0.75,
            source="conversation",
            updated_at="2024-03-17T10:00:00Z",
            memory_time=None,
        ),
        SemanticMemoryUnit(
            memory_id="5",
            content="User works as a backend developer specializing in Python and Go.",
            type="fact",
            keywords=["backend developer", "Python", "Go", "occupation"],
            entities=["Python", "Go"],
            confidence=0.95,
            source="conversation",
            updated_at="2024-03-20T10:00:00Z",
            memory_time=None,
        ),
    ]
    
    # Test query
    query = "What programming languages does the user prefer?"
    
    print(f"\nQuery: {query}")
    print(f"\nTotal memories to re-rank: {len(memories)}")
    print("\nOriginal order:")
    for i, memory in enumerate(memories, 1):
        print(f"  {i}. [{memory.memory_id}] {memory.content[:60]}...")
    
    try:
        # Initialize Cohere re-ranker (will read API key from .env)
        reranker = CohereReranker()
        print("\n✓ Cohere re-ranker initialized successfully")
        
        # Test re-ranking
        print("\nRe-ranking memories with Cohere...")
        reranked_memories = await reranker.rerank(
            query=query,
            memories=memories,
            top_n=3  # Get top 3 most relevant
        )
        
        print(f"\n✓ Re-ranking completed! Got {len(reranked_memories)} results")
        print("\nRe-ranked order (top 3):")
        for i, memory in enumerate(reranked_memories, 1):
            print(f"  {i}. [{memory.memory_id}] {memory.content[:60]}...")
        
        # Test with all results
        print("\n" + "=" * 80)
        print("Testing without top_n limit...")
        all_reranked = await reranker.rerank(
            query=query,
            memories=memories,
            top_n=None  # Get all ranked results
        )
        
        print(f"\n✓ Got {len(all_reranked)} re-ranked memories")
        print("\nAll re-ranked memories:")
        for i, memory in enumerate(all_reranked, 1):
            print(f"  {i}. [{memory.memory_id}] {memory.content[:80]}...")
        
        print("\n" + "=" * 80)
        print("✅ All tests passed successfully!")
        print("=" * 80)
        
    except ImportError as e:
        print(f"\n❌ Import Error: {e}")
        print("Please install cohere: pip install cohere==5.5.1")
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("Please ensure COHERE_API_KEY is set in .env file")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_cohere_reranker())
