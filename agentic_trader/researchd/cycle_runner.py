"""Safe executor for the first continuous research-loop slice."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from time import sleep
from typing import Callable

from agentic_trader.config import Settings
from agentic_trader.researchd.cycle_plan import research_cycle_plan_payload
from agentic_trader.researchd.orchestrator import (
    ResearchPipelineResult,
    ResearchSidecar,
    utc_now_iso,
)
from agentic_trader.researchd.persistence import persist_research_result

SleepFn = Callable[[float], None]


@dataclass(frozen=True)
class ResearchCycleRequest:
    symbols: list[str]
    cycles: int = 1
    cadence_seconds: int = 60
    max_proposals_per_cycle: int = 1
    persist: bool = True
    sleep_between_cycles: bool = True


@dataclass(frozen=True)
class _ResolvedResearchCycleRequest:
    symbols: list[str]
    requested_cycles: int
    safe_cycles: int
    safe_cadence: int
    max_proposals_per_cycle: int
    persist: bool
    sleep_between_cycles: bool


@dataclass(frozen=True)
class ResearchCycleExecution:
    """One safe research-loop iteration."""

    cycle_index: int
    started_at: str
    completed_at: str
    state_status: str
    backend: str
    watched_symbols: list[str]
    raw_evidence_count: int
    macro_event_count: int
    social_signal_count: int
    persisted_snapshot_id: str | None = None
    next_run_at: str | None = None
    preflight: dict[str, object] = field(default_factory=dict)
    source_health_delta: dict[str, object] = field(default_factory=dict)
    cadence: dict[str, object] = field(default_factory=dict)
    digest: dict[str, object] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, object]:
        return {
            "cycle_index": self.cycle_index,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "state_status": self.state_status,
            "backend": self.backend,
            "watched_symbols": list(self.watched_symbols),
            "raw_evidence_count": self.raw_evidence_count,
            "macro_event_count": self.macro_event_count,
            "social_signal_count": self.social_signal_count,
            "persisted_snapshot_id": self.persisted_snapshot_id,
            "next_run_at": self.next_run_at,
            "preflight": dict(self.preflight),
            "source_health_delta": dict(self.source_health_delta),
            "cadence": dict(self.cadence),
            "digest": dict(self.digest),
            "notes": list(self.notes),
        }


def run_research_cycle(
    settings: Settings,
    *,
    symbols: list[str] | None = None,
    request: ResearchCycleRequest | None = None,
    cycles: int = 1,
    cadence_seconds: int = 60,
    max_proposals_per_cycle: int = 1,
    persist: bool = True,
    sleep_between_cycles: bool = True,
    sleep_fn: SleepFn = sleep,
) -> dict[str, object]:
    """Run a bounded, evidence-only research cycle without broker authority."""

    resolved = _resolve_research_cycle_request(
        request=request,
        symbols=symbols,
        cycles=cycles,
        cadence_seconds=cadence_seconds,
        max_proposals_per_cycle=max_proposals_per_cycle,
        persist=persist,
        sleep_between_cycles=sleep_between_cycles,
    )
    settings.research_symbols = ",".join(resolved.symbols)
    plan = research_cycle_plan_payload(
        symbols=resolved.symbols,
        cadence_seconds=resolved.safe_cadence,
        max_proposals_per_cycle=resolved.max_proposals_per_cycle,
    )
    executions: list[ResearchCycleExecution] = []
    previous_source_health: dict[str, int] = {}
    for index in range(resolved.safe_cycles):
        started_at = utc_now_iso()
        result = ResearchSidecar(settings).collect_once()
        record = persist_research_result(settings, result) if resolved.persist else None
        completed_at = utc_now_iso()
        is_final_cycle = index == resolved.safe_cycles - 1
        next_run_at = (
            _iso_after(completed_at, resolved.safe_cadence)
            if resolved.sleep_between_cycles and not is_final_cycle
            else None
        )
        source_health_summary = dict(result.state.source_health_summary)
        executions.append(
            _build_research_cycle_execution(
                settings=settings,
                result=result,
                record_snapshot_id=record.snapshot_id if record is not None else None,
                cycle_index=index + 1,
                started_at=started_at,
                completed_at=completed_at,
                next_run_at=next_run_at,
                previous_source_health=previous_source_health,
                cadence_seconds=resolved.safe_cadence,
                sleep_between_cycles=resolved.sleep_between_cycles,
            )
        )
        previous_source_health = source_health_summary
        if resolved.sleep_between_cycles and index < resolved.safe_cycles - 1:
            sleep_fn(float(resolved.safe_cadence))

    latest_digest = executions[-1].digest if executions else {}
    return {
        "cycle": "research-cycle-run",
        "plan": plan,
        "requested_cycles": resolved.requested_cycles,
        "executed_cycles": len(executions),
        "cadence_seconds": resolved.safe_cadence,
        "persisted": resolved.persist,
        "sleep_between_cycles": resolved.sleep_between_cycles,
        "execution_policy": _execution_policy_payload(),
        "latest_digest": latest_digest,
        "executions": [execution.to_payload() for execution in executions],
    }


def _resolve_research_cycle_request(
    *,
    request: ResearchCycleRequest | None,
    symbols: list[str] | None,
    cycles: int,
    cadence_seconds: int,
    max_proposals_per_cycle: int,
    persist: bool,
    sleep_between_cycles: bool,
) -> _ResolvedResearchCycleRequest:
    if request is not None and symbols is not None:
        raise ValueError("Pass either request or symbols, not both.")
    resolved_request = request or ResearchCycleRequest(
        symbols=symbols or [],
        cycles=cycles,
        cadence_seconds=cadence_seconds,
        max_proposals_per_cycle=max_proposals_per_cycle,
        persist=persist,
        sleep_between_cycles=sleep_between_cycles,
    )
    clean_symbols = _clean_research_symbols(resolved_request.symbols)
    if not clean_symbols:
        raise ValueError("symbols must contain at least one non-empty symbol")
    return _ResolvedResearchCycleRequest(
        symbols=clean_symbols,
        requested_cycles=resolved_request.cycles,
        safe_cycles=max(1, min(resolved_request.cycles, 24)),
        safe_cadence=max(1, resolved_request.cadence_seconds),
        max_proposals_per_cycle=resolved_request.max_proposals_per_cycle,
        persist=resolved_request.persist,
        sleep_between_cycles=resolved_request.sleep_between_cycles,
    )


def _clean_research_symbols(symbols: list[str]) -> list[str]:
    return [symbol.strip().upper() for symbol in symbols if symbol.strip()]


def _build_research_cycle_execution(
    *,
    settings: Settings,
    result: ResearchPipelineResult,
    record_snapshot_id: str | None,
    cycle_index: int,
    started_at: str,
    completed_at: str,
    next_run_at: str | None,
    previous_source_health: dict[str, int],
    cadence_seconds: int,
    sleep_between_cycles: bool,
) -> ResearchCycleExecution:
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
        persisted_snapshot_id=record_snapshot_id,
        next_run_at=next_run_at,
        preflight=_preflight_payload(
            settings=settings,
            state_status=result.state.status,
            source_health_summary=source_health_summary,
        ),
        source_health_delta=_source_health_delta(
            current=source_health_summary,
            previous=previous_source_health,
        ),
        cadence={
            "seconds": cadence_seconds,
            "sleep_between_cycles": sleep_between_cycles,
            "next_run_at": next_run_at,
        },
        digest=_digest_payload(
            result=result,
            snapshot_id=record_snapshot_id,
        ),
        notes=_research_cycle_notes(settings),
    )


def _research_cycle_notes(settings: Settings) -> list[str]:
    notes = [
        "broker_access=false",
        "proposal_approval=false",
        "raw_web_text_in_core_prompt=false",
    ]
    if not settings.research_sidecar_enabled or settings.research_mode == "off":
        notes.append("research_sidecar_disabled")
    return notes


def _execution_policy_payload() -> dict[str, bool]:
    return {
        "broker_access": False,
        "proposal_approval": False,
        "proposal_creation": False,
        "raw_web_text_in_core_prompt": False,
        "manual_review_required": True,
    }


def _iso_after(iso_value: str, seconds: int) -> str:
    parsed = datetime.fromisoformat(iso_value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return (parsed + timedelta(seconds=seconds)).isoformat()


def _preflight_payload(
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


def _source_health_delta(
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


def _digest_payload(
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
