from __future__ import annotations

from collections.abc import Callable

import typer
from rich.panel import Panel

from agentic_trader.cli_modules.common import console
from agentic_trader.config import Settings
from agentic_trader.schemas import ServiceStateSnapshot
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.ui_text import (
    MESSAGE_BACKGROUND_SERVICE_NOT_ACTIVE,
    MESSAGE_SERVICE_STALE_RUNTIME_RECOVERED,
    MESSAGE_SERVICE_STALE_RUNTIME_RECOVERED_EVENT,
    MESSAGE_SERVICE_STOP_REQUESTED,
    TITLE_NOT_RUNNING,
    TITLE_STALE_STATE_RECOVERED,
    TITLE_STOP_REQUESTED,
)

ReadServiceState = Callable[[Settings], ServiceStateSnapshot | None]
IsProcessAlive = Callable[[int], bool]
RequestStop = Callable[[Settings], None]
DatabaseFactory = Callable[[Settings], TradingDatabase]
TerminateProcess = Callable[[int], object]


def run_stop_service_command(
    *,
    settings: Settings,
    force: bool,
    read_state: ReadServiceState,
    process_alive: IsProcessAlive,
    request_service_stop: RequestStop,
    database_factory: DatabaseFactory,
    terminate_process: TerminateProcess,
) -> None:
    state = read_state(settings)
    if state is None or state.pid is None:
        _print_panel(
            TITLE_NOT_RUNNING,
            MESSAGE_BACKGROUND_SERVICE_NOT_ACTIVE,
            border_style="yellow",
        )
        raise typer.Exit(code=0)

    pid = state.pid
    if not process_alive(pid):
        _recover_stale_service_state(
            settings=settings,
            state=state,
            pid=pid,
            database_factory=database_factory,
        )
        _print_panel(
            TITLE_STALE_STATE_RECOVERED,
            MESSAGE_SERVICE_STALE_RUNTIME_RECOVERED.format(pid=pid),
            border_style="yellow",
        )
        raise typer.Exit(code=0)

    _request_running_service_stop(
        settings=settings,
        pid=pid,
        force=force,
        request_service_stop=request_service_stop,
        database_factory=database_factory,
        terminate_process=terminate_process,
    )
    _print_panel(
        TITLE_STOP_REQUESTED,
        MESSAGE_SERVICE_STOP_REQUESTED.format(pid=pid),
        border_style="yellow",
    )


def _recover_stale_service_state(
    *,
    settings: Settings,
    state: ServiceStateSnapshot,
    pid: int,
    database_factory: DatabaseFactory,
) -> None:
    db = database_factory(settings)
    try:
        message = MESSAGE_SERVICE_STALE_RUNTIME_RECOVERED_EVENT.format(pid=pid)
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
    finally:
        db.close()


def _request_running_service_stop(
    *,
    settings: Settings,
    pid: int,
    force: bool,
    request_service_stop: RequestStop,
    database_factory: DatabaseFactory,
    terminate_process: TerminateProcess,
) -> None:
    request_service_stop(settings)
    try:
        db = database_factory(settings)
        try:
            db.request_stop_service()
        finally:
            db.close()
    except Exception:
        pass
    if force:
        terminate_process(pid)


def _print_panel(title: str, body: str, *, border_style: str) -> None:
    console.print(Panel(body, title=title, border_style=border_style))
