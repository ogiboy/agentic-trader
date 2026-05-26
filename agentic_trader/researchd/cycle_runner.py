"""Safe executor for the first continuous research-loop slice."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from time import sleep
from typing import Callable
from uuid import uuid4

from agentic_trader.config import Settings
from agentic_trader.payloads import dataclass_payload
from agentic_trader.researchd.control import get_research_cycle_control
from agentic_trader.researchd.cycle_plan import research_cycle_plan_payload
from agentic_trader.researchd.orchestrator import (
    ResearchPipelineResult,
    ResearchSidecar,
    utc_now_iso,
)
from agentic_trader.researchd.persistence import persist_research_result
from agentic_trader.runtime_feed import (
    read_latest_research_snapshot,
    read_research_digest_replay,
    write_research_digest_replay,
)
from agentic_trader.schemas import ResearchDigestReplayRecord, ResearchSnapshotRecord

SleepFn = Callable[[float], None]


def _empty_payload() -> dict[str, object]:
    return {}


def _empty_notes() -> list[str]:
    return []


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
    prior_snapshot_id: str | None = None
    prior_digest_available: bool = False
    persisted_snapshot_id: str | None = None
    next_run_at: str | None = None
    preflight: dict[str, object] = field(default_factory=_empty_payload)
    source_health_delta: dict[str, object] = field(default_factory=_empty_payload)
    cadence: dict[str, object] = field(default_factory=_empty_payload)
    digest: dict[str, object] = field(default_factory=_empty_payload)
    notes: list[str] = field(default_factory=_empty_notes)


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
    """
    Run a bounded, evidence-only research loop that collects research snapshots, optionally persists a digest replay, and returns an execution summary.

    Parameters:
        settings (Settings): Runtime settings used for collection, persistence, and sidecar control.
        symbols (list[str] | None): Optional list of symbols to run the research cycle against. Mutually exclusive with `request`.
        request (ResearchCycleRequest | None): Optional request object describing symbols and execution preferences. Mutually exclusive with `symbols`.
        cycles (int): Requested number of cycles; clamped to a safe range.
        cadence_seconds (int): Intended seconds between cycles; clamped to at least 1.
        max_proposals_per_cycle (int): Upper bound for proposal creation per cycle (research mode disables proposal authority).
        persist (bool): If true, persists snapshots and writes a digest replay artifact.
        sleep_between_cycles (bool): If true, pauses between cycles according to `cadence_seconds`.
        sleep_fn (SleepFn): Function used to perform the sleep/delay between cycles.

    Returns:
        dict[str, object]: A summary payload containing:
            - "cycle": static identifier string.
            - "plan": planned run payload (symbols, cadence, proposal limits).
            - "requested_cycles": original requested cycles.
            - "executed_cycles": number of cycles actually executed.
            - "cadence_seconds": effective cadence used.
            - "persisted": whether persistence was enabled.
            - "sleep_between_cycles": whether sleeps were performed between cycles.
            - "execution_policy": policy flags applied during execution.
            - "operator_control": operator control payload in JSON-serializable form.
            - "digest_replay": persisted digest replay record (JSON-serializable) when persisted.
            - "latest_digest": digest payload from the last execution (or {}).
            - "executions": list of per-cycle execution payloads.
    """

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
    prior_snapshot = read_latest_research_snapshot(settings)
    prior_digest = read_research_digest_replay(settings)
    plan = research_cycle_plan_payload(
        symbols=resolved.symbols,
        cadence_seconds=resolved.safe_cadence,
        max_proposals_per_cycle=resolved.max_proposals_per_cycle,
    )
    operator_control = get_research_cycle_control(settings)
    executions = _execute_research_cycles(
        settings=settings,
        resolved=resolved,
        prior_snapshot=prior_snapshot,
        prior_digest_available=prior_digest is not None,
        sleep_fn=sleep_fn,
    )
    latest_digest = executions[-1].digest if executions else {}
    execution_policy = _execution_policy_payload()
    digest_replay = ResearchDigestReplayRecord(
        artifact_id=f"research-digest-{uuid4()}",
        generated_at=utc_now_iso(),
        snapshot_id=(
            str(latest_digest.get("snapshot_id"))
            if latest_digest.get("snapshot_id") is not None
            else None
        ),
        mode=settings.research_mode,
        backend=(
            executions[-1].backend if executions else settings.research_sidecar_backend
        ),
        watched_symbols=list(resolved.symbols),
        digest=dict(latest_digest),
        executions=[
            research_cycle_execution_payload(execution)
            for execution in executions
        ],
        execution_policy=execution_policy,
        operator_control=operator_control,
        replay_notes=[
            "artifact_replays_operator_digest_only",
            "raw_web_text_is_not_included",
            "broker_or_proposal_authority_is_disabled",
        ],
    )
    if resolved.persist:
        write_research_digest_replay(settings, digest_replay)
    return {
        "cycle": "research-cycle-run",
        "plan": plan,
        "requested_cycles": resolved.requested_cycles,
        "executed_cycles": len(executions),
        "cadence_seconds": resolved.safe_cadence,
        "persisted": resolved.persist,
        "sleep_between_cycles": resolved.sleep_between_cycles,
        "execution_policy": execution_policy,
        "operator_control": operator_control.model_dump(mode="json"),
        "digest_replay": digest_replay.model_dump(mode="json"),
        "latest_digest": latest_digest,
        "executions": [
            research_cycle_execution_payload(execution)
            for execution in executions
        ],
    }


def research_cycle_execution_payload(
    execution: ResearchCycleExecution,
) -> dict[str, object]:
    return dataclass_payload(execution)


def _execute_research_cycles(
    *,
    settings: Settings,
    resolved: _ResolvedResearchCycleRequest,
    prior_snapshot: ResearchSnapshotRecord | None,
    prior_digest_available: bool,
    sleep_fn: SleepFn,
) -> list[ResearchCycleExecution]:
    """
    Run the resolved number of research cycles, tracking and updating prior state between iterations.

    Executes up to `resolved.safe_cycles` cycles by calling the per-cycle runner, collects each cycle's ResearchCycleExecution, updates the prior source health, prior snapshot id, and prior-digest availability for subsequent cycles, and optionally sleeps between cycles according to `resolved.safe_cadence`.

    Parameters:
        settings (Settings): Runtime settings used for each cycle.
        resolved (_ResolvedResearchCycleRequest): Normalized request with safety bounds and execution policy.
        prior_snapshot (ResearchSnapshotRecord | None): Snapshot record from before the run; its source health and snapshot id seed the first cycle.
        prior_digest_available (bool): Whether a prior digest replay is available for the first cycle.
        sleep_fn (SleepFn): Function used to pause between cycles when `resolved.sleep_between_cycles` is true; called with seconds as a float.

    Returns:
        list[ResearchCycleExecution]: Ordered list of execution records, one per executed cycle.
    """
    executions: list[ResearchCycleExecution] = []
    previous_source_health = _source_health_from_snapshot(prior_snapshot)
    previous_snapshot_id = (
        prior_snapshot.snapshot_id if prior_snapshot is not None else None
    )
    has_previous_digest = prior_digest_available
    for index in range(resolved.safe_cycles):
        execution, record, source_health = _run_one_research_cycle(
            settings=settings,
            resolved=resolved,
            cycle_index=index,
            previous_source_health=previous_source_health,
            previous_snapshot_id=previous_snapshot_id,
            previous_digest_available=has_previous_digest,
        )
        executions.append(execution)
        previous_source_health = source_health
        previous_snapshot_id = record.snapshot_id if record is not None else None
        has_previous_digest = resolved.persist
        if resolved.sleep_between_cycles and index < resolved.safe_cycles - 1:
            sleep_fn(float(resolved.safe_cadence))
    return executions


def _run_one_research_cycle(
    *,
    settings: Settings,
    resolved: _ResolvedResearchCycleRequest,
    cycle_index: int,
    previous_source_health: dict[str, int],
    previous_snapshot_id: str | None,
    previous_digest_available: bool,
) -> tuple[ResearchCycleExecution, ResearchSnapshotRecord | None, dict[str, int]]:
    """
    Execute a single research collection cycle and produce its execution record, optional persisted snapshot, and the resulting source health summary.

    Parameters:
        settings (Settings): Runtime configuration and feature flags used for collection and persistence.
        resolved (_ResolvedResearchCycleRequest): Normalized request containing safe cycle/cadence bounds and persistence/sleep flags.
        cycle_index (int): Zero-based index of the cycle being run.
        previous_source_health (dict[str, int]): Source health summary from the previous snapshot or {} if none; used to compute deltas.
        previous_snapshot_id (str | None): Snapshot id of the prior persisted research record, or None if not present.
        previous_digest_available (bool): Whether a prior digest replay was available before this cycle.

    Returns:
        tuple:
            execution (ResearchCycleExecution): Assembled execution record for this cycle.
            record (ResearchSnapshotRecord | None): Persisted snapshot record if persistence was enabled and succeeded, otherwise None.
            source_health_summary (dict[str, int]): Copy of the current cycle's source health summary from the pipeline result.
    """
    started_at = utc_now_iso()
    result = ResearchSidecar(settings).collect_once()
    record = persist_research_result(settings, result) if resolved.persist else None
    completed_at = utc_now_iso()
    next_run_at = _next_cycle_run_at(
        completed_at=completed_at,
        cycle_index=cycle_index,
        safe_cycles=resolved.safe_cycles,
        safe_cadence=resolved.safe_cadence,
        sleep_between_cycles=resolved.sleep_between_cycles,
    )
    execution = _build_research_cycle_execution(
        settings=settings,
        result=result,
        record_snapshot_id=record.snapshot_id if record is not None else None,
        cycle_index=cycle_index + 1,
        started_at=started_at,
        completed_at=completed_at,
        next_run_at=next_run_at,
        previous_source_health=previous_source_health,
        previous_snapshot_id=previous_snapshot_id,
        previous_digest_available=previous_digest_available,
        cadence_seconds=resolved.safe_cadence,
        sleep_between_cycles=resolved.sleep_between_cycles,
    )
    return execution, record, dict(result.state.source_health_summary)


def _next_cycle_run_at(
    *,
    completed_at: str,
    cycle_index: int,
    safe_cycles: int,
    safe_cadence: int,
    sleep_between_cycles: bool,
) -> str | None:
    """
    Compute the ISO 8601 timestamp for when the next cycle should run.

    Parameters:
        completed_at (str): ISO 8601 timestamp when the current cycle completed.
        cycle_index (int): Zero-based index of the current cycle.
        safe_cycles (int): Total number of cycles to execute.
        safe_cadence (int): Number of seconds to wait between cycles.
        sleep_between_cycles (bool): If false, no next-run timestamp is produced.

    Returns:
        str | None: ISO 8601 timestamp for the next run (completed_at + safe_cadence seconds), or `None` if sleeping is disabled or this is the final cycle.
    """
    if not sleep_between_cycles or cycle_index == safe_cycles - 1:
        return None
    return _iso_after(completed_at, safe_cadence)


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
    """
    Resolve and normalize a research cycle request into a safe, validated internal request.

    If a `request` object is provided it is used; otherwise a request is constructed from the individual parameters. Symbols are cleaned (whitespace trimmed and uppercased) and must contain at least one non-empty symbol. Cycle and cadence values are clamped to safe ranges: cycles to the range 1–24 and cadence to a minimum of 1 second. Mutual exclusivity between `request` and `symbols` is enforced.

    Parameters:
        request (ResearchCycleRequest | None): Optional external request object.
        symbols (list[str] | None): Optional list of symbols to construct a request from.
        cycles (int): Requested number of cycles (used when `request` is not provided).
        cadence_seconds (int): Requested cadence in seconds (used when `request` is not provided).
        max_proposals_per_cycle (int): Proposal limit per cycle (used when `request` is not provided).
        persist (bool): Whether to persist outputs (used when `request` is not provided).
        sleep_between_cycles (bool): Whether to sleep between cycles (used when `request` is not provided).

    Returns:
        _ResolvedResearchCycleRequest: Normalized request with cleaned symbols, the original requested cycles, `safe_cycles` clamped to 1–24, `safe_cadence` clamped to at least 1, and other fields forwarded.

    Raises:
        ValueError: If both `request` and `symbols` are provided, or if no valid symbols remain after cleaning.
    """
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
    previous_snapshot_id: str | None,
    previous_digest_available: bool,
    cadence_seconds: int,
    sleep_between_cycles: bool,
) -> ResearchCycleExecution:
    """
    Assembles a ResearchCycleExecution record summarizing a single research cycle run.

    Parameters:
        settings (Settings): Runtime settings used to compute preflight and notes.
        result (ResearchPipelineResult): Collected research result for this cycle.
        record_snapshot_id (str | None): Snapshot ID persisted for this cycle, or `None` if no snapshot was saved.
        cycle_index (int): Index of this cycle within the run (as supplied by the caller).
        started_at (str): ISO timestamp when the cycle started.
        completed_at (str): ISO timestamp when the cycle completed.
        next_run_at (str | None): ISO timestamp for the next scheduled run, or `None` if not applicable.
        previous_source_health (dict[str, int]): Source health summary from the previous cycle or prior snapshot.
        previous_snapshot_id (str | None): Snapshot ID from the prior run/snapshot, or `None` if unavailable.
        previous_digest_available (bool): Whether a prior digest replay was available to this run.
        cadence_seconds (int): Intended cadence in seconds between cycles.
        sleep_between_cycles (bool): Whether the executor will sleep between cycles.

    Returns:
        ResearchCycleExecution: A populated execution dataclass including timing, counts, prior-state linkage,
        preflight status, source health delta, cadence metadata, digest summary, and execution notes.
    """
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
        notes=_research_cycle_notes(
            settings,
            prior_snapshot_id=previous_snapshot_id,
            prior_digest_available=previous_digest_available,
        ),
    )


def _source_health_from_snapshot(
    record: ResearchSnapshotRecord | None,
) -> dict[str, int]:
    """
    Return the source health summary extracted from a research snapshot record.

    Parameters:
        record (ResearchSnapshotRecord | None): Snapshot record to extract source health from.

    Returns:
        dict[str, int]: A mapping of source health keys (e.g., "missing", "stale", "unknown") to their counts.
        Returns an empty dict if `record` is None.
    """
    if record is None:
        return {}
    return dict(record.state.source_health_summary)


def _research_cycle_notes(
    settings: Settings,
    *,
    prior_snapshot_id: str | None,
    prior_digest_available: bool,
) -> list[str]:
    """
    Builds the list of execution notes that describe policy flags and prior-state replay markers.

    Parameters:
        settings (Settings): Global settings; used to determine if the research sidecar is disabled.
        prior_snapshot_id (str | None): If provided, includes a marker indicating a prior snapshot was replayed.
        prior_digest_available (bool): If true, includes a marker indicating a prior digest replay is available.

    Returns:
        list[str]: Ordered list of note strings. Always contains the base policy flags
        ("broker_access=false", "proposal_approval=false", "raw_web_text_in_core_prompt=false")
        and conditionally includes "prior_research_snapshot_replayed", "prior_digest_replay_available",
        and "research_sidecar_disabled".
    """
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
