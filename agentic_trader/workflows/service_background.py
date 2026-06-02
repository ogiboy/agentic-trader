"""Background service process launch and restart helpers."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from agentic_trader.config import Settings
from agentic_trader.runtime_feed import clear_stop_request, request_stop
from agentic_trader.runtime_status import build_runtime_status_view, is_process_alive
from agentic_trader.schemas import ServiceStateSnapshot
from agentic_trader.security import open_private_append_binary
from agentic_trader.storage.db import TradingDatabase


def terminate_service_process(pid: int | None) -> bool:
    """Best-effort SIGTERM for a recorded service PID after safety checks."""
    if pid is None or pid <= 1 or not is_process_alive(pid):
        return False
    try:
        os.kill(pid, signal.SIGTERM)  # NOSONAR - guarded service PID, no user input.
    except OSError:
        return False
    return True


def override_or_next(
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
    launch_count, restart_count = _service_launch_counts(
        state=state,
        launch_count_override=launch_count_override,
        restart_count_override=restart_count_override,
    )
    _ensure_service_can_start(db, state)

    stdout_path = settings.runtime_dir / "service.out.log"
    stderr_path = settings.runtime_dir / "service.err.log"
    process = _spawn_service_process(
        command=_service_run_command(
            symbols=symbols,
            interval=interval,
            lookback=lookback,
            poll_seconds=poll_seconds,
            continuous=continuous,
            max_cycles=max_cycles,
        ),
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        workdir=workdir,
    )
    _record_spawned_service(
        db=db,
        process=process,
        symbols=symbols,
        interval=interval,
        lookback=lookback,
        poll_seconds=poll_seconds,
        continuous=continuous,
        max_cycles=max_cycles,
        launch_count=launch_count,
        restart_count=restart_count,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )
    db.close()
    return process.pid


def _service_launch_counts(
    *,
    state: ServiceStateSnapshot | None,
    launch_count_override: int | None,
    restart_count_override: int | None,
) -> tuple[int, int]:
    launch_count = override_or_next(
        launch_count_override,
        state.launch_count if state is not None else None,
        increment=True,
    )
    restart_count = override_or_next(
        restart_count_override,
        state.restart_count if state is not None else None,
        increment=False,
    )
    return launch_count, restart_count


def _ensure_service_can_start(
    db: TradingDatabase, state: ServiceStateSnapshot | None
) -> None:
    if (
        state is None
        or state.state not in {"starting", "running", "stopping"}
        or state.pid is None
    ):
        return

    view = build_runtime_status_view(state)
    if view.runtime_state == "active":
        raise RuntimeError(f"Service is already active with PID {state.pid}.")
    if view.live_process:
        raise RuntimeError(
            "Service heartbeat is stale but PID "
            f"{state.pid} is still alive. Use restart-service or "
            "stop-service --force before launching another background service."
        )
    _record_stale_service_recovery(db, state)


def _record_stale_service_recovery(
    db: TradingDatabase, state: ServiceStateSnapshot
) -> None:
    message = f"Recovered stale runtime state from dead PID {state.pid}."
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
        message=message,
        last_error=state.last_error,
        pid=None,
        clear_pid=True,
        stop_requested=False,
    )
    db.insert_service_event(
        level="warning",
        event_type="stale_service_recovered",
        message=message,
        cycle_count=state.cycle_count if state.cycle_count > 0 else None,
        symbol=state.current_symbol,
    )


def _service_run_command(
    *,
    symbols: list[str],
    interval: str,
    lookback: str,
    poll_seconds: int,
    continuous: bool,
    max_cycles: int | None,
) -> list[str]:
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
    return command


def _spawn_service_process(
    *,
    command: list[str],
    stdout_path: Path,
    stderr_path: Path,
    workdir: Path | None,
) -> subprocess.Popen[bytes]:
    with (
        open_private_append_binary(stdout_path) as stdout_handle,
        open_private_append_binary(stderr_path) as stderr_handle,
    ):
        return subprocess.Popen(
            command,
            cwd=str(workdir or Path.cwd()),
            stdout=stdout_handle,
            stderr=stderr_handle,
            start_new_session=True,
        )


def _record_spawned_service(
    *,
    db: TradingDatabase,
    process: subprocess.Popen[bytes],
    symbols: list[str],
    interval: str,
    lookback: str,
    poll_seconds: int,
    continuous: bool,
    max_cycles: int | None,
    launch_count: int,
    restart_count: int,
    stdout_path: Path,
    stderr_path: Path,
) -> None:
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
