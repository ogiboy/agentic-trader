"""Safe executor for the first continuous research-loop slice."""

from __future__ import annotations

from time import sleep

from agentic_trader.config import Settings
from agentic_trader.researchd.control import get_research_cycle_control
from agentic_trader.researchd.cycle_execution import (
    build_research_cycle_execution,
    source_health_from_snapshot,
)
from agentic_trader.researchd.cycle_plan import research_cycle_plan_payload
from agentic_trader.researchd.cycle_request import (
    next_cycle_run_at,
    resolve_research_cycle_request,
)
from agentic_trader.researchd.cycle_runner_payloads import (
    execution_policy_payload,
    research_cycle_execution_payload,
    research_cycle_run_payload,
    research_digest_replay,
)
from agentic_trader.researchd.cycle_runner_types import (
    ResearchCycleExecution,
    ResearchCycleRequest,
    ResolvedResearchCycleRequest,
    SleepFn,
)
from agentic_trader.researchd.orchestrator import (
    ResearchSidecar,
    utc_now_iso,
)
from agentic_trader.researchd.persistence import persist_research_result
from agentic_trader.runtime_feed import (
    read_latest_research_snapshot,
    read_research_digest_replay,
    write_research_digest_replay,
)
from agentic_trader.schemas import ResearchSnapshotRecord

__all__ = [
    "ResearchCycleExecution",
    "ResearchCycleRequest",
    "research_cycle_execution_payload",
    "run_research_cycle",
]


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
    """Run a bounded evidence-only research loop and return an execution summary."""

    resolved = resolve_research_cycle_request(
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
    execution_policy = execution_policy_payload()
    digest_replay = research_digest_replay(
        settings=settings,
        resolved=resolved,
        executions=executions,
        latest_digest=latest_digest,
        execution_policy=execution_policy,
        operator_control=operator_control,
    )
    if resolved.persist:
        write_research_digest_replay(settings, digest_replay)
    return research_cycle_run_payload(
        plan=plan,
        resolved=resolved,
        executions=executions,
        execution_policy=execution_policy,
        operator_control=operator_control,
        digest_replay=digest_replay,
        latest_digest=latest_digest,
    )


def _execute_research_cycles(
    *,
    settings: Settings,
    resolved: ResolvedResearchCycleRequest,
    prior_snapshot: ResearchSnapshotRecord | None,
    prior_digest_available: bool,
    sleep_fn: SleepFn,
) -> list[ResearchCycleExecution]:
    """
    Execute the bounded series of research cycles and return their per-cycle execution summaries.

    Runs the number of cycles determined by `resolved.safe_cycles`, updating prior snapshot identity, source-health summary, and digest-availability between iterations. When enabled, pauses between cycles using `sleep_fn`.

    Parameters:
        settings (Settings): Runtime settings used for each cycle.
        resolved (_ResolvedResearchCycleRequest): Normalized request specifying safe counts, cadence, persistence, and sleep behavior.
        prior_snapshot (ResearchSnapshotRecord | None): Snapshot record that seeds the initial source-health summary and prior snapshot id.
        prior_digest_available (bool): Whether a prior digest replay is available for the first cycle.
        sleep_fn (SleepFn): Callable invoked with a float number of seconds to pause between cycles when sleeping is enabled.

    Returns:
        list[ResearchCycleExecution]: Ordered list of execution records, one per executed cycle.
    """
    executions: list[ResearchCycleExecution] = []
    previous_source_health = source_health_from_snapshot(prior_snapshot)
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
    resolved: ResolvedResearchCycleRequest,
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
    next_run_at = next_cycle_run_at(
        completed_at=completed_at,
        cycle_index=cycle_index,
        safe_cycles=resolved.safe_cycles,
        safe_cadence=resolved.safe_cadence,
        sleep_between_cycles=resolved.sleep_between_cycles,
    )
    execution = build_research_cycle_execution(
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
