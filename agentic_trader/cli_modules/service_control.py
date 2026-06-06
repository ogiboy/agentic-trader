from __future__ import annotations

from collections.abc import Callable

import typer
from rich.panel import Panel

from agentic_trader.cli_modules.common import console
from agentic_trader.config import Settings
from agentic_trader.schemas import ServiceStateSnapshot
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.ui_text import t as ui_t

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
    """
    Coordinate stopping the background service recorded in persistent state.
    
    Reads the current service snapshot and:
    - If no active snapshot or no PID is recorded, prints a "not running" panel and exits.
    - If a PID is recorded but the process is not alive, updates persisted state to reflect the stopped service, inserts a stale-recovery event, prints a recovery panel, and exits.
    - If the PID appears alive, requests the running service to stop (via provided request hooks and the database), and optionally force-terminates the process.
    
    Parameters:
        settings: Runtime settings passed to state/database helpers.
        force: If True, forcibly terminate the running process after requesting a graceful stop.
        read_state: Callable that returns the current persisted service snapshot or None.
        process_alive: Callable that returns True if a given PID appears alive.
        request_service_stop: Callable invoked to request the service stop at the application level.
        database_factory: Callable that returns a database handle used to persist state/events.
        terminate_process: Callable invoked to terminate a process by PID when force is True.
    
    Raises:
        typer.Exit: Exits with code 0 for "not running" and "stale state recovered" outcomes.
    """
    state = read_state(settings)
    if state is None or state.pid is None:
        _print_panel(
            ui_t("title.not_running"),
            ui_t("message.background_service_not_active"),
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
            ui_t("title.stale_state_recovered"),
            ui_t("message.service_stale_runtime_recovered").format(pid=pid),
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
        ui_t("title.stop_requested"),
        ui_t("message.service_stop_requested").format(pid=pid),
        border_style="yellow",
    )


def _recover_stale_service_state(
    *,
    settings: Settings,
    state: ServiceStateSnapshot,
    pid: int,
    database_factory: DatabaseFactory,
) -> None:
    """
    Persist an updated stopped service state and record a recovery event for a stale runtime PID.
    
    Updates the persisted service state to mark it stopped (clearing runtime-specific fields) and inserts a warning event describing that a previously recorded PID was recovered. Always closes the database handle created from `database_factory`, even if an error occurs.
    
    Parameters:
        settings (Settings): Application settings used to create the database handle.
        state (ServiceStateSnapshot): Snapshot of the previous service state; most persisted fields are copied from this snapshot.
        pid (int): The stale runtime PID that was recovered; included in the recovery message.
        database_factory (DatabaseFactory): Callable that accepts `settings` and returns a `TradingDatabase` instance used for persistence.
    """
    db = database_factory(settings)
    try:
        message = ui_t("message.service_stale_runtime_recovered_event").format(pid=pid)
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
