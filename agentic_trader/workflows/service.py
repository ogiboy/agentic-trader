import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from agentic_trader.config import Settings
from agentic_trader.engine.paper_broker import PaperBroker
from agentic_trader.engine.position_manager import evaluate_position_exit
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import LLMHealthStatus, RunArtifacts
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.workflows.run_once import persist_run, run_once


@dataclass
class ServiceCycleResult:
    symbol: str
    artifacts: RunArtifacts
    order_id: str


def _stop_requested(db: TradingDatabase) -> bool:
    state = db.get_service_state()
    return bool(state and state.stop_requested)


def _manage_open_position(
    *,
    db: TradingDatabase,
    broker: PaperBroker,
    artifacts: RunArtifacts,
    cycle_count: int,
) -> str | None:
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
    health = LocalLLM(settings).health_check()
    if not health.service_reachable:
        raise RuntimeError(health.message)
    if settings.strict_llm and not health.model_available:
        raise RuntimeError(health.message)
    return health


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
    ensure_llm_ready(settings)
    db = TradingDatabase(settings)
    broker = PaperBroker(db, settings)
    db.upsert_service_state(
        state="starting",
        continuous=continuous,
        poll_seconds=poll_seconds,
        cycle_count=0,
        current_symbol=None,
        message="Runtime gate passed. Orchestrator is starting.",
        pid=os.getpid(),
        stop_requested=False,
    )
    db.insert_service_event(
        level="info",
        event_type="service_started",
        message="Orchestrator started after passing LLM readiness checks.",
    )

    cycle_results: list[ServiceCycleResult] = []
    cycle_count = 0
    try:
        while True:
            if _stop_requested(db):
                db.upsert_service_state(
                    state="stopped",
                    continuous=continuous,
                    poll_seconds=poll_seconds,
                    cycle_count=cycle_count,
                    current_symbol=None,
                    message="Service stopped before a new cycle started.",
                    pid=os.getpid(),
                    stop_requested=True,
                )
                db.insert_service_event(
                    level="warning",
                    event_type="service_stopped",
                    message="Orchestrator stopped before a new cycle started.",
                    cycle_count=cycle_count if cycle_count > 0 else None,
                )
                break
            cycle_count += 1
            db.upsert_service_state(
                state="running",
                continuous=continuous,
                poll_seconds=poll_seconds,
                cycle_count=cycle_count,
                current_symbol=None,
                message=f"Cycle {cycle_count} started.",
                pid=os.getpid(),
            )
            db.insert_service_event(
                level="info",
                event_type="cycle_started",
                message=f"Cycle {cycle_count} started for {len(symbols)} symbol(s).",
                cycle_count=cycle_count,
            )
            for symbol in symbols:
                db.upsert_service_state(
                    state="running",
                    continuous=continuous,
                    poll_seconds=poll_seconds,
                    cycle_count=cycle_count,
                    current_symbol=symbol,
                    message=f"Processing {symbol} in cycle {cycle_count}.",
                    pid=os.getpid(),
                )
                artifacts = run_once(
                    settings=settings,
                    symbol=symbol,
                    interval=interval,
                    lookback=lookback,
                    allow_fallback=False,
                )
                exit_order_id = _manage_open_position(
                    db=db,
                    broker=broker,
                    artifacts=artifacts,
                    cycle_count=cycle_count,
                )
                if exit_order_id is not None:
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
                    cycle_results.append(
                        ServiceCycleResult(
                            symbol=symbol,
                            artifacts=artifacts,
                            order_id=exit_order_id,
                        )
                    )
                    continue
                order_id = persist_run(settings=settings, artifacts=artifacts)
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
                cycle_results.append(
                    ServiceCycleResult(
                        symbol=symbol,
                        artifacts=artifacts,
                        order_id=order_id,
                    )
                )
                if _stop_requested(db):
                    db.upsert_service_state(
                        state="stopped",
                        continuous=continuous,
                        poll_seconds=poll_seconds,
                        cycle_count=cycle_count,
                        current_symbol=None,
                        message=f"Stop requested after processing {symbol}.",
                        pid=os.getpid(),
                        stop_requested=True,
                    )
                    db.insert_service_event(
                        level="warning",
                        event_type="service_stopped",
                        message=f"Orchestrator stopped after processing {symbol}.",
                        cycle_count=cycle_count,
                        symbol=symbol,
                    )
                    return cycle_results

            if not continuous:
                db.record_account_mark(
                    source="cycle_completed",
                    note=f"Cycle {cycle_count} completed.",
                    cycle_count=cycle_count,
                )
                break
            if max_cycles is not None and cycle_count >= max_cycles:
                db.record_account_mark(
                    source="cycle_completed",
                    note=f"Cycle {cycle_count} completed.",
                    cycle_count=cycle_count,
                )
                break
            db.record_account_mark(
                source="cycle_completed",
                note=f"Cycle {cycle_count} completed.",
                cycle_count=cycle_count,
            )
            time.sleep(poll_seconds)

        db.upsert_service_state(
            state="completed",
            continuous=continuous,
            poll_seconds=poll_seconds,
            cycle_count=cycle_count,
            current_symbol=None,
            message=f"Orchestrator completed after {cycle_count} cycle(s).",
            pid=os.getpid(),
            stop_requested=False,
        )
        db.insert_service_event(
            level="info",
            event_type="service_completed",
            message=f"Orchestrator completed after {cycle_count} cycle(s).",
            cycle_count=cycle_count,
        )
    except Exception as exc:
        db.upsert_service_state(
            state="failed",
            continuous=continuous,
            poll_seconds=poll_seconds,
            cycle_count=cycle_count,
            current_symbol=None,
            message="Orchestrator failed.",
            last_error=str(exc),
            pid=os.getpid(),
        )
        db.insert_service_event(
            level="error",
            event_type="service_failed",
            message=str(exc),
            cycle_count=cycle_count if cycle_count > 0 else None,
        )
        raise

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
) -> int:
    db = TradingDatabase(settings)
    state = db.get_service_state()
    if state is not None and state.state in {"starting", "running", "stopping"} and state.pid is not None:
        raise RuntimeError(f"Service is already active with PID {state.pid}.")

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
        "--continuous",
    ]
    command.append("--continuous" if continuous else "--no-continuous")
    if max_cycles is not None:
        command.extend(["--max-cycles", str(max_cycles)])

    with open(stdout_path, "ab") as stdout_handle, open(stderr_path, "ab") as stderr_handle:
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
        current_symbol=None,
        message="Background service spawned.",
        pid=process.pid,
        stop_requested=False,
    )
    db.insert_service_event(
        level="info",
        event_type="service_spawned",
        message=f"Background service spawned with PID {process.pid}.",
    )
    return process.pid
