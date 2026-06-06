from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table

from agentic_trader.schemas import InvestmentPreferences
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.ui_text import UI_LIST_SEPARATOR, t

console = Console()


def render_preferences(preferences: InvestmentPreferences) -> Table:
    """
    Builds a Rich Table showing investment preference settings.
    
    List-valued fields (regions, exchanges, currencies, sectors) are joined with UI_LIST_SEPARATOR; empty lists and missing notes are rendered as "-". Column headers and labels use the translation helper `t(...)`.
    
    Returns:
        table (Table): Rich Table with two columns ("setting", "value") populated from the given preferences.
    """
    table = Table(title=t("title.investment.preferences"))
    table.add_column(t("label.setting"))
    table.add_column(t("label.value"))
    table.add_row(t("label.regions"), UI_LIST_SEPARATOR.join(preferences.regions) or "-")
    table.add_row(t("label.exchanges"), UI_LIST_SEPARATOR.join(preferences.exchanges) or "-")
    table.add_row(
        t("label.currencies"), UI_LIST_SEPARATOR.join(preferences.currencies) or "-"
    )
    table.add_row(t("label.sectors"), UI_LIST_SEPARATOR.join(preferences.sectors) or "-")
    table.add_row(t("label.risk.profile"), preferences.risk_profile)
    table.add_row(t("label.trade.style"), preferences.trade_style)
    table.add_row(t("label.behavior.preset"), preferences.behavior_preset)
    table.add_row(t("label.agent.profile"), preferences.agent_profile)
    table.add_row(t("label.agent.tone"), preferences.agent_tone)
    table.add_row(t("label.strictness"), preferences.strictness_preset)
    table.add_row(t("label.intervention"), preferences.intervention_style)
    table.add_row(t("label.notes"), preferences.notes or "-")
    return table


def render_recent_runs(db: TradingDatabase) -> None:
    """
    Render a table of recent runs to the console.
    
    Prints a table of up to 8 recent runs retrieved from the database. If no runs are found, prints a highlighted panel informing the user instead. Each displayed row contains the run id, creation time, symbol, interval, and approval status.
    """
    runs = db.list_recent_runs(limit=8)
    table = Table(title=t("title.recent.runs"))
    table.add_column(t("label.run.id"))
    table.add_column(t("label.created"))
    table.add_column(t("label.symbol"))
    table.add_column(t("label.interval"))
    table.add_column(t("label.approved"))
    if not runs:
        console.print(
            Panel(
                t("message.no.runs.recorded"),
                title=t("title.recent.runs"),
                border_style="yellow",
            )
        )
        return
    for run_id, created_at, symbol, interval, approved in runs:
        table.add_row(run_id, created_at, symbol, interval, str(approved))
    console.print(table)


def recent_runs_table(db: TradingDatabase) -> Table:
    """
    Builds a Rich Table listing up to eight recent runs.
    
    If no runs are available the table contains a single row of "-" placeholders for each column.
    
    Returns:
        Table: A Rich Table with columns for run id, created time, symbol, interval, and approved; rows contain recent run data with `approved` converted to a string.
    """
    runs = db.list_recent_runs(limit=8)
    table = Table(title=t("title.recent.runs"))
    table.add_column(t("label.run.id"))
    table.add_column(t("label.created"))
    table.add_column(t("label.symbol"))
    table.add_column(t("label.interval"))
    table.add_column(t("label.approved"))
    if not runs:
        table.add_row("-", "-", "-", "-", "-")
        return table
    for run_id, created_at, symbol, interval, approved in runs:
        table.add_row(run_id, created_at, symbol, interval, str(approved))
    return table


def trade_journal_table(db: TradingDatabase, *, limit: int = 8) -> Table:
    """
    Builds a Rich Table displaying recent trade journal entries.
    
    The table has columns for opened time, symbol, status, side, and PnL. Realized PnL is formatted with two decimal places; if an entry's realized_pnl is None the PnL cell contains "-". If there are no entries, the table contains a single row of "-" placeholders for all columns.
    
    Parameters:
        limit (int): Maximum number of journal entries to include.
    
    Returns:
        table (Table): A Rich Table populated with up to `limit` trade journal rows.
    """
    entries = db.list_trade_journal(limit=limit)
    table = Table(title=t("title.trade.journal"))
    table.add_column(t("label.opened"))
    table.add_column(t("label.symbol"))
    table.add_column(t("label.status"))
    table.add_column(t("label.side"))
    table.add_column(t("label.pnl"))
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
    """
    Builds a Rich Table presenting the daily risk report for the report's date.
    
    The table contains labeled rows for equity, gross exposure, largest position, drawdown from peak, fills today, and the number of warnings; numeric values are formatted for display.
    
    Returns:
    	Table: A Rich Table titled with the report date and populated with the day's risk metrics.
    """
    report = db.build_daily_risk_report()
    table = Table(
        title=t("title.daily.risk.report.for.date", report_date=report.report_date)
    )
    table.add_column(t("label.field"))
    table.add_column(t("label.value"))
    table.add_row(t("label.equity"), f"{report.equity:.2f}")
    table.add_row(t("label.gross.exposure"), f"{report.gross_exposure_pct:.2%}")
    table.add_row(t("label.largest.position"), f"{report.largest_position_pct:.2%}")
    table.add_row(t("label.drawdown.from.peak"), f"{report.drawdown_from_peak_pct:.2%}")
    table.add_row(t("label.fills.today"), str(report.fills_today))
    table.add_row(t("label.warnings"), str(len(report.warnings)))
    return table


def portfolio_renderable(db: TradingDatabase) -> Group:
    """
    Builds a portfolio summary renderable containing a metrics table and a positions table.
    
    Produces a Rich Group with two tables:
    - a summary table of portfolio metrics (cash, market value, equity, realized and unrealized PnL, open positions, marked-at time and mark source) with values formatted and annotated with the account currency;
    - a positions table listing symbol, quantity, average price, market price, market value and unrealized PnL, using a single row of "-" placeholders when no positions exist.
    
    Parameters:
        db (TradingDatabase): Database handle used to fetch the account snapshot, preferences, recent marks and current positions.
    
    Returns:
        Group: A Rich Group containing the populated summary table and positions table.
    """
    snapshot = db.get_account_snapshot()
    preferences = db.load_preferences()
    currency = (preferences.currencies[0] if preferences.currencies else "USD").upper()
    latest_marks = db.list_account_marks(limit=1)
    mark_time = (
        latest_marks[0].created_at if latest_marks else t("message.mark.time.unavailable")
    )
    mark_source = latest_marks[0].source if latest_marks else "-"
    currency_suffix = " (" + currency + ")"
    paper_mark_suffix = " (" + currency + ", " + t("label.paper.mark") + ")"
    summary = Table(title=t("title.portfolio"))
    summary.add_column(t("label.metric"))
    summary.add_column(t("label.value"))
    summary.add_row(t("label.cash") + currency_suffix, f"{snapshot.cash:.2f}")
    summary.add_row(
        t("label.market.value") + currency_suffix, f"{snapshot.market_value:.2f}"
    )
    summary.add_row(t("label.equity") + currency_suffix, f"{snapshot.equity:.2f}")
    summary.add_row(
        t("label.realized.pnl") + currency_suffix, f"{snapshot.realized_pnl:.2f}"
    )
    summary.add_row(
        t("label.unrealized.pnl") + paper_mark_suffix,
        f"{snapshot.unrealized_pnl:.2f}",
    )
    summary.add_row(t("label.open.positions"), str(snapshot.open_positions))
    summary.add_row(t("label.marked.at"), mark_time)
    summary.add_row(t("label.mark.source"), mark_source)

    positions = db.list_positions()
    positions_table = Table(title=t("title.positions"))
    positions_table.add_column(t("label.symbol"))
    positions_table.add_column(t("label.quantity"))
    positions_table.add_column(t("label.average.price"))
    positions_table.add_column(t("label.market.price"))
    positions_table.add_column(t("label.market.value"))
    positions_table.add_column(t("label.unrealized.pnl"))
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
