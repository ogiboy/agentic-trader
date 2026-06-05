from collections.abc import Callable, Sequence
from dataclasses import dataclass

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agentic_trader.config import Settings
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.ui_text import t

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
    """
    Wraps the given text with the configured key-column Rich markup style.
    
    Parameters:
        text (str): The text to be wrapped.
    
    Returns:
        styled_text (str): The input string surrounded by Rich style tags using the style token from t("style.key.column").
    """
    style = t("style.key.column")
    return f"[{style}]{text}[/{style}]"


def split_csv(value: str) -> list[str]:
    """
    Split a comma-separated string into trimmed, uppercase tokens and omit empty entries.
    
    Parameters:
        value (str): Input CSV string; items may contain surrounding whitespace and mixed case.
    
    Returns:
        list[str]: Tokens from `value` with whitespace removed and converted to uppercase, excluding any empty items.
    """
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def menu_table(title: str, items: Sequence[TuiMenuAction | tuple[str, str]]) -> Table:
    """
    Create a two-column Rich Table for a menu, listing keys and their corresponding actions.
    
    Parameters:
        title (str): Title displayed at the top of the table.
        items (Sequence[TuiMenuAction | tuple[str, str]]): Sequence of menu entries; each entry is either a TuiMenuAction (rows use its `key` and `label`) or a 2-tuple (key, label).
    
    Returns:
        table (Table): A Rich Table with two columns (key and action) populated from `items`.
    """
    table = Table(title=title)
    table.add_column(t("label.key"), style=t("style.key.column"))
    table.add_column(t("label.action"))
    for item in items:
        if isinstance(item, TuiMenuAction):
            table.add_row(item.key, item.label)
        else:
            table.add_row(item[0], item[1])
    return table


def run_readonly_db_menu_action(settings: Settings, action: TuiMenuAction) -> None:
    from agentic_trader.tui_modules.monitor_runtime import (
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
    """
    Create a control-room banner panel that adapts its layout to the current terminal width.
    
    For terminals narrower than 120 columns the panel contains a centered compact title and subtitle;
    for wider terminals it contains an ASCII-art title with a full subtitle. Text and styles are
    sourced from localization via `t(...)`.
    
    Returns:
        panel (Panel): A Rich Panel containing the rendered banner.
    """
    if console.width < 120:
        compact = (
            "[bold green]AGENTIC TRADER[/bold green] "
            f"[cyan]// {t('title.control.room').upper()}[/cyan]\n"
            f"[dim]{t('message.control.room.compact.subtitle')}[/dim]"
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
        f"[bold cyan]{t('title.control.room')}[/bold cyan]\n"
        f"[dim]{t('message.control.room.full.subtitle')}[/dim]"
    )
    return Panel(f"[green]{art}[/green]\n{subtitle}", border_style="bright_blue")


def exit_cleanly() -> None:
    """
    Display a closing panel indicating the control room has been closed.
    
    The panel shows a localized "closed" message, uses a localized "Exit" title, and renders with a blue border.
    """
    console.print(Panel(t("message.control.room.closed"), title=t("title.exit"), border_style="blue"))
