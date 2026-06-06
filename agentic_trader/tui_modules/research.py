from collections.abc import Sequence

from rich.prompt import IntPrompt, Prompt
from rich.table import Table

from agentic_trader.config import Settings
from agentic_trader.market.data import fetch_ohlcv
from agentic_trader.market.features import build_snapshot
from agentic_trader.memory.retrieval import retrieve_similar_memories
from agentic_trader.runtime_feed import read_service_events
from agentic_trader.schemas import HistoricalMemoryMatch
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.tui_modules.common import (
    TuiMenuAction,
    console,
    menu_table,
    run_readonly_db_menu_action,
)
from agentic_trader.tui_modules.monitor_runtime import (
    render_runtime_events,
)
from agentic_trader.tui_modules.monitor_tables import render_recent_runs
from agentic_trader.ui_text import t


def memory_explorer_table(matches: Sequence[HistoricalMemoryMatch]) -> Table:
    """
    Builds a rich Table displaying a list of historical memory matches.
    
    Creates a Table titled with the localized UI key for the memory explorer and adds columns for created, symbol, score, regime, strategy, and bias. If `matches` is empty the table contains a single row of "-" placeholders; otherwise one row is added per match with the match's created_at, symbol, similarity_score (formatted to two decimals), regime, strategy_family, and manager_bias.
    
    Parameters:
        matches (Sequence[HistoricalMemoryMatch]): Sequence of historical memory match objects to display.
    
    Returns:
        Table: A populated rich.table.Table ready for rendering.
    """
    table = Table(title=t("title.decision.evidence.explorer"))
    table.add_column(t("label.created"))
    table.add_column(t("label.symbol"))
    table.add_column(t("label.score"))
    table.add_column(t("label.regime"))
    table.add_column(t("label.strategy"))
    table.add_column(t("label.bias"))
    if not matches:
        table.add_row("-", "-", "-", "-", "-", "-")
        return table

    for match in matches:
        table.add_row(
            match.created_at,
            match.symbol,
            f"{match.similarity_score:.2f}",
            match.regime,
            match.strategy_family,
            match.manager_bias,
        )
    return table


def show_memory_explorer(_settings: Settings, db: TradingDatabase) -> None:
    """
    Open an interactive prompt to search for historical memory matches for a symbol and display the results in a table.
    
    Prompts the user for symbol, interval, lookback window and maximum matches, fetches market data, builds a feature snapshot, retrieves similar historical memories from the provided database, and renders the matches using the memory explorer table.
    """
    symbol = Prompt.ask(t("label.symbol"), default="AAPL").strip().upper()
    interval = Prompt.ask(t("label.interval"), default="1d")
    lookback = Prompt.ask(t("label.lookback"), default="180d")
    limit = IntPrompt.ask(t("label.matches"), default=5)
    frame = fetch_ohlcv(symbol, interval=interval, lookback=lookback)
    snapshot = build_snapshot(
        frame, symbol=symbol, interval=interval, lookback=lookback
    )
    matches = retrieve_similar_memories(db, snapshot, limit=limit)

    console.print(memory_explorer_table(matches))


def research_menu(settings: Settings) -> None:
    """
    Display an interactive TUI research menu for exploring historical memories and recent runs.
    
    Runs a loop that presents menu actions to open the memory explorer, show recent runs (and render recent runtime events after that action), or go back; executes the selected action using a read-only database context and prompts the user to continue between iterations.
    
    Parameters:
        settings (Settings): Application settings and environment used to access services and the database.
    """
    actions = {
        "1": TuiMenuAction(
            "1",
            t("menu.action.open.memory.explorer"),
            t("title.memory.explorer"),
            lambda db: show_memory_explorer(settings, db),
        ),
        "2": TuiMenuAction(
            "2",
            t("menu.action.show.recent.runs.and.events"),
            t("title.recent.runs"),
            render_recent_runs,
        ),
    }
    while True:
        console.clear()
        console.print(
            menu_table(
                t("title.research.and.memory"),
                [*actions.values(), ("3", t("menu.action.back"))],
            )
        )
        choice = Prompt.ask(t("prompt.select.action"), choices=["1", "2", "3"], default="1")
        if choice == "3":
            return
        run_readonly_db_menu_action(settings, actions[choice])
        if choice == "2":
            render_runtime_events(read_service_events(settings, limit=6))
        Prompt.ask(t("prompt.continue"), default="")
