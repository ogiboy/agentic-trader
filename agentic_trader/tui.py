import json
from typing import Sequence

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

from agentic_trader.config import Settings, get_settings
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import InvestmentPreferences
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.workflows.run_once import persist_run, run_once
from agentic_trader.workflows.service import ensure_llm_ready, run_service

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
    console.print(_render_preferences(db.load_preferences()))
    _render_recent_runs(db)


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
    notes = Prompt.ask("Notes", default=current.notes)
    updated = InvestmentPreferences(
        regions=_split_csv(regions) or current.regions,
        exchanges=_split_csv(exchanges) or current.exchanges,
        currencies=_split_csv(currencies) or current.currencies,
        sectors=_split_csv(sectors),
        risk_profile=risk_profile,
        trade_style=trade_style,
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
    poll_seconds = IntPrompt.ask(
        "Poll interval seconds",
        default=settings.default_poll_seconds,
    )
    max_cycles = None
    if continuous:
        max_cycles_input = Prompt.ask("Max cycles (blank for infinite)", default="")
        max_cycles = int(max_cycles_input) if max_cycles_input.strip() else None
    results = run_service(
        settings=settings,
        symbols=list(symbols),
        interval=interval,
        lookback=lookback,
        poll_seconds=poll_seconds,
        continuous=continuous,
        max_cycles=max_cycles,
    )
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
        menu.add_row("5", "Show paper portfolio")
        menu.add_row("6", "Show recent runs / logs")
        menu.add_row("7", "Exit")
        console.print(menu)

        choice = Prompt.ask("Select action", choices=["1", "2", "3", "4", "5", "6", "7"], default="2")
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
                _show_portfolio(db)
            elif choice == "6":
                _render_recent_runs(db)
            else:
                console.print(Panel("Leaving control room.", title="Exit", border_style="blue"))
                return
        except Exception as exc:
            console.print(Panel(str(exc), title="Action Failed", border_style="red"))
        Prompt.ask("Press Enter to continue", default="")
