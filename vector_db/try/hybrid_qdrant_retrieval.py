import sys
from pathlib import Path

# Add setup directory to path
setup_dir = Path(__file__).parent.parent / "setup"
sys.path.insert(0, str(setup_dir))

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchAny
from embeddings import OllamaEmbeddings
from datetime import datetime
import re
import time

# Initialize
client = QdrantClient(host="localhost", port=6333)
embedder = OllamaEmbeddings()
COLLECTION_NAME = "EventFactualMemory"


def extract_entities_from_query(query):
    """Extract potential entities from query"""
    known_entities = ["Ramesh", "Embark", "Amazon", "Pulchowk", "Himalayan", "Java", "MemBlocks"]
    found = [e for e in known_entities if e.lower() in query.lower()]
    return found


def retrieve_memories_for_query(user_question, top_k=5, verbose=True):
    """
    Retrieve most relevant memories for a user's question
    Returns formatted text ready for LLM context
    """
    
    start_time = time.time()
    
    if verbose:
        print("\n🔍 RETRIEVING MEMORIES...")
        print("-" * 60)
    
    all_results = {}
    
    # Strategy 1: Check for entity mentions
    entity_start = time.time()
    entities = extract_entities_from_query(user_question)
    
    if entities and verbose:
        print(f"✓ Found entities in question: {entities}")
    
    if entities:
        points, _ = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=Filter(
                must=[FieldCondition(key="entities", match=MatchAny(any=entities))]
            ),
            limit=top_k
        )
        
        for point in points:
            all_results[str(point.id)] = {
                'payload': point.payload,
                'score': 100 + point.payload.get('importance_score', 5) * 2,
                'match_type': 'entity_match'
            }
    
    entity_time = time.time() - entity_start
    
    # Strategy 2: Semantic search
    semantic_start = time.time()
    if verbose:
        print(f"✓ Searching semantically for: '{user_question}'")
    
    query_vector = embedder.embed_text(user_question)
    search_results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=top_k
    ).points
    
    semantic_time = time.time() - semantic_start
    
    for hit in search_results:
        point_id = str(hit.id)
        base_score = hit.score
        print(f"Debug: Hit ID {point_id} with hit score {hit.score}")
        
        if point_id in all_results:
            all_results[point_id]['score'] += base_score
            all_results[point_id]['match_type'] = 'entity+semantic'
        else:
            all_results[point_id] = {
                'payload': hit.payload,
                'score': base_score,
                'match_type': 'semantic'
            }
    
    # Strategy 3: Boost recent events if query asks about "recent" things
    query_lower = user_question.lower()
    if any(word in query_lower for word in ['recent', 'lately', 'these days', 'now', 'currently']):
        now = datetime.now()
        for item in all_results.values():
            event_date = datetime.fromisoformat(item['payload']['event_timestamp'])
            days_ago = (now - event_date).days
            if days_ago < 14:
                item['score'] += 30
                if verbose:
                    print(f"✓ Boosted recent memory: {item['payload']['summary'][:40]}...")
    
    # Sort by score and filter out low-scoring results
    sorted_results = sorted(all_results.values(), key=lambda x: x['score'], reverse=True)
    
    # Adaptive threshold: If we have entity matches (high scores), be strict
    # If no entity matches, be more lenient
    has_entity_matches = any(r['score'] > 80 for r in sorted_results)
    MIN_SCORE = 60 if has_entity_matches else 0
    
    filtered_results = [r for r in sorted_results if r['score'] > MIN_SCORE][:top_k]
    
    total_time = time.time() - start_time
    
    if verbose:
        print(f"✓ Found {len(filtered_results)} relevant memories (filtered from {len(sorted_results)} total, threshold: {MIN_SCORE})")
        print("-" * 60)
        print(f"⏱️  TIMING BREAKDOWN:")
        print(f"   Entity search: {entity_time*1000:.2f}ms")
        print(f"   Semantic search (inc. embedding): {semantic_time*1000:.2f}ms")
        print(f"   Total retrieval time: {total_time*1000:.2f}ms ({total_time:.3f}s)")
        print("-" * 60)
    
    # Format for LLM
    if not filtered_results:
        return "No relevant memories found.", []
    
    sorted_results = filtered_results  # Use filtered results
    
    context = "=== USER'S MEMORIES ===\n\n"
    for i, item in enumerate(sorted_results, 1):
        p = item['payload']
        context += f"Memory {i}:\n"
        context += f"  Summary: {p['summary']}\n"
        context += f"  Details: {p['details']}\n"
        context += f"  Date: {p['event_timestamp'][:10]}\n"
        context += f"  Type: {p['memory_type']}\n\n"
        context += f"  Score: {item['score']:.1f} (Match type: {item['match_type']})\n"
    
    return context, sorted_results


def create_llm_prompt(user_question, memories_context):
    """Create the full prompt to send to LLM"""
    
    prompt = f"""You are a helpful AI assistant with access to the user's personal memory system.

{memories_context}

Based on the memories above, please answer the following question:

USER QUESTION: {user_question}

INSTRUCTIONS:
- Answer naturally and conversationally
- Only use information from the memories provided above
- If the memories don't contain relevant information, say so honestly
- Be specific and cite which memory you're using when relevant
- If asked about "recent" events, prioritize newer dates
"""
    
    return prompt


def interactive_memory_chat():
    """Main interactive loop"""
    
    print("=" * 70)
    print("🧠 MEMORY-ENHANCED CHAT SYSTEM")
    print("=" * 70)
    print("\nThis system retrieves your memories and generates LLM prompts.")
    print("\nCommands:")
    print("  - Type your question to retrieve memories and get LLM prompt")
    print("  - Type 'quit' or 'exit' to stop")
    print("=" * 70)
    
    while True:
        print("\n")
        user_question = input("💭 Your question: ").strip()
        
        if not user_question:
            continue
            
        if user_question.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Goodbye!")
            break
        
        # Retrieve memories
        memories_context, results = retrieve_memories_for_query(user_question, top_k=5, verbose=True)
        
        # Show retrieved memories
        print("\n📚 RETRIEVED MEMORIES:")
        print("=" * 70)
        print(memories_context)
        
        # # Create LLM prompt
        # full_prompt = create_llm_prompt(user_question, memories_context)
        
        # print("\n" + "=" * 70)
        # print("📋 PROMPT FOR LLM (Copy this to Claude/ChatGPT):")
        # print("=" * 70)
        # print(full_prompt)
        # print("=" * 70)
        
        print("\n💡 Next steps:")
        print("   1. Copy the prompt above")
        print("   2. Paste it into Claude, ChatGPT, or any LLM")
        print("   3. The LLM will answer using your memories!")
        print("\n   OR just paste it here in our conversation and I'll respond!")


# Example usage without interaction
def demo_query(question):
    """Quick demo of a single query"""
    print("=" * 70)
    print(f"DEMO QUERY: {question}")
    print("=" * 70)
    
    memories, results = retrieve_memories_for_query(question, top_k=3, verbose=True)
    prompt = create_llm_prompt(question, memories)
    
    print("\n" + prompt)
    print("\n" + "=" * 70)


if __name__ == "__main__":
    # Uncomment ONE of these:
    
    # Option 1: Interactive mode (recommended)
    interactive_memory_chat()
    
    # Option 2: Demo a single query
    # demo_query("What do you know about my friend Ramesh?")