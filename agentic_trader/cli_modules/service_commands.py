# pyright: reportUnusedFunction=false
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
from agentic_trader.ui_text import (
    HELP_MONITOR_REFRESH_SECONDS,
    HELP_RESTART_SERVICE_GRACE_SECONDS,
    HELP_STOP_SERVICE_FORCE,
    LABEL_LATEST_ORDER,
    MESSAGE_BACKGROUND_SERVICE_RESTARTED,
    MESSAGE_LAUNCH_SYMBOL_REQUIRED,
    MESSAGE_NO_ORDERS_RECORDED,
    TITLE_RESTART_BLOCKED,
    TITLE_SERVICE_RESTARTED,
)


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
    @app.command()
    def monitor(
        refresh_seconds: float = typer.Option(
            1.0, min=0.2, help=HELP_MONITOR_REFRESH_SECONDS
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
    @app.command("stop-service")
    def stop_service(
        force: bool = typer.Option(False, help=HELP_STOP_SERVICE_FORCE),
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
            3.0, min=0.0, help=HELP_RESTART_SERVICE_GRACE_SECONDS
        ),
    ) -> None:
        """
        Restart the managed background orchestrator using its last recorded launch configuration.

        Parameters:
            grace_seconds (float): Seconds to wait for a graceful stop before forcing relaunch.
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
                    TITLE_RESTART_BLOCKED,
                    str(exc),
                    border_style="red",
                )
            )
            raise typer.Exit(code=1) from exc
        console.print(
            deps.render_health_panel(
                TITLE_SERVICE_RESTARTED,
                MESSAGE_BACKGROUND_SERVICE_RESTARTED.format(pid=pid),
                border_style="green",
            )
        )


def _register_service_run_command(app: typer.Typer, deps: ServiceCommandDeps) -> None:
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
            raise typer.BadParameter(MESSAGE_LAUNCH_SYMBOL_REQUIRED)
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
        """Show the latest paper order."""
        settings = deps.get_settings()
        db = deps.database_factory(settings)
        try:
            order = db.latest_order()
        finally:
            db.close()
        if order is None:
            console.print(Text(MESSAGE_NO_ORDERS_RECORDED, style="yellow"))
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
        table = Table(title=LABEL_LATEST_ORDER)
        for column in columns:
            table.add_column(column)
        table.add_row(*(str(value) for value in order))
        console.print(table)


__all__ = ("ServiceCommandDeps", "register_service_commands")
