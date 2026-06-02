from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from agentic_trader.config import Settings
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.tui_modules.common import (
    TuiMenuAction,
    console,
    menu_table,
    run_readonly_db_menu_action,
)
from agentic_trader.ui_text import (
    LABEL_FALLBACK,
    LABEL_MODEL,
    LABEL_ROLE,
    MENU_ACTION_BACK,
    MENU_ACTION_INSPECT_LATEST_RUN_REVIEW,
    MENU_ACTION_INSPECT_LATEST_RUN_TRACE,
    MESSAGE_NO_PERSISTED_RUNS_REVIEW,
    MESSAGE_NO_PERSISTED_RUNS_TRACE,
    PROMPT_CONTINUE,
    PROMPT_SELECT_ACTION,
    TITLE_AGENT_TRACE_FOR_RUN,
    TITLE_LATEST_RUN_REVIEW,
    TITLE_REVIEW_AND_TRACE,
    TITLE_RUN_REVIEW,
    TITLE_TRACE,
)


def show_latest_run_review(db: TradingDatabase) -> None:
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


def show_latest_run_trace(db: TradingDatabase) -> None:
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


def review_menu(settings: Settings) -> None:
    actions = {
        "1": TuiMenuAction(
            "1",
            MENU_ACTION_INSPECT_LATEST_RUN_REVIEW,
            TITLE_LATEST_RUN_REVIEW,
            show_latest_run_review,
        ),
        "2": TuiMenuAction(
            "2",
            MENU_ACTION_INSPECT_LATEST_RUN_TRACE,
            TITLE_AGENT_TRACE_FOR_RUN,
            show_latest_run_trace,
        ),
    }
    while True:
        console.clear()
        console.print(
            menu_table(
                TITLE_REVIEW_AND_TRACE,
                [*actions.values(), ("3", MENU_ACTION_BACK)],
            )
        )
        choice = Prompt.ask(PROMPT_SELECT_ACTION, choices=["1", "2", "3"], default="1")
        if choice == "3":
            return
        run_readonly_db_menu_action(settings, actions[choice])
        Prompt.ask(PROMPT_CONTINUE, default="")
