from collections.abc import Callable
from dataclasses import dataclass, field

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
class ResolvedResearchCycleRequest:
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
