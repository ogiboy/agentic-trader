"""Service state, event, and stop-aware wait helpers."""

from __future__ import annotations

import os
import time

from agentic_trader.config import Settings
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.workflows.service_runtime import service_stop_requested
from agentic_trader.workflows.service_types import ServiceRunConfig


def record_cycle_completed_mark(db: TradingDatabase, cycle_count: int) -> None:
    """
    Record an account mark indicating completion of a service cycle.

    Writes a mark with source "cycle_completed", a human-readable note "Cycle {cycle_count} completed.", and the provided cycle_count value.

    Parameters:
        cycle_count (int): The completed cycle number to record.
    """
    db.record_account_mark(
        source="cycle_completed",
        note=f"Cycle {cycle_count} completed.",
        cycle_count=cycle_count,
    )


def upsert_runtime_state(
    db: TradingDatabase,
    config: ServiceRunConfig,
    *,
    state: str,
    cycle_count: int,
    current_symbol: str | None,
    message: str,
    last_error: str | None = None,
    stop_requested_flag: bool | None = None,
) -> None:
    db.upsert_service_state(
        state=state,
        continuous=config.continuous,
        poll_seconds=config.poll_seconds,
        cycle_count=cycle_count,
        symbols=config.symbols,
        interval=config.interval,
        lookback=config.lookback,
        max_cycles=config.max_cycles,
        current_symbol=current_symbol,
        message=message,
        last_error=last_error,
        pid=os.getpid(),
        stop_requested=stop_requested_flag,
    )


def record_service_starting(db: TradingDatabase, config: ServiceRunConfig) -> None:
    upsert_runtime_state(
        db,
        config,
        state="starting",
        cycle_count=0,
        current_symbol=None,
        message="Runtime gate passed. Orchestrator is starting.",
        stop_requested_flag=False,
    )
    db.insert_service_event(
        level="info",
        event_type="service_started",
        message="Orchestrator started after passing LLM readiness checks.",
    )


def record_stop_before_cycle(
    db: TradingDatabase, config: ServiceRunConfig, cycle_count: int
) -> None:
    upsert_runtime_state(
        db,
        config,
        state="stopped",
        cycle_count=cycle_count,
        current_symbol=None,
        message="Service stopped before a new cycle started.",
        stop_requested_flag=True,
    )
    db.insert_service_event(
        level="warning",
        event_type="service_stopped",
        message="Orchestrator stopped before a new cycle started.",
        cycle_count=cycle_count if cycle_count > 0 else None,
    )


def record_cycle_started(
    db: TradingDatabase, config: ServiceRunConfig, cycle_count: int
) -> None:
    upsert_runtime_state(
        db,
        config,
        state="running",
        cycle_count=cycle_count,
        current_symbol=None,
        message=f"Cycle {cycle_count} started.",
    )
    db.insert_service_event(
        level="info",
        event_type="cycle_started",
        message=f"Cycle {cycle_count} started for {len(config.symbols)} symbol(s).",
        cycle_count=cycle_count,
    )


def service_progress_callback(
    db: TradingDatabase,
    config: ServiceRunConfig,
    *,
    symbol: str,
    cycle_count: int,
):
    def _progress(stage: str, status: str, message: str) -> None:
        upsert_runtime_state(
            db,
            config,
            state="running",
            cycle_count=cycle_count,
            current_symbol=symbol,
            message=message,
        )
        db.insert_service_event(
            level="info",
            event_type=f"agent_{stage}_{status}",
            message=message,
            cycle_count=cycle_count,
            symbol=symbol,
        )

    return _progress


def record_symbol_skipped(
    db: TradingDatabase,
    config: ServiceRunConfig,
    *,
    symbol: str,
    cycle_count: int,
    exc: Exception,
) -> None:
    upsert_runtime_state(
        db,
        config,
        state="running",
        cycle_count=cycle_count,
        current_symbol=None,
        message=f"Skipped {symbol}: {exc}",
        last_error=str(exc),
    )
    db.insert_service_event(
        level="warning",
        event_type="symbol_skipped",
        message=str(exc),
        cycle_count=cycle_count,
        symbol=symbol,
    )


def record_position_lifecycle(
    db: TradingDatabase, *, symbol: str, cycle_count: int
) -> None:
    db.insert_service_event(
        level="info",
        event_type="position_lifecycle",
        message=f"Open position for {symbol} was evaluated and closed before new entries were considered.",
        cycle_count=cycle_count,
        symbol=symbol,
    )
    db.record_account_mark(
        source="position_lifecycle",
        note=f"{symbol} position lifecycle event closed the active trade.",
        cycle_count=cycle_count,
        symbol=symbol,
    )


def record_symbol_completed(
    db: TradingDatabase, *, symbol: str, cycle_count: int, order_id: str
) -> None:
    db.insert_service_event(
        level="info",
        event_type="symbol_completed",
        message=f"Cycle {cycle_count} completed for {symbol} with order {order_id}.",
        cycle_count=cycle_count,
        symbol=symbol,
    )
    db.record_account_mark(
        source="symbol_completed",
        note=f"Cycle {cycle_count} completed for {symbol}.",
        cycle_count=cycle_count,
        symbol=symbol,
    )


def record_stop_after_symbol(
    db: TradingDatabase,
    config: ServiceRunConfig,
    *,
    symbol: str,
    cycle_count: int,
) -> None:
    upsert_runtime_state(
        db,
        config,
        state="stopped",
        cycle_count=cycle_count,
        current_symbol=None,
        message=f"Stop requested after processing {symbol}.",
        stop_requested_flag=True,
    )
    db.insert_service_event(
        level="warning",
        event_type="service_stopped",
        message=f"Orchestrator stopped after processing {symbol}.",
        cycle_count=cycle_count,
        symbol=symbol,
    )


def record_cycle_nonfatal_summary(
    db: TradingDatabase, config: ServiceRunConfig, cycle_count: int
) -> None:
    upsert_runtime_state(
        db,
        config,
        state="running",
        cycle_count=cycle_count,
        current_symbol=None,
        message=f"Cycle {cycle_count} completed with one or more skipped symbols.",
        last_error="One or more symbols were skipped because market data was unavailable.",
    )


def _completion_message(cycle_count: int, had_nonfatal_failure: bool) -> str:
    if had_nonfatal_failure:
        return f"Orchestrator completed after {cycle_count} cycle(s) with one or more skipped symbols."
    return f"Orchestrator completed after {cycle_count} cycle(s)."


def record_service_completed(
    db: TradingDatabase,
    config: ServiceRunConfig,
    *,
    cycle_count: int,
    had_nonfatal_failure: bool,
) -> None:
    message = _completion_message(cycle_count, had_nonfatal_failure)
    last_error = (
        "One or more symbols were skipped because market data was unavailable."
        if had_nonfatal_failure
        else None
    )
    upsert_runtime_state(
        db,
        config,
        state="completed",
        cycle_count=cycle_count,
        current_symbol=None,
        message=message,
        last_error=last_error,
        stop_requested_flag=False,
    )
    db.insert_service_event(
        level="info",
        event_type="service_completed",
        message=message,
        cycle_count=cycle_count,
    )


def record_service_failed(
    db: TradingDatabase,
    config: ServiceRunConfig,
    *,
    cycle_count: int,
    exc: Exception,
) -> None:
    upsert_runtime_state(
        db,
        config,
        state="failed",
        cycle_count=cycle_count,
        current_symbol=None,
        message="Orchestrator failed.",
        last_error=str(exc),
    )
    db.insert_service_event(
        level="error",
        event_type="service_failed",
        message=str(exc),
        cycle_count=cycle_count if cycle_count > 0 else None,
    )


def record_service_blocked(
    db: TradingDatabase,
    config: ServiceRunConfig,
    *,
    exc: Exception,
) -> None:
    upsert_runtime_state(
        db,
        config,
        state="blocked",
        cycle_count=0,
        current_symbol=None,
        message="Runtime gate blocked before orchestrator start.",
        last_error=str(exc),
        stop_requested_flag=False,
    )
    db.insert_service_event(
        level="error",
        event_type="service_blocked",
        message=str(exc),
    )


def should_stop_after_cycle(config: ServiceRunConfig, cycle_count: int) -> bool:
    if not config.continuous:
        return True
    return config.max_cycles is not None and cycle_count >= config.max_cycles


def sleep_until_next_cycle(
    db: TradingDatabase,
    config: ServiceRunConfig,
    *,
    cycle_count: int,
) -> bool:
    deadline = time.monotonic() + max(0, config.poll_seconds)
    while time.monotonic() < deadline:
        if service_stop_requested(db):
            record_stop_before_cycle(db, config, cycle_count)
            return True
        time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))
    if service_stop_requested(db):
        record_stop_before_cycle(db, config, cycle_count)
        return True
    return False


def wait_for_next_service_cycle(
    db: TradingDatabase,
    *,
    settings: Settings,
    symbols: list[str],
    interval: str,
    lookback: str,
    poll_seconds: int,
    continuous: bool,
    max_cycles: int | None,
    cycle_count: int,
) -> bool:
    """Wait for the next service cycle using the same stop-aware path as the runtime loop."""
    config = ServiceRunConfig(
        settings=settings,
        symbols=symbols,
        interval=interval,
        lookback=lookback,
        poll_seconds=poll_seconds,
        continuous=continuous,
        max_cycles=max_cycles,
    )
    return sleep_until_next_cycle(db, config, cycle_count=cycle_count)
