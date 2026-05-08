"""Safe executor for the first continuous research-loop slice."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import sleep
from typing import Callable

from agentic_trader.config import Settings
from agentic_trader.researchd.cycle_plan import research_cycle_plan_payload
from agentic_trader.researchd.orchestrator import ResearchSidecar, utc_now_iso
from agentic_trader.researchd.persistence import persist_research_result

SleepFn = Callable[[float], None]


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
            "notes": list(self.notes),
        }


def run_research_cycle(
    settings: Settings,
    *,
    symbols: list[str],
    cycles: int = 1,
    cadence_seconds: int = 60,
    max_proposals_per_cycle: int = 1,
    persist: bool = True,
    sleep_between_cycles: bool = True,
    sleep_fn: SleepFn = sleep,
) -> dict[str, object]:
    """Run a bounded, evidence-only research cycle without broker authority."""

    clean_symbols = [symbol.strip().upper() for symbol in symbols if symbol.strip()]
    if not clean_symbols:
        raise ValueError("symbols must contain at least one non-empty symbol")
    safe_cycles = max(1, min(cycles, 24))
    safe_cadence = max(1, cadence_seconds)
    settings.research_symbols = ",".join(clean_symbols)
    plan = research_cycle_plan_payload(
        symbols=clean_symbols,
        cadence_seconds=safe_cadence,
        max_proposals_per_cycle=max_proposals_per_cycle,
    )
    executions: list[ResearchCycleExecution] = []
    for index in range(safe_cycles):
        started_at = utc_now_iso()
        result = ResearchSidecar(settings).collect_once()
        record = persist_research_result(settings, result) if persist else None
        notes = [
            "broker_access=false",
            "proposal_approval=false",
            "raw_web_text_in_core_prompt=false",
        ]
        if not settings.research_sidecar_enabled or settings.research_mode == "off":
            notes.append("research_sidecar_disabled")
        executions.append(
            ResearchCycleExecution(
                cycle_index=index + 1,
                started_at=started_at,
                completed_at=utc_now_iso(),
                state_status=result.state.status,
                backend=result.state.backend,
                watched_symbols=list(result.state.watched_symbols),
                raw_evidence_count=len(result.raw_evidence),
                macro_event_count=len(result.macro_events),
                social_signal_count=len(result.social_signals),
                persisted_snapshot_id=record.snapshot_id if record is not None else None,
                notes=notes,
            )
        )
        if sleep_between_cycles and index < safe_cycles - 1:
            sleep_fn(float(safe_cadence))

    return {
        "cycle": "research-cycle-run",
        "plan": plan,
        "requested_cycles": cycles,
        "executed_cycles": len(executions),
        "cadence_seconds": safe_cadence,
        "persisted": persist,
        "sleep_between_cycles": sleep_between_cycles,
        "execution_policy": {
            "broker_access": False,
            "proposal_approval": False,
            "proposal_creation": False,
            "raw_web_text_in_core_prompt": False,
            "manual_review_required": True,
        },
        "executions": [execution.to_payload() for execution in executions],
    }
