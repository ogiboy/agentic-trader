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
