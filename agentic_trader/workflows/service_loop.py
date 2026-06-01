"""Foreground service loop orchestration."""

from __future__ import annotations

from agentic_trader.config import Settings
from agentic_trader.engine.broker import BrokerAdapter, get_broker_adapter
from agentic_trader.runtime_feed import clear_stop_request
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.workflows.run_once import persist_run, run_once
from agentic_trader.workflows.service_records import (
    record_cycle_completed_mark,
    record_cycle_nonfatal_summary,
    record_cycle_started,
    record_position_lifecycle,
    record_service_blocked,
    record_service_completed,
    record_service_failed,
    record_service_starting,
    record_stop_after_symbol,
    record_stop_before_cycle,
    record_symbol_completed,
    record_symbol_skipped,
    service_progress_callback,
    should_stop_after_cycle,
    sleep_until_next_cycle,
    upsert_runtime_state,
)
from agentic_trader.workflows.service_runtime import (
    ensure_llm_ready,
    is_nonfatal_symbol_error,
    manage_open_position,
    service_stop_requested,
)
from agentic_trader.workflows.service_types import (
    ServiceCycleResult,
    ServiceLoopState,
    ServiceRunConfig,
    ServiceSymbolOutcome,
)


def process_service_symbol(
    *,
    db: TradingDatabase,
    broker: BrokerAdapter,
    config: ServiceRunConfig,
    symbol: str,
    cycle_count: int,
) -> ServiceSymbolOutcome:
    upsert_runtime_state(
        db,
        config,
        state="running",
        cycle_count=cycle_count,
        current_symbol=symbol,
        message=f"Processing {symbol} in cycle {cycle_count}.",
    )
    try:
        artifacts = run_once(
            settings=config.settings,
            symbol=symbol,
            interval=config.interval,
            lookback=config.lookback,
            allow_fallback=False,
            progress_callback=service_progress_callback(
                db,
                config,
                symbol=symbol,
                cycle_count=cycle_count,
            ),
        )
    except Exception as exc:
        if not is_nonfatal_symbol_error(exc):
            raise
        record_symbol_skipped(
            db,
            config,
            symbol=symbol,
            cycle_count=cycle_count,
            exc=exc,
        )
        return ServiceSymbolOutcome(skipped=True)

    exit_order_id = manage_open_position(
        db=db,
        broker=broker,
        artifacts=artifacts,
        cycle_count=cycle_count,
    )
    if exit_order_id is not None:
        record_position_lifecycle(db, symbol=symbol, cycle_count=cycle_count)
        return ServiceSymbolOutcome(
            result=ServiceCycleResult(
                symbol=symbol,
                artifacts=artifacts,
                order_id=exit_order_id,
            )
        )

    order_id = persist_run(settings=config.settings, artifacts=artifacts)
    record_symbol_completed(
        db,
        symbol=symbol,
        cycle_count=cycle_count,
        order_id=order_id,
    )
    if service_stop_requested(db):
        record_stop_after_symbol(
            db,
            config,
            symbol=symbol,
            cycle_count=cycle_count,
        )
        return ServiceSymbolOutcome(
            result=ServiceCycleResult(
                symbol=symbol, artifacts=artifacts, order_id=order_id
            ),
            stop_requested=True,
        )

    return ServiceSymbolOutcome(
        result=ServiceCycleResult(symbol=symbol, artifacts=artifacts, order_id=order_id)
    )


def handle_symbol_outcome(
    *,
    db: TradingDatabase,
    config: ServiceRunConfig,
    state: ServiceLoopState,
    symbol: str,
    outcome: ServiceSymbolOutcome,
) -> bool:
    if outcome.skipped:
        state.run_had_nonfatal_failure = True
        if service_stop_requested(db):
            record_stop_after_symbol(
                db,
                config,
                symbol=symbol,
                cycle_count=state.cycle_count,
            )
            state.stopped = True
            return True
        return False

    if outcome.result is not None:
        state.cycle_results.append(outcome.result)
    if outcome.stop_requested:
        state.stopped = True
    return outcome.stop_requested


def process_service_cycle(
    *,
    db: TradingDatabase,
    broker: BrokerAdapter,
    config: ServiceRunConfig,
    state: ServiceLoopState,
) -> bool:
    state.cycle_count += 1
    record_cycle_started(db, config, state.cycle_count)
    cycle_had_nonfatal_failure = False
    for symbol in config.symbols:
        outcome = process_service_symbol(
            db=db,
            broker=broker,
            config=config,
            symbol=symbol,
            cycle_count=state.cycle_count,
        )
        cycle_had_nonfatal_failure = cycle_had_nonfatal_failure or outcome.skipped
        if handle_symbol_outcome(
            db=db,
            config=config,
            state=state,
            symbol=symbol,
            outcome=outcome,
        ):
            return True

    record_cycle_completed_mark(db, state.cycle_count)
    if should_stop_after_cycle(config, state.cycle_count):
        return True
    if cycle_had_nonfatal_failure:
        record_cycle_nonfatal_summary(db, config, state.cycle_count)
    if sleep_until_next_cycle(db, config, cycle_count=state.cycle_count):
        state.stopped = True
        return True
    return False


def run_service_loop(
    *,
    db: TradingDatabase,
    broker: BrokerAdapter,
    config: ServiceRunConfig,
) -> ServiceLoopState:
    state = ServiceLoopState(cycle_results=[])
    while True:
        if service_stop_requested(db):
            record_stop_before_cycle(db, config, state.cycle_count)
            state.stopped = True
            break
        if process_service_cycle(db=db, broker=broker, config=config, state=state):
            break
    return state


def run_service(
    *,
    settings: Settings,
    symbols: list[str],
    interval: str,
    lookback: str,
    poll_seconds: int,
    continuous: bool,
    max_cycles: int | None,
) -> list[ServiceCycleResult]:
    """Run the orchestrator loop across configured symbols and cycles."""
    config = ServiceRunConfig(
        settings=settings,
        symbols=symbols,
        interval=interval,
        lookback=lookback,
        poll_seconds=poll_seconds,
        continuous=continuous,
        max_cycles=max_cycles,
    )
    db = TradingDatabase(settings)
    try:
        ensure_llm_ready(settings)
    except Exception as exc:
        record_service_blocked(db, config, exc=exc)
        clear_stop_request(settings)
        raise

    clear_stop_request(settings)
    broker = get_broker_adapter(db=db, settings=settings)
    record_service_starting(db, config)

    loop_state = ServiceLoopState(cycle_results=[])
    try:
        loop_state = run_service_loop(db=db, broker=broker, config=config)
        if not loop_state.stopped:
            record_service_completed(
                db,
                config,
                cycle_count=loop_state.cycle_count,
                had_nonfatal_failure=loop_state.run_had_nonfatal_failure,
            )
    except Exception as exc:
        record_service_failed(
            db,
            config,
            cycle_count=loop_state.cycle_count,
            exc=exc,
        )
        raise
    finally:
        clear_stop_request(settings)

    return loop_state.cycle_results
