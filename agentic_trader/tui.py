import json
import time
from typing import Sequence, cast

from rich.console import Console, Group
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.text import Text
from rich.columns import Columns
from rich.align import Align

from agentic_trader.agents.operator_chat import (
    apply_preference_update,
    chat_with_persona,
    interpret_operator_instruction,
)
from agentic_trader.config import Settings, get_settings
from agentic_trader.llm.client import LocalLLM
from agentic_trader.market.data import fetch_ohlcv
from agentic_trader.market.features import build_snapshot
from agentic_trader.memory.retrieval import retrieve_similar_memories
from agentic_trader.runtime_feed import (
    read_service_events,
    read_service_state,
    request_stop,
)
from agentic_trader.runtime_status import build_runtime_status_view, is_process_alive
from agentic_trader.runtime_status import build_agent_activity_view
from agentic_trader.schemas import (
    AgentProfile,
    BehaviorPreset,
    ChatPersona,
    InvestmentPreferences,
    RiskProfile,
    ServiceEvent,
    ServiceStateSnapshot,
    TradeStyle,
)
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.workflows.run_once import persist_run, run_once
from agentic_trader.workflows.service import ensure_llm_ready, start_background_service

console = Console()


def _open_db(settings: Settings, *, read_only: bool) -> TradingDatabase:
    return TradingDatabase(settings, read_only=read_only)


def _banner() -> Panel:
    art = r"""
 █████╗  ██████╗ ███████╗███╗   ██╗████████╗██╗ ██████╗    ████████╗██████╗  █████╗ ██████╗ ███████╗██████╗
██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝██║██╔════╝    ╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗
███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   ██║██║            ██║   ██████╔╝███████║██║  ██║█████╗  ██████╔╝
██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   ██║██║            ██║   ██╔══██╗██╔══██║██║  ██║██╔══╝  ██╔══██╗
██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   ██║╚██████╗       ██║   ██║  ██║██║  ██║██████╔╝███████╗██║  ██║
╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝ ╚═════╝       ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝╚═╝  ╚═╝
"""
    subtitle = (
        "[bold cyan]Agentic Trader control room[/bold cyan]\n"
        "[dim]Strict LLM gate, saved preferences, portfolio state, recent runs, and launch controls.[/dim]"
    )
    return Panel(f"[green]{art}[/green]\n{subtitle}", border_style="bright_blue")


def _split_csv(value: str) -> list[str]:
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def _render_preferences(preferences: InvestmentPreferences) -> Table:
    table = Table(title="Investment Preferences")
    table.add_column("Setting")
    table.add_column("Value")
    table.add_row("Regions", ", ".join(preferences.regions) or "-")
    table.add_row("Exchanges", ", ".join(preferences.exchanges) or "-")
    table.add_row("Currencies", ", ".join(preferences.currencies) or "-")
    table.add_row("Sectors", ", ".join(preferences.sectors) or "-")
    table.add_row("Risk Profile", preferences.risk_profile)
    table.add_row("Trade Style", preferences.trade_style)
    table.add_row("Behavior Preset", preferences.behavior_preset)
    table.add_row("Agent Profile", preferences.agent_profile)
    table.add_row("Notes", preferences.notes or "-")
    return table


def _render_recent_runs(db: TradingDatabase) -> None:
    runs = db.list_recent_runs(limit=8)
    table = Table(title="Recent Runs")
    table.add_column("Run ID")
    table.add_column("Created")
    table.add_column("Symbol")
    table.add_column("Interval")
    table.add_column("Approved")
    if not runs:
        console.print(
            Panel("No runs recorded yet.", title="Recent Runs", border_style="yellow")
        )
        return
    for run_id, created_at, symbol, interval, approved in runs:
        table.add_row(run_id, created_at, symbol, interval, str(approved))
    console.print(table)


def _recent_runs_table(db: TradingDatabase) -> Table:
    runs = db.list_recent_runs(limit=8)
    table = Table(title="Recent Runs")
    table.add_column("Run ID")
    table.add_column("Created")
    table.add_column("Symbol")
    table.add_column("Interval")
    table.add_column("Approved")
    if not runs:
        table.add_row("-", "-", "-", "-", "-")
        return table
    for run_id, created_at, symbol, interval, approved in runs:
        table.add_row(run_id, created_at, symbol, interval, str(approved))
    return table


def _trade_journal_table(db: TradingDatabase, *, limit: int = 8) -> Table:
    entries = db.list_trade_journal(limit=limit)
    table = Table(title="Trade Journal")
    table.add_column("Opened")
    table.add_column("Symbol")
    table.add_column("Status")
    table.add_column("Side")
    table.add_column("PnL")
    if not entries:
        table.add_row("-", "-", "-", "-", "-")
        return table
    for entry in entries:
        table.add_row(
            entry.opened_at,
            entry.symbol,
            entry.journal_status,
            entry.planned_side,
            f"{entry.realized_pnl:.2f}" if entry.realized_pnl is not None else "-",
        )
    return table


def _risk_report_table(db: TradingDatabase) -> Table:
    report = db.build_daily_risk_report()
    table = Table(title=f"Risk Report / {report.report_date}")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Equity", f"{report.equity:.2f}")
    table.add_row("Gross Exposure", f"{report.gross_exposure_pct:.2%}")
    table.add_row("Largest Position", f"{report.largest_position_pct:.2%}")
    table.add_row("Drawdown From Peak", f"{report.drawdown_from_peak_pct:.2%}")
    table.add_row("Fills Today", str(report.fills_today))
    table.add_row("Warnings", str(len(report.warnings)))
    return table


def _safe_open_read_db(settings: Settings) -> TradingDatabase | None:
    state = read_service_state(settings)
    view = build_runtime_status_view(state)
    if view.live_process and view.last_recorded_state in {"starting", "running", "stopping"}:
        return None
    try:
        return TradingDatabase(settings, read_only=True)
    except Exception:
        return None


def _observer_mode_panel(feature: str, error: str | None = None) -> Panel:
    body = f"{feature} is temporarily unavailable while the runtime writer owns the database."
    if error:
        body += f"\n\n{error}"
    return Panel(body, title="Observer Mode", border_style="yellow")


def _render_runtime_state(state: ServiceStateSnapshot | None) -> None:
    view = build_runtime_status_view(state)
    if view.state is None:
        console.print(
            Panel(
                "No runtime state recorded yet.",
                title="Runtime Status",
                border_style="yellow",
            )
        )
        return
    snapshot = view.state

    table = Table(title="Runtime Status")
    table.add_column("Key")
    table.add_column("Value")
    table.add_row("Runtime", view.runtime_state)
    table.add_row("Live Process", "yes" if view.live_process else "no")
    table.add_row("Last Recorded State", view.last_recorded_state or "-")
    table.add_row("Updated", snapshot.updated_at)
    table.add_row("Heartbeat", snapshot.last_heartbeat_at or "-")
    table.add_row(
        "Heartbeat Age", f"{view.age_seconds}s" if view.age_seconds is not None else "-"
    )
    table.add_row("Cycle Count", str(snapshot.cycle_count))
    table.add_row("Current Symbol", snapshot.current_symbol or "-")
    table.add_row("PID", str(snapshot.pid) if snapshot.pid is not None else "-")
    table.add_row("Stop Requested", str(snapshot.stop_requested))
    table.add_row("Continuous", str(snapshot.continuous))
    table.add_row("Background Mode", str(snapshot.background_mode))
    table.add_row("Launch Count", str(snapshot.launch_count))
    table.add_row("Restart Count", str(snapshot.restart_count))
    table.add_row("Last Terminal State", snapshot.last_terminal_state or "-")
    table.add_row("Last Terminal At", snapshot.last_terminal_at or "-")
    table.add_row("Status Note", view.status_message)
    table.add_row("Last Recorded Message", snapshot.message or "-")
    table.add_row("Last Recorded Error", snapshot.last_error or "-")
    console.print(table)


def _render_runtime_events(events: list[ServiceEvent]) -> None:
    if not events:
        console.print(
            Panel(
                "No runtime events recorded yet.",
                title="Runtime Events",
                border_style="yellow",
            )
        )
        return
    table = Table(title="Runtime Events")
    table.add_column("Created")
    table.add_column("Level")
    table.add_column("Type")
    table.add_column("Cycle")
    table.add_column("Symbol")
    for event in events:
        table.add_row(
            event.created_at,
            event.level,
            event.event_type,
            str(event.cycle_count) if event.cycle_count is not None else "-",
            event.symbol or "-",
        )
    console.print(table)


def _runtime_events_table(events: list[ServiceEvent]) -> Table:
    table = Table(title="Runtime Events")
    table.add_column("Created")
    table.add_column("Level")
    table.add_column("Type")
    table.add_column("Cycle")
    table.add_column("Symbol")
    if not events:
        table.add_row("-", "-", "-", "-", "-")
        return table
    for event in events:
        table.add_row(
            event.created_at,
            event.level,
            event.event_type,
            str(event.cycle_count) if event.cycle_count is not None else "-",
            event.symbol or "-",
        )
    return table


def _agent_activity_table(events: list[ServiceEvent]) -> Table:
    table = Table(title="Live Agent Activity")
    table.add_column("Stage")
    table.add_column("Status")
    table.add_column("Message")
    activity = build_agent_activity_view(None, events)
    if not activity.stage_statuses:
        table.add_row("-", "-", "No live agent stage events yet.")
        return table
    for stage in activity.stage_statuses:
        table.add_row(stage.stage, stage.status, stage.message)
    return table


def _current_activity_panel(
    state: ServiceStateSnapshot | None, events: list[ServiceEvent]
) -> Panel:
    view = build_runtime_status_view(state)
    activity = build_agent_activity_view(state, events)
    lines = [
        f"Runtime: {view.runtime_state}",
        f"Current Symbol: {view.state.current_symbol if view.state is not None and view.state.current_symbol else '-'}",
        f"Cycle: {view.state.cycle_count if view.state is not None else '-'}",
        f"Current Note: {view.state.message if view.state is not None and view.state.message else '-'}",
        "",
        f"Current Stage: {activity.current_stage or '-'}",
        f"Stage Status: {activity.current_stage_status or '-'}",
        f"Stage Message: {activity.current_stage_message or 'No agent activity recorded yet.'}",
        f"Last Completed Stage: {activity.last_completed_stage or '-'}",
        f"Completed Note: {activity.last_completed_message or '-'}",
    ]
    if activity.last_outcome_message is not None:
        lines.extend(
            [
                "",
                f"Last Outcome Type: {activity.last_outcome_type or '-'}",
                f"Last Outcome: {activity.last_outcome_message}",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "Last Outcome: Waiting for a completed symbol, exit, or service result.",
            ]
        )
    return Panel("\n".join(lines), title="Current Cycle", border_style="bright_cyan")


def _runtime_state_table(state: ServiceStateSnapshot | None) -> Table:
    table = Table(title="Runtime Status")
    table.add_column("Key")
    table.add_column("Value")
    view = build_runtime_status_view(state)
    if view.state is None:
        table.add_row("State", "no runtime state recorded yet")
        return table
    snapshot = view.state
    table.add_row("Runtime", view.runtime_state)
    table.add_row("Live Process", "yes" if view.live_process else "no")
    table.add_row("Last Recorded State", view.last_recorded_state or "-")
    table.add_row("Updated", snapshot.updated_at)
    table.add_row("Heartbeat", snapshot.last_heartbeat_at or "-")
    table.add_row(
        "Heartbeat Age", f"{view.age_seconds}s" if view.age_seconds is not None else "-"
    )
    table.add_row("Cycle Count", str(snapshot.cycle_count))
    table.add_row("Current Symbol", snapshot.current_symbol or "-")
    table.add_row("PID", str(snapshot.pid) if snapshot.pid is not None else "-")
    table.add_row("Stop Requested", str(snapshot.stop_requested))
    table.add_row("Continuous", str(snapshot.continuous))
    table.add_row("Background Mode", str(snapshot.background_mode))
    table.add_row("Launch Count", str(snapshot.launch_count))
    table.add_row("Restart Count", str(snapshot.restart_count))
    table.add_row("Last Terminal State", snapshot.last_terminal_state or "-")
    table.add_row("Last Terminal At", snapshot.last_terminal_at or "-")
    table.add_row("Status Note", view.status_message)
    table.add_row("Last Recorded Message", snapshot.message or "-")
    table.add_row("Last Recorded Error", snapshot.last_error or "-")
    return table


def _system_status_table(settings: Settings, db: TradingDatabase | None) -> Table:
    health = LocalLLM(settings).health_check()
    latest_order = db.latest_order() if db is not None else None
    table = Table(title="System Status")
    table.add_column("Key")
    table.add_column("Value")
    table.add_row("Runtime Dir", str(settings.runtime_dir))
    table.add_row("Model", settings.model_name)
    table.add_row("Base URL", settings.base_url)
    table.add_row("Ollama Reachable", "yes" if health.service_reachable else "no")
    table.add_row("Model Available", "yes" if health.model_available else "no")
    table.add_row("Strict LLM", str(settings.strict_llm))
    if db is not None:
        table.add_row(
            "Latest Order", latest_order[0] if latest_order is not None else "-"
        )
    return table


def _portfolio_renderable(db: TradingDatabase) -> Group:
    snapshot = db.get_account_snapshot()
    summary = Table(title="Portfolio")
    summary.add_column("Metric")
    summary.add_column("Value")
    summary.add_row("Cash", f"{snapshot.cash:.2f}")
    summary.add_row("Market Value", f"{snapshot.market_value:.2f}")
    summary.add_row("Equity", f"{snapshot.equity:.2f}")
    summary.add_row("Realized PnL", f"{snapshot.realized_pnl:.2f}")
    summary.add_row("Unrealized PnL", f"{snapshot.unrealized_pnl:.2f}")
    summary.add_row("Open Positions", str(snapshot.open_positions))

    positions = db.list_positions()
    positions_table = Table(title="Positions")
    positions_table.add_column("Symbol")
    positions_table.add_column("Quantity")
    positions_table.add_column("Average Price")
    positions_table.add_column("Market Price")
    positions_table.add_column("Market Value")
    positions_table.add_column("Unrealized PnL")
    if not positions:
        positions_table.add_row("-", "-", "-", "-", "-", "-")
    else:
        for position in positions:
            positions_table.add_row(
                position.symbol,
                f"{position.quantity:.6f}",
                f"{position.average_price:.4f}",
                f"{position.market_price:.4f}",
                f"{position.market_value:.2f}",
                f"{position.unrealized_pnl:.2f}",
            )
    return Group(summary, positions_table)


def build_monitor_renderable(
    settings: Settings, db: TradingDatabase | None = None
) -> Group:
    db = db if db is not None else _safe_open_read_db(settings)
    runtime_state = read_service_state(settings)
    events = read_service_events(settings, limit=20)
    header = Panel(
        Text("Agentic Trader Live Monitor", style="bold cyan"),
        subtitle="Ctrl+C to return",
        border_style="bright_blue",
    )
    top = Columns(
        [
            _current_activity_panel(runtime_state, events),
            Panel(_agent_activity_table(events), border_style="bright_magenta"),
        ],
        equal=True,
        expand=True,
    )
    middle = Columns(
        [
            Panel(_runtime_state_table(runtime_state), border_style="magenta"),
            Panel(_system_status_table(settings, db), border_style="cyan"),
        ],
        equal=True,
        expand=True,
    )
    bottom = Columns(
        [
            (
                Panel(_render_preferences(db.load_preferences()), border_style="green")
                if db is not None
                else _observer_mode_panel("Preferences")
            ),
            (
                Panel(_portfolio_renderable(db), border_style="yellow")
                if db is not None
                else _observer_mode_panel("Portfolio")
            ),
        ],
        equal=True,
        expand=True,
    )
    footer = Columns(
        [
            (
                Panel(
                    Group(_recent_runs_table(db), _trade_journal_table(db, limit=5)),
                    border_style="white",
                )
                if db is not None
                else _observer_mode_panel("Run review and trade journal")
            ),
            Panel(_runtime_events_table(events), border_style="bright_blue"),
        ],
        equal=True,
        expand=True,
    )
    extra = (
        Panel(_risk_report_table(db), border_style="red")
        if db is not None
        else _observer_mode_panel("Risk report")
    )
    return Group(header, top, middle, bottom, footer, extra)


def run_live_monitor(
    settings: Settings,
    db: TradingDatabase | None = None,
    *,
    refresh_seconds: float = 1.0,
) -> None:
    with Live(
        build_monitor_renderable(settings, db),
        console=console,
        refresh_per_second=max(
            1, int(1 / refresh_seconds) if refresh_seconds < 1 else 1
        ),
        screen=True,
    ) as live:
        try:
            while True:
                live.update(build_monitor_renderable(settings, db))
                time.sleep(refresh_seconds)
        except KeyboardInterrupt:
            return


def _render_status(settings: Settings, db: TradingDatabase | None) -> None:
    health = LocalLLM(settings).health_check()
    status = Table(title="System Status")
    status.add_column("Key")
    status.add_column("Value")
    status.add_row("Runtime Dir", str(settings.runtime_dir))
    status.add_row("Database", str(settings.database_path))
    status.add_row("Model", settings.model_name)
    status.add_row("Base URL", settings.base_url)
    status.add_row("Ollama Reachable", "yes" if health.service_reachable else "no")
    status.add_row("Model Available", "yes" if health.model_available else "no")
    status.add_row("Strict LLM", str(settings.strict_llm))
    console.print(status)
    _render_runtime_state(read_service_state(settings))
    console.print(
        _current_activity_panel(
            read_service_state(settings), read_service_events(settings, limit=12)
        )
    )
    if db is None:
        console.print(_observer_mode_panel("Preferences and portfolio-backed views"))
    else:
        console.print(_render_preferences(db.load_preferences()))
        _render_recent_runs(db)
    _render_runtime_events(read_service_events(settings, limit=6))


def _configure_preferences(db: TradingDatabase) -> None:
    current = db.load_preferences()
    console.print(_render_preferences(current))
    regions = Prompt.ask(
        "Regions (comma-separated)", default=", ".join(current.regions)
    )
    exchanges = Prompt.ask(
        "Exchanges (comma-separated)", default=", ".join(current.exchanges)
    )
    currencies = Prompt.ask(
        "Currencies (comma-separated)", default=", ".join(current.currencies)
    )
    sectors = Prompt.ask(
        "Sectors (comma-separated, optional)",
        default=", ".join(current.sectors),
    )
    risk_profile = Prompt.ask(
        "Risk profile",
        choices=["conservative", "balanced", "aggressive"],
        default=current.risk_profile,
    )
    trade_style = Prompt.ask(
        "Trade style",
        choices=["swing", "position", "intraday"],
        default=current.trade_style,
    )
    behavior_preset = Prompt.ask(
        "Behavior preset",
        choices=["balanced_core", "trend_biased", "contrarian", "capital_preservation"],
        default=current.behavior_preset,
    )
    agent_profile = Prompt.ask(
        "Agent profile",
        choices=["neutral", "disciplined", "aggressive", "explanatory"],
        default=current.agent_profile,
    )
    notes = Prompt.ask("Notes", default=current.notes)
    updated = InvestmentPreferences(
        regions=_split_csv(regions) or current.regions,
        exchanges=_split_csv(exchanges) or current.exchanges,
        currencies=_split_csv(currencies) or current.currencies,
        sectors=_split_csv(sectors),
        risk_profile=cast(RiskProfile, risk_profile),
        trade_style=cast(TradeStyle, trade_style),
        behavior_preset=cast(BehaviorPreset, behavior_preset),
        agent_profile=cast(AgentProfile, agent_profile),
        notes=notes,
    )
    db.save_preferences(updated)
    console.print(Panel("Preferences saved.", title="Saved", border_style="green"))


def _show_portfolio(db: TradingDatabase) -> None:
    snapshot = db.get_account_snapshot()
    summary = Table(title="Portfolio")
    summary.add_column("Metric")
    summary.add_column("Value")
    summary.add_row("Cash", f"{snapshot.cash:.2f}")
    summary.add_row("Market Value", f"{snapshot.market_value:.2f}")
    summary.add_row("Equity", f"{snapshot.equity:.2f}")
    summary.add_row("Realized PnL", f"{snapshot.realized_pnl:.2f}")
    summary.add_row("Unrealized PnL", f"{snapshot.unrealized_pnl:.2f}")
    summary.add_row("Open Positions", str(snapshot.open_positions))
    console.print(summary)
    positions = db.list_positions()
    if not positions:
        console.print(
            Panel("No open positions.", title="Positions", border_style="yellow")
        )
        return
    table = Table(title="Positions")
    table.add_column("Symbol")
    table.add_column("Quantity")
    table.add_column("Average Price")
    table.add_column("Market Price")
    table.add_column("Market Value")
    table.add_column("Unrealized PnL")
    for position in positions:
        table.add_row(
            position.symbol,
            f"{position.quantity:.6f}",
            f"{position.average_price:.4f}",
            f"{position.market_price:.4f}",
            f"{position.market_value:.2f}",
            f"{position.unrealized_pnl:.2f}",
        )
    console.print(table)
    console.print(_risk_report_table(db))


def _show_trade_journal(db: TradingDatabase) -> None:
    console.print(_trade_journal_table(db, limit=20))


def _show_risk_report(db: TradingDatabase) -> None:
    console.print(_risk_report_table(db))


def _show_latest_run_review(db: TradingDatabase) -> None:
    record = db.latest_run()
    if record is None:
        console.print(
            Panel(
                "No persisted runs are available to review.",
                title="Run Review",
                border_style="yellow",
            )
        )
        return
    console.print(
        Panel(
            record.artifacts.model_dump_json(indent=2),
            title=f"Latest Run Review / {record.run_id}",
            border_style="cyan",
        )
    )


def _show_memory_explorer(settings: Settings, db: TradingDatabase) -> None:
    symbol = Prompt.ask("Symbol", default="AAPL").strip().upper()
    interval = Prompt.ask("Interval", default="1d")
    lookback = Prompt.ask("Lookback", default="180d")
    limit = IntPrompt.ask("Matches", default=5)
    frame = fetch_ohlcv(symbol, interval=interval, lookback=lookback)
    snapshot = build_snapshot(frame, symbol=symbol, interval=interval)
    matches = retrieve_similar_memories(db, snapshot, limit=limit)

    table = Table(title="Memory Explorer")
    table.add_column("Created")
    table.add_column("Symbol")
    table.add_column("Score")
    table.add_column("Regime")
    table.add_column("Strategy")
    table.add_column("Bias")
    if not matches:
        table.add_row("-", "-", "-", "-", "-", "-")
    else:
        for match in matches:
            table.add_row(
                match.created_at,
                match.symbol,
                f"{match.similarity_score:.2f}",
                match.regime,
                match.strategy_family,
                match.manager_bias,
            )
    console.print(table)


def _show_latest_run_trace(db: TradingDatabase) -> None:
    record = db.latest_run()
    if record is None:
        console.print(
            Panel(
                "No persisted runs are available to trace.",
                title="Trace Viewer",
                border_style="yellow",
            )
        )
        return
    table = Table(title=f"Agent Trace / {record.run_id}")
    table.add_column("Role")
    table.add_column("Model")
    table.add_column("Fallback")
    for trace in record.artifacts.agent_traces:
        table.add_row(trace.role, trace.model_name, str(trace.used_fallback))
    console.print(table)


def _chat_screen(settings: Settings, db: TradingDatabase) -> None:
    ensure_llm_ready(settings)
    llm = LocalLLM(settings)
    persona = cast(
        ChatPersona,
        Prompt.ask(
            "Chat persona",
            choices=[
                "operator_liaison",
                "regime_analyst",
                "strategy_selector",
                "risk_steward",
                "portfolio_manager",
            ],
            default="operator_liaison",
        ),
    )
    transcript: list[tuple[str, str]] = []
    while True:
        console.clear()
        console.print(_banner())
        console.print(
            Panel(
                "Type /exit to leave chat.",
                title=f"Chat / {persona}",
                border_style="cyan",
            )
        )
        for role, message in transcript[-8:]:
            border = "bright_blue" if role == "operator" else "green"
            console.print(Panel(message, title=role, border_style=border))
        user_message = Prompt.ask("You")
        if user_message.strip().lower() in {"/exit", "exit", "quit"}:
            return
        transcript.append(("operator", user_message))
        response = chat_with_persona(
            llm=llm,
            db=db,
            settings=settings,
            persona=persona,
            user_message=user_message,
        )
        transcript.append((persona, response))


def _instruction_screen(settings: Settings, db: TradingDatabase) -> None:
    ensure_llm_ready(settings)
    llm = LocalLLM(settings)
    message = Prompt.ask("Instruction")
    instruction = interpret_operator_instruction(
        llm=llm,
        db=db,
        settings=settings,
        user_message=message,
        allow_fallback=True,
    )
    console.print(
        Panel(
            instruction.model_dump_json(indent=2),
            title="Parsed Operator Instruction",
            border_style="cyan",
        )
    )
    if instruction.should_update_preferences and Confirm.ask(
        "Apply preference update?", default=False
    ):
        updated = apply_preference_update(db, instruction.preference_update)
        console.print(
            Panel(
                updated.model_dump_json(indent=2),
                title="Updated Preferences",
                border_style="green",
            )
        )


def _strict_one_shot(
    settings: Settings, symbols: Sequence[str], interval: str, lookback: str
) -> None:
    ensure_llm_ready(settings)
    for symbol in symbols:
        latest_message = f"Preparing {symbol}."
        with console.status(
            f"[bold cyan]{latest_message}[/bold cyan]", spinner="dots"
        ) as status:

            def _progress(stage: str, event: str, message: str) -> None:
                nonlocal latest_message
                latest_message = f"[{stage}] {message}"
                status.update(f"[bold cyan]{latest_message}[/bold cyan]")

            artifacts = run_once(
                settings=settings,
                symbol=symbol,
                interval=interval,
                lookback=lookback,
                allow_fallback=False,
                progress_callback=_progress,
            )
        order_id = persist_run(settings=settings, artifacts=artifacts)
        console.print(
            Panel(
                f"Final stage update: {latest_message}\n\n{json.dumps(artifacts.model_dump(mode='json'), indent=2)}",
                title=f"Run Completed: {symbol} / {order_id}",
                border_style="green",
            )
        )


def _launch_service(
    settings: Settings, symbols: Sequence[str], interval: str, lookback: str
) -> None:
    continuous = Confirm.ask("Continuous mode?", default=False)
    poll_seconds = IntPrompt.ask(
        "Poll interval seconds",
        default=settings.default_poll_seconds,
    )
    max_cycles = None
    if continuous:
        max_cycles_input = Prompt.ask("Max cycles (blank for infinite)", default="")
        max_cycles = int(max_cycles_input) if max_cycles_input.strip() else None
    pid = start_background_service(
        settings=settings,
        symbols=list(symbols),
        interval=interval,
        lookback=lookback,
        poll_seconds=poll_seconds,
        continuous=continuous,
        max_cycles=max_cycles,
    )
    console.print(
        Panel(
            f"Service spawned in the background with PID {pid}.\n\n"
            "The control room stays responsive. Open the live monitor to watch progress or request a stop at any time.",
            title="Service Spawned",
            border_style="green",
        )
    )
    if Confirm.ask("Open live monitor now?", default=True):
        run_live_monitor(settings, refresh_seconds=1.0)


def _runtime_menu(settings: Settings) -> None:
    while True:
        console.clear()
        console.print(_banner())
        table = Table(title="Runtime Control")
        table.add_column("Key", style="bold cyan")
        table.add_column("Action")
        table.add_row("1", "Doctor and system checks")
        table.add_row("2", "Start one strict agent cycle")
        table.add_row("3", "Start orchestrator service")
        table.add_row("4", "Request orchestrator stop")
        table.add_row("5", "Open live monitor")
        table.add_row("6", "Back")
        console.print(table)
        choice = Prompt.ask(
            "Select action", choices=["1", "2", "3", "4", "5", "6"], default="1"
        )
        if choice == "1":
            db = _safe_open_read_db(settings)
            try:
                _render_status(settings, db)
            finally:
                if db is not None:
                    db.close()
        elif choice == "2":
            db = _safe_open_read_db(settings)
            try:
                if db is None:
                    console.print(
                        Panel(
                            "Preferences are temporarily unavailable while the runtime writer owns the database.",
                            title="Observer Mode",
                            border_style="yellow",
                        )
                    )
                    Prompt.ask("Press Enter to continue", default="")
                    continue
                prefs = db.load_preferences()
            finally:
                if db is not None:
                    db.close()
            default_symbols = "AAPL,MSFT" if "US" in prefs.regions else "BTC-USD"
            symbols = _split_csv(Prompt.ask("Symbols", default=default_symbols))
            interval = Prompt.ask("Interval", default="1d")
            lookback = Prompt.ask("Lookback", default="180d")
            _strict_one_shot(settings, symbols, interval, lookback)
        elif choice == "3":
            symbols = _split_csv(Prompt.ask("Symbols", default="AAPL,MSFT"))
            interval = Prompt.ask("Interval", default="1d")
            lookback = Prompt.ask("Lookback", default="180d")
            _launch_service(settings, symbols, interval, lookback)
        elif choice == "4":
            state = read_service_state(settings)
            if state is None or state.pid is None:
                console.print(
                    Panel(
                        "No managed service is currently active.",
                        title="Not Running",
                        border_style="yellow",
                    )
                )
            elif not is_process_alive(state.pid):
                console.print(
                    Panel(
                        f"PID {state.pid} is no longer alive. The next start will recover the stale runtime state automatically.",
                        title="Stale Runtime",
                        border_style="yellow",
                    )
                )
            else:
                request_stop(settings)
                try:
                    db = _open_db(settings, read_only=False)
                    try:
                        db.request_stop_service()
                    finally:
                        db.close()
                except Exception:
                    pass
                console.print(
                    Panel(
                        f"Stop requested for PID {state.pid}.",
                        title="Stop Requested",
                        border_style="yellow",
                    )
                )
        elif choice == "5":
            refresh_seconds = float(Prompt.ask("Refresh seconds", default="1.0"))
            run_live_monitor(settings, refresh_seconds=refresh_seconds)
        else:
            return
        Prompt.ask("Press Enter to continue", default="")


def _operator_menu(settings: Settings) -> None:
    while True:
        console.clear()
        console.print(_banner())
        table = Table(title="Operator Desk")
        table.add_column("Key", style="bold cyan")
        table.add_column("Action")
        table.add_row("1", "Open operator chat")
        table.add_row("2", "Parse operator instruction")
        table.add_row("3", "Back")
        console.print(table)
        choice = Prompt.ask("Select action", choices=["1", "2", "3"], default="1")
        if choice == "1":
            db = _safe_open_read_db(settings)
            if db is None:
                console.print(_observer_mode_panel("Operator chat memory context"))
            else:
                try:
                    _chat_screen(settings, db)
                finally:
                    db.close()
        elif choice == "2":
            try:
                db = _open_db(settings, read_only=False)
            except Exception as exc:
                console.print(_observer_mode_panel("Instruction application", str(exc)))
                Prompt.ask("Press Enter to continue", default="")
                continue
            try:
                _instruction_screen(settings, db)
            finally:
                db.close()
        else:
            return


def _portfolio_menu(settings: Settings) -> None:
    while True:
        console.clear()
        table = Table(title="Portfolio And Risk")
        table.add_column("Key", style="bold cyan")
        table.add_column("Action")
        table.add_row("1", "Show paper portfolio")
        table.add_row("2", "Show trade journal")
        table.add_row("3", "Show daily risk report")
        table.add_row("4", "Back")
        console.print(table)
        choice = Prompt.ask("Select action", choices=["1", "2", "3", "4"], default="1")
        if choice == "1":
            db = _safe_open_read_db(settings)
            if db is None:
                console.print(_observer_mode_panel("Paper portfolio"))
            else:
                try:
                    _show_portfolio(db)
                finally:
                    db.close()
        elif choice == "2":
            db = _safe_open_read_db(settings)
            if db is None:
                console.print(_observer_mode_panel("Trade journal"))
            else:
                try:
                    _show_trade_journal(db)
                finally:
                    db.close()
        elif choice == "3":
            db = _safe_open_read_db(settings)
            if db is None:
                console.print(_observer_mode_panel("Daily risk report"))
            else:
                try:
                    _show_risk_report(db)
                finally:
                    db.close()
        else:
            return
        Prompt.ask("Press Enter to continue", default="")


def _research_menu(settings: Settings) -> None:
    while True:
        console.clear()
        table = Table(title="Research And Memory")
        table.add_column("Key", style="bold cyan")
        table.add_column("Action")
        table.add_row("1", "Open memory explorer")
        table.add_row("2", "Show recent runs and events")
        table.add_row("3", "Back")
        console.print(table)
        choice = Prompt.ask("Select action", choices=["1", "2", "3"], default="1")
        if choice == "1":
            db = _safe_open_read_db(settings)
            if db is None:
                console.print(_observer_mode_panel("Memory explorer"))
            else:
                try:
                    _show_memory_explorer(settings, db)
                finally:
                    db.close()
        elif choice == "2":
            db = _safe_open_read_db(settings)
            try:
                if db is None:
                    console.print(_observer_mode_panel("Recent runs"))
                else:
                    _render_recent_runs(db)
                _render_runtime_events(read_service_events(settings, limit=6))
            finally:
                if db is not None:
                    db.close()
        else:
            return
        Prompt.ask("Press Enter to continue", default="")


def _review_menu(settings: Settings) -> None:
    while True:
        console.clear()
        table = Table(title="Review And Trace")
        table.add_column("Key", style="bold cyan")
        table.add_column("Action")
        table.add_row("1", "Inspect latest run review")
        table.add_row("2", "Inspect latest run trace")
        table.add_row("3", "Back")
        console.print(table)
        choice = Prompt.ask("Select action", choices=["1", "2", "3"], default="1")
        if choice == "1":
            db = _safe_open_read_db(settings)
            if db is None:
                console.print(_observer_mode_panel("Latest run review"))
            else:
                try:
                    _show_latest_run_review(db)
                finally:
                    db.close()
        elif choice == "2":
            db = _safe_open_read_db(settings)
            if db is None:
                console.print(_observer_mode_panel("Latest run trace"))
            else:
                try:
                    _show_latest_run_trace(db)
                finally:
                    db.close()
        else:
            return
        Prompt.ask("Press Enter to continue", default="")


def run_main_menu() -> None:
    settings = get_settings()
    settings.ensure_directories()

    while True:
        console.clear()
        console.print(_banner())
        db = _safe_open_read_db(settings)
        try:
            _render_status(settings, db)
        finally:
            if db is not None:
                db.close()
        menu = Table(title="Main Menu")
        menu.add_column("Key", style="bold cyan")
        menu.add_column("Action")
        menu.add_row("1", "Configure investment preferences")
        menu.add_row("2", "Runtime control")
        menu.add_row("3", "Operator desk")
        menu.add_row("4", "Portfolio and risk")
        menu.add_row("5", "Research and memory")
        menu.add_row("6", "Review and trace")
        menu.add_row("7", "Exit")
        console.print(menu)

        choice = Prompt.ask(
            "Select action", choices=["1", "2", "3", "4", "5", "6", "7"], default="2"
        )
        try:
            if choice == "1":
                try:
                    db = _open_db(settings, read_only=False)
                except Exception as exc:
                    console.print(_observer_mode_panel("Preference editing", str(exc)))
                    Prompt.ask("Press Enter to continue", default="")
                    continue
                try:
                    _configure_preferences(db)
                finally:
                    db.close()
            elif choice == "2":
                _runtime_menu(settings)
            elif choice == "3":
                _operator_menu(settings)
            elif choice == "4":
                _portfolio_menu(settings)
            elif choice == "5":
                _research_menu(settings)
            elif choice == "6":
                _review_menu(settings)
            else:
                console.print(
                    Panel("Leaving control room.", title="Exit", border_style="blue")
                )
                return
        except KeyboardInterrupt:
            console.print(
                Panel(
                    "Action cancelled. Returning to the control room.",
                    title="Cancelled",
                    border_style="yellow",
                )
            )
        except Exception as exc:
            console.print(Panel(str(exc), title="Action Failed", border_style="red"))
        Prompt.ask("Press Enter to continue", default="")
