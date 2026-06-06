from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

import typer
from rich.table import Table
from rich.text import Text

from agentic_trader.cli_modules.common import console
from agentic_trader.cli_modules.service_control import run_stop_service_command
from agentic_trader.config import Settings
from agentic_trader.schemas import ServiceStateSnapshot
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.ui_text import t as ui_t


class RunLiveMonitor(Protocol):
    def __call__(
        self,
        settings: Settings,
        *,
        refresh_seconds: float,
    ) -> object: ...


class RestartBackgroundService(Protocol):
    def __call__(self, *, settings: Settings, grace_seconds: float) -> int: ...


class RunService(Protocol):
    def __call__(
        self,
        *,
        settings: Settings,
        symbols: list[str],
        interval: str,
        lookback: str,
        poll_seconds: int,
        continuous: bool,
        max_cycles: int | None,
    ) -> object: ...


RenderHealthPanel = Callable[..., object]
ReadServiceState = Callable[[Settings], ServiceStateSnapshot | None]
IsProcessAlive = Callable[[int], bool]
RequestStop = Callable[[Settings], None]
TerminateProcess = Callable[[int], object]


@dataclass(frozen=True)
class ServiceCommandDeps:
    get_settings: Callable[[], Settings]
    build_monitor_renderable: Callable[[Settings], object]
    run_live_monitor: RunLiveMonitor
    read_service_state: ReadServiceState
    is_process_alive: IsProcessAlive
    request_stop: RequestStop
    database_factory: Callable[[Settings], TradingDatabase]
    terminate_service_process: TerminateProcess
    restart_background_service: RestartBackgroundService
    render_health_panel: RenderHealthPanel
    run_service: RunService
    run_main_menu: Callable[[], None]


def register_service_commands(app: typer.Typer, deps: ServiceCommandDeps) -> None:
    _register_monitor_command(app, deps)
    _register_stop_service_command(app, deps)
    _register_restart_service_command(app, deps)
    _register_service_run_command(app, deps)
    _register_menu_command(app, deps)
    _register_latest_order_command(app, deps)


def _register_monitor_command(app: typer.Typer, deps: ServiceCommandDeps) -> None:
    """
    Attach to and display the live runtime monitor.
    
    Parameters:
    	refresh_seconds (float): Dashboard refresh interval in seconds; values less than 0.2 are not allowed.
    """
    @app.command()
    def monitor(
        refresh_seconds: float = typer.Option(
            1.0, min=0.2, help=ui_t("help.monitor_refresh_seconds")
        ),
    ) -> None:
        """
        Open and attach to the live runtime monitor.

        Parameters:
            refresh_seconds (float): Dashboard refresh interval in seconds (minimum 0.2).
        """
        settings = deps.get_settings()
        console.print(deps.build_monitor_renderable(settings))
        deps.run_live_monitor(settings, refresh_seconds=refresh_seconds)


def _register_stop_service_command(app: typer.Typer, deps: ServiceCommandDeps) -> None:
    """
    Request a graceful stop for the background orchestrator.
    
    Parameters:
    	force (bool): If `True`, force immediate termination of the service process instead of requesting a graceful stop.
    """
    @app.command("stop-service")
    def stop_service(
        force: bool = typer.Option(False, help=ui_t("help.stop_service_force")),
    ) -> None:
        """Request a graceful stop for the background orchestrator."""
        run_stop_service_command(
            settings=deps.get_settings(),
            force=force,
            read_state=deps.read_service_state,
            process_alive=deps.is_process_alive,
            request_service_stop=deps.request_stop,
            database_factory=deps.database_factory,
            terminate_process=deps.terminate_service_process,
        )


def _register_restart_service_command(
    app: typer.Typer, deps: ServiceCommandDeps
) -> None:
    @app.command("restart-service")
    def restart_service(
        grace_seconds: float = typer.Option(
            3.0, min=0.0, help=ui_t("help.restart_service_grace_seconds")
        ),
    ) -> None:
        """
        Restart the managed background orchestrator using its last recorded launch configuration.
        
        Parameters:
            grace_seconds (float): Seconds to wait for a graceful stop before forcing a relaunch.
        
        Raises:
            typer.Exit: Exits with code 1 if restarting the background service fails.
        """
        settings = deps.get_settings()
        try:
            pid = deps.restart_background_service(
                settings=settings,
                grace_seconds=grace_seconds,
            )
        except Exception as exc:
            console.print(
                deps.render_health_panel(
                    ui_t("title.restart_blocked"),
                    str(exc),
                    border_style="red",
                )
            )
            raise typer.Exit(code=1) from exc
        console.print(
            deps.render_health_panel(
                ui_t("title.service_restarted"),
                ui_t("message.background_service_restarted").format(pid=pid),
                border_style="green",
            )
        )


def _register_service_run_command(app: typer.Typer, deps: ServiceCommandDeps) -> None:
    """
    Entrypoint for the hidden background worker command that launches the service run loop.
    
    Parses the comma-separated `symbols` string into an uppercase list (empty entries are discarded) and invokes the injected service runner with the provided timing and control options. Raises a `typer.BadParameter` if no valid symbols are supplied.
    
    Parameters:
        symbols (str): Comma-separated symbol identifiers (whitespace ignored; each symbol is uppercased).
        interval (str): Data interval string used by the service (e.g., "1d").
        lookback (str): Historical lookback period string (e.g., "180d").
        poll_seconds (int): Seconds between polling cycles.
        max_cycles (int | None): Optional maximum number of cycles to run; `None` means unlimited.
        continuous (bool): Whether the service should run continuously between cycles.
    """
    @app.command("service-run", hidden=True)
    def service_run(
        symbols: str = typer.Option(...),
        interval: str = typer.Option("1d"),
        lookback: str = typer.Option("180d"),
        poll_seconds: int = typer.Option(300),
        max_cycles: int | None = typer.Option(None),
        continuous: bool = typer.Option(True),
    ) -> None:
        """Internal background worker entrypoint."""
        settings = deps.get_settings()
        symbol_list = [
            item.strip().upper() for item in symbols.split(",") if item.strip()
        ]
        if not symbol_list:
            raise typer.BadParameter(ui_t("message.launch_symbol_required"))
        deps.run_service(
            settings=settings,
            symbols=symbol_list,
            interval=interval,
            lookback=lookback,
            poll_seconds=poll_seconds,
            continuous=continuous,
            max_cycles=max_cycles,
        )


def _register_menu_command(app: typer.Typer, deps: ServiceCommandDeps) -> None:
    @app.command()
    def menu() -> None:
        """Open the interactive terminal control room."""
        deps.run_main_menu()


def _register_latest_order_command(app: typer.Typer, deps: ServiceCommandDeps) -> None:
    @app.command("latest-order")
    def latest_order() -> None:
        """
        Display the most recent paper order in a tabular format.
        
        If a latest order exists, prints a table titled with the localized label containing the order's fields. If no order is recorded, prints a localized yellow notice and exits the CLI with code 0.
        """
        settings = deps.get_settings()
        db = deps.database_factory(settings)
        try:
            order = db.latest_order()
        finally:
            db.close()
        if order is None:
            console.print(Text(ui_t("message.no_orders_recorded"), style="yellow"))
            raise typer.Exit(code=0)

        columns: list[str] = [
            "order_id",
            "created_at",
            "symbol",
            "side",
            "approved",
            "entry_price",
            "stop_loss",
            "take_profit",
            "position_size_pct",
            "confidence",
        ]
        table = Table(title=ui_t("label.latest_order"))
        for column in columns:
            table.add_column(column)
        table.add_row(*(str(value) for value in order))
        console.print(table)


__all__ = ("ServiceCommandDeps", "register_service_commands")
