"""Shared service workflow data contracts."""

from __future__ import annotations

from dataclasses import dataclass

from agentic_trader.config import Settings
from agentic_trader.schemas import RunArtifacts


@dataclass
class ServiceCycleResult:
    symbol: str
    artifacts: RunArtifacts
    order_id: str


@dataclass
class ServiceRunConfig:
    settings: Settings
    symbols: list[str]
    interval: str
    lookback: str
    poll_seconds: int
    continuous: bool
    max_cycles: int | None


@dataclass
class ServiceSymbolOutcome:
    result: ServiceCycleResult | None = None
    skipped: bool = False
    stop_requested: bool = False


@dataclass
class ServiceLoopState:
    cycle_results: list[ServiceCycleResult]
    cycle_count: int = 0
    run_had_nonfatal_failure: bool = False
    stopped: bool = False
