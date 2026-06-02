from collections.abc import Callable, Sequence
from dataclasses import dataclass

from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from agentic_trader.config import Settings, get_settings
from agentic_trader.tui_modules.common import banner, console, exit_cleanly
from agentic_trader.tui_modules.monitor_sections import safe_open_read_db
from agentic_trader.tui_modules.operator import operator_menu
from agentic_trader.tui_modules.portfolio import portfolio_menu
from agentic_trader.tui_modules.preferences import edit_preferences_action
from agentic_trader.tui_modules.research import research_menu
from agentic_trader.tui_modules.review import review_menu
from agentic_trader.tui_modules.runtime import runtime_menu
from agentic_trader.tui_modules.status import render_compact_status, render_status
from agentic_trader.ui_text import (
    LABEL_ACTION,
    LABEL_KEY,
    MENU_ACTION_CONFIGURE_INVESTMENT_PREFERENCES,
    MENU_ACTION_EXIT,
    MENU_ACTION_OPERATOR_DESK,
    MENU_ACTION_PORTFOLIO_AND_RISK,
    MENU_ACTION_RESEARCH_AND_MEMORY,
    MENU_ACTION_REVIEW_AND_TRACE,
    MENU_ACTION_RUNTIME_CONTROL,
    MESSAGE_ACTION_CANCELLED_RETURNING,
    MESSAGE_CONTROL_ROOM_CLOSED,
    PROMPT_CONTINUE,
    PROMPT_SELECT_ACTION,
    STYLE_KEY_COLUMN,
    TITLE_ACTION_FAILED,
    TITLE_CANCELLED,
    TITLE_EXIT,
    TITLE_MAIN_MENU,
)


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
    console.print(
        Panel(MESSAGE_CONTROL_ROOM_CLOSED, title=TITLE_EXIT, border_style="blue")
    )


def main_menu_actions() -> tuple[TuiMainMenuAction, ...]:
    return (
        TuiMainMenuAction(
            "1",
            MENU_ACTION_CONFIGURE_INVESTMENT_PREFERENCES,
            edit_preferences_action,
        ),
        TuiMainMenuAction("2", MENU_ACTION_RUNTIME_CONTROL, runtime_menu),
        TuiMainMenuAction("3", MENU_ACTION_OPERATOR_DESK, operator_menu),
        TuiMainMenuAction("4", MENU_ACTION_PORTFOLIO_AND_RISK, portfolio_menu),
        TuiMainMenuAction("5", MENU_ACTION_RESEARCH_AND_MEMORY, research_menu),
        TuiMainMenuAction("6", MENU_ACTION_REVIEW_AND_TRACE, review_menu),
        TuiMainMenuAction("7", MENU_ACTION_EXIT, _exit_menu_action, exits_menu=True),
    )


def main_menu_table(actions: Sequence[TuiMainMenuAction]) -> Table:
    menu = Table(title=TITLE_MAIN_MENU)
    menu.add_column(LABEL_KEY, style=STYLE_KEY_COLUMN)
    menu.add_column(LABEL_ACTION)
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
                PROMPT_SELECT_ACTION,
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
            exit_cleanly()
            return
