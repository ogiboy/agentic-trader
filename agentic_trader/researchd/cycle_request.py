"""Request normalization and timing helpers for research cycles."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from agentic_trader.researchd.cycle_runner_types import (
    ResearchCycleRequest,
    ResolvedResearchCycleRequest,
)


def resolve_research_cycle_request(
    *,
    request: ResearchCycleRequest | None,
    symbols: list[str] | None,
    cycles: int,
    cadence_seconds: int,
    max_proposals_per_cycle: int,
    persist: bool,
    sleep_between_cycles: bool,
) -> ResolvedResearchCycleRequest:
    """Resolve CLI/API inputs into a bounded internal cycle request."""

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
    clean_symbols = clean_research_symbols(resolved_request.symbols)
    if not clean_symbols:
        raise ValueError("symbols must contain at least one non-empty symbol")
    return ResolvedResearchCycleRequest(
        symbols=clean_symbols,
        requested_cycles=resolved_request.cycles,
        safe_cycles=max(1, min(resolved_request.cycles, 24)),
        safe_cadence=max(1, resolved_request.cadence_seconds),
        max_proposals_per_cycle=resolved_request.max_proposals_per_cycle,
        persist=resolved_request.persist,
        sleep_between_cycles=resolved_request.sleep_between_cycles,
    )


def clean_research_symbols(symbols: list[str]) -> list[str]:
    return [symbol.strip().upper() for symbol in symbols if symbol.strip()]


def next_cycle_run_at(
    *,
    completed_at: str,
    cycle_index: int,
    safe_cycles: int,
    safe_cadence: int,
    sleep_between_cycles: bool,
) -> str | None:
    if not sleep_between_cycles or cycle_index == safe_cycles - 1:
        return None
    return iso_after(completed_at, safe_cadence)


def iso_after(iso_value: str, seconds: int) -> str:
    parsed = datetime.fromisoformat(iso_value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return (parsed + timedelta(seconds=seconds)).isoformat()
