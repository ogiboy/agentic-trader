from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, cast

import typer
from rich.panel import Panel
from rich.table import Table

from agentic_trader.ui_text import t as ui_t
from agentic_trader.cli_modules.common import console
from agentic_trader.config import Settings
from agentic_trader.json_utils import object_list, object_mapping, object_mapping_list
from agentic_trader.runtime_status import RuntimeStatusView
from agentic_trader.schemas import (
    PortfolioSnapshot,
    PositionSnapshot,
    ServiceStateSnapshot,
)


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
    """
    Register the `portfolio` CLI subcommand which displays the current portfolio or its JSON payload.
    
    The command accepts a `--json` flag: when set, the raw portfolio payload produced by the dependencies is emitted as JSON. When run in UI mode, if the portfolio data is reported unavailable the command prints an observer-mode panel with the error message and exits; otherwise it renders a portfolio summary and the list of positions using the module's render helpers.
    """
    @app.command()
    def portfolio(
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
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
                    ui_t("message.portfolio_temporarily_unavailable").format(
                        error=error
                    ),
                    title=ui_t("label.observer_mode"),
                    border_style="yellow",
                )
            )
            raise typer.Exit(code=0)

        _render_portfolio_summary(snapshot)
        _render_positions(positions)


def _render_portfolio_summary(snapshot: PortfolioSnapshot) -> None:
    """
    Render and print a summary table of portfolio totals to the console.
    
    Parameters:
        snapshot (PortfolioSnapshot): Aggregated portfolio totals (cash, market value, equity,
            realized/unrealized P&L, open positions) to display in the table.
    """
    summary = Table(title=ui_t("title.portfolio"))
    summary.add_column(ui_t("label.metric"))
    summary.add_column(ui_t("label.value"))
    summary.add_row(ui_t("label.cash"), f"{snapshot.cash:.2f}")
    summary.add_row(ui_t("label.market_value"), f"{snapshot.market_value:.2f}")
    summary.add_row(ui_t("label.equity"), f"{snapshot.equity:.2f}")
    summary.add_row(ui_t("label.realized_pnl"), f"{snapshot.realized_pnl:.2f}")
    summary.add_row(ui_t("label.unrealized_pnl"), f"{snapshot.unrealized_pnl:.2f}")
    summary.add_row(ui_t("label.open_positions"), str(snapshot.open_positions))
    console.print(summary)


def _render_positions(positions: list[PositionSnapshot]) -> None:
    """
    Render a table of open positions or a notice when no positions are available.
    
    Renders a Rich Table titled with the localized "positions" label containing rows for
    symbol, quantity, average price, market price, market value, and unrealized P&L.
    Numeric columns are formatted to fixed decimal places (quantity: 6, average/market price: 4,
    market value and unrealized P&L: 2). If the provided list is empty, prints a yellow
    panel with a localized "no open positions" message instead of the table.
    
    Parameters:
        positions (list[PositionSnapshot]): Sequence of position snapshots to display.
    """
    positions_table = Table(title=ui_t("title.positions"))
    positions_table.add_column(ui_t("label.symbol"))
    positions_table.add_column(ui_t("label.quantity"))
    positions_table.add_column(ui_t("label.average_price"))
    positions_table.add_column(ui_t("label.market_price"))
    positions_table.add_column(ui_t("label.market_value"))
    positions_table.add_column(ui_t("label.unrealized_pnl"))
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
                ui_t("message.no_open_positions"),
                title=ui_t("title.positions"),
                border_style="yellow",
            )
        )


def _register_runtime_status_commands(
    app: typer.Typer, deps: StatusCommandDeps
) -> None:
    """
    Register the 'status' and 'supervisor-status' CLI commands on the given Typer application.
    
    The `status` command reads the current service runtime state and either renders it or emits a JSON payload. The `supervisor-status` command builds the service supervisor payload and either renders the supervisor view or emits the payload as JSON.
    
    Parameters:
        app (typer.Typer): Typer application to which the commands will be added.
        deps (StatusCommandDeps): Dependency container providing settings access, state reading,
            payload builders, JSON emission, and rendering callables used by the commands.
    """
    @app.command()
    def status(
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
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
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
    ) -> None:
        """
        Display the service supervisor status as either JSON or a human-readable view.
        
        Builds the supervisor payload from current settings and either emits the raw JSON payload (when json_output is true) or renders a formatted supervisor status view for interactive terminals.
        
        Parameters:
            json_output (bool): If true, emit the supervisor payload as JSON instead of rendering a human-readable view.
        """
        settings = deps.get_settings()
        payload = deps.service_supervisor_payload(settings)
        if json_output:
            deps.emit_json(payload)
            return
        _render_supervisor_payload(payload)


def _render_supervisor_payload(payload: dict[str, object]) -> None:
    """
    Render the service supervisor payload to the console.
    
    If `payload["state"]` is None, prints a warning panel indicating no runtime state and returns.
    Otherwise prints a table summarizing supervisor fields (runtime state, live process, background mode,
    launch/restart counts, last terminal state/time, stdout/stderr log paths, and status message) and
    prints panels containing the stdout and stderr tail lines.
    
    Parameters:
        payload (dict[str, object]): Supervisor payload with expected keys:
            - "state": mapping validated into ServiceStateSnapshot or None.
            - "runtime_state": current runtime state value.
            - "live_process": truthy if a live process exists.
            - "status_message": textual status note.
            - "stdout_tail": list of stdout tail lines.
            - "stderr_tail": list of stderr tail lines.
    """
    state_json = payload["state"]
    if state_json is None:
        console.print(
            Panel(
                ui_t("message.no_runtime_state"),
                title=ui_t("title.service_supervisor"),
                border_style="yellow",
            )
        )
        return

    state = ServiceStateSnapshot.model_validate(state_json)
    table = Table(title=ui_t("title.service_supervisor"))
    table.add_column(ui_t("label.field"))
    table.add_column(ui_t("label.value"))
    table.add_row(ui_t("label.runtime"), str(payload["runtime_state"]))
    table.add_row(
        ui_t("label.live_process"),
        ui_t("label.yes") if payload["live_process"] else ui_t("label.no"),
    )
    table.add_row(ui_t("label.background_mode"), str(state.background_mode))
    table.add_row(ui_t("label.launch_count"), str(state.launch_count))
    table.add_row(ui_t("label.restart_count"), str(state.restart_count))
    table.add_row(ui_t("label.last_terminal_state"), state.last_terminal_state or "-")
    table.add_row(ui_t("label.last_terminal_at"), state.last_terminal_at or "-")
    table.add_row(ui_t("label.stdout_log"), state.stdout_log_path or "-")
    table.add_row(ui_t("label.stderr_log"), state.stderr_log_path or "-")
    table.add_row(ui_t("label.status_note"), str(payload["status_message"]))
    console.print(table)
    console.print(
        Panel(
            "\n".join(cast(list[str], payload["stdout_tail"]))
            or ui_t("message.no_stdout_log_lines"),
            title=ui_t("title.service_stdout_tail"),
            border_style="cyan",
        )
    )
    console.print(
        Panel(
            "\n".join(cast(list[str], payload["stderr_tail"]))
            or ui_t("message.no_stderr_log_lines"),
            title=ui_t("title.service_stderr_tail"),
            border_style="yellow",
        )
    )


def _register_broker_status_command(app: typer.Typer, deps: StatusCommandDeps) -> None:
    """
    Register the "broker-status" CLI command on the given Typer app.
    
    The command loads application settings, obtains a broker status payload from deps, and either emits the payload as JSON when the `--json` option is set or renders the broker status for human-readable output.
    """
    @app.command("broker-status")
    def broker_status(
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
    ) -> None:
        settings = deps.get_settings()
        payload = deps.broker_payload(settings)
        if json_output:
            deps.emit_json(payload)
            return
        _render_broker_status(payload)


def _render_broker_status(payload: dict[str, object]) -> None:
    """
    Render broker connection and health information as a Rich table to the console.
    
    Parameters:
        payload (dict[str, object]): Mapping containing broker status fields:
            - "backend": broker backend identifier
            - "adapter_name": adapter implementation name
            - "state": broker connection/state label
            - "simulated": whether the broker is in simulation mode
            - "live_execution_enabled": whether live execution is allowed
            - "kill_switch_active": whether the kill switch is active
            - "live_requested": whether live mode has been requested
            - "live_ready": whether live mode is ready
            - "message": additional status message
            - "healthcheck" (optional): mapping with an optional "message" field whose value will be shown as the healthcheck message if present
    """
    table = Table(title=ui_t("title.broker_status"))
    table.add_column(ui_t("label.field"))
    table.add_column(ui_t("label.value"))
    table.add_row(ui_t("label.backend"), str(payload["backend"]))
    table.add_row(ui_t("label.adapter"), str(payload["adapter_name"]))
    table.add_row(ui_t("label.state"), str(payload["state"]))
    table.add_row(ui_t("label.simulated"), str(payload["simulated"]))
    table.add_row(
        ui_t("label.live_execution_enabled"),
        str(payload["live_execution_enabled"]),
    )
    table.add_row(ui_t("label.kill_switch_active"), str(payload["kill_switch_active"]))
    table.add_row(ui_t("label.live_requested"), str(payload["live_requested"]))
    table.add_row(ui_t("label.live_ready"), str(payload["live_ready"]))
    table.add_row(ui_t("label.message"), str(payload["message"]))
    healthcheck = object_mapping(payload.get("healthcheck"))
    if healthcheck:
        table.add_row(ui_t("label.healthcheck"), str(healthcheck.get("message", "-")))
    console.print(table)


def _register_provider_readiness_commands(
    app: typer.Typer, deps: StatusCommandDeps
) -> None:
    """
    Register the provider diagnostics and v1-readiness CLI subcommands on the given Typer app.
    
    Parameters:
    	app (typer.Typer): The Typer application to attach the commands to.
    	deps (StatusCommandDeps): Dependency container used by the commands to load settings, build payloads, emit JSON, and render UI.
    
    Detailed behavior:
    	- Adds `provider-diagnostics` which builds a provider diagnostics payload and either emits it as JSON or renders provider diagnostics output.
    	- Adds `v1-readiness` which builds a v1 readiness payload (optionally performing a provider check) and either emits it as JSON or renders v1 readiness output.
    """
    @app.command("provider-diagnostics")
    def provider_diagnostics(
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
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
            help=ui_t("help.v1_provider_check"),
        ),
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
    ) -> None:
        """
        Render v1 readiness information and exit.
        
        Parameters:
            check_provider (bool): When True, include provider-level readiness checks in the evaluation.
            json_output (bool): When True, emit the readiness payload as JSON instead of rendering a UI.
        """
        settings = deps.get_settings()
        payload = deps.v1_readiness_payload(settings, check_provider=check_provider)
        if json_output:
            deps.emit_json(payload)
            return
        _render_v1_readiness(payload)


def _render_provider_diagnostics(payload: dict[str, object]) -> None:
    """
    Render a concise provider diagnostics summary and the provider source ladder to the console.
    
    Parameters:
    	payload (dict[str, object]): Diagnostics payload produced by the provider diagnostics command. Expected keys include:
    		- "llm": mapping with keys like "provider", "default_model", "base_url"
    		- "market_data": mapping with "selected_provider" and "selected_role"
    		- "news": mapping with "mode"
    		- "alpaca": mapping with "paper_endpoint", "data_feed", "credentials_configured"
    		- "providers": optional list used by the provider ladder renderer
    """
    summary = Table(title=ui_t("title.provider_diagnostics"))
    summary.add_column(ui_t("label.field"))
    summary.add_column(ui_t("label.value"))
    llm = object_mapping(payload.get("llm"))
    market_data = object_mapping(payload.get("market_data"))
    news = object_mapping(payload.get("news"))
    alpaca = object_mapping(payload.get("alpaca"))
    summary.add_row(ui_t("label.llm_provider"), str(llm.get("provider", "-")))
    summary.add_row(ui_t("label.default_model"), str(llm.get("default_model", "-")))
    summary.add_row(ui_t("label.base_url"), str(llm.get("base_url", "-")))
    summary.add_row(
        ui_t("label.market_provider"),
        str(market_data.get("selected_provider", "-")),
    )
    summary.add_row(
        ui_t("label.market_role"), str(market_data.get("selected_role", "-"))
    )
    summary.add_row(ui_t("label.news_mode"), str(news.get("mode", "-")))
    summary.add_row(
        ui_t("label.alpaca_paper_endpoint"), str(alpaca.get("paper_endpoint", "-"))
    )
    summary.add_row(ui_t("label.alpaca_feed"), str(alpaca.get("data_feed", "-")))
    summary.add_row(
        ui_t("label.alpaca_credentials_configured"),
        str(alpaca.get("credentials_configured", False)),
    )
    console.print(summary)
    _render_provider_ladder(payload)


def _render_provider_ladder(payload: dict[str, object]) -> None:
    """
    Render a table showing configured provider sources and their metadata.
    
    Parameters:
        payload (dict[str, object]): Mapping that should contain a "providers" key with a list of provider mappings. Each provider mapping may include:
            - provider_id: identifier displayed under the "provider" column
            - provider_type: provider implementation/type
            - role: provider role (e.g., market, news)
            - enabled: boolean indicating whether the provider is enabled
            - api_key_ready: API key / credential readiness indicator
            - freshness: freshness or last-updated indicator
            - notes: list of note strings to be joined and displayed in the "notes" column
    """
    provider_table = Table(title=ui_t("title.provider_source_ladder"))
    provider_table.add_column(ui_t("label.provider"))
    provider_table.add_column(ui_t("label.type"))
    provider_table.add_column(ui_t("label.role"))
    provider_table.add_column(ui_t("label.enabled"))
    provider_table.add_column(ui_t("label.api_key"))
    provider_table.add_column(ui_t("label.freshness"))
    provider_table.add_column(ui_t("label.notes"))
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
    """
    Render the v1 readiness summary and associated readiness check tables to the console.
    
    Parameters:
        payload (dict[str, object]): A mapping containing readiness information. Expected keys:
            - "summary" (str, optional): Top-line summary message displayed in the panel.
            - "paper_operations" (mapping-like, optional): Payload for paper operation readiness; must contain an "allowed" boolean-ish value and a "checks" sequence for rendering the checks table.
            - "alpaca_paper" (mapping-like, optional): Payload for Alpaca paper readiness; should contain a "checks" sequence for rendering the checks table.
    
    Behavior:
        Prints a titled panel with the summary (uses a default message if absent). The panel border is green when paper operations are allowed, yellow otherwise. Then renders two readiness-check tables: one for paper operations and one for Alpaca paper, using the respective payloads' "checks" entries.
    """
    paper = object_mapping(payload.get("paper_operations"))
    alpaca = object_mapping(payload.get("alpaca_paper"))
    paper_allowed = bool(paper.get("allowed"))
    console.print(
        Panel(
            str(
                payload.get("summary", ui_t("message.v1_readiness_status_unavailable"))
            ),
            title=ui_t("title.v1_readiness"),
            border_style="green" if paper_allowed else "yellow",
        )
    )
    _render_readiness_checks(ui_t("title.paper_operation_checks"), paper)
    _render_readiness_checks(ui_t("title.alpaca_paper_checks"), alpaca)


def _render_readiness_checks(title: str, payload: Mapping[str, object]) -> None:
    """
    Render a table of readiness checks under the given title.
    
    Parameters:
    	title (str): Table title to display above the checks.
    	payload (Mapping[str, object]): Payload containing a "checks" iterable where each item is a mapping with optional keys:
    		- "name": human-readable check name (defaults to "-")
    		- "passed": truthy if the check passed
    		- "blocking": whether the check is blocking (defaults to True)
    		- "details": additional details or message (defaults to "")
    """
    checks = payload.get("checks", [])
    table = Table(title=title)
    table.add_column(ui_t("label.check"))
    table.add_column(ui_t("label.state"))
    table.add_column(ui_t("label.blocking"))
    table.add_column(ui_t("label.details"))
    for item in object_mapping_list(checks):
        passed = bool(item.get("passed"))
        state_label = (
            f"[green]{ui_t('status.pass')}[/green]"
            if passed
            else f"[red]{ui_t('status.fail')}[/red]"
        )
        table.add_row(
            str(item.get("name", "-")),
            state_label,
            str(item.get("blocking", True)),
            str(item.get("details", "")),
        )
    console.print(table)


def _register_finance_ops_commands(app: typer.Typer, deps: StatusCommandDeps) -> None:
    """
    Register the finance-related CLI subcommands ("finance-ops" and "position-plan-repair") on the given Typer application.
    
    The "finance-ops" command builds a finance operations payload from dependencies and either emits it as JSON or renders it to the terminal depending on the `--json` flag.
    
    The "position-plan-repair" command attempts to open the database (read-only unless `--apply` is set), run a missing position-plan repair operation with a configurable `--max-holding-bars` limit, and then either emits a summary payload as JSON or renders the repair results. If the database or repair operation fails, a user-facing panel is printed and the command exits gracefully.
    
    Parameters:
        app (typer.Typer): The Typer application to register commands on.
        deps (StatusCommandDeps): Dependency container providing settings, payload builders, emitters, DB access, and renderers used by the commands.
    """
    @app.command("finance-ops")
    def finance_ops(
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
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
            help=ui_t("help.position_plan_repair_apply"),
        ),
        max_holding_bars: int = typer.Option(
            20,
            min=1,
            max=500,
            help=ui_t("help.position_plan_repair_max_holding_bars"),
        ),
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
    ) -> None:
        """
        Run the position-plan repair operation and present a summary of found or applied repairs.
        
        Parameters:
            apply_changes (bool): If True, apply repairs to the database; otherwise only identify repair candidates.
            max_holding_bars (int): Maximum number of holding bars to consider when generating repair candidates (1–500).
            json_output (bool): If True, emit the results as JSON; otherwise render human-friendly CLI output.
        
        Raises:
            typer.Exit: Exits with code 0 after printing a user-facing panel if the repair operation cannot be performed due to an exception.
        """
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
                    ui_t("message.position_plan_repair_temporarily_unavailable").format(
                        error=exc
                    ),
                    title=ui_t("label.observer_mode"),
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
