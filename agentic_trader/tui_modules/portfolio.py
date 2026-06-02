from rich.prompt import Prompt

from agentic_trader.config import Settings
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.tui_modules.common import (
    TuiMenuAction,
    console,
    menu_table,
    run_readonly_db_menu_action,
)
from agentic_trader.tui_modules.monitor_sections import (
    portfolio_renderable,
    risk_report_table,
    trade_journal_table,
)
from agentic_trader.ui_text import (
    MENU_ACTION_BACK,
    MENU_ACTION_SHOW_DAILY_RISK_REPORT,
    MENU_ACTION_SHOW_PAPER_PORTFOLIO,
    MENU_ACTION_SHOW_TRADE_JOURNAL,
    PROMPT_CONTINUE,
    PROMPT_SELECT_ACTION,
    TITLE_DAILY_RISK_REPORT,
    TITLE_PAPER_PORTFOLIO,
    TITLE_PORTFOLIO_AND_RISK,
    TITLE_TRADE_JOURNAL,
)


def show_portfolio(db: TradingDatabase) -> None:
    console.print(portfolio_renderable(db))
    console.print(risk_report_table(db))


def show_trade_journal(db: TradingDatabase) -> None:
    console.print(trade_journal_table(db, limit=20))


def show_risk_report(db: TradingDatabase) -> None:
    console.print(risk_report_table(db))


def portfolio_menu(settings: Settings) -> None:
    actions = {
        "1": TuiMenuAction(
            "1",
            MENU_ACTION_SHOW_PAPER_PORTFOLIO,
            TITLE_PAPER_PORTFOLIO,
            show_portfolio,
        ),
        "2": TuiMenuAction(
            "2",
            MENU_ACTION_SHOW_TRADE_JOURNAL,
            TITLE_TRADE_JOURNAL,
            show_trade_journal,
        ),
        "3": TuiMenuAction(
            "3",
            MENU_ACTION_SHOW_DAILY_RISK_REPORT,
            TITLE_DAILY_RISK_REPORT,
            show_risk_report,
        ),
    }
    while True:
        console.clear()
        console.print(
            menu_table(
                TITLE_PORTFOLIO_AND_RISK,
                [*actions.values(), ("4", MENU_ACTION_BACK)],
            )
        )
        choice = Prompt.ask(
            PROMPT_SELECT_ACTION, choices=["1", "2", "3", "4"], default="1"
        )
        if choice == "4":
            return
        run_readonly_db_menu_action(settings, actions[choice])
        Prompt.ask(PROMPT_CONTINUE, default="")
