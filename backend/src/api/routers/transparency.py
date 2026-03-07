"""Transparency router — exposes memblocks_lib observability data."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from backend.src.api.dependencies import get_client
from backend.src.api.routers.auth import CurrentUser, get_current_user
from memblocks import MemBlocksClient

router = APIRouter(prefix="/transparency", tags=["transparency"])


@router.get("/stats", response_model=Dict[str, Any])
async def get_transparency_stats(
    current_user: CurrentUser = Depends(get_current_user),
    client: MemBlocksClient = Depends(get_client),
) -> Dict[str, Any]:
    """Get transparency stats: operation log summary and recent pipeline runs."""
    operation_summary = {}
    try:
        operation_summary = client.operation_log.summary()
    except Exception:
        pass

    pipeline_runs = []
    try:
        recent_runs = client.processing_history.get_runs(limit=10)
        pipeline_runs = [
            {
                "task_id": run.task_id,
                "status": run.status,
                "trigger_event": run.trigger_event,
                "input_message_count": run.input_message_count,
                "extracted_semantic_count": run.extracted_semantic_count,
                "conflicts_resolved_count": run.conflicts_resolved_count,
                "core_memory_updated": run.core_memory_updated,
                "summary_generated": run.summary_generated,
                "timestamp_started": run.timestamp_started.isoformat() if run.timestamp_started else None,
                "timestamp_completed": run.timestamp_completed.isoformat() if run.timestamp_completed else None,
                "error_details": run.error_details,
            }
            for run in recent_runs
        ]
    except Exception:
        pass

    retrieval_entries = []
    try:
        recent_retrievals = client.retrieval_log.get_entries(limit=10)
        retrieval_entries = [
            {
                "source": entry.source,
                "query": entry.query_text,
                "results_count": entry.num_results,
                "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
            }
            for entry in recent_retrievals
        ]
    except Exception:
        pass

    return {
        "operation_summary": operation_summary,
        "pipeline_runs": pipeline_runs,
        "recent_retrievals": retrieval_entries,
    }


@router.get("/processing-history", response_model=List[Dict[str, Any]])
async def get_processing_history(
    limit: int = 20,
    current_user: CurrentUser = Depends(get_current_user),
    client: MemBlocksClient = Depends(get_client),
) -> List[Dict[str, Any]]:
    """Get recent memory pipeline processing runs."""
    runs = client.processing_history.get_runs(limit=limit)
    return [
        {
            "task_id": run.task_id,
            "status": run.status,
            "trigger_event": run.trigger_event,
            "input_message_count": run.input_message_count,
            "extracted_semantic_count": run.extracted_semantic_count,
            "conflicts_resolved_count": run.conflicts_resolved_count,
            "core_memory_updated": run.core_memory_updated,
            "summary_generated": run.summary_generated,
            "timestamp_started": run.timestamp_started.isoformat() if run.timestamp_started else None,
            "timestamp_completed": run.timestamp_completed.isoformat() if run.timestamp_completed else None,
            "error_details": run.error_details,
        }
        for run in runs
    ]
