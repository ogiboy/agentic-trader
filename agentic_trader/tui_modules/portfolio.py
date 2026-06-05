from rich.prompt import Prompt

from agentic_trader.config import Settings
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.tui_modules.common import (
    TuiMenuAction,
    console,
    menu_table,
    run_readonly_db_menu_action,
)
from agentic_trader.tui_modules.monitor_tables import (
    portfolio_renderable,
    risk_report_table,
    trade_journal_table,
)
from agentic_trader.ui_text import t


def show_portfolio(db: TradingDatabase) -> None:
    """
    Display the portfolio view and its risk report to the console.
    
    Parameters:
        db (TradingDatabase): Trading database used to build the portfolio and risk report views.
    """
    console.print(portfolio_renderable(db))
    console.print(risk_report_table(db))


def show_trade_journal(db: TradingDatabase) -> None:
    console.print(trade_journal_table(db, limit=20))


def show_risk_report(db: TradingDatabase) -> None:
    console.print(risk_report_table(db))


def portfolio_menu(settings: Settings) -> None:
    """
    Display an interactive portfolio and risk menu in the TUI and run the selected read-only action.
    
    Shows options to view the paper portfolio (with risk report), the trade journal, or the daily risk report. Presents a "back" option to exit the menu. The provided Settings object is used when executing the selected read-only database actions.
    Parameters:
        settings (Settings): Application settings used to run the selected read-only database menu actions.
    """
    actions = {
        "1": TuiMenuAction(
            "1",
            t("menu.action.show.paper.portfolio"),
            t("title.paper.portfolio"),
            show_portfolio,
        ),
        "2": TuiMenuAction(
            "2",
            t("menu.action.show.trade.journal"),
            t("title.trade.journal"),
            show_trade_journal,
        ),
        "3": TuiMenuAction(
            "3",
            t("menu.action.show.daily.risk.report"),
            t("title.daily.risk.report"),
            show_risk_report,
        ),
    }
    while True:
        console.clear()
        console.print(
            menu_table(
                t("title.portfolio.and.risk"),
                [*actions.values(), ("4", t("menu.action.back"))],
            )
        )
        choice = Prompt.ask(
            t("prompt.select.action"), choices=["1", "2", "3", "4"], default="1"
        )
        if choice == "4":
            return
        run_readonly_db_menu_action(settings, actions[choice])
        Prompt.ask(t("prompt.continue"), default="")
