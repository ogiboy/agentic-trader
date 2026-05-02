import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from agentic_trader.config import Settings
from agentic_trader.engine.broker import BrokerAdapter, get_broker_adapter
from agentic_trader.engine.position_manager import evaluate_position_exit
from agentic_trader.llm.client import LocalLLM
from agentic_trader.runtime_feed import clear_stop_request, request_stop, stop_requested
from agentic_trader.runtime_status import build_runtime_status_view, is_process_alive
from agentic_trader.schemas import LLMHealthStatus, RunArtifacts
from agentic_trader.security import open_private_append_binary
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.workflows.run_once import persist_run, run_once


@dataclass
class ServiceCycleResult:
    symbol: str
    artifacts: RunArtifacts
    order_id: str


@dataclass
class _ServiceRunConfig:
    settings: Settings
    symbols: list[str]
    interval: str
    lookback: str
    poll_seconds: int
    continuous: bool
    max_cycles: int | None


@dataclass
class _ServiceSymbolOutcome:
    result: ServiceCycleResult | None = None
    skipped: bool = False
    stop_requested: bool = False


def _stop_requested(db: TradingDatabase) -> bool:
    """
    Check whether a stop of the service has been requested.

    Returns:
        True if a stop has been requested via settings or the persisted service state, False otherwise.
    """
    if stop_requested(db.settings):
        return True
    state = db.get_service_state()
    return bool(state and state.stop_requested)


def _is_nonfatal_symbol_error(exc: Exception) -> bool:
    """
    Determine whether an exception represents a non-fatal symbol-level market-data error.

    Inspect the exception message and classify it as non-fatal when it indicates missing or incomplete market data.

    Parameters:
        exc (Exception): The exception whose message will be inspected.

    Returns:
        bool: `True` if the exception message describes symbol-scoped data absence, invalid market data, or lookback undercoverage; `False` otherwise.
    """
    message = str(exc)
    return (
        message.startswith("No market data returned for ")
        or message.startswith("Missing columns from market data:")
        or "coverage is too thin" in message
        or "Refusing to run agents" in message
    )


def terminate_service_process(pid: int | None) -> bool:
    """Best-effort SIGTERM for a recorded service PID after safety checks."""
    if pid is None or pid <= 1 or not is_process_alive(pid):
        return False
    try:
        os.kill(pid, signal.SIGTERM)  # NOSONAR - guarded service PID, no user input.
    except OSError:
        return False
    return True


def _manage_open_position(
    *,
    db: TradingDatabase,
    broker: BrokerAdapter,
    artifacts: RunArtifacts,
    cycle_count: int,
) -> str | None:
    """
    Close an open position for the given symbol when its position plan indicates an exit and record the closure.

    If a non-zero position and a corresponding position plan exist, increments the plan's holding bars, re-evaluates exit conditions against the latest plan and snapshot, and when an exit is required uses the broker to close the position and records a `position_closed` service event.

    Parameters:
        artifacts (RunArtifacts): Run artifacts containing the snapshot with the symbol to check.
        cycle_count (int): Current service cycle number to attach to the recorded event.

    Returns:
        str | None: The broker order id for the exit if a position was closed, `None` otherwise.
    """
    position = db.get_position(artifacts.snapshot.symbol)
    if position is None or position.quantity == 0:
        return None
    plan = db.get_position_plan(artifacts.snapshot.symbol)
    if plan is None:
        return None

    db.update_position_plan_holding(plan.symbol, plan.holding_bars + 1)
    refreshed_plan = db.get_position_plan(plan.symbol)
    if refreshed_plan is None:
        return None
    exit_decision = evaluate_position_exit(artifacts.snapshot, position, refreshed_plan)
    if not exit_decision.should_exit:
        return None

    exit_order_id = broker.close_position(exit_decision)
    db.insert_service_event(
        level="info",
        event_type="position_closed",
        message=f"{artifacts.snapshot.symbol} exited via {exit_decision.reason} with order {exit_order_id}.",
        cycle_count=cycle_count,
        symbol=artifacts.snapshot.symbol,
    )
    return exit_order_id


def ensure_llm_ready(settings: Settings) -> LLMHealthStatus:
    """
    Ensure the local LLM service is reachable and, if configured, that the required model is available.

    Parameters:
        settings (Settings): Application settings. When `settings.runtime_mode == "operation"`, `settings.strict_llm` must be True.

    Returns:
        LLMHealthStatus: Health report returned by the local LLM.

    Raises:
        RuntimeError: If operation mode is configured without `strict_llm`, if the LLM service is not reachable (message provided by the health check), or if `strict_llm` is True but the required model is unavailable (message provided by the health check).
    """
    if settings.runtime_mode == "operation" and not settings.strict_llm:
        raise RuntimeError("Operation mode requires strict LLM gating.")
    health = LocalLLM(settings).health_check()
    if not health.service_reachable:
        raise RuntimeError(health.message)
    if settings.strict_llm and not health.model_available:
        raise RuntimeError(health.message)
    return health


def _override_or_next(
    override: int | None, current: int | None, *, increment: bool
) -> int:
    """
    Compute the next integer value using an optional override and an increment flag.

    Parameters:
        override (int | None): If provided, this value is returned verbatim.
        current (int | None): Current base value; treated as 0 if None.
        increment (bool): If True and `override` is None, return `current` + 1; otherwise return `current`.

    Returns:
        int: `override` when not None; otherwise `current` (treated as 0) plus 1 if `increment` is True, or `current` (treated as 0) if False.
    """
    if override is not None:
        return override
    base_value = current or 0
    return base_value + 1 if increment else base_value


def _record_cycle_completed_mark(db: TradingDatabase, cycle_count: int) -> None:
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


def _upsert_runtime_state(
    db: TradingDatabase,
    config: _ServiceRunConfig,
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


def _record_service_starting(db: TradingDatabase, config: _ServiceRunConfig) -> None:
    _upsert_runtime_state(
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


def _record_stop_before_cycle(
    db: TradingDatabase, config: _ServiceRunConfig, cycle_count: int
) -> None:
    _upsert_runtime_state(
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


def _record_cycle_started(
    db: TradingDatabase, config: _ServiceRunConfig, cycle_count: int
) -> None:
    _upsert_runtime_state(
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


def _progress_callback(
    db: TradingDatabase,
    config: _ServiceRunConfig,
    *,
    symbol: str,
    cycle_count: int,
):
    def _progress(stage: str, status: str, message: str) -> None:
        _upsert_runtime_state(
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


def _record_symbol_skipped(
    db: TradingDatabase,
    config: _ServiceRunConfig,
    *,
    symbol: str,
    cycle_count: int,
    exc: Exception,
) -> None:
    _upsert_runtime_state(
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


def _record_position_lifecycle(
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


def _record_symbol_completed(
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


def _record_stop_after_symbol(
    db: TradingDatabase,
    config: _ServiceRunConfig,
    *,
    symbol: str,
    cycle_count: int,
) -> None:
    _upsert_runtime_state(
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


def _record_cycle_nonfatal_summary(
    db: TradingDatabase, config: _ServiceRunConfig, cycle_count: int
) -> None:
    _upsert_runtime_state(
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


def _record_service_completed(
    db: TradingDatabase,
    config: _ServiceRunConfig,
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
    _upsert_runtime_state(
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


def _record_service_failed(
    db: TradingDatabase,
    config: _ServiceRunConfig,
    *,
    cycle_count: int,
    exc: Exception,
) -> None:
    _upsert_runtime_state(
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


def _record_service_blocked(
    db: TradingDatabase,
    config: _ServiceRunConfig,
    *,
    exc: Exception,
) -> None:
    _upsert_runtime_state(
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


def _should_stop_after_cycle(config: _ServiceRunConfig, cycle_count: int) -> bool:
    if not config.continuous:
        return True
    return config.max_cycles is not None and cycle_count >= config.max_cycles


def _sleep_until_next_cycle(
    db: TradingDatabase,
    config: _ServiceRunConfig,
    *,
    cycle_count: int,
) -> bool:
    deadline = time.monotonic() + max(0, config.poll_seconds)
    while time.monotonic() < deadline:
        if _stop_requested(db):
            _record_stop_before_cycle(db, config, cycle_count)
            return True
        time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))
    if _stop_requested(db):
        _record_stop_before_cycle(db, config, cycle_count)
        return True
    return False


def _process_service_symbol(
    *,
    db: TradingDatabase,
    broker: BrokerAdapter,
    config: _ServiceRunConfig,
    symbol: str,
    cycle_count: int,
) -> _ServiceSymbolOutcome:
    _upsert_runtime_state(
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
            progress_callback=_progress_callback(
                db,
                config,
                symbol=symbol,
                cycle_count=cycle_count,
            ),
        )
    except Exception as exc:
        if not _is_nonfatal_symbol_error(exc):
            raise
        _record_symbol_skipped(
            db,
            config,
            symbol=symbol,
            cycle_count=cycle_count,
            exc=exc,
        )
        return _ServiceSymbolOutcome(skipped=True)

    exit_order_id = _manage_open_position(
        db=db,
        broker=broker,
        artifacts=artifacts,
        cycle_count=cycle_count,
    )
    if exit_order_id is not None:
        _record_position_lifecycle(db, symbol=symbol, cycle_count=cycle_count)
        return _ServiceSymbolOutcome(
            result=ServiceCycleResult(
                symbol=symbol,
                artifacts=artifacts,
                order_id=exit_order_id,
            )
        )

    order_id = persist_run(settings=config.settings, artifacts=artifacts)
    _record_symbol_completed(
        db,
        symbol=symbol,
        cycle_count=cycle_count,
        order_id=order_id,
    )
    if _stop_requested(db):
        _record_stop_after_symbol(
            db,
            config,
            symbol=symbol,
            cycle_count=cycle_count,
        )
        return _ServiceSymbolOutcome(
            result=ServiceCycleResult(
                symbol=symbol, artifacts=artifacts, order_id=order_id
            ),
            stop_requested=True,
        )

    return _ServiceSymbolOutcome(
        result=ServiceCycleResult(symbol=symbol, artifacts=artifacts, order_id=order_id)
    )


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
    config = _ServiceRunConfig(
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
        _record_service_blocked(db, config, exc=exc)
        clear_stop_request(settings)
        raise

    clear_stop_request(settings)
    broker = get_broker_adapter(db=db, settings=settings)
    _record_service_starting(db, config)

    cycle_results: list[ServiceCycleResult] = []
    cycle_count = 0
    run_had_nonfatal_failure = False
    stopped = False
    try:
        while True:
            if _stop_requested(db):
                _record_stop_before_cycle(db, config, cycle_count)
                stopped = True
                break
            cycle_count += 1
            _record_cycle_started(db, config, cycle_count)
            cycle_had_nonfatal_failure = False
            for symbol in symbols:
                outcome = _process_service_symbol(
                    db=db,
                    broker=broker,
                    config=config,
                    symbol=symbol,
                    cycle_count=cycle_count,
                )
                if outcome.skipped:
                    cycle_had_nonfatal_failure = True
                    run_had_nonfatal_failure = True
                    if _stop_requested(db):
                        _record_stop_after_symbol(
                            db,
                            config,
                            symbol=symbol,
                            cycle_count=cycle_count,
                        )
                        return cycle_results
                    continue
                if outcome.result is not None:
                    cycle_results.append(outcome.result)
                if outcome.stop_requested:
                    return cycle_results

            _record_cycle_completed_mark(db, cycle_count)
            if _should_stop_after_cycle(config, cycle_count):
                break
            if cycle_had_nonfatal_failure:
                _record_cycle_nonfatal_summary(db, config, cycle_count)
            if _sleep_until_next_cycle(db, config, cycle_count=cycle_count):
                stopped = True
                break

        if not stopped:
            _record_service_completed(
                db,
                config,
                cycle_count=cycle_count,
                had_nonfatal_failure=run_had_nonfatal_failure,
            )
    except Exception as exc:
        _record_service_failed(db, config, cycle_count=cycle_count, exc=exc)
        raise
    finally:
        clear_stop_request(settings)

    return cycle_results


def start_background_service(
    *,
    settings: Settings,
    symbols: list[str],
    interval: str,
    lookback: str,
    poll_seconds: int,
    continuous: bool,
    max_cycles: int | None,
    workdir: Path | None = None,
    launch_count_override: int | None = None,
    restart_count_override: int | None = None,
) -> int:
    """
    Spawn the trading service as a background process and record its runtime metadata.

    If an earlier recorded service state indicates a stale PID (process not alive), that state is marked recovered before launching. The function upserts a new `starting` service state, inserts a spawn event, and returns the spawned process PID.

    Parameters:
        settings (Settings): Runtime and environment configuration.
        symbols (list[str]): Symbols the background service will process.
        interval (str): Trading interval string used by the service.
        lookback (str): Lookback period string used by the service.
        poll_seconds (int): Seconds the background service will sleep between cycles when continuous.
        continuous (bool): Whether the background service should run continuously.
        max_cycles (int | None): Maximum number of cycles for the background service, or `None` for unlimited.
        workdir (Path | None): Working directory for the spawned process; defaults to current working directory when `None`.
        launch_count_override (int | None): Optional explicit launch count to record; when `None`, an incremented prior launch count is used.
        restart_count_override (int | None): Optional explicit restart count to record; when `None`, the prior restart count is used.

    Returns:
        int: PID of the spawned background process.

    Raises:
        RuntimeError: If a recorded service state indicates the service is already active (an alive PID).
    """
    clear_stop_request(settings)
    db = TradingDatabase(settings)
    state = db.get_service_state()
    launch_count = _override_or_next(
        launch_count_override,
        state.launch_count if state is not None else None,
        increment=True,
    )
    restart_count = _override_or_next(
        restart_count_override,
        state.restart_count if state is not None else None,
        increment=False,
    )
    if (
        state is not None
        and state.state in {"starting", "running", "stopping"}
        and state.pid is not None
    ):
        view = build_runtime_status_view(state)
        if view.runtime_state == "active":
            raise RuntimeError(f"Service is already active with PID {state.pid}.")
        if view.live_process:
            raise RuntimeError(
                "Service heartbeat is stale but PID "
                f"{state.pid} is still alive. Use restart-service or "
                "stop-service --force before launching another background service."
            )
        db.upsert_service_state(
            state="stopped",
            continuous=state.continuous,
            poll_seconds=state.poll_seconds,
            cycle_count=state.cycle_count,
            symbols=state.symbols,
            interval=state.interval,
            lookback=state.lookback,
            max_cycles=state.max_cycles,
            current_symbol=None,
            message=f"Recovered stale runtime state from dead PID {state.pid}.",
            last_error=state.last_error,
            pid=None,
            clear_pid=True,
            stop_requested=False,
        )
        db.insert_service_event(
            level="warning",
            event_type="stale_service_recovered",
            message=f"Recovered stale runtime state from dead PID {state.pid}.",
            cycle_count=state.cycle_count if state.cycle_count > 0 else None,
            symbol=state.current_symbol,
        )

    stdout_path = settings.runtime_dir / "service.out.log"
    stderr_path = settings.runtime_dir / "service.err.log"
    command = [
        sys.executable,
        "-m",
        "agentic_trader.cli",
        "service-run",
        "--symbols",
        ",".join(symbols),
        "--interval",
        interval,
        "--lookback",
        lookback,
        "--poll-seconds",
        str(poll_seconds),
    ]
    command.append("--continuous" if continuous else "--no-continuous")
    if max_cycles is not None:
        command.extend(["--max-cycles", str(max_cycles)])

    with (
        open_private_append_binary(stdout_path) as stdout_handle,
        open_private_append_binary(stderr_path) as stderr_handle,
    ):
        process = subprocess.Popen(
            command,
            cwd=str(workdir or Path.cwd()),
            stdout=stdout_handle,
            stderr=stderr_handle,
            start_new_session=True,
        )

    db.upsert_service_state(
        state="starting",
        continuous=continuous,
        poll_seconds=poll_seconds,
        cycle_count=0,
        symbols=symbols,
        interval=interval,
        lookback=lookback,
        max_cycles=max_cycles,
        current_symbol=None,
        message="Background service spawned.",
        pid=process.pid,
        stop_requested=False,
        background_mode=True,
        launch_count=launch_count,
        restart_count=restart_count,
        stdout_log_path=str(stdout_path),
        stderr_log_path=str(stderr_path),
    )
    db.insert_service_event(
        level="info",
        event_type="service_spawned",
        message=f"Background service spawned with PID {process.pid}.",
    )
    db.close()
    return process.pid


def restart_background_service(
    *,
    settings: Settings,
    grace_seconds: float = 3.0,
    workdir: Path | None = None,
) -> int:
    db = TradingDatabase(settings)
    state = db.get_service_state()
    if (
        state is None
        or not state.symbols
        or state.interval is None
        or state.lookback is None
    ):
        db.close()
        raise RuntimeError(
            "No restartable background service configuration is recorded yet."
        )
    if not state.continuous:
        db.close()
        raise RuntimeError(
            "Restart is only supported for continuous service configurations."
        )

    if state.pid is not None and is_process_alive(state.pid):
        request_stop(settings)
        db.request_stop_service()
        deadline = time.time() + grace_seconds
        while time.time() < deadline and is_process_alive(state.pid):
            time.sleep(0.2)
        if is_process_alive(state.pid):
            terminate_service_process(state.pid)
    restart_count = state.restart_count + 1
    launch_count = state.launch_count + 1
    db.close()
    return start_background_service(
        settings=settings,
        symbols=state.symbols,
        interval=state.interval,
        lookback=state.lookback,
        poll_seconds=state.poll_seconds or settings.default_poll_seconds,
        continuous=True,
        max_cycles=state.max_cycles,
        workdir=workdir,
        launch_count_override=launch_count,
        restart_count_override=restart_count,
    )
