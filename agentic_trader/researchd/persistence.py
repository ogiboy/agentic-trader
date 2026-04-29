"""Persistence helpers for research sidecar snapshots."""

from uuid import uuid4

from agentic_trader.config import Settings
from agentic_trader.researchd.orchestrator import ResearchPipelineResult, utc_now_iso
from agentic_trader.runtime_feed import append_research_snapshot
from agentic_trader.schemas import ResearchSnapshotRecord


def record_from_pipeline_result(
    result: ResearchPipelineResult,
) -> ResearchSnapshotRecord:
    """Build a file-backed snapshot record from a sidecar result."""
    snapshot_id = (
        result.world_state.snapshot_id
        if result.world_state is not None
        else f"research-{uuid4()}"
    )
    created_at = (
        result.world_state.generated_at
        if result.world_state is not None
        else result.state.updated_at or utc_now_iso()
    )
    return ResearchSnapshotRecord(
        snapshot_id=snapshot_id,
        created_at=created_at,
        mode=result.state.mode,
        backend=result.state.backend,
        status=result.state.status,
        watched_symbols=result.state.watched_symbols,
        raw_evidence=list(result.raw_evidence),
        world_state=result.world_state,
        state=result.state,
        memory_update=dict(result.memory_update),
    )


def persist_research_result(
    settings: Settings, result: ResearchPipelineResult
) -> ResearchSnapshotRecord:
    """Persist a sidecar snapshot without opening the main trading database."""
    record = record_from_pipeline_result(result)
    append_research_snapshot(settings, record)
    return record
