"""Daily risk-report helpers for the paper portfolio store."""

from dataclasses import dataclass
from datetime import datetime, timezone

import duckdb

from agentic_trader.config import Settings
from agentic_trader.schemas import DailyRiskReport, PortfolioSnapshot, PositionSnapshot
from agentic_trader.storage.portfolio_account import get_account_snapshot
from agentic_trader.storage.portfolio_positions import list_positions


@dataclass(frozen=True)
class _DailyActivityStats:
    fills_today: int
    daily_realized_pnl: float
    marks_recorded: int
    all_time_peak: float


@dataclass(frozen=True)
class _ExposureStats:
    gross_exposure: float
    largest_position: float
    portfolio_hhi: float
    drawdown_from_peak_pct: float
    top_position_symbols: list[str]


def build_daily_risk_report(
    conn: duckdb.DuckDBPyConnection,
    settings: Settings,
    report_date: str | None = None,
) -> DailyRiskReport:
    resolved_date = report_date or datetime.now(timezone.utc).date().isoformat()
    snapshot = get_account_snapshot(conn)
    positions = list_positions(conn)
    daily_stats = _daily_activity_stats(conn, resolved_date, snapshot)
    equity = snapshot.equity if snapshot.equity != 0 else 1.0
    exposure = _exposure_stats(
        positions,
        equity=equity,
        all_time_peak=daily_stats.all_time_peak,
        current_equity=snapshot.equity,
    )

    return DailyRiskReport(
        report_date=resolved_date,
        generated_at=datetime.now(timezone.utc).isoformat(),
        cash=snapshot.cash,
        market_value=snapshot.market_value,
        equity=snapshot.equity,
        realized_pnl=snapshot.realized_pnl,
        unrealized_pnl=snapshot.unrealized_pnl,
        open_positions=snapshot.open_positions,
        fills_today=daily_stats.fills_today,
        marks_recorded=daily_stats.marks_recorded,
        daily_realized_pnl=daily_stats.daily_realized_pnl,
        gross_exposure_pct=exposure.gross_exposure / equity,
        largest_position_pct=exposure.largest_position / equity,
        portfolio_hhi=exposure.portfolio_hhi,
        top_position_symbols=exposure.top_position_symbols,
        drawdown_from_peak_pct=exposure.drawdown_from_peak_pct,
        warnings=_risk_warnings(
            settings=settings,
            snapshot=snapshot,
            equity=equity,
            exposure=exposure,
        ),
    )


def _daily_activity_stats(
    conn: duckdb.DuckDBPyConnection,
    report_date: str,
    snapshot: PortfolioSnapshot,
) -> _DailyActivityStats:
    fills_row = conn.execute(
        """
        select count(*), coalesce(sum(realized_pnl_delta), 0)
        from fills
        where created_at like ?
        """,
        [f"{report_date}%"],
    ).fetchone()
    marks_row = conn.execute(
        """
        select count(*), coalesce(max(equity), 0)
        from account_marks
        where created_at like ?
        """,
        [f"{report_date}%"],
    ).fetchone()
    peak_row = conn.execute("""
        select coalesce(max(equity), 0)
        from account_marks
        """).fetchone()
    return _DailyActivityStats(
        fills_today=int(fills_row[0]) if fills_row is not None else 0,
        daily_realized_pnl=float(fills_row[1]) if fills_row is not None else 0.0,
        marks_recorded=int(marks_row[0]) if marks_row is not None else 0,
        all_time_peak=(float(peak_row[0]) if peak_row is not None else snapshot.equity),
    )


def _exposure_stats(
    positions: list[PositionSnapshot],
    *,
    equity: float,
    all_time_peak: float,
    current_equity: float,
) -> _ExposureStats:
    _ = equity
    gross_exposure = sum(abs(position.market_value) for position in positions)
    largest_position = max(
        (abs(position.market_value) for position in positions),
        default=0.0,
    )
    portfolio_hhi = (
        sum(
            (abs(position.market_value) / gross_exposure) ** 2 for position in positions
        )
        if gross_exposure > 0
        else 0.0
    )
    drawdown_from_peak_pct = (
        max(0.0, (all_time_peak - current_equity) / all_time_peak)
        if all_time_peak > 0
        else 0.0
    )
    top_positions = sorted(
        positions,
        key=lambda position: abs(position.market_value),
        reverse=True,
    )
    return _ExposureStats(
        gross_exposure=gross_exposure,
        largest_position=largest_position,
        portfolio_hhi=portfolio_hhi,
        drawdown_from_peak_pct=drawdown_from_peak_pct,
        top_position_symbols=[position.symbol for position in top_positions[:5]],
    )


def _risk_warnings(
    *,
    settings: Settings,
    snapshot: PortfolioSnapshot,
    equity: float,
    exposure: _ExposureStats,
) -> list[str]:
    warnings: list[str] = []
    if snapshot.open_positions >= settings.max_open_positions:
        warnings.append("Open position count is elevated.")
    if exposure.gross_exposure / equity > settings.max_gross_exposure_pct:
        warnings.append(
            f"Gross exposure is above {settings.max_gross_exposure_pct:.0%} of equity."
        )
    if exposure.largest_position / equity > settings.max_position_pct:
        warnings.append(
            f"Largest position is above {settings.max_position_pct:.0%} of equity."
        )
    if exposure.portfolio_hhi > 0.25:
        warnings.append(
            f"Portfolio concentration HHI is elevated at {exposure.portfolio_hhi:.3f}."
        )
    if exposure.drawdown_from_peak_pct > 0.1:
        warnings.append("Portfolio drawdown from peak is above 10%.")
    return warnings
