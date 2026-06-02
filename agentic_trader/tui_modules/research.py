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
from agentic_trader.ui_text import (
    LABEL_BIAS,
    LABEL_CREATED,
    LABEL_INTERVAL,
    LABEL_LOOKBACK,
    LABEL_REGIME,
    LABEL_SCORE,
    LABEL_STRATEGY,
    LABEL_SYMBOL,
    MENU_ACTION_BACK,
    MENU_ACTION_OPEN_MEMORY_EXPLORER,
    MENU_ACTION_SHOW_RECENT_RUNS_AND_EVENTS,
    PROMPT_CONTINUE,
    PROMPT_SELECT_ACTION,
    TITLE_DECISION_EVIDENCE_EXPLORER,
    TITLE_MEMORY_EXPLORER,
    TITLE_RECENT_RUNS,
    TITLE_RESEARCH_AND_MEMORY,
    get_ui_text,
)


def memory_explorer_table(matches: Sequence[HistoricalMemoryMatch]) -> Table:
    table = Table(title=TITLE_DECISION_EVIDENCE_EXPLORER)
    table.add_column(LABEL_CREATED)
    table.add_column(LABEL_SYMBOL)
    table.add_column(LABEL_SCORE)
    table.add_column(LABEL_REGIME)
    table.add_column(LABEL_STRATEGY)
    table.add_column(LABEL_BIAS)
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
    copy = get_ui_text()
    symbol = Prompt.ask(LABEL_SYMBOL, default="AAPL").strip().upper()
    interval = Prompt.ask(LABEL_INTERVAL, default="1d")
    lookback = Prompt.ask(LABEL_LOOKBACK, default="180d")
    limit = IntPrompt.ask(copy.label_matches, default=5)
    frame = fetch_ohlcv(symbol, interval=interval, lookback=lookback)
    snapshot = build_snapshot(
        frame, symbol=symbol, interval=interval, lookback=lookback
    )
    matches = retrieve_similar_memories(db, snapshot, limit=limit)

    console.print(memory_explorer_table(matches))


def research_menu(settings: Settings) -> None:
    actions = {
        "1": TuiMenuAction(
            "1",
            MENU_ACTION_OPEN_MEMORY_EXPLORER,
            TITLE_MEMORY_EXPLORER,
            lambda db: show_memory_explorer(settings, db),
        ),
        "2": TuiMenuAction(
            "2",
            MENU_ACTION_SHOW_RECENT_RUNS_AND_EVENTS,
            TITLE_RECENT_RUNS,
            render_recent_runs,
        ),
    }
    while True:
        console.clear()
        console.print(
            menu_table(
                TITLE_RESEARCH_AND_MEMORY,
                [*actions.values(), ("3", MENU_ACTION_BACK)],
            )
        )
        choice = Prompt.ask(PROMPT_SELECT_ACTION, choices=["1", "2", "3"], default="1")
        if choice == "3":
            return
        run_readonly_db_menu_action(settings, actions[choice])
        if choice == "2":
            render_runtime_events(read_service_events(settings, limit=6))
        Prompt.ask(PROMPT_CONTINUE, default="")
