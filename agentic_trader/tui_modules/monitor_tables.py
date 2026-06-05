from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table

from agentic_trader.schemas import InvestmentPreferences
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.ui_text import UI_LIST_SEPARATOR, t

console = Console()


def render_preferences(preferences: InvestmentPreferences) -> Table:
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
