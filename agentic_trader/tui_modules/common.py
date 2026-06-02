from collections.abc import Callable, Sequence
from dataclasses import dataclass

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agentic_trader.config import Settings
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.ui_text import (
    LABEL_ACTION,
    LABEL_KEY,
    MESSAGE_CONTROL_ROOM_CLOSED,
    STYLE_KEY_COLUMN,
    TITLE_EXIT,
)

console = Console()


@dataclass(frozen=True, slots=True)
class TuiMenuAction:
    key: str
    label: str
    observer_title: str
    renderer: Callable[[TradingDatabase], None]


def open_db(settings: Settings, *, read_only: bool) -> TradingDatabase:
    return TradingDatabase(settings, read_only=read_only)


def style_key(text: str) -> str:
    return f"[{STYLE_KEY_COLUMN}]{text}[/{STYLE_KEY_COLUMN}]"


def split_csv(value: str) -> list[str]:
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def menu_table(title: str, items: Sequence[TuiMenuAction | tuple[str, str]]) -> Table:
    table = Table(title=title)
    table.add_column(LABEL_KEY, style=STYLE_KEY_COLUMN)
    table.add_column(LABEL_ACTION)
    for item in items:
        if isinstance(item, TuiMenuAction):
            table.add_row(item.key, item.label)
        else:
            table.add_row(item[0], item[1])
    return table


def run_readonly_db_menu_action(settings: Settings, action: TuiMenuAction) -> None:
    from agentic_trader.tui_modules.monitor_sections import (
        observer_mode_panel,
        safe_open_read_db,
    )

    db = safe_open_read_db(settings)
    if db is None:
        console.print(observer_mode_panel(action.observer_title))
        return
    try:
        action.renderer(db)
    finally:
        db.close()


def banner() -> Panel:
    if console.width < 120:
        compact = (
            "[bold green]AGENTIC TRADER[/bold green] "
            "[cyan]// CONTROL ROOM[/cyan]\n"
            "[dim]Strict LLM gate, portfolio state, runtime controls.[/dim]"
        )
        return Panel(Align.center(compact), border_style="bright_blue")

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


def exit_cleanly() -> None:
    console.print(
        Panel(MESSAGE_CONTROL_ROOM_CLOSED, title=TITLE_EXIT, border_style="blue")
    )
