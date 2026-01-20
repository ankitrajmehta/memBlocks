"""
MemBlocks - Qdrant Schema Setup
================================

This module handles:
1. Connecting Pydantic models to Qdrant collections
2. Creating MemoryBlocks with their associated collections
3. Schema definition and validation

NO data insertion or retrieval - just setup!
"""

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from .embeddings import OllamaEmbeddings
from datetime import datetime
import uuid
import sys
from pathlib import Path
from typing import Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from models.container import MemoryBlock, MemoryBlockMetaData


class MemBlockQdrantManager:
    """
    Manages the connection between MemoryBlock Pydantic models and Qdrant collections.
    
    Architecture:
    -------------
    One MemoryBlock = 3 Qdrant Collections
    
    MemoryBlock "personal" (id: block_abc123)
      ├─ Collection: "block_abc123_semantic"   (SemanticMemoryUnit instances)
      ├─ Collection: "block_abc123_core"       (CoreMemoryUnit instances)
      └─ Collection: "block_abc123_resource"   (ResourceMemoryUnit instances)
    
    Each collection stores:
    - Vector: Embedding of the memory content (768-dim for nomic-embed-text)
    - Payload: The full Pydantic model as JSON
    """
    
    def __init__(self, qdrant_host="localhost", qdrant_port=6333):
        """
        Initialize connection to Qdrant and embedding model.
        
        Args:
            qdrant_host: Qdrant server hostname
            qdrant_port: Qdrant server port
        """
        self.client = QdrantClient(host=qdrant_host, port=qdrant_port)
        self.embedder = OllamaEmbeddings()
        
        # Get embedding dimension from the model
        print("🔍 Detecting embedding dimension...")
        self.vector_size = self.embedder.get_dimension()
        print(f"   ✓ Using {self.vector_size}-dimensional vectors")
        
    def create_memory_block(
        self, 
        description: str, 
        user_id: Optional[str] = None
    ) -> MemoryBlock:
        """
        Create a new MemoryBlock with 3 associated Qdrant collections.
        
        This creates the STRUCTURE only - no data is inserted yet.
        
        Args:
            description: User-provided description of this block's purpose
                        e.g., "Personal memories about friends and family"
            user_id: Optional user identifier for multi-user systems
            
        Returns:
            MemoryBlock instance with metadata and collection references
            
        Example:
            >>> manager = MemBlockQdrantManager()
            >>> block = manager.create_memory_block(
            ...     description="Work-related memories and documents",
            ...     user_id="user_123"
            ... )
            >>> print(block.meta_data.id)
            'block_a1b2c3d4e5f6'
        """
        
        # Generate unique block ID
        block_id = f"block_{uuid.uuid4().hex[:12]}"
        
        print(f"\n{'='*70}")
        print(f"Creating MemoryBlock: {block_id}")
        print(f"{'='*70}")
        print(f"Description: {description}")
        if user_id:
            print(f"User ID: {user_id}")
        
        # Create metadata
        now = datetime.now().isoformat()
        metadata = MemoryBlockMetaData(
            id=block_id,
            created_at=now,
            updated_at=now,
            usage=[],
            user_id=user_id
        )
        
        # Define collection names for this block
        collection_names = {
            'semantic': f"{block_id}_semantic",
            'core': f"{block_id}_core",
            'resource': f"{block_id}_resource"
        }
        
        print(f"\nCreating 3 Qdrant collections:")
        
        # Create each collection
        for section_type, collection_name in collection_names.items():
            self._create_collection(collection_name, section_type)
        
        # Create MemoryBlock instance
        # The Pydantic model stores collection names as strings
        memory_block = MemoryBlock(
            meta_data=metadata,
            description=description,
            semantic_memories=collection_names['semantic'],
            core_memories=collection_names['core'],
            resource_memories=collection_names['resource']
        )
        
        print(f"\n✅ MemoryBlock '{block_id}' created successfully!")
        print(f"   Ready to store memories in 3 separate collections")
        print(f"{'='*70}\n")
        
        return memory_block
    
    def _create_collection(self, collection_name: str, section_type: str):
        """
        Create a single Qdrant collection with proper vector configuration.
        
        Args:
            collection_name: Name of the collection (e.g., "block_abc_semantic")
            section_type: Type of section (semantic/core/resource) for logging
        """
        
        # Check if collection already exists
        if self._collection_exists(collection_name):
            print(f"   ⚠️  [{section_type}] Collection '{collection_name}' already exists")
            return
        
        # Create collection with vector configuration
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=self.vector_size,      # 768 for nomic-embed-text
                distance=Distance.COSINE    # Cosine similarity for semantic search
            )
        )
        
        print(f"   ✅ [{section_type}] {collection_name}")
    
    def _collection_exists(self, collection_name: str) -> bool:
        """
        Check if a Qdrant collection exists.
        
        Args:
            collection_name: Name to check
            
        Returns:
            True if exists, False otherwise
        """
        collections = self.client.get_collections().collections
        return any(c.name == collection_name for c in collections)
    
    def delete_memory_block(self, block: MemoryBlock):
        """
        Delete a MemoryBlock and all its associated Qdrant collections.
        
        WARNING: This permanently deletes all data in the block!
        
        Args:
            block: MemoryBlock instance to delete
        """
        
        print(f"\n🗑️  Deleting MemoryBlock: {block.meta_data.id}")
        
        # Collection names to delete
        collections = [
            block.semantic_memories,
            block.core_memories,
            block.resource_memories
        ]
        
        for collection_name in collections:
            if collection_name and self._collection_exists(collection_name):
                self.client.delete_collection(collection_name)
                print(f"   ✓ Deleted collection: {collection_name}")
        
        print(f"✅ MemoryBlock deleted\n")
    
    def list_all_blocks(self) -> list[str]:
        """
        List all MemoryBlocks by scanning Qdrant collection names.
        
        This finds all collections matching the pattern "block_*_semantic"
        and extracts unique block IDs.
        
        Returns:
            List of block IDs (e.g., ["block_abc123", "block_def456"])
        """
        
        collections = self.client.get_collections().collections
        
        # Extract unique block IDs from collection names
        # Collection names follow pattern: block_<id>_<type>
        block_ids = set()
        for collection in collections:
            name = collection.name
            
            # Check if it's a block collection
            if name.startswith("block_") and "_" in name[6:]:
                # Extract block ID (e.g., "block_abc123" from "block_abc123_semantic")
                parts = name.split("_")
                if len(parts) >= 3:
                    block_id = f"{parts[0]}_{parts[1]}"  # "block_abc123"
                    block_ids.add(block_id)
        
        return sorted(list(block_ids))
    
    def get_collection_info(self, collection_name: str) -> dict:
        """
        Get information about a Qdrant collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Dict with collection metadata
        """
        
        if not self._collection_exists(collection_name):
            return {"error": "Collection does not exist"}
        
        info = self.client.get_collection(collection_name)
        
        return {
            "name": collection_name,
            "vector_size": info.config.params.vectors.size,
            "distance_metric": info.config.params.vectors.distance,
            "points_count": info.points_count,
            "status": info.status
        }
    
    def close(self):
        """Close Qdrant client connection"""
        # Qdrant client doesn't need explicit closing, but good practice
        print("🔌 Connection closed")


# =================================================
# DEMO / TESTING
# =================================================

def demo_basic_setup():
    """
    Demo: Create multiple MemoryBlocks and inspect their structure.
    No data insertion - just schema setup!
    """
    
    print("\n" + "="*70)
    print("MEMBLOCKS QDRANT SETUP DEMO")
    print("="*70)
    
    # Initialize manager
    manager = MemBlockQdrantManager()
    
    # Create personal memory block
    print("\n📦 Creating 'Personal' MemoryBlock...")
    personal_block = manager.create_memory_block(
        description="Personal memories about friends, family, and daily life",
        user_id="user_123"
    )
    
    # Create project memory block
    print("\n📦 Creating 'Project' MemoryBlock...")
    project_block = manager.create_memory_block(
        description="Work and project-related memories, code, and documentation",
        user_id="user_123"
    )
    
    # List all blocks
    print("\n📋 Listing all MemoryBlocks...")
    all_blocks = manager.list_all_blocks()
    print(f"   Total blocks: {len(all_blocks)}")
    for block_id in all_blocks:
        print(f"   - {block_id}")
    
    # Inspect a collection
    print(f"\n🔍 Inspecting collection: {personal_block.semantic_memories}")
    info = manager.get_collection_info(personal_block.semantic_memories)
    print(f"   Vector size: {info['vector_size']}")
    print(f"   Distance metric: {info['distance_metric']}")
    print(f"   Points stored: {info['points_count']}")
    print(f"   Status: {info['status']}")
    
    # Show block structure
    print(f"\n📊 MemoryBlock Structure:")
    print(f"   Block ID: {personal_block.meta_data.id}")
    print(f"   Description: {personal_block.description}")
    print(f"   Collections:")
    print(f"     - Semantic: {personal_block.semantic_memories}")
    print(f"     - Core: {personal_block.core_memories}")
    print(f"     - Resource: {personal_block.resource_memories}")
    
    print("\n" + "="*70)
    print("✅ Setup complete! Collections created and ready for data.")
    print("="*70)
    
    return manager, personal_block, project_block


if __name__ == "__main__":
    demo_basic_setup()