from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from vector_db.try.embeddings import OllamaEmbeddings
from datetime import datetime
import uuid

# Initialize
client = QdrantClient(host="localhost", port=6333)
embedder = OllamaEmbeddings()
COLLECTION_NAME = "EventFactualMemory"

# Hardcoded memories - CUSTOMIZE WITH YOUR INFO
memories = [
    {
        "summary": "Bestfriend Ramesh got married",
        "details": "My bestfriend Ramesh got married on January 10th, 2026. It was a beautiful ceremony with family and close friends.",
        "memory_type": "event",
        "event_timestamp": "2026-01-10T00:00:00",
        "stored_timestamp": datetime.now().isoformat(),
        "entities": ["Ramesh", "bestfriend", "marriage", "wedding"],
        "source": "user_provided",
        "importance_score": 9
    },
    {
        "summary": "Ramesh works at Amazon",
        "details": "Ramesh is employed at Amazon as a software engineer. He works in the AWS division.",
        "memory_type": "fact",
        "event_timestamp": "2025-03-01T00:00:00",
        "stored_timestamp": datetime.now().isoformat(),
        "entities": ["Ramesh", "Amazon", "AWS", "software engineer"],
        "source": "user_provided",
        "importance_score": 7
    },
    {
        "summary": "Embark College is located in Pulchowk",
        "details": "Embark College is an educational institution located in Pulchowk, Lalitpur. It's known for tech education.",
        "memory_type": "fact",
        "event_timestamp": "2020-01-01T00:00:00",
        "stored_timestamp": datetime.now().isoformat(),
        "entities": ["Embark College", "Pulchowk", "Lalitpur", "education"],
        "source": "user_provided",
        "importance_score": 6
    },
    {
        "summary": "Attended workshop at Embark College",
        "details": "I attended a workshop on AI and Machine Learning at Embark College in Pulchowk on January 15th, 2026. Learned about vector databases.",
        "memory_type": "event",
        "event_timestamp": "2026-01-15T00:00:00",
        "stored_timestamp": datetime.now().isoformat(),
        "entities": ["Embark College", "workshop", "AI", "Machine Learning", "vector databases"],
        "source": "user_provided",
        "importance_score": 8
    },
    {
        "summary": "Favorite coffee shop is Himalayan Java",
        "details": "My favorite coffee place is Himalayan Java. I usually order cappuccino and work on my laptop there.",
        "memory_type": "fact",
        "event_timestamp": "2024-01-01T00:00:00",
        "stored_timestamp": datetime.now().isoformat(),
        "entities": ["Himalayan Java", "coffee", "cappuccino", "cafe"],
        "source": "user_provided",
        "importance_score": 5
    },
    {
        "summary": "Working on MemBlocks project",
        "details": "Currently developing MemBlocks - a modular memory framework for LLMs. Using Qdrant for vector storage and Ollama for embeddings.",
        "memory_type": "event",
        "event_timestamp": "2026-01-16T00:00:00",
        "stored_timestamp": datetime.now().isoformat(),
        "entities": ["MemBlocks", "Qdrant", "Ollama", "LLM", "vector database", "project"],
        "source": "user_provided",
        "importance_score": 10
    }
]

try:
    print("🔄 Generating embeddings and inserting memories...")
    print(f"   Total memories: {len(memories)}")
    
    points = []
    
    for i, memory in enumerate(memories, 1):
        # Combine summary and details for embedding
        text_to_embed = f"{memory['summary']}. {memory['details']}"
        
        print(f"\n   [{i}/{len(memories)}] Processing: {memory['summary']}")
        
        # Generate embedding
        vector = embedder.embed_text(text_to_embed)
        
        # Create point
        point = PointStruct(
            id=str(uuid.uuid4()),  # Generate unique ID
            vector=vector,
            payload=memory  # All metadata goes in payload
        )
        
        points.append(point)
        print(f"      ✅ Embedded (dim: {len(vector)})")
    
    # Insert all points at once
    print(f"\n📤 Uploading {len(points)} points to Qdrant...")
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )
    
    print(f"✅ Successfully inserted {len(memories)} memories!")
    
    # Verify
    collection_info = client.get_collection(collection_name=COLLECTION_NAME)
    print(f"\n📊 Collection stats:")
    print(f"   Total points: {collection_info.points_count}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    raise