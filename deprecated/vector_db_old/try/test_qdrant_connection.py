from qdrant_client import QdrantClient
import requests

# Connect to local Qdrant
client = QdrantClient(host="localhost", port=6333)

try:
    # Check connection
    print("🔍 Testing Qdrant connection...")
    
    # Get cluster info
    info = client.get_collections()
    print(f"✅ Connected to Qdrant successfully!")
    print(f"\nCollections: {len(info.collections)}")
    
    if info.collections:
        for collection in info.collections:
            print(f"  - {collection.name}")
    else:
        print("  (No collections yet)")
    
    # Get Qdrant version/health
    response = requests.get("http://localhost:6333/collections")
    if response.status_code == 200:
        print(f"\n💚 Health status: OK")
    
except Exception as e:
    print(f"❌ Error connecting to Qdrant: {e}")