# pyright: reportUnusedFunction=false
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, cast

import typer
from rich.panel import Panel
from rich.table import Table

from agentic_trader import ui_text as text
from agentic_trader.cli_modules.common import console
from agentic_trader.config import Settings
from agentic_trader.json_utils import object_list, object_mapping, object_mapping_list
from agentic_trader.runtime_status import RuntimeStatusView
from agentic_trader.schemas import PortfolioSnapshot, PositionSnapshot
from agentic_trader.schemas import ServiceStateSnapshot


@dataclass(frozen=True)
class StatusCommandDeps:
    get_settings: Callable[[], Settings]
    emit_json: Callable[[object], None]
    portfolio_payload: Callable[[Settings], dict[str, object]]
    runtime_status_payload: Callable[[RuntimeStatusView, Settings], dict[str, object]]
    service_supervisor_payload: Callable[[Settings], dict[str, object]]
    broker_payload: Callable[[Settings], dict[str, object]]
    finance_ops_payload: Callable[[Settings], dict[str, object]]
    render_finance_ops: Callable[[dict[str, object]], None]
    render_position_plan_repair: Callable[[dict[str, object]], None]
    provider_diagnostics_payload: Any
    v1_readiness_payload: Any
    read_service_state: Callable[[Settings], ServiceStateSnapshot | None]
    build_runtime_status_view: Callable[
        [ServiceStateSnapshot | None], RuntimeStatusView
    ]
    render_service_state: Callable[[ServiceStateSnapshot | None], None]
    open_db: Any
    repair_missing_position_plans: Any


def register_status_commands(app: typer.Typer, deps: StatusCommandDeps) -> None:
    _register_portfolio_command(app, deps)
    _register_runtime_status_commands(app, deps)
    _register_broker_status_command(app, deps)
    _register_provider_readiness_commands(app, deps)
    _register_finance_ops_commands(app, deps)


def _register_portfolio_command(app: typer.Typer, deps: StatusCommandDeps) -> None:
    @app.command()
    def portfolio(
        json_output: bool = typer.Option(False, "--json", help=text.HELP_JSON),
    ) -> None:
        settings = deps.get_settings()
        payload = deps.portfolio_payload(settings)
        snapshot = PortfolioSnapshot.model_validate(
            cast(dict[str, object], payload["snapshot"])
        )
        position_payloads = cast(list[dict[str, object]], payload["positions"])
        positions = [
            PositionSnapshot.model_validate(position) for position in position_payloads
        ]
        available = bool(payload["available"])
        error = payload["error"]
        if json_output:
            deps.emit_json(payload)
            return
        if not available:
            console.print(
                Panel(
                    text.MESSAGE_PORTFOLIO_TEMPORARILY_UNAVAILABLE.format(
                        error=error
                    ),
                    title=text.LABEL_OBSERVER_MODE,
                    border_style="yellow",
                )
            )
            raise typer.Exit(code=0)

        _render_portfolio_summary(snapshot)
        _render_positions(positions)


def _render_portfolio_summary(snapshot: PortfolioSnapshot) -> None:
    summary = Table(title=text.TITLE_PORTFOLIO)
    summary.add_column(text.LABEL_METRIC)
    summary.add_column(text.LABEL_VALUE)
    summary.add_row(text.LABEL_CASH, f"{snapshot.cash:.2f}")
    summary.add_row(text.LABEL_MARKET_VALUE, f"{snapshot.market_value:.2f}")
    summary.add_row(text.LABEL_EQUITY, f"{snapshot.equity:.2f}")
    summary.add_row(text.LABEL_REALIZED_PNL, f"{snapshot.realized_pnl:.2f}")
    summary.add_row(text.LABEL_UNREALIZED_PNL, f"{snapshot.unrealized_pnl:.2f}")
    summary.add_row(text.LABEL_OPEN_POSITIONS, str(snapshot.open_positions))
    console.print(summary)


def _render_positions(positions: list[PositionSnapshot]) -> None:
    positions_table = Table(title=text.TITLE_POSITIONS)
    positions_table.add_column(text.LABEL_SYMBOL)
    positions_table.add_column(text.LABEL_QUANTITY)
    positions_table.add_column(text.LABEL_AVERAGE_PRICE)
    positions_table.add_column(text.LABEL_MARKET_PRICE)
    positions_table.add_column(text.LABEL_MARKET_VALUE)
    positions_table.add_column(text.LABEL_UNREALIZED_PNL)
    for position in positions:
        positions_table.add_row(
            position.symbol,
            f"{position.quantity:.6f}",
            f"{position.average_price:.4f}",
            f"{position.market_price:.4f}",
            f"{position.market_value:.2f}",
            f"{position.unrealized_pnl:.2f}",
        )
    if positions:
        console.print(positions_table)
    else:
        console.print(
            Panel(
                text.MESSAGE_NO_OPEN_POSITIONS,
                title=text.TITLE_POSITIONS,
                border_style="yellow",
            )
        )


def _register_runtime_status_commands(
    app: typer.Typer, deps: StatusCommandDeps
) -> None:
    @app.command()
    def status(
        json_output: bool = typer.Option(False, "--json", help=text.HELP_JSON),
    ) -> None:
        settings = deps.get_settings()
        state = deps.read_service_state(settings)
        if json_output:
            view = deps.build_runtime_status_view(state)
            deps.emit_json(deps.runtime_status_payload(view, settings))
            return
        deps.render_service_state(state)

    @app.command("supervisor-status")
    def supervisor_status(
        json_output: bool = typer.Option(False, "--json", help=text.HELP_JSON),
    ) -> None:
        settings = deps.get_settings()
        payload = deps.service_supervisor_payload(settings)
        if json_output:
            deps.emit_json(payload)
            return
        _render_supervisor_payload(payload)


def _render_supervisor_payload(payload: dict[str, object]) -> None:
    state_json = payload["state"]
    if state_json is None:
        console.print(
            Panel(
                text.MESSAGE_NO_RUNTIME_STATE,
                title=text.TITLE_SERVICE_SUPERVISOR,
                border_style="yellow",
            )
        )
        return

    state = ServiceStateSnapshot.model_validate(state_json)
    table = Table(title=text.TITLE_SERVICE_SUPERVISOR)
    table.add_column(text.LABEL_FIELD)
    table.add_column(text.LABEL_VALUE)
    table.add_row(text.LABEL_RUNTIME, str(payload["runtime_state"]))
    table.add_row(
        text.LABEL_LIVE_PROCESS,
        text.LABEL_YES if payload["live_process"] else text.LABEL_NO,
    )
    table.add_row(text.LABEL_BACKGROUND_MODE, str(state.background_mode))
    table.add_row(text.LABEL_LAUNCH_COUNT, str(state.launch_count))
    table.add_row(text.LABEL_RESTART_COUNT, str(state.restart_count))
    table.add_row(text.LABEL_LAST_TERMINAL_STATE, state.last_terminal_state or "-")
    table.add_row(text.LABEL_LAST_TERMINAL_AT, state.last_terminal_at or "-")
    table.add_row(text.LABEL_STDOUT_LOG, state.stdout_log_path or "-")
    table.add_row(text.LABEL_STDERR_LOG, state.stderr_log_path or "-")
    table.add_row(text.LABEL_STATUS_NOTE, str(payload["status_message"]))
    console.print(table)
    console.print(
        Panel(
            "\n".join(cast(list[str], payload["stdout_tail"]))
            or text.MESSAGE_NO_STDOUT_LOG_LINES,
            title=text.TITLE_SERVICE_STDOUT_TAIL,
            border_style="cyan",
        )
    )
    console.print(
        Panel(
            "\n".join(cast(list[str], payload["stderr_tail"]))
            or text.MESSAGE_NO_STDERR_LOG_LINES,
            title=text.TITLE_SERVICE_STDERR_TAIL,
            border_style="yellow",
        )
    )


def _register_broker_status_command(app: typer.Typer, deps: StatusCommandDeps) -> None:
    @app.command("broker-status")
    def broker_status(
        json_output: bool = typer.Option(False, "--json", help=text.HELP_JSON),
    ) -> None:
        settings = deps.get_settings()
        payload = deps.broker_payload(settings)
        if json_output:
            deps.emit_json(payload)
            return
        _render_broker_status(payload)


def _render_broker_status(payload: dict[str, object]) -> None:
    table = Table(title=text.TITLE_BROKER_STATUS)
    table.add_column(text.LABEL_FIELD)
    table.add_column(text.LABEL_VALUE)
    table.add_row(text.LABEL_BACKEND, str(payload["backend"]))
    table.add_row(text.LABEL_ADAPTER, str(payload["adapter_name"]))
    table.add_row(text.LABEL_STATE, str(payload["state"]))
    table.add_row(text.LABEL_SIMULATED, str(payload["simulated"]))
    table.add_row(
        text.LABEL_LIVE_EXECUTION_ENABLED,
        str(payload["live_execution_enabled"]),
    )
    table.add_row(text.LABEL_KILL_SWITCH_ACTIVE, str(payload["kill_switch_active"]))
    table.add_row(text.LABEL_LIVE_REQUESTED, str(payload["live_requested"]))
    table.add_row(text.LABEL_LIVE_READY, str(payload["live_ready"]))
    table.add_row(text.LABEL_MESSAGE, str(payload["message"]))
    healthcheck = object_mapping(payload.get("healthcheck"))
    if healthcheck:
        table.add_row(text.LABEL_HEALTHCHECK, str(healthcheck.get("message", "-")))
    console.print(table)


def _register_provider_readiness_commands(
    app: typer.Typer, deps: StatusCommandDeps
) -> None:
    @app.command("provider-diagnostics")
    def provider_diagnostics(
        json_output: bool = typer.Option(False, "--json", help=text.HELP_JSON),
    ) -> None:
        settings = deps.get_settings()
        payload = deps.provider_diagnostics_payload(settings)
        if json_output:
            deps.emit_json(payload)
            return
        _render_provider_diagnostics(payload)

    @app.command("v1-readiness")
    def v1_readiness(
        check_provider: bool = typer.Option(
            False,
            "--provider-check/--skip-provider-check",
            help=text.HELP_V1_PROVIDER_CHECK,
        ),
        json_output: bool = typer.Option(False, "--json", help=text.HELP_JSON),
    ) -> None:
        settings = deps.get_settings()
        payload = deps.v1_readiness_payload(settings, check_provider=check_provider)
        if json_output:
            deps.emit_json(payload)
            return
        _render_v1_readiness(payload)


def _render_provider_diagnostics(payload: dict[str, object]) -> None:
    summary = Table(title=text.TITLE_PROVIDER_DIAGNOSTICS)
    summary.add_column(text.LABEL_FIELD)
    summary.add_column(text.LABEL_VALUE)
    llm = object_mapping(payload.get("llm"))
    market_data = object_mapping(payload.get("market_data"))
    news = object_mapping(payload.get("news"))
    alpaca = object_mapping(payload.get("alpaca"))
    summary.add_row(text.LABEL_LLM_PROVIDER, str(llm.get("provider", "-")))
    summary.add_row(text.LABEL_DEFAULT_MODEL, str(llm.get("default_model", "-")))
    summary.add_row(text.LABEL_BASE_URL, str(llm.get("base_url", "-")))
    summary.add_row(
        text.LABEL_MARKET_PROVIDER,
        str(market_data.get("selected_provider", "-")),
    )
    summary.add_row(text.LABEL_MARKET_ROLE, str(market_data.get("selected_role", "-")))
    summary.add_row(text.LABEL_NEWS_MODE, str(news.get("mode", "-")))
    summary.add_row(text.LABEL_ALPACA_PAPER_ENDPOINT, str(alpaca.get("paper_endpoint", "-")))
    summary.add_row(text.LABEL_ALPACA_FEED, str(alpaca.get("data_feed", "-")))
    summary.add_row(
        text.LABEL_ALPACA_CREDENTIALS_CONFIGURED,
        str(alpaca.get("credentials_configured", False)),
    )
    console.print(summary)
    _render_provider_ladder(payload)


def _render_provider_ladder(payload: dict[str, object]) -> None:
    provider_table = Table(title=text.TITLE_PROVIDER_SOURCE_LADDER)
    provider_table.add_column(text.LABEL_PROVIDER)
    provider_table.add_column(text.LABEL_TYPE)
    provider_table.add_column(text.LABEL_ROLE)
    provider_table.add_column(text.LABEL_ENABLED)
    provider_table.add_column(text.LABEL_API_KEY)
    provider_table.add_column(text.LABEL_FRESHNESS)
    provider_table.add_column(text.LABEL_NOTES)
    for row in object_mapping_list(payload.get("providers", [])):
        provider_table.add_row(
            str(row.get("provider_id", "-")),
            str(row.get("provider_type", "-")),
            str(row.get("role", "-")),
            str(row.get("enabled", False)),
            str(row.get("api_key_ready", "-")),
            str(row.get("freshness", "-")),
            ", ".join(str(note) for note in object_list(row.get("notes", []))),
        )
    console.print(provider_table)


def _render_v1_readiness(payload: dict[str, object]) -> None:
    paper = object_mapping(payload.get("paper_operations"))
    alpaca = object_mapping(payload.get("alpaca_paper"))
    paper_allowed = bool(paper.get("allowed"))
    console.print(
        Panel(
            str(payload.get("summary", text.MESSAGE_V1_READINESS_STATUS_UNAVAILABLE)),
            title=text.TITLE_V1_READINESS,
            border_style="green" if paper_allowed else "yellow",
        )
    )
    _render_readiness_checks(text.TITLE_PAPER_OPERATION_CHECKS, paper)
    _render_readiness_checks(text.TITLE_ALPACA_PAPER_CHECKS, alpaca)


def _render_readiness_checks(title: str, payload: Mapping[str, object]) -> None:
    checks = payload.get("checks", [])
    table = Table(title=title)
    table.add_column(text.LABEL_CHECK)
    table.add_column(text.LABEL_STATE)
    table.add_column(text.LABEL_BLOCKING)
    table.add_column(text.LABEL_DETAILS)
    for item in object_mapping_list(checks):
        passed = bool(item.get("passed"))
        state_label = (
            f"[green]{text.STATUS_PASS}[/green]"
            if passed
            else f"[red]{text.STATUS_FAIL}[/red]"
        )
        table.add_row(
            str(item.get("name", "-")),
            state_label,
            str(item.get("blocking", True)),
            str(item.get("details", "")),
        )
    console.print(table)


def _register_finance_ops_commands(app: typer.Typer, deps: StatusCommandDeps) -> None:
    @app.command("finance-ops")
    def finance_ops(
        json_output: bool = typer.Option(False, "--json", help=text.HELP_JSON),
    ) -> None:
        settings = deps.get_settings()
        payload = deps.finance_ops_payload(settings)
        if json_output:
            deps.emit_json(payload)
            return
        deps.render_finance_ops(payload)

    @app.command("position-plan-repair")
    def position_plan_repair(
        apply_changes: bool = typer.Option(
            False,
            "--apply",
            help=text.HELP_POSITION_PLAN_REPAIR_APPLY,
        ),
        max_holding_bars: int = typer.Option(
            20,
            min=1,
            max=500,
            help=text.HELP_POSITION_PLAN_REPAIR_MAX_HOLDING_BARS,
        ),
        json_output: bool = typer.Option(False, "--json", help=text.HELP_JSON),
    ) -> None:
        settings = deps.get_settings()
        try:
            db = deps.open_db(settings, read_only=not apply_changes)
            try:
                repairs = deps.repair_missing_position_plans(
                    db=db,
                    apply_repair=apply_changes,
                    max_holding_bars=max_holding_bars,
                )
            finally:
                db.close()
        except Exception as exc:
            console.print(
                Panel(
                    text.MESSAGE_POSITION_PLAN_REPAIR_TEMPORARILY_UNAVAILABLE.format(
                        error=exc
                    ),
                    title=text.LABEL_OBSERVER_MODE,
                    border_style="yellow",
                )
            )
            raise typer.Exit(code=0) from exc

        payload = _position_plan_repair_payload(
            apply_changes=apply_changes,
            repairs=repairs,
        )
        if json_output:
            deps.emit_json(payload)
            return
        deps.render_position_plan_repair(payload)


def _position_plan_repair_payload(
    *, apply_changes: bool, repairs: list[dict[str, object]]
) -> dict[str, object]:
    created = sum(1 for item in repairs if item["status"] == "created")
    candidates = sum(1 for item in repairs if item["status"] == "candidate")
    skipped = sum(1 for item in repairs if item["status"] == "skipped")
    return {
        "applied": apply_changes,
        "created": created,
        "candidates": candidates,
        "skipped": skipped,
        "repairs": repairs,
        "summary": (
            f"Created {created} repaired position plan(s)."
            if apply_changes
            else f"Found {candidates} repair candidate(s)."
        ),
    }
