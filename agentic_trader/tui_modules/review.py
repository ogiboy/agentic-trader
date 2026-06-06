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
from agentic_trader.ui_text import t


def show_latest_run_review(db: TradingDatabase) -> None:
    """
    Display a review panel for the latest persisted run or a message when none exist.
    
    Prints a rich Panel containing the latest run's model JSON and a title with the run ID; if no persisted run is found, prints a yellow Panel stating there are no persisted runs to review.
    """
    record = db.latest_run()
    if record is None:
        console.print(
            Panel(
                t("message.no.persisted.runs.review"),
                title=t("title.run.review"),
                border_style="yellow",
            )
        )
        return
    console.print(
        Panel(
            record.artifacts.model_dump_json(indent=2),
            title=t("title.latest.run.review", run_id=record.run_id),
            border_style="cyan",
        )
    )


def show_latest_run_trace(db: TradingDatabase) -> None:
    """
    Display a table of agent traces for the latest persisted run from the database.
    
    If no persisted run exists, prints a yellow panel with a localized "no persisted runs" message and returns. If a run exists, prints a table titled with the run ID containing each trace's role, model name, and whether a fallback was used.
    
    Parameters:
        db (TradingDatabase): Database instance used to retrieve the latest persisted run.
    """
    record = db.latest_run()
    if record is None:
        console.print(
            Panel(
                t("message.no.persisted.runs.trace"),
                title=t("title.trace"),
                border_style="yellow",
            )
        )
        return
    table = Table(title=t("title.agent.trace.for.run", run_id=record.run_id))
    table.add_column(t("label.role"))
    table.add_column(t("label.model"))
    table.add_column(t("label.fallback"))
    for trace in record.artifacts.agent_traces:
        table.add_row(trace.role, trace.model_name, str(trace.used_fallback))
    console.print(table)


def review_menu(settings: Settings) -> None:
    """
    Display an interactive "review and trace" menu that lets the user inspect the latest persisted run or view its agent trace.
    
    Shows a three-option menu: inspect latest run review, inspect latest run trace, or go back. Selecting an inspection runs the chosen action within a read-only database context and then prompts the user to continue; choosing the back option exits the menu.
    
    Parameters:
        settings (Settings): Application settings used to acquire a read-only database context when executing the selected menu action.
    """
    actions = {
        "1": TuiMenuAction(
            "1",
            t("menu.action.inspect.latest.run.review"),
            t("title.latest.run.review"),
            show_latest_run_review,
        ),
        "2": TuiMenuAction(
            "2",
            t("menu.action.inspect.latest.run.trace"),
            t("title.agent.trace.for.run"),
            show_latest_run_trace,
        ),
    }
    while True:
        console.clear()
        console.print(
            menu_table(
                t("title.review.and.trace"),
                [*actions.values(), ("3", t("menu.action.back"))],
            )
        )
        choice = Prompt.ask(t("prompt.select.action"), choices=["1", "2", "3"], default="1")
        if choice == "3":
            return
        run_readonly_db_menu_action(settings, actions[choice])
        Prompt.ask(t("prompt.continue"), default="")
