from collections.abc import Callable, Sequence
from dataclasses import dataclass

from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from agentic_trader.config import Settings, get_settings
from agentic_trader.tui_modules.common import banner, console, exit_cleanly
from agentic_trader.tui_modules.monitor_runtime import safe_open_read_db
from agentic_trader.tui_modules.operator import operator_menu
from agentic_trader.tui_modules.portfolio import portfolio_menu
from agentic_trader.tui_modules.preferences import edit_preferences_action
from agentic_trader.tui_modules.research import research_menu
from agentic_trader.tui_modules.review import review_menu
from agentic_trader.tui_modules.runtime import runtime_menu
from agentic_trader.tui_modules.status import render_compact_status, render_status
from agentic_trader.ui_text import t


@dataclass(frozen=True, slots=True)
class TuiMainMenuAction:
    key: str
    label: str
    handler: Callable[[Settings], None]
    exits_menu: bool = False


def render_main_status(settings: Settings) -> None:
    db = safe_open_read_db(settings)
    try:
        if console.height < 40:
            render_compact_status(settings, db)
        else:
            render_status(settings, db)
    finally:
        if db is not None:
            db.close()


def _exit_menu_action(_settings: Settings) -> None:
    """
    Exit the application cleanly.
    
    This action handler terminates the program by calling exit_cleanly and does not use the provided settings.
    
    Parameters:
        _settings (Settings): Ignored; present to match the action handler signature.
    """
    exit_cleanly()


def main_menu_actions() -> tuple[TuiMainMenuAction, ...]:
    """
    Get the fixed tuple of main-menu actions used by the TUI.
    
    Each entry is a TuiMainMenuAction mapping a single-character key to a localized label and a handler;
    the final action (key "7") is configured to exit the menu loop.
    Returns:
    	tuple[TuiMainMenuAction, ...]: Ordered sequence of seven main-menu actions (keys "1" through "7").
    """
    return (
        TuiMainMenuAction(
            "1",
            t("menu.action.configure.investment.preferences"),
            edit_preferences_action,
        ),
        TuiMainMenuAction("2", t("menu.action.runtime.control"), runtime_menu),
        TuiMainMenuAction("3", t("menu.action.operator.desk"), operator_menu),
        TuiMainMenuAction("4", t("menu.action.portfolio.and.risk"), portfolio_menu),
        TuiMainMenuAction("5", t("menu.action.research.and.memory"), research_menu),
        TuiMainMenuAction("6", t("menu.action.review.and.trace"), review_menu),
        TuiMainMenuAction(
            "7", t("menu.action.exit"), _exit_menu_action, exits_menu=True
        ),
    )


def main_menu_table(actions: Sequence[TuiMainMenuAction]) -> Table:
    """
    Builds a Rich Table representing the main menu from the provided actions.
    
    Parameters:
        actions (Sequence[TuiMainMenuAction]): Sequence of menu actions used to populate the table; each action yields one row with its `key` and `label`.
    
    Returns:
        Table: A `rich.table.Table` titled with the main menu text, containing two columns (key and action label) and one row per action.
    """
    menu = Table(title=t("title.main.menu"))
    menu.add_column(t("label.key"), style=t("style.key.column"))
    menu.add_column(t("label.action"))
    for action in actions:
        menu.add_row(action.key, action.label)
    return menu


def run_main_menu_action(
    settings: Settings,
    choice: str,
    actions: Sequence[TuiMainMenuAction],
) -> bool:
    action_by_key = {action.key: action for action in actions}
    action = action_by_key[choice]
    action.handler(settings)
    return not action.exits_menu


def run_main_menu(
    *,
    settings_provider: Callable[[], Settings] = get_settings,
) -> None:
    """
    Run the interactive main menu loop using a settings provider.
    
    Displays the application banner, current status, and main menu; prompts the user to choose actions and dispatches the selected action handlers until an exit action is chosen or an EOF condition occurs.
    
    Parameters:
        settings_provider (Callable[[], Settings]): Callable that returns a Settings instance; used to obtain configuration and ensure required directories exist before entering the menu loop.
    
    Behavior notes:
        - Calls exit_cleanly() and returns when an EOF is encountered while prompting.
        - Catches KeyboardInterrupt during action execution and returns to the menu after showing a cancellation message.
        - Catches other exceptions raised by actions and displays an error panel, then continues the menu loop.
    """
    settings = settings_provider()
    settings.ensure_directories()
    actions = main_menu_actions()
    choices = [action.key for action in actions]

    while True:
        console.clear()
        console.print(banner())
        render_main_status(settings)
        console.print(main_menu_table(actions))

        try:
            choice = Prompt.ask(
                t("prompt.select.action"),
                choices=choices,
                default="2",
            )
        except EOFError:
            exit_cleanly()
            return
        try:
            if not run_main_menu_action(settings, choice, actions):
                return
        except EOFError:
            exit_cleanly()
            return
        except KeyboardInterrupt:
            console.print(
                Panel(
                    t("message.action.cancelled.returning"),
                    title=t("title.cancelled"),
                    border_style="yellow",
                )
            )
        except Exception as exc:
            console.print(
                Panel(str(exc), title=t("title.action.failed"), border_style="red")
            )
        try:
            Prompt.ask(t("prompt.continue"), default="")
        except EOFError:
            exit_cleanly()
            return
