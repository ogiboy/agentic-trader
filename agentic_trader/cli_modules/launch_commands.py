from __future__ import annotations

from collections.abc import Callable

import typer
from rich.panel import Panel

from agentic_trader.cli_modules.common import console
from agentic_trader.config import Settings
from agentic_trader.schemas import LLMHealthStatus, RunArtifacts
from agentic_trader.ui_text import t as ui_t
from agentic_trader.workflows.service import ServiceCycleResult

RunOnce = Callable[..., RunArtifacts]
PersistRun = Callable[..., str]
RenderExecution = Callable[[str, RunArtifacts], None]
EnsureReady = Callable[[Settings], LLMHealthStatus]
RunService = Callable[..., list[ServiceCycleResult]]
StartBackgroundService = Callable[..., int]


def register_launch_commands(
    app: typer.Typer,
    *,
    settings_provider: Callable[[], Settings],
    ensure_ready: EnsureReady,
    run_once: RunOnce,
    persist_run: PersistRun,
    run_service: RunService,
    start_background_service: StartBackgroundService,
    render_execution: RenderExecution,
) -> None:
    _register_run_command(
        app,
        settings_provider=settings_provider,
        ensure_ready=ensure_ready,
        run_once=run_once,
        persist_run=persist_run,
        render_execution=render_execution,
    )
    _register_launch_command(
        app,
        settings_provider=settings_provider,
        ensure_ready=ensure_ready,
        run_service=run_service,
        start_background_service=start_background_service,
        render_execution=render_execution,
    )


def _register_run_command(
    app: typer.Typer,
    *,
    settings_provider: Callable[[], Settings],
    ensure_ready: EnsureReady,
    run_once: RunOnce,
    persist_run: PersistRun,
    render_execution: RenderExecution,
) -> None:
    @app.command()
    def run(
        symbol: str = typer.Option(..., help=ui_t("help.symbol")),
        interval: str = typer.Option("1d", help=ui_t("help.interval")),
        lookback: str = typer.Option("180d", help=ui_t("help.lookback")),
    ) -> None:
        settings = settings_provider()
        try:
            ensure_ready(settings)
            artifacts = run_once(
                settings=settings,
                symbol=symbol,
                interval=interval,
                lookback=lookback,
                allow_fallback=False,
            )
            order_id = persist_run(settings=settings, artifacts=artifacts)
            render_execution(order_id, artifacts)
        except Exception as exc:
            console.print(
                _render_health_panel(
                    ui_t("title.run_blocked"),
                    str(exc),
                    border_style="red",
                )
            )
            raise typer.Exit(code=1) from exc


def _register_launch_command(
    app: typer.Typer,
    *,
    settings_provider: Callable[[], Settings],
    ensure_ready: EnsureReady,
    run_service: RunService,
    start_background_service: StartBackgroundService,
    render_execution: RenderExecution,
) -> None:
    @app.command()
    def launch(
        symbols: str = typer.Option(..., help=ui_t("help.launch_symbols")),
        interval: str = typer.Option("1d", help=ui_t("help.interval")),
        lookback: str = typer.Option("180d", help=ui_t("help.lookback")),
        poll_seconds: int = typer.Option(300, help=ui_t("help.launch_poll_seconds")),
        continuous: bool = typer.Option(False, help=ui_t("help.launch_continuous")),
        max_cycles: int | None = typer.Option(
            None, help=ui_t("help.launch_max_cycles")
        ),
        background: bool = typer.Option(False, help=ui_t("help.launch_background")),
    ) -> None:
        settings = settings_provider()
        symbol_list = _parse_launch_symbols(symbols)
        try:
            health = ensure_ready(settings)
            _render_launch_gate(health)
            _render_launch_plan(
                symbols=symbol_list,
                interval=interval,
                lookback=lookback,
                continuous=continuous,
                poll_seconds=poll_seconds,
                background=background,
            )
            if background:
                _start_launch_background(
                    start_background_service=start_background_service,
                    settings=settings,
                    symbols=symbol_list,
                    interval=interval,
                    lookback=lookback,
                    poll_seconds=poll_seconds,
                    continuous=continuous,
                    max_cycles=max_cycles,
                )
                return
            results = _run_launch_foreground(
                run_service=run_service,
                settings=settings,
                symbols=symbol_list,
                interval=interval,
                lookback=lookback,
                poll_seconds=poll_seconds,
                continuous=continuous,
                max_cycles=max_cycles,
            )
            _render_launch_results(results, render_execution=render_execution)
        except Exception as exc:
            console.print(
                _render_health_panel(
                    "Launch Blocked",
                    str(exc),
                    border_style="red",
                )
            )
            raise typer.Exit(code=1) from exc


def _parse_launch_symbols(symbols: str) -> list[str]:
    symbol_list = [item.strip().upper() for item in symbols.split(",") if item.strip()]
    if not symbol_list:
        raise typer.BadParameter(ui_t("message.launch_symbol_required"))
    return symbol_list


def _render_launch_gate(health: LLMHealthStatus) -> None:
    console.print(
        _render_health_panel(
            ui_t("title.runtime_gate_open"),
            ui_t("message.runtime_gate_open").format(
                base_url=health.base_url,
                model_name=health.model_name,
            ),
            border_style="green",
        )
    )


def _render_launch_plan(
    *,
    symbols: list[str],
    interval: str,
    lookback: str,
    continuous: bool,
    poll_seconds: int,
    background: bool,
) -> None:
    console.print(
        Panel(
            ui_t("message.launch_plan").format(
                symbols=", ".join(symbols),
                interval=interval,
                lookback=lookback,
                continuous=continuous,
                poll_seconds=poll_seconds,
                background=background,
            ),
            title=ui_t("title.launch_plan"),
            border_style="cyan",
        )
    )


def _start_launch_background(
    *,
    start_background_service: StartBackgroundService,
    settings: Settings,
    symbols: list[str],
    interval: str,
    lookback: str,
    poll_seconds: int,
    continuous: bool,
    max_cycles: int | None,
) -> None:
    if not continuous:
        raise typer.BadParameter(ui_t("message.background_requires_continuous"))
    pid = start_background_service(
        settings=settings,
        symbols=symbols,
        interval=interval,
        lookback=lookback,
        poll_seconds=poll_seconds,
        continuous=continuous,
        max_cycles=max_cycles,
    )
    console.print(
        _render_health_panel(
            "Background Service Started",
            f"Orchestrator is running in the background with PID {pid}.",
            border_style="green",
        )
    )


def _run_launch_foreground(
    *,
    run_service: RunService,
    settings: Settings,
    symbols: list[str],
    interval: str,
    lookback: str,
    poll_seconds: int,
    continuous: bool,
    max_cycles: int | None,
) -> list[ServiceCycleResult]:
    return run_service(
        settings=settings,
        symbols=symbols,
        interval=interval,
        lookback=lookback,
        poll_seconds=poll_seconds,
        continuous=continuous,
        max_cycles=max_cycles,
    )


def _render_launch_results(
    results: list[ServiceCycleResult],
    *,
    render_execution: RenderExecution,
) -> None:
    if not results:
        console.print(
            _render_health_panel(
                "Service Stopped",
                "No new results were produced before the orchestrator stopped.",
                border_style="yellow",
            )
        )
        return
    latest_result = results[-1]
    render_execution(latest_result.order_id, latest_result.artifacts)


def _render_health_panel(status: str, body: str, *, border_style: str) -> Panel:
    return Panel(
        body,
        title=f"Agentic Trader // {status}",
        border_style=border_style,
    )
