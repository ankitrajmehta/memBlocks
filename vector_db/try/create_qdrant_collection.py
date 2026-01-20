import sys
from pathlib import Path

# Add setup directory to path
setup_dir = Path(__file__).parent.parent / "setup"
sys.path.insert(0, str(setup_dir))

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from embeddings import OllamaEmbeddings
from datetime import datetime
import re
import time

# Initialize clients
client = QdrantClient(host="localhost", port=6333)
embedder = OllamaEmbeddings()

# Collection name
COLLECTION_NAME = "EventFactualMemory"

try:
    # Check if collection exists and delete it (for fresh start)
    collections = client.get_collections().collections
    if any(c.name == COLLECTION_NAME for c in collections):
        print(f"⚠️  Collection '{COLLECTION_NAME}' already exists. Deleting it...")
        client.delete_collection(collection_name=COLLECTION_NAME)
        print("✅ Deleted old collection")
    
    # Get embedding dimension
    print("\n📏 Getting embedding dimension...")
    vector_size = embedder.get_dimension()
    print(f"   Dimension: {vector_size}")
    
    # Create collection
    print(f"\n🏗️  Creating collection '{COLLECTION_NAME}'...")
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=vector_size,
            distance=Distance.COSINE  # Cosine similarity for semantic search
        )
    )
    
    print(f"✅ Collection '{COLLECTION_NAME}' created successfully!")
    
    # Verify collection
    collection_info = client.get_collection(collection_name=COLLECTION_NAME)
    print(f"\n📊 Collection Info:")
    print(f"   Name: {collection_info.config.params.vectors.size}")
    print(f"   Vector Size: {collection_info.config.params.vectors.size}")
    print(f"   Distance Metric: {collection_info.config.params.vectors.distance}")
    print(f"   Points Count: {collection_info.points_count}")
    
    print("\n" + "="*60)
    print("PAYLOAD SCHEMA (Qdrant uses flexible JSON payloads):")
    print("="*60)
    print("""
    Each point will have these fields in payload:
    - summary (str): Short description
    - details (str): Extended context
    - memory_type (str): 'event' or 'fact'
    - event_timestamp (str): ISO datetime
    - stored_timestamp (str): ISO datetime
    - entities (list): Extracted keywords
    - source (str): Origin of memory
    - importance_score (int): 1-10 ranking
    """)
    
except Exception as e:
    print(f"❌ Error: {e}")
    raise