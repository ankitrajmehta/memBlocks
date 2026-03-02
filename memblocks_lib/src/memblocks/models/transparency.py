"""Transparency data models — pure Pydantic types for the observability layer.

These models are consumed by the log/event classes in services/transparency.py
and may be serialised and returned to callers via the MemBlocksClient API.
"""

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class DBType(str, Enum):
    """Which database the operation was performed against."""

    MONGO = "mongo"
    QDRANT = "qdrant"


class OperationType(str, Enum):
    """Broad category of database write."""

    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    UPSERT = "upsert"


class OperationEntry(BaseModel):
    """A single recorded database write operation."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    db_type: DBType
    collection_name: str
    operation_type: OperationType
    document_id: Optional[str] = None
    payload_summary: str = ""  # brief description of what changed
    success: bool = True
    error: Optional[str] = None


class RetrievalEntry(BaseModel):
    """A single recorded memory retrieval event."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    query_text: str
    source: str  # "semantic", "core", "resource"
    num_results: int = 0
    top_scores: List[float] = Field(default_factory=list)
    memory_ids: List[str] = Field(default_factory=list)
    memory_summaries: List[str] = Field(default_factory=list)
    # Enhanced retrieval metadata
    expanded_queries: List[str] = Field(default_factory=list, description="Query expansion results")
    hypothetical_paragraphs: List[str] = Field(default_factory=list, description="Hypothetical answer paragraphs")
    reranked: bool = Field(default=False, description="Whether results were re-ranked")
    retrieval_method: str = Field(default="vector", description="Retrieval method used: vector, hybrid, etc.")


class PipelineRunEntry(BaseModel):
    """A single recorded pipeline processing run."""

    task_id: str
    timestamp_started: datetime = Field(default_factory=datetime.utcnow)
    timestamp_completed: Optional[datetime] = None
    status: str = "running"  # running | success | failure
    trigger_event: str = ""  # e.g., "message_window_full"
    input_message_count: int = 0
    extracted_semantic_count: int = 0
    conflicts_resolved_count: int = 0
    core_memory_updated: bool = False
    summary_generated: bool = False
    error_details: Optional[str] = None


__all__ = [
    "DBType",
    "OperationType",
    "OperationEntry",
    "RetrievalEntry",
    "PipelineRunEntry",
]
