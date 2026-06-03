from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table

from agentic_trader.schemas import InvestmentPreferences
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.ui_text import (
    LABEL_AGENT_PROFILE,
    LABEL_AGENT_TONE,
    LABEL_APPROVED,
    LABEL_AVERAGE_PRICE,
    LABEL_BEHAVIOR_PRESET,
    LABEL_CASH,
    LABEL_CREATED,
    LABEL_CURRENCIES,
    LABEL_DRAWDOWN_FROM_PEAK,
    LABEL_EQUITY,
    LABEL_EXCHANGES,
    LABEL_FIELD,
    LABEL_FILLS_TODAY,
    LABEL_GROSS_EXPOSURE,
    LABEL_INTERVAL,
    LABEL_INTERVENTION,
    LABEL_LARGEST_POSITION,
    LABEL_MARK_SOURCE,
    LABEL_MARKED_AT,
    LABEL_MARKET_PRICE,
    LABEL_MARKET_VALUE,
    LABEL_METRIC,
    LABEL_NOTES,
    LABEL_OPEN_POSITIONS,
    LABEL_OPENED,
    LABEL_PAPER_MARK,
    LABEL_PNL,
    LABEL_QUANTITY,
    LABEL_REALIZED_PNL,
    LABEL_REGIONS,
    LABEL_RISK_PROFILE,
    LABEL_RUN_ID,
    LABEL_SECTORS,
    LABEL_SETTING,
    LABEL_SIDE,
    LABEL_STATUS,
    LABEL_STRICTNESS,
    LABEL_SYMBOL,
    LABEL_TRADE_STYLE,
    LABEL_UNREALIZED_PNL,
    LABEL_VALUE,
    LABEL_WARNINGS,
    MESSAGE_MARK_TIME_UNAVAILABLE,
    MESSAGE_NO_RUNS_RECORDED,
    TITLE_DAILY_RISK_REPORT_FOR_DATE,
    TITLE_INVESTMENT_PREFERENCES,
    TITLE_PORTFOLIO,
    TITLE_POSITIONS,
    TITLE_RECENT_RUNS,
    TITLE_TRADE_JOURNAL,
    UI_LIST_SEPARATOR,
)

console = Console()


def render_preferences(preferences: InvestmentPreferences) -> Table:
    table = Table(title=TITLE_INVESTMENT_PREFERENCES)
    table.add_column(LABEL_SETTING)
    table.add_column(LABEL_VALUE)
    table.add_row(LABEL_REGIONS, UI_LIST_SEPARATOR.join(preferences.regions) or "-")
    table.add_row(LABEL_EXCHANGES, UI_LIST_SEPARATOR.join(preferences.exchanges) or "-")
    table.add_row(
        LABEL_CURRENCIES, UI_LIST_SEPARATOR.join(preferences.currencies) or "-"
    )
    table.add_row(LABEL_SECTORS, UI_LIST_SEPARATOR.join(preferences.sectors) or "-")
    table.add_row(LABEL_RISK_PROFILE, preferences.risk_profile)
    table.add_row(LABEL_TRADE_STYLE, preferences.trade_style)
    table.add_row(LABEL_BEHAVIOR_PRESET, preferences.behavior_preset)
    table.add_row(LABEL_AGENT_PROFILE, preferences.agent_profile)
    table.add_row(LABEL_AGENT_TONE, preferences.agent_tone)
    table.add_row(LABEL_STRICTNESS, preferences.strictness_preset)
    table.add_row(LABEL_INTERVENTION, preferences.intervention_style)
    table.add_row(LABEL_NOTES, preferences.notes or "-")
    return table


def render_recent_runs(db: TradingDatabase) -> None:
    runs = db.list_recent_runs(limit=8)
    table = Table(title=TITLE_RECENT_RUNS)
    table.add_column(LABEL_RUN_ID)
    table.add_column(LABEL_CREATED)
    table.add_column(LABEL_SYMBOL)
    table.add_column(LABEL_INTERVAL)
    table.add_column(LABEL_APPROVED)
    if not runs:
        console.print(
            Panel(
                MESSAGE_NO_RUNS_RECORDED,
                title=TITLE_RECENT_RUNS,
                border_style="yellow",
            )
        )
        return
    for run_id, created_at, symbol, interval, approved in runs:
        table.add_row(run_id, created_at, symbol, interval, str(approved))
    console.print(table)


def recent_runs_table(db: TradingDatabase) -> Table:
    runs = db.list_recent_runs(limit=8)
    table = Table(title=TITLE_RECENT_RUNS)
    table.add_column(LABEL_RUN_ID)
    table.add_column(LABEL_CREATED)
    table.add_column(LABEL_SYMBOL)
    table.add_column(LABEL_INTERVAL)
    table.add_column(LABEL_APPROVED)
    if not runs:
        table.add_row("-", "-", "-", "-", "-")
        return table
    for run_id, created_at, symbol, interval, approved in runs:
        table.add_row(run_id, created_at, symbol, interval, str(approved))
    return table


def trade_journal_table(db: TradingDatabase, *, limit: int = 8) -> Table:
    entries = db.list_trade_journal(limit=limit)
    table = Table(title=TITLE_TRADE_JOURNAL)
    table.add_column(LABEL_OPENED)
    table.add_column(LABEL_SYMBOL)
    table.add_column(LABEL_STATUS)
    table.add_column(LABEL_SIDE)
    table.add_column(LABEL_PNL)
    if not entries:
        table.add_row("-", "-", "-", "-", "-")
        return table
    for entry in entries:
        table.add_row(
            entry.opened_at,
            entry.symbol,
            entry.journal_status,
            entry.planned_side,
            f"{entry.realized_pnl:.2f}" if entry.realized_pnl is not None else "-",
        )
    return table


def risk_report_table(db: TradingDatabase) -> Table:
    report = db.build_daily_risk_report()
    table = Table(
        title=TITLE_DAILY_RISK_REPORT_FOR_DATE.format(report_date=report.report_date)
    )
    table.add_column(LABEL_FIELD)
    table.add_column(LABEL_VALUE)
    table.add_row(LABEL_EQUITY, f"{report.equity:.2f}")
    table.add_row(LABEL_GROSS_EXPOSURE, f"{report.gross_exposure_pct:.2%}")
    table.add_row(LABEL_LARGEST_POSITION, f"{report.largest_position_pct:.2%}")
    table.add_row(LABEL_DRAWDOWN_FROM_PEAK, f"{report.drawdown_from_peak_pct:.2%}")
    table.add_row(LABEL_FILLS_TODAY, str(report.fills_today))
    table.add_row(LABEL_WARNINGS, str(len(report.warnings)))
    return table


def portfolio_renderable(db: TradingDatabase) -> Group:
    snapshot = db.get_account_snapshot()
    preferences = db.load_preferences()
    currency = (preferences.currencies[0] if preferences.currencies else "USD").upper()
    latest_marks = db.list_account_marks(limit=1)
    mark_time = (
        latest_marks[0].created_at if latest_marks else MESSAGE_MARK_TIME_UNAVAILABLE
    )
    mark_source = latest_marks[0].source if latest_marks else "-"
    currency_suffix = " (" + currency + ")"
    paper_mark_suffix = " (" + currency + ", " + LABEL_PAPER_MARK + ")"
    summary = Table(title=TITLE_PORTFOLIO)
    summary.add_column(LABEL_METRIC)
    summary.add_column(LABEL_VALUE)
    summary.add_row(LABEL_CASH + currency_suffix, f"{snapshot.cash:.2f}")
    summary.add_row(
        LABEL_MARKET_VALUE + currency_suffix, f"{snapshot.market_value:.2f}"
    )
    summary.add_row(LABEL_EQUITY + currency_suffix, f"{snapshot.equity:.2f}")
    summary.add_row(
        LABEL_REALIZED_PNL + currency_suffix, f"{snapshot.realized_pnl:.2f}"
    )
    summary.add_row(
        LABEL_UNREALIZED_PNL + paper_mark_suffix,
        f"{snapshot.unrealized_pnl:.2f}",
    )
    summary.add_row(LABEL_OPEN_POSITIONS, str(snapshot.open_positions))
    summary.add_row(LABEL_MARKED_AT, mark_time)
    summary.add_row(LABEL_MARK_SOURCE, mark_source)

    positions = db.list_positions()
    positions_table = Table(title=TITLE_POSITIONS)
    positions_table.add_column(LABEL_SYMBOL)
    positions_table.add_column(LABEL_QUANTITY)
    positions_table.add_column(LABEL_AVERAGE_PRICE)
    positions_table.add_column(LABEL_MARKET_PRICE)
    positions_table.add_column(LABEL_MARKET_VALUE)
    positions_table.add_column(LABEL_UNREALIZED_PNL)
    if not positions:
        positions_table.add_row("-", "-", "-", "-", "-", "-")
    else:
        for position in positions:
            positions_table.add_row(
                position.symbol,
                f"{position.quantity:.6f}",
                f"{position.average_price:.4f}",
                f"{position.market_price:.4f}",
                f"{position.market_value:.2f}",
                f"{position.unrealized_pnl:.2f}",
            )
    return Group(summary, positions_table)


__all__ = (
    "portfolio_renderable",
    "recent_runs_table",
    "render_preferences",
    "render_recent_runs",
    "risk_report_table",
    "trade_journal_table",
)
