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

from agentic_trader.agents.operator_chat import apply_preference_update, chat_with_persona, interpret_operator_instruction
from agentic_trader.config import Settings, get_settings
from agentic_trader.llm.client import LocalLLM
from agentic_trader.market.data import fetch_ohlcv
from agentic_trader.market.features import build_snapshot
from agentic_trader.memory.retrieval import retrieve_similar_memories
from agentic_trader.schemas import AgentProfile, BehaviorPreset, ChatPersona, InvestmentPreferences, RiskProfile, ServiceEvent, ServiceStateSnapshot, TradeStyle
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.workflows.run_once import persist_run, run_once
from agentic_trader.workflows.service import ensure_llm_ready, run_service, start_background_service

console = Console()


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
        console.print(Panel("No runs recorded yet.", title="Recent Runs", border_style="yellow"))
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


def _render_runtime_state(state: ServiceStateSnapshot | None) -> None:
    if state is None:
        console.print(Panel("No runtime state recorded yet.", title="Runtime Status", border_style="yellow"))
        return

    table = Table(title="Runtime Status")
    table.add_column("Key")
    table.add_column("Value")
    table.add_row("State", state.state)
    table.add_row("Updated", state.updated_at)
    table.add_row("Heartbeat", state.last_heartbeat_at or "-")
    table.add_row("Cycle Count", str(state.cycle_count))
    table.add_row("Current Symbol", state.current_symbol or "-")
    table.add_row("PID", str(state.pid) if state.pid is not None else "-")
    table.add_row("Stop Requested", str(state.stop_requested))
    table.add_row("Continuous", str(state.continuous))
    table.add_row("Message", state.message or "-")
    table.add_row("Last Error", state.last_error or "-")
    console.print(table)


def _render_runtime_events(events: list[ServiceEvent]) -> None:
    if not events:
        console.print(Panel("No runtime events recorded yet.", title="Runtime Events", border_style="yellow"))
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


def _runtime_state_table(state: ServiceStateSnapshot | None) -> Table:
    table = Table(title="Runtime Status")
    table.add_column("Key")
    table.add_column("Value")
    if state is None:
        table.add_row("State", "no runtime state recorded yet")
        return table
    table.add_row("State", state.state)
    table.add_row("Updated", state.updated_at)
    table.add_row("Heartbeat", state.last_heartbeat_at or "-")
    table.add_row("Cycle Count", str(state.cycle_count))
    table.add_row("Current Symbol", state.current_symbol or "-")
    table.add_row("PID", str(state.pid) if state.pid is not None else "-")
    table.add_row("Stop Requested", str(state.stop_requested))
    table.add_row("Continuous", str(state.continuous))
    table.add_row("Message", state.message or "-")
    table.add_row("Last Error", state.last_error or "-")
    return table


def _system_status_table(settings: Settings, db: TradingDatabase) -> Table:
    health = LocalLLM(settings).health_check()
    latest_order = db.latest_order()
    table = Table(title="System Status")
    table.add_column("Key")
    table.add_column("Value")
    table.add_row("Runtime Dir", str(settings.runtime_dir))
    table.add_row("Database", str(settings.database_path))
    table.add_row("Model", settings.model_name)
    table.add_row("Routing", json.dumps(settings.model_routing(), indent=2))
    table.add_row("Base URL", settings.base_url)
    table.add_row("Ollama Reachable", "yes" if health.service_reachable else "no")
    table.add_row("Model Available", "yes" if health.model_available else "no")
    table.add_row("Strict LLM", str(settings.strict_llm))
    table.add_row("Latest Order", latest_order[0] if latest_order is not None else "-")
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


def build_monitor_renderable(settings: Settings, db: TradingDatabase) -> Group:
    header = Panel(
        Text("Agentic Trader Live Monitor", style="bold cyan"),
        subtitle="Ctrl+C to return",
        border_style="bright_blue",
    )
    top = Columns(
        [
            Panel(_system_status_table(settings, db), border_style="cyan"),
            Panel(_runtime_state_table(db.get_service_state()), border_style="magenta"),
        ],
        equal=True,
        expand=True,
    )
    middle = Columns(
        [
            Panel(_render_preferences(db.load_preferences()), border_style="green"),
            Panel(_portfolio_renderable(db), border_style="yellow"),
        ],
        equal=True,
        expand=True,
    )
    bottom = Columns(
        [
            Panel(_runtime_events_table(db.list_service_events(limit=10)), border_style="bright_blue"),
            Panel(Group(_recent_runs_table(db), _trade_journal_table(db, limit=5)), border_style="white"),
        ],
        equal=True,
        expand=True,
    )
    footer = Columns(
        [
            Panel(_risk_report_table(db), border_style="red"),
            Panel(Align.center(Text("Live service attach surface for runtime, portfolio, journal, and recent activity.", style="dim")), border_style="bright_black"),
        ],
        equal=True,
        expand=True,
    )
    return Group(header, top, middle, bottom, footer)


def run_live_monitor(settings: Settings, db: TradingDatabase, *, refresh_seconds: float = 1.0) -> None:
    with Live(build_monitor_renderable(settings, db), console=console, refresh_per_second=max(1, int(1 / refresh_seconds) if refresh_seconds < 1 else 1), screen=True) as live:
        try:
            while True:
                live.update(build_monitor_renderable(settings, db))
                time.sleep(refresh_seconds)
        except KeyboardInterrupt:
            return


def _render_status(settings: Settings, db: TradingDatabase) -> None:
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
    _render_runtime_state(db.get_service_state())
    console.print(_render_preferences(db.load_preferences()))
    _render_recent_runs(db)
    _render_runtime_events(db.list_service_events(limit=6))


def _configure_preferences(db: TradingDatabase) -> None:
    current = db.load_preferences()
    console.print(_render_preferences(current))
    regions = Prompt.ask("Regions (comma-separated)", default=", ".join(current.regions))
    exchanges = Prompt.ask("Exchanges (comma-separated)", default=", ".join(current.exchanges))
    currencies = Prompt.ask("Currencies (comma-separated)", default=", ".join(current.currencies))
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
        console.print(Panel("No open positions.", title="Positions", border_style="yellow"))
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
        console.print(Panel("No persisted runs are available to review.", title="Run Review", border_style="yellow"))
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


def _chat_screen(settings: Settings, db: TradingDatabase) -> None:
    ensure_llm_ready(settings)
    llm = LocalLLM(settings)
    persona = cast(
        ChatPersona,
        Prompt.ask(
            "Chat persona",
            choices=["operator_liaison", "regime_analyst", "strategy_selector", "risk_steward", "portfolio_manager"],
            default="operator_liaison",
        ),
    )
    transcript: list[tuple[str, str]] = []
    while True:
        console.clear()
        console.print(_banner())
        console.print(Panel("Type /exit to leave chat.", title=f"Chat / {persona}", border_style="cyan"))
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
    if instruction.should_update_preferences and Confirm.ask("Apply preference update?", default=False):
        updated = apply_preference_update(db, instruction.preference_update)
        console.print(
            Panel(
                updated.model_dump_json(indent=2),
                title="Updated Preferences",
                border_style="green",
            )
        )


def _strict_one_shot(settings: Settings, symbols: Sequence[str], interval: str, lookback: str) -> None:
    ensure_llm_ready(settings)
    for symbol in symbols:
        artifacts = run_once(
            settings=settings,
            symbol=symbol,
            interval=interval,
            lookback=lookback,
            allow_fallback=False,
        )
        order_id = persist_run(settings=settings, artifacts=artifacts)
        console.print(
            Panel(
                json.dumps(artifacts.model_dump(mode="json"), indent=2),
                title=f"Run Completed: {symbol} / {order_id}",
                border_style="green",
            )
        )


def _launch_service(settings: Settings, symbols: Sequence[str], interval: str, lookback: str) -> None:
    continuous = Confirm.ask("Continuous mode?", default=False)
    background = Confirm.ask("Background service?", default=False) if continuous else False
    poll_seconds = IntPrompt.ask(
        "Poll interval seconds",
        default=settings.default_poll_seconds,
    )
    max_cycles = None
    if continuous:
        max_cycles_input = Prompt.ask("Max cycles (blank for infinite)", default="")
        max_cycles = int(max_cycles_input) if max_cycles_input.strip() else None
    if background:
        pid = start_background_service(
            settings=settings,
            symbols=list(symbols),
            interval=interval,
            lookback=lookback,
            poll_seconds=poll_seconds,
            max_cycles=max_cycles,
        )
        console.print(
            Panel(
                f"Background service started with PID {pid}.",
                title="Service Spawned",
                border_style="green",
            )
        )
        return
    results = run_service(
        settings=settings,
        symbols=list(symbols),
        interval=interval,
        lookback=lookback,
        poll_seconds=poll_seconds,
        continuous=continuous,
        max_cycles=max_cycles,
    )
    if not results:
        console.print(
            Panel(
                "Service stopped before producing a new result.",
                title="Service Stopped",
                border_style="yellow",
            )
        )
        return
    latest = results[-1]
    console.print(
        Panel(
            json.dumps(latest.artifacts.model_dump(mode="json"), indent=2),
            title=f"Service Completed: {latest.symbol} / {latest.order_id}",
            border_style="bright_magenta",
        )
    )


def run_main_menu() -> None:
    settings = get_settings()
    try:
        db = TradingDatabase(settings)
    except Exception as exc:
        console.print(
            Panel(
                f"Unable to open the runtime database.\n\n{exc}\n\nSet AGENTIC_TRADER_RUNTIME_DIR / AGENTIC_TRADER_DATABASE_PATH if needed, then try again.",
                title="Menu Blocked",
                border_style="red",
            )
        )
        return

    while True:
        console.clear()
        console.print(_banner())
        _render_status(settings, db)
        menu = Table(title="Main Menu")
        menu.add_column("Key", style="bold cyan")
        menu.add_column("Action")
        menu.add_row("1", "Configure investment preferences")
        menu.add_row("2", "Run doctor and system checks")
        menu.add_row("3", "Start one strict agent cycle")
        menu.add_row("4", "Start orchestrator service")
        menu.add_row("5", "Request orchestrator stop")
        menu.add_row("6", "Open operator chat")
        menu.add_row("7", "Open live monitor")
        menu.add_row("8", "Parse operator instruction")
        menu.add_row("9", "Show paper portfolio")
        menu.add_row("10", "Show trade journal")
        menu.add_row("11", "Show daily risk report")
        menu.add_row("12", "Inspect latest run review")
        menu.add_row("13", "Open memory explorer")
        menu.add_row("14", "Show recent runs / logs")
        menu.add_row("15", "Exit")
        console.print(menu)

        choice = Prompt.ask("Select action", choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15"], default="2")
        try:
            if choice == "1":
                _configure_preferences(db)
            elif choice == "2":
                _render_status(settings, db)
            elif choice == "3":
                prefs = db.load_preferences()
                default_symbols = "AAPL,MSFT" if "US" in prefs.regions else "BTC-USD"
                symbols = _split_csv(Prompt.ask("Symbols", default=default_symbols))
                interval = Prompt.ask("Interval", default="1d")
                lookback = Prompt.ask("Lookback", default="180d")
                _strict_one_shot(settings, symbols, interval, lookback)
            elif choice == "4":
                symbols = _split_csv(Prompt.ask("Symbols", default="AAPL,MSFT"))
                interval = Prompt.ask("Interval", default="1d")
                lookback = Prompt.ask("Lookback", default="180d")
                _launch_service(settings, symbols, interval, lookback)
            elif choice == "5":
                state = db.get_service_state()
                if state is None or state.pid is None:
                    console.print(Panel("No managed service is currently active.", title="Not Running", border_style="yellow"))
                else:
                    db.request_stop_service()
                    db.insert_service_event(
                        level="warning",
                        event_type="stop_requested",
                        message="Stop requested by operator from the TUI.",
                        cycle_count=state.cycle_count,
                        symbol=state.current_symbol,
                    )
                    console.print(Panel(f"Stop requested for PID {state.pid}.", title="Stop Requested", border_style="yellow"))
            elif choice == "6":
                _chat_screen(settings, db)
            elif choice == "7":
                refresh_seconds = float(Prompt.ask("Refresh seconds", default="1.0"))
                run_live_monitor(settings, db, refresh_seconds=refresh_seconds)
            elif choice == "8":
                _instruction_screen(settings, db)
            elif choice == "9":
                _show_portfolio(db)
            elif choice == "10":
                _show_trade_journal(db)
            elif choice == "11":
                _show_risk_report(db)
            elif choice == "12":
                _show_latest_run_review(db)
            elif choice == "13":
                _show_memory_explorer(settings, db)
            elif choice == "14":
                _render_recent_runs(db)
            else:
                console.print(Panel("Leaving control room.", title="Exit", border_style="blue"))
                return
        except Exception as exc:
            console.print(Panel(str(exc), title="Action Failed", border_style="red"))
        Prompt.ask("Press Enter to continue", default="")
