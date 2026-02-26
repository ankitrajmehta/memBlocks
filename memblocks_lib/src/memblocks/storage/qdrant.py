"""QdrantAdapter — non-singleton, config-injected Qdrant vector database layer."""

from uuid import uuid4
from typing import Optional, Dict, Any, List, TYPE_CHECKING

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    Filter,
    PointIdsList,
    PointStruct,
    VectorParams,
)

if TYPE_CHECKING:
    from memblocks.config import MemBlocksConfig
    from memblocks.storage.embeddings import EmbeddingProvider
    from memblocks.services.transparency import OperationLog


class QdrantAdapter:
    """
    Instance-based Qdrant vector database adapter.

    Replaces: ``vector_db/vector_db_manager.py`` → ``VectorDBManager``
    (all-static class with import-time side-effects).

    Changes from VectorDBManager:

    1. **No import-time connections.**
       The old class ran three statements at class body level
       (vector_db_manager.py:12-14):
           client = QdrantClient(host="localhost", port=6333, prefer_grpc=True)
           embedder = OllamaEmbeddings()
           vector_size = embedder.get_dimension()   # HTTP call to Ollama!
       This caused an ImportError if Qdrant or Ollama was down.
       The new constructor is safe to call regardless of service availability.

    2. **Config-driven host/port.**
       VectorDBManager ignored ``config.qdrant_host`` / ``config.qdrant_port``
       entirely and hardcoded "localhost:6333".  This adapter reads from config.

    3. **Static → instance methods.**
       All six static methods become regular instance methods using
       ``self._client`` instead of ``VectorDBManager.get_client()``.

    4. **Lazy vector size.**
       ``vector_size`` was resolved at class creation time (HTTP call).
       It is now resolved lazily on the first ``create_collection`` call.

    5. **Bug fix: ``get_all_points()`` added.**
       ``backend/routers/memory.py`` (lines 129, 238) calls
       ``VectorDBManager.get_all_points()`` which did not exist.
    """

    def __init__(
        self,
        config: "MemBlocksConfig",
        embeddings: Optional["EmbeddingProvider"] = None,
        operation_log: Optional["OperationLog"] = None,
    ) -> None:
        """
        Args:
            config: Library configuration. Reads qdrant_host, qdrant_port,
                    and qdrant_prefer_grpc.
            embeddings: Optional EmbeddingProvider used to resolve vector
                        dimension lazily.  If not supplied, ``create_collection``
                        will require the ``vector_size`` argument.
            operation_log: Optional transparency log placeholder.  Will be
                           wired fully in Phase 9.
        """
        self._client = QdrantClient(
            host=config.qdrant_host,  # Was: hardcoded "localhost"
            port=config.qdrant_port,  # Was: hardcoded 6333
            prefer_grpc=config.qdrant_prefer_grpc,
        )
        self._embeddings: Optional["EmbeddingProvider"] = embeddings
        self._log: Optional["OperationLog"] = operation_log
        self._vector_size: Optional[int] = None  # Resolved lazily

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _record_op(
        self,
        collection_name: str,
        operation_type: str,
        document_id: Optional[str] = None,
        payload_summary: str = "",
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """Record a write operation in the OperationLog (no-op if log not set)."""
        if self._log is None:
            return
        from memblocks.models.transparency import DBType, OperationEntry, OperationType

        self._log.record(
            OperationEntry(
                db_type=DBType.QDRANT,
                collection_name=collection_name,
                operation_type=OperationType(operation_type),
                document_id=document_id,
                payload_summary=payload_summary,
                success=success,
                error=error,
            )
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_vector_size(self) -> int:
        """
        Resolve and cache vector dimension.

        Lazily fetches the dimension from the EmbeddingProvider on first call
        (replaces the import-time ``vector_size = embedder.get_dimension()``
        at vector_db_manager.py:14).
        """
        if self._vector_size is None:
            if self._embeddings is None:
                raise RuntimeError(
                    "QdrantAdapter needs an EmbeddingProvider to resolve vector "
                    "dimension automatically. Either pass one to the constructor "
                    "or supply vector_size explicitly to create_collection()."
                )
            self._vector_size = self._embeddings.get_dimension()
        return self._vector_size

    # ------------------------------------------------------------------
    # Collection management
    # Mirrors VectorDBManager.create_collection() (vector_db_manager.py:29-58)
    # ------------------------------------------------------------------

    def create_collection(
        self,
        collection_name: str,
        vector_size: Optional[int] = None,
    ) -> bool:
        """
        Create a Qdrant collection if it does not already exist.

        Args:
            collection_name: Name of the collection.
            vector_size: Dimension of the vectors.  If None and an
                         EmbeddingProvider was supplied, the dimension is
                         resolved automatically.

        Returns:
            True if the collection exists (or was just created).
        """
        resolved_size = vector_size or self._get_vector_size()
        try:
            collections = self._client.get_collections().collections
            if any(col.name == collection_name for col in collections):
                print(f"Collection '{collection_name}' already exists.")
                return True

            self._client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=resolved_size,
                    distance=Distance.COSINE,
                ),
            )
            return True
        except Exception as e:
            print(f"Error creating collection: {e}")
            return False

    # ------------------------------------------------------------------
    # Vector writes
    # Mirrors VectorDBManager.store_vector() (vector_db_manager.py:61-85)
    # ------------------------------------------------------------------

    def store_vector(
        self,
        collection_name: str,
        vector: List[float],
        payload: Dict[str, Any],
        point_id: Optional[str] = None,
    ) -> bool:
        """
        Upsert a single vector into a collection.

        Args:
            collection_name: Target Qdrant collection.
            vector: Embedding vector.
            payload: Metadata stored alongside the vector.
            point_id: Optional explicit UUID string ID.  Auto-generated if None.

        Returns:
            True if successful, False otherwise.
        """
        try:
            resolved_id = point_id or str(uuid4())
            self._client.upsert(
                collection_name=collection_name,
                points=[
                    PointStruct(
                        id=resolved_id,
                        vector=vector,
                        payload=payload,
                    )
                ],
                wait=False,
            )
            self._record_op(
                collection_name,
                "upsert",
                document_id=resolved_id,
                payload_summary=f"store vector in {collection_name}",
            )
            return True
        except Exception as e:
            self._record_op(
                collection_name,
                "upsert",
                success=False,
                error=str(e),
                payload_summary=f"store vector in {collection_name}",
            )
            print(f"Error storing vector: {e}")
            return False

    # ------------------------------------------------------------------
    # Vector reads
    # Mirrors VectorDBManager.retrieve_from_vector() (vector_db_manager.py:88-108)
    # ------------------------------------------------------------------

    def retrieve_from_vector(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 5,
    ) -> list:
        """
        Retrieve top-k most similar vectors.

        Args:
            collection_name: Source Qdrant collection.
            query_vector: Query embedding.
            top_k: Number of results to return.

        Returns:
            List of ``ScoredPoint`` objects (qdrant_client types).
        """
        try:
            results = self._client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=top_k,
            )
            return results.points
        except Exception as e:
            print(f"Error retrieving vectors: {e}")
            return []

    # Unused
    def retrieve_from_payload(
        self,
        collection_name: str,
        payload_filter: Filter,
        top_k: int = 5,
    ) -> list:
        """
        Retrieve vectors by payload filter (scroll).

        Mirrors VectorDBManager.retrieve_from_payload() (vector_db_manager.py:111-143).

        Args:
            collection_name: Source Qdrant collection.
            payload_filter: Qdrant ``Filter`` object.
            top_k: Maximum number of results.

        Returns:
            List of ``Record`` objects (qdrant_client types).
        """
        try:
            if hasattr(self._client, "scroll"):
                points, _ = self._client.scroll(
                    collection_name=collection_name,
                    scroll_filter=payload_filter,
                    limit=top_k,
                    with_vectors=False,
                )
                return points

            results = self._client.query_points(
                collection_name=collection_name,
                query_filter=payload_filter,
                limit=top_k,
                with_vectors=False,
            )
            return results.points
        except Exception as e:
            print(f"Error retrieving vectors by payload: {e}")
            return []

    class QueryObject:
        query_vector: List[float]
        keywords: List[str] 
        entities: List[str]
            
    def hybrid_retrieve(self, query_objects: List[QueryObject], top_k: int = 5) -> list:
        """
        Retrieve vectors by hybrid search.
        Use query_vector for vector search
        Use keywords and entities for BM25 search
        Combine the results using Reciprocal Rank Fusion (RRF)
        """
        #TODO: implement
        pass


    # ------------------------------------------------------------------
    # Vector deletion
    # Mirrors VectorDBManager.delete_vector() (vector_db_manager.py:146-168)
    # ------------------------------------------------------------------

    def delete_vector(self, collection_name: str, point_id: str) -> bool:
        """
        Delete a single point from a collection.

        Args:
            collection_name: Source Qdrant collection.
            point_id: UUID string ID of the point to delete.

        Returns:
            True if successful, False on error.
        """
        try:
            self._client.delete(
                collection_name=collection_name,
                points_selector=PointIdsList(points=[point_id]),
            )
            self._record_op(
                collection_name,
                "delete",
                document_id=point_id,
                payload_summary=f"delete vector {point_id} from {collection_name}",
            )
            print(f"✓ Deleted vector {point_id} from {collection_name}")
            return True
        except Exception as e:
            self._record_op(
                collection_name,
                "delete",
                document_id=point_id,
                success=False,
                error=str(e),
                payload_summary=f"delete vector {point_id} from {collection_name}",
            )
            print(f"⚠️ Error deleting vector {point_id}: {e}")
            return False

    # ------------------------------------------------------------------
    # Bug fix: get_all_points()
    # Referenced by backend/routers/memory.py:129 and :238 but never
    # implemented in VectorDBManager. Added here.
    # ------------------------------------------------------------------

    def get_all_points(
        self,
        collection_name: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all points from a collection (for admin/debugging purposes).

        Fixes the missing ``VectorDBManager.get_all_points()`` referenced in
        ``backend/routers/memory.py`` lines 129 and 238.

        Args:
            collection_name: Source Qdrant collection.
            limit: Maximum number of points to return (default 100).

        Returns:
            List of dicts with ``id`` and ``payload`` keys.
        """
        try:
            records, _ = self._client.scroll(
                collection_name=collection_name,
                limit=limit,
                with_vectors=False,
                with_payload=True,
            )
            return [
                {"id": str(record.id), "payload": record.payload} for record in records
            ]
        except Exception as e:
            print(f"Error retrieving all points from '{collection_name}': {e}")
            return []
