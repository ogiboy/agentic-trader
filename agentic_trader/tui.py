from collections.abc import Callable
from dataclasses import dataclass
from typing import Sequence

from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt
from rich.table import Table

from agentic_trader.config import Settings, get_settings
from agentic_trader.llm.client import LocalLLM as LocalLLM
from agentic_trader.market.data import fetch_ohlcv
from agentic_trader.market.features import build_snapshot
from agentic_trader.memory.retrieval import retrieve_similar_memories
from agentic_trader.runtime_feed import read_service_events
from agentic_trader.schemas import (
    HistoricalMemoryMatch,
)
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.tui_modules.common import (
    TuiMenuAction,
)
from agentic_trader.tui_modules.common import banner as _banner
from agentic_trader.tui_modules.common import (
    console,
)
from agentic_trader.tui_modules.common import exit_cleanly as _exit_cleanly
from agentic_trader.tui_modules.common import split_csv as _split_csv
from agentic_trader.tui_modules.common import style_key as _style_key
from agentic_trader.tui_modules.monitor import (
    build_monitor_renderable as _build_monitor_renderable,
)
from agentic_trader.tui_modules.monitor import run_live_monitor as _run_live_monitor
from agentic_trader.tui_modules.monitor_sections import (
    agent_activity_lines as _export_agent_activity_lines,
)
from agentic_trader.tui_modules.monitor_sections import (
    agent_activity_table as _export_agent_activity_table,
)
from agentic_trader.tui_modules.monitor_sections import (
    broker_gate_lines as _export_broker_gate_lines,
)
from agentic_trader.tui_modules.monitor_sections import (
    last_outcome_lines as _export_last_outcome_lines,
)
from agentic_trader.tui_modules.monitor_sections import (
    observer_mode_panel,
    portfolio_renderable,
    render_recent_runs,
    render_runtime_events,
    risk_report_table,
    safe_open_read_db,
)
from agentic_trader.tui_modules.monitor_sections import (
    system_status_table as _export_system_status_table,
)
from agentic_trader.tui_modules.monitor_sections import (
    trade_journal_table,
)
from agentic_trader.tui_modules.operator import operator_menu as _operator_menu
from agentic_trader.tui_modules.preferences import (
    edit_preferences_action as _edit_preferences_action,
)
from agentic_trader.tui_modules.runtime import runtime_menu as _runtime_menu
from agentic_trader.tui_modules.status import (
    render_compact_status,
    render_status,
)
from agentic_trader.tui_modules.monitor_sections import (
    runtime_cycle_lines as _export_runtime_cycle_lines,
)
from agentic_trader.tui_modules.monitor_sections import (
    runtime_state_table as _export_runtime_state_table,
)
from agentic_trader.ui_text import (
    LABEL_ACTION,
    LABEL_BIAS,
    LABEL_CREATED,
    LABEL_FALLBACK,
    LABEL_KEY,
    LABEL_MODEL,
    LABEL_REGIME,
    LABEL_ROLE,
    LABEL_SCORE,
    LABEL_STRATEGY,
    LABEL_SYMBOL,
    MENU_ACTION_BACK,
    MENU_ACTION_CONFIGURE_INVESTMENT_PREFERENCES,
    MENU_ACTION_EXIT,
    MENU_ACTION_INSPECT_LATEST_RUN_REVIEW,
    MENU_ACTION_INSPECT_LATEST_RUN_TRACE,
    MENU_ACTION_OPEN_MEMORY_EXPLORER,
    MENU_ACTION_OPERATOR_DESK,
    MENU_ACTION_PORTFOLIO_AND_RISK,
    MENU_ACTION_RESEARCH_AND_MEMORY,
    MENU_ACTION_REVIEW_AND_TRACE,
    MENU_ACTION_RUNTIME_CONTROL,
    MENU_ACTION_SHOW_DAILY_RISK_REPORT,
    MENU_ACTION_SHOW_PAPER_PORTFOLIO,
    MENU_ACTION_SHOW_RECENT_RUNS_AND_EVENTS,
    MENU_ACTION_SHOW_TRADE_JOURNAL,
    MESSAGE_ACTION_CANCELLED_RETURNING,
    MESSAGE_CONTROL_ROOM_CLOSED,
    MESSAGE_NO_PERSISTED_RUNS_REVIEW,
    MESSAGE_NO_PERSISTED_RUNS_TRACE,
    PROMPT_CONTINUE,
    PROMPT_SELECT_ACTION,
    STYLE_KEY_COLUMN,
    TITLE_ACTION_FAILED,
    TITLE_AGENT_TRACE_FOR_RUN,
    TITLE_CANCELLED,
    TITLE_DAILY_RISK_REPORT,
    TITLE_DECISION_EVIDENCE_EXPLORER,
    TITLE_EXIT,
    TITLE_LATEST_RUN_REVIEW,
    TITLE_MAIN_MENU,
    TITLE_MEMORY_EXPLORER,
    TITLE_PAPER_PORTFOLIO,
    TITLE_PORTFOLIO_AND_RISK,
    TITLE_RECENT_RUNS,
    TITLE_RESEARCH_AND_MEMORY,
    TITLE_REVIEW_AND_TRACE,
    TITLE_RUN_REVIEW,
    TITLE_TRACE,
    TITLE_TRADE_JOURNAL,
)


@dataclass(frozen=True, slots=True)
class TuiMainMenuAction:
    key: str
    label: str
    handler: Callable[[Settings], None]
    exits_menu: bool = False


def _show_portfolio(db: TradingDatabase) -> None:
    """
    Render the portfolio summary, positions list, and daily risk report to the console.

    Prints a combined portfolio renderable (summary plus positions, with a placeholder when no open positions exist) followed by the account risk report.
    """
    console.print(portfolio_renderable(db))
    console.print(risk_report_table(db))


def _show_trade_journal(db: TradingDatabase) -> None:
    console.print(trade_journal_table(db, limit=20))


def _show_risk_report(db: TradingDatabase) -> None:
    console.print(risk_report_table(db))


def _show_latest_run_review(db: TradingDatabase) -> None:
    """
    Display the latest persisted run review or a notice if none exists.

    If a persisted run is available, prints the run's artifacts as pretty-printed JSON with the run id in the panel title. If no persisted run exists, prints a notice indicating there are no persisted runs to review.
    """
    record = db.latest_run()
    if record is None:
        console.print(
            Panel(
                MESSAGE_NO_PERSISTED_RUNS_REVIEW,
                title=TITLE_RUN_REVIEW,
                border_style="yellow",
            )
        )
        return
    console.print(
        Panel(
            record.artifacts.model_dump_json(indent=2),
            title=TITLE_LATEST_RUN_REVIEW.format(run_id=record.run_id),
            border_style="cyan",
        )
    )


def _memory_explorer_table(matches: Sequence[HistoricalMemoryMatch]) -> Table:
    """
    Builds a Rich Table showing historical memory matches for the decision evidence explorer.

    Parameters:
        matches (Sequence[HistoricalMemoryMatch]): Sequence of memory match records to display. When empty, the table contains a single placeholder row.

    Returns:
        Table: A Rich Table with columns "Created", "Symbol", "Score", "Regime", "Strategy", and "Bias". The `Score` column is formatted to two decimal places.
    """
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


def _show_memory_explorer(_settings: Settings, db: TradingDatabase) -> None:
    """
    Launch an interactive memory explorer that prompts for symbol, interval, lookback, and match limit, then prints a table of similar historical memories.

    Parameters:
        _settings (Settings): Unused in this view; kept for API symmetry.
        db (TradingDatabase): Database used to retrieve and rank matching memories; results are printed to the console.
    """
    symbol = Prompt.ask("Symbol", default="AAPL").strip().upper()
    interval = Prompt.ask("Interval", default="1d")
    lookback = Prompt.ask("Lookback", default="180d")
    limit = IntPrompt.ask("Matches", default=5)
    frame = fetch_ohlcv(symbol, interval=interval, lookback=lookback)
    snapshot = build_snapshot(
        frame, symbol=symbol, interval=interval, lookback=lookback
    )
    matches = retrieve_similar_memories(db, snapshot, limit=limit)

    console.print(_memory_explorer_table(matches))


def _show_latest_run_trace(db: TradingDatabase) -> None:
    """
    Display the most recent run's agent trace or an informational panel when none exists.

    Prints a table listing each agent trace's role, model name, and whether a fallback was used for the latest recorded run; if no persisted run is available, prints a yellow panel stating that no run trace is present.
    """
    record = db.latest_run()
    if record is None:
        console.print(
            Panel(
                MESSAGE_NO_PERSISTED_RUNS_TRACE,
                title=TITLE_TRACE,
                border_style="yellow",
            )
        )
        return
    table = Table(title=TITLE_AGENT_TRACE_FOR_RUN.format(run_id=record.run_id))
    table.add_column(LABEL_ROLE)
    table.add_column(LABEL_MODEL)
    table.add_column(LABEL_FALLBACK)
    for trace in record.artifacts.agent_traces:
        table.add_row(trace.role, trace.model_name, str(trace.used_fallback))
    console.print(table)


def _menu_table(title: str, items: Sequence[TuiMenuAction | tuple[str, str]]) -> Table:
    """
    Build a Rich Table listing menu entries with key and action label columns.

    Parameters:
        title (str): Table title displayed above the menu.
        items (Sequence[TuiMenuAction | tuple[str, str]]): Sequence of menu entries; each entry is either a TuiMenuAction or a (key, label) tuple.

    Returns:
        Table: A Rich Table with two columns (key, action label) and one row per item.
    """
    table = Table(title=title)
    table.add_column(LABEL_KEY, style=STYLE_KEY_COLUMN)
    table.add_column(LABEL_ACTION)
    for item in items:
        if isinstance(item, TuiMenuAction):
            table.add_row(item.key, item.label)
        else:
            table.add_row(item[0], item[1])
    return table


def _run_readonly_db_menu_action(settings: Settings, action: TuiMenuAction) -> None:
    db = safe_open_read_db(settings)
    if db is None:
        console.print(observer_mode_panel(action.observer_title))
        return
    try:
        action.renderer(db)
    finally:
        db.close()


def _portfolio_menu(settings: Settings) -> None:
    actions = {
        "1": TuiMenuAction(
            "1",
            MENU_ACTION_SHOW_PAPER_PORTFOLIO,
            TITLE_PAPER_PORTFOLIO,
            _show_portfolio,
        ),
        "2": TuiMenuAction(
            "2",
            MENU_ACTION_SHOW_TRADE_JOURNAL,
            TITLE_TRADE_JOURNAL,
            _show_trade_journal,
        ),
        "3": TuiMenuAction(
            "3",
            MENU_ACTION_SHOW_DAILY_RISK_REPORT,
            TITLE_DAILY_RISK_REPORT,
            _show_risk_report,
        ),
    }
    while True:
        console.clear()
        console.print(
            _menu_table(
                TITLE_PORTFOLIO_AND_RISK,
                [*actions.values(), ("4", MENU_ACTION_BACK)],
            )
        )
        choice = Prompt.ask(
            PROMPT_SELECT_ACTION, choices=["1", "2", "3", "4"], default="1"
        )
        if choice == "4":
            return
        _run_readonly_db_menu_action(settings, actions[choice])
        Prompt.ask(PROMPT_CONTINUE, default="")


def _research_menu(settings: Settings) -> None:
    """
    Display the Research and Memory menu and handle the operator's selection loop.

    Presents options to open the memory explorer, show recent runs (followed by a short runtime events list), or return to the previous menu. When a readable database is required the function attempts a safe read-only open and displays an observer-mode notice if the runtime writer prevents access; any opened database is closed before continuing.

    Parameters:
        settings (Settings): Application settings used to locate and open the trading database and service state.
    """
    actions = {
        "1": TuiMenuAction(
            "1",
            MENU_ACTION_OPEN_MEMORY_EXPLORER,
            TITLE_MEMORY_EXPLORER,
            lambda db: _show_memory_explorer(settings, db),
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
            _menu_table(
                TITLE_RESEARCH_AND_MEMORY,
                [*actions.values(), ("3", MENU_ACTION_BACK)],
            )
        )
        choice = Prompt.ask(PROMPT_SELECT_ACTION, choices=["1", "2", "3"], default="1")
        if choice == "3":
            return
        _run_readonly_db_menu_action(settings, actions[choice])
        if choice == "2":
            render_runtime_events(read_service_events(settings, limit=6))
        Prompt.ask(PROMPT_CONTINUE, default="")


def _review_menu(settings: Settings) -> None:
    """
    Present an interactive "Review and Trace" menu that lets the operator inspect the latest persisted run review or its trace.

    Displays a menu, prompts for a selection, opens a read-only database when needed to render the chosen view, and returns to the caller when the user selects "Back".

    Parameters:
        settings (Settings): Application settings used to locate and open the trading database for read-only inspection.
    """
    actions = {
        "1": TuiMenuAction(
            "1",
            MENU_ACTION_INSPECT_LATEST_RUN_REVIEW,
            TITLE_LATEST_RUN_REVIEW,
            _show_latest_run_review,
        ),
        "2": TuiMenuAction(
            "2",
            MENU_ACTION_INSPECT_LATEST_RUN_TRACE,
            TITLE_AGENT_TRACE_FOR_RUN,
            _show_latest_run_trace,
        ),
    }
    while True:
        console.clear()
        console.print(
            _menu_table(
                TITLE_REVIEW_AND_TRACE,
                [*actions.values(), ("3", MENU_ACTION_BACK)],
            )
        )
        choice = Prompt.ask(PROMPT_SELECT_ACTION, choices=["1", "2", "3"], default="1")
        if choice == "3":
            return
        _run_readonly_db_menu_action(settings, actions[choice])
        Prompt.ask(PROMPT_CONTINUE, default="")


def _render_main_status(settings: Settings) -> None:
    db = safe_open_read_db(settings)
    try:
        if console.height < 40:
            render_compact_status(settings, db)
        else:
            render_status(settings, db)
    finally:
        if db is not None:
            db.close()


def _runtime_menu_action(settings: Settings) -> None:
    _runtime_menu(settings)


def _operator_menu_action(settings: Settings) -> None:
    _operator_menu(settings)


def _portfolio_menu_action(settings: Settings) -> None:
    _portfolio_menu(settings)


def _research_menu_action(settings: Settings) -> None:
    _research_menu(settings)


def _review_menu_action(settings: Settings) -> None:
    _review_menu(settings)


def _exit_menu_action(_settings: Settings) -> None:
    """
    Display a closing panel indicating the control room has been closed.
    """
    console.print(
        Panel(MESSAGE_CONTROL_ROOM_CLOSED, title=TITLE_EXIT, border_style="blue")
    )


def _main_menu_actions() -> tuple[TuiMainMenuAction, ...]:
    """
    Build the ordered set of main menu actions for the TUI.

    Returns:
        tuple[TuiMainMenuAction, ...]: Tuple of `TuiMainMenuAction` objects in menu order: configure investment preferences, runtime control, operator desk, portfolio and risk, research and memory, review and trace, and exit (the exit action is flagged to leave the menu).
    """
    return (
        TuiMainMenuAction(
            "1",
            MENU_ACTION_CONFIGURE_INVESTMENT_PREFERENCES,
            _edit_preferences_action,
        ),
        TuiMainMenuAction("2", MENU_ACTION_RUNTIME_CONTROL, _runtime_menu_action),
        TuiMainMenuAction("3", MENU_ACTION_OPERATOR_DESK, _operator_menu_action),
        TuiMainMenuAction("4", MENU_ACTION_PORTFOLIO_AND_RISK, _portfolio_menu_action),
        TuiMainMenuAction("5", MENU_ACTION_RESEARCH_AND_MEMORY, _research_menu_action),
        TuiMainMenuAction("6", MENU_ACTION_REVIEW_AND_TRACE, _review_menu_action),
        TuiMainMenuAction("7", MENU_ACTION_EXIT, _exit_menu_action, exits_menu=True),
    )


def _main_menu_table(actions: Sequence[TuiMainMenuAction]) -> Table:
    """
    Builds a Rich Table representing the main menu from the given actions.

    Parameters:
        actions (Sequence[TuiMainMenuAction]): Ordered menu actions whose `key` and `label` populate each row.

    Returns:
        table (Table): A Rich Table titled with the main-menu title, containing two columns (key and action) and one row per action.
    """
    menu = Table(title=TITLE_MAIN_MENU)
    menu.add_column(LABEL_KEY, style=STYLE_KEY_COLUMN)
    menu.add_column(LABEL_ACTION)
    for action in actions:
        menu.add_row(action.key, action.label)
    return menu


def _run_main_menu_action(
    settings: Settings,
    choice: str,
    actions: Sequence[TuiMainMenuAction],
) -> bool:
    action_by_key = {action.key: action for action in actions}
    action = action_by_key[choice]
    action.handler(settings)
    return not action.exits_menu


def run_main_menu() -> None:
    """
    Run the interactive terminal control-room loop for the Agentic Trader UI.

    Displays the system banner and status, presents the main menu, dispatches to sub-menus (preferences, runtime control, operator desk, portfolio/risk, research/memory, review/trace), and manages opening/closing the trading database as needed. Handles EOF and interrupt signals to exit cleanly and reports action errors to the user.
    """
    settings = get_settings()
    settings.ensure_directories()
    actions = _main_menu_actions()
    choices = [action.key for action in actions]

    while True:
        console.clear()
        console.print(_banner())
        _render_main_status(settings)
        console.print(_main_menu_table(actions))

        try:
            choice = Prompt.ask(
                PROMPT_SELECT_ACTION,
                choices=choices,
                default="2",
            )
        except EOFError:
            _exit_cleanly()
            return
        try:
            if not _run_main_menu_action(settings, choice, actions):
                return
        except EOFError:
            _exit_cleanly()
            return
        except KeyboardInterrupt:
            console.print(
                Panel(
                    MESSAGE_ACTION_CANCELLED_RETURNING,
                    title=TITLE_CANCELLED,
                    border_style="yellow",
                )
            )
        except Exception as exc:
            console.print(
                Panel(str(exc), title=TITLE_ACTION_FAILED, border_style="red")
            )
        try:
            Prompt.ask(PROMPT_CONTINUE, default="")
        except EOFError:
            _exit_cleanly()
            return


split_csv = _split_csv
style_key = _style_key
system_status_table = _export_system_status_table
runtime_state_table = _export_runtime_state_table
runtime_cycle_lines = _export_runtime_cycle_lines
last_outcome_lines = _export_last_outcome_lines
broker_gate_lines = _export_broker_gate_lines
agent_activity_lines = _export_agent_activity_lines
agent_activity_table = _export_agent_activity_table
build_monitor_renderable = _build_monitor_renderable
run_live_monitor = _run_live_monitor
memory_explorer_table = _memory_explorer_table
menu_table = _menu_table
main_menu_actions = _main_menu_actions
main_menu_table = _main_menu_table
run_main_menu_action = _run_main_menu_action
