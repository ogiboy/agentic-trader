"""Execution payload helpers for bounded research cycles."""

from __future__ import annotations

from agentic_trader.config import Settings
from agentic_trader.researchd.cycle_runner_types import ResearchCycleExecution
from agentic_trader.researchd.orchestrator import ResearchPipelineResult
from agentic_trader.schemas import ResearchSnapshotRecord


def build_research_cycle_execution(
    *,
    settings: Settings,
    result: ResearchPipelineResult,
    record_snapshot_id: str | None,
    cycle_index: int,
    started_at: str,
    completed_at: str,
    next_run_at: str | None,
    previous_source_health: dict[str, int],
    previous_snapshot_id: str | None,
    previous_digest_available: bool,
    cadence_seconds: int,
    sleep_between_cycles: bool,
) -> ResearchCycleExecution:
    """Assemble a cycle execution record from pipeline result and replay state."""

    source_health_summary = dict(result.state.source_health_summary)
    return ResearchCycleExecution(
        cycle_index=cycle_index,
        started_at=started_at,
        completed_at=completed_at,
        state_status=result.state.status,
        backend=result.state.backend,
        watched_symbols=list(result.state.watched_symbols),
        raw_evidence_count=len(result.raw_evidence),
        macro_event_count=len(result.macro_events),
        social_signal_count=len(result.social_signals),
        prior_snapshot_id=previous_snapshot_id,
        prior_digest_available=previous_digest_available,
        persisted_snapshot_id=record_snapshot_id,
        next_run_at=next_run_at,
        preflight=preflight_payload(
            settings=settings,
            state_status=result.state.status,
            source_health_summary=source_health_summary,
        ),
        source_health_delta=source_health_delta(
            current=source_health_summary,
            previous=previous_source_health,
        ),
        cadence={
            "seconds": cadence_seconds,
            "sleep_between_cycles": sleep_between_cycles,
            "next_run_at": next_run_at,
        },
        digest=digest_payload(
            result=result,
            snapshot_id=record_snapshot_id,
        ),
        notes=research_cycle_notes(
            settings,
            prior_snapshot_id=previous_snapshot_id,
            prior_digest_available=previous_digest_available,
        ),
    )


def source_health_from_snapshot(
    record: ResearchSnapshotRecord | None,
) -> dict[str, int]:
    if record is None:
        return {}
    return dict(record.state.source_health_summary)


def research_cycle_notes(
    settings: Settings,
    *,
    prior_snapshot_id: str | None,
    prior_digest_available: bool,
) -> list[str]:
    notes = [
        "broker_access=false",
        "proposal_approval=false",
        "raw_web_text_in_core_prompt=false",
    ]
    if prior_snapshot_id is not None:
        notes.append("prior_research_snapshot_replayed")
    if prior_digest_available:
        notes.append("prior_digest_replay_available")
    if not settings.research_sidecar_enabled or settings.research_mode == "off":
        notes.append("research_sidecar_disabled")
    return notes


def preflight_payload(
    *,
    settings: Settings,
    state_status: str,
    source_health_summary: dict[str, int],
) -> dict[str, object]:
    blocking_gates: list[str] = []
    if not settings.research_sidecar_enabled or settings.research_mode == "off":
        blocking_gates.append("research_sidecar_disabled")
    if state_status == "failed":
        blocking_gates.append("research_sidecar_failed")
    degraded_sources = {
        key: value
        for key, value in source_health_summary.items()
        if key in {"missing", "unknown", "stale"} and value > 0
    }
    if blocking_gates:
        status = "blocked"
    elif degraded_sources:
        status = "degraded"
    else:
        status = "passed"
    return {
        "phase": "PRE-FLIGHT",
        "status": status,
        "blocking_gates": blocking_gates,
        "degraded_sources": degraded_sources,
        "source_health_summary": source_health_summary,
    }


def source_health_delta(
    *,
    current: dict[str, int],
    previous: dict[str, int],
) -> dict[str, object]:
    keys = sorted(set(current) | set(previous))
    return {
        "current": current,
        "previous": previous,
        "delta": {key: current.get(key, 0) - previous.get(key, 0) for key in keys},
    }


def digest_payload(
    *,
    result: ResearchPipelineResult,
    snapshot_id: str | None,
) -> dict[str, object]:
    source_health_summary = dict(result.state.source_health_summary)
    raw_web_text_injected = bool(result.memory_update.get("raw_web_text_injected"))
    return {
        "summary": result.world_state.summary if result.world_state is not None else "",
        "snapshot_id": snapshot_id
        or (result.world_state.snapshot_id if result.world_state is not None else None),
        "provider_count": len(result.state.provider_health),
        "fresh_sources": source_health_summary.get("fresh", 0),
        "missing_sources": source_health_summary.get("missing", 0),
        "unknown_sources": source_health_summary.get("unknown", 0),
        "raw_evidence_count": len(result.raw_evidence),
        "macro_event_count": len(result.macro_events),
        "social_signal_count": len(result.social_signals),
        "memory_status": str(result.memory_update.get("status", "unknown")),
        "raw_web_text_injected": raw_web_text_injected,
        "watch_next": list(result.state.watched_symbols),
        "operator_next_step": (
            "review_source_health"
            if source_health_summary.get("missing", 0)
            or source_health_summary.get("unknown", 0)
            else "review_digest"
        ),
    }
