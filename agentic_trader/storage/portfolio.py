from datetime import datetime, timezone
from typing import cast
from uuid import uuid4

import duckdb

from agentic_trader.config import Settings
from agentic_trader.schemas import (
    AccountMark,
    DailyRiskReport,
    PortfolioSnapshot,
    PositionPlanSnapshot,
    PositionSnapshot,
    TradeSide,
)


def record_account_mark(
    conn: duckdb.DuckDBPyConnection,
    *,
    source: str,
    note: str,
    cycle_count: int | None = None,
    symbol: str | None = None,
) -> str:
    snapshot = get_account_snapshot(conn)
    mark_id = f"mark-{uuid4().hex[:12]}"
    conn.execute(
        """
        insert into account_marks (
            mark_id, created_at, source, note, cycle_count, symbol,
            cash, market_value, equity, realized_pnl, unrealized_pnl, open_positions
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            mark_id,
            datetime.now(timezone.utc).isoformat(),
            source,
            note,
            cycle_count,
            symbol,
            snapshot.cash,
            snapshot.market_value,
            snapshot.equity,
            snapshot.realized_pnl,
            snapshot.unrealized_pnl,
            snapshot.open_positions,
        ],
    )
    return mark_id


def list_account_marks(
    conn: duckdb.DuckDBPyConnection,
    limit: int = 20,
) -> list[AccountMark]:
    rows = conn.execute(
        """
        select mark_id, created_at, source, note, cycle_count, symbol,
               cash, market_value, equity, realized_pnl, unrealized_pnl, open_positions
        from account_marks
        order by created_at desc
        limit ?
        """,
        [limit],
    ).fetchall()
    marks: list[AccountMark] = []
    for row in rows:
        marks.append(
            AccountMark(
                mark_id=str(row[0]),
                created_at=str(row[1]),
                source=str(row[2]),
                note=str(row[3]),
                cycle_count=int(row[4]) if row[4] is not None else None,
                symbol=str(row[5]) if row[5] is not None else None,
                cash=float(row[6]),
                market_value=float(row[7]),
                equity=float(row[8]),
                realized_pnl=float(row[9]),
                unrealized_pnl=float(row[10]),
                open_positions=int(row[11]),
            )
        )
    return marks


def build_daily_risk_report(
    conn: duckdb.DuckDBPyConnection,
    settings: Settings,
    report_date: str | None = None,
) -> DailyRiskReport:
    resolved_date = report_date or datetime.now(timezone.utc).date().isoformat()
    snapshot = get_account_snapshot(conn)
    positions = list_positions(conn)
    fills_row = conn.execute(
        """
        select count(*), coalesce(sum(realized_pnl_delta), 0)
        from fills
        where created_at like ?
        """,
        [f"{resolved_date}%"],
    ).fetchone()
    marks_row = conn.execute(
        """
        select count(*), coalesce(max(equity), 0)
        from account_marks
        where created_at like ?
        """,
        [f"{resolved_date}%"],
    ).fetchone()
    peak_row = conn.execute("""
        select coalesce(max(equity), 0)
        from account_marks
        """).fetchone()
    fills_today = int(fills_row[0]) if fills_row is not None else 0
    daily_realized_pnl = float(fills_row[1]) if fills_row is not None else 0.0
    marks_recorded = int(marks_row[0]) if marks_row is not None else 0
    all_time_peak = float(peak_row[0]) if peak_row is not None else snapshot.equity
    gross_exposure = sum(abs(position.market_value) for position in positions)
    largest_position = max(
        (abs(position.market_value) for position in positions),
        default=0.0,
    )
    top_positions = sorted(
        positions,
        key=lambda position: abs(position.market_value),
        reverse=True,
    )
    equity = snapshot.equity if snapshot.equity != 0 else 1.0
    portfolio_hhi = (
        sum(
            (abs(position.market_value) / gross_exposure) ** 2 for position in positions
        )
        if gross_exposure > 0
        else 0.0
    )
    drawdown_from_peak_pct = (
        max(0.0, (all_time_peak - snapshot.equity) / all_time_peak)
        if all_time_peak > 0
        else 0.0
    )

    warnings: list[str] = []
    if snapshot.open_positions >= settings.max_open_positions:
        warnings.append("Open position count is elevated.")
    if gross_exposure / equity > settings.max_gross_exposure_pct:
        warnings.append(
            f"Gross exposure is above {settings.max_gross_exposure_pct:.0%} of equity."
        )
    if largest_position / equity > settings.max_position_pct:
        warnings.append(
            f"Largest position is above {settings.max_position_pct:.0%} of equity."
        )
    if portfolio_hhi > 0.25:
        warnings.append(
            f"Portfolio concentration HHI is elevated at {portfolio_hhi:.3f}."
        )
    if drawdown_from_peak_pct > 0.1:
        warnings.append("Portfolio drawdown from peak is above 10%.")

    return DailyRiskReport(
        report_date=resolved_date,
        generated_at=datetime.now(timezone.utc).isoformat(),
        cash=snapshot.cash,
        market_value=snapshot.market_value,
        equity=snapshot.equity,
        realized_pnl=snapshot.realized_pnl,
        unrealized_pnl=snapshot.unrealized_pnl,
        open_positions=snapshot.open_positions,
        fills_today=fills_today,
        marks_recorded=marks_recorded,
        daily_realized_pnl=daily_realized_pnl,
        gross_exposure_pct=gross_exposure / equity,
        largest_position_pct=largest_position / equity,
        portfolio_hhi=portfolio_hhi,
        top_position_symbols=[position.symbol for position in top_positions[:5]],
        drawdown_from_peak_pct=drawdown_from_peak_pct,
        warnings=warnings,
    )


def get_account_snapshot(conn: duckdb.DuckDBPyConnection) -> PortfolioSnapshot:
    row = conn.execute("""
        select cash, realized_pnl
        from account_state
        where account_id = 'paper'
        """).fetchone()
    if row is None:
        raise RuntimeError("Paper account state is missing")

    positions = list_positions(conn)
    market_value = sum(
        position.quantity * position.market_price for position in positions
    )
    unrealized_pnl = sum(position.unrealized_pnl for position in positions)
    cash = float(row[0])
    realized_pnl = float(row[1])
    equity = cash + market_value
    return PortfolioSnapshot(
        cash=cash,
        market_value=market_value,
        equity=equity,
        realized_pnl=realized_pnl,
        unrealized_pnl=unrealized_pnl,
        open_positions=len(positions),
    )


def get_position(
    conn: duckdb.DuckDBPyConnection,
    symbol: str,
) -> PositionSnapshot | None:
    row = conn.execute(
        """
        select symbol, quantity, average_price, market_price
        from positions
        where symbol = ?
        """,
        [symbol],
    ).fetchone()
    if row is None:
        return None

    quantity = float(row[1])
    average_price = float(row[2])
    market_price = float(row[3])
    market_value = quantity * market_price
    unrealized_pnl = (market_price - average_price) * quantity
    return PositionSnapshot(
        symbol=str(row[0]),
        quantity=quantity,
        average_price=average_price,
        market_price=market_price,
        market_value=market_value,
        unrealized_pnl=unrealized_pnl,
    )


def list_positions(conn: duckdb.DuckDBPyConnection) -> list[PositionSnapshot]:
    rows = conn.execute("""
        select symbol, quantity, average_price, market_price
        from positions
        where abs(quantity) > 0
        order by symbol
        """).fetchall()
    positions: list[PositionSnapshot] = []
    for row in rows:
        quantity = float(row[1])
        average_price = float(row[2])
        market_price = float(row[3])
        positions.append(
            PositionSnapshot(
                symbol=str(row[0]),
                quantity=quantity,
                average_price=average_price,
                market_price=market_price,
                market_value=quantity * market_price,
                unrealized_pnl=(market_price - average_price) * quantity,
            )
        )
    return positions


def save_position_plan(
    conn: duckdb.DuckDBPyConnection,
    *,
    symbol: str,
    side: str,
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    max_holding_bars: int,
    holding_bars: int,
    invalidation_logic: str,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        insert into position_plans (
            symbol, side, entry_price, stop_loss, take_profit,
            max_holding_bars, holding_bars, invalidation_logic, updated_at
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(symbol) do update set
            side = excluded.side,
            entry_price = excluded.entry_price,
            stop_loss = excluded.stop_loss,
            take_profit = excluded.take_profit,
            max_holding_bars = excluded.max_holding_bars,
            holding_bars = excluded.holding_bars,
            invalidation_logic = excluded.invalidation_logic,
            updated_at = excluded.updated_at
        """,
        [
            symbol,
            side,
            entry_price,
            stop_loss,
            take_profit,
            max_holding_bars,
            holding_bars,
            invalidation_logic,
            now,
        ],
    )


def get_position_plan(
    conn: duckdb.DuckDBPyConnection,
    symbol: str,
) -> PositionPlanSnapshot | None:
    row = conn.execute(
        """
        select symbol, side, entry_price, stop_loss, take_profit,
               max_holding_bars, holding_bars, invalidation_logic, updated_at
        from position_plans
        where symbol = ?
        """,
        [symbol],
    ).fetchone()
    if row is None:
        return None
    return PositionPlanSnapshot(
        symbol=str(row[0]),
        side=cast(TradeSide, str(row[1])),
        entry_price=float(row[2]),
        stop_loss=float(row[3]),
        take_profit=float(row[4]),
        max_holding_bars=int(row[5]),
        holding_bars=int(row[6]),
        invalidation_logic=str(row[7]),
        updated_at=str(row[8]),
    )


def list_position_plans(
    conn: duckdb.DuckDBPyConnection,
) -> list[PositionPlanSnapshot]:
    rows = conn.execute("""
        select symbol, side, entry_price, stop_loss, take_profit,
               max_holding_bars, holding_bars, invalidation_logic, updated_at
        from position_plans
        order by symbol
        """).fetchall()
    plans: list[PositionPlanSnapshot] = []
    for row in rows:
        plans.append(
            PositionPlanSnapshot(
                symbol=str(row[0]),
                side=cast(TradeSide, str(row[1])),
                entry_price=float(row[2]),
                stop_loss=float(row[3]),
                take_profit=float(row[4]),
                max_holding_bars=int(row[5]),
                holding_bars=int(row[6]),
                invalidation_logic=str(row[7]),
                updated_at=str(row[8]),
            )
        )
    return plans


def update_position_plan_holding(
    conn: duckdb.DuckDBPyConnection,
    symbol: str,
    holding_bars: int,
) -> None:
    conn.execute(
        """
        update position_plans
        set holding_bars = ?, updated_at = ?
        where symbol = ?
        """,
        [holding_bars, datetime.now(timezone.utc).isoformat(), symbol],
    )


def delete_position_plan(conn: duckdb.DuckDBPyConnection, symbol: str) -> None:
    conn.execute(
        "delete from position_plans where symbol = ?",
        [symbol],
    )


def apply_fill(
    conn: duckdb.DuckDBPyConnection,
    *,
    fill_id: str,
    order_id: str,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    cash_delta: float,
    realized_pnl_delta: float,
    new_quantity: float,
    new_average_price: float,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        insert into fills (
            fill_id, order_id, created_at, symbol, side, quantity, price,
            cash_delta, realized_pnl_delta
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            fill_id,
            order_id,
            now,
            symbol,
            side,
            quantity,
            price,
            cash_delta,
            realized_pnl_delta,
        ],
    )
    conn.execute(
        """
        update account_state
        set updated_at = ?, cash = cash + ?, realized_pnl = realized_pnl + ?
        where account_id = 'paper'
        """,
        [now, cash_delta, realized_pnl_delta],
    )
    conn.execute(
        """
        insert into positions (symbol, quantity, average_price, market_price, updated_at)
        values (?, ?, ?, ?, ?)
        on conflict(symbol) do update set
            quantity = excluded.quantity,
            average_price = excluded.average_price,
            market_price = excluded.market_price,
            updated_at = excluded.updated_at
        """,
        [symbol, new_quantity, new_average_price, price, now],
    )


def mark_price(
    conn: duckdb.DuckDBPyConnection,
    symbol: str,
    market_price: float,
) -> None:
    conn.execute(
        """
        update positions
        set market_price = ?, updated_at = ?
        where symbol = ?
        """,
        [market_price, datetime.now(timezone.utc).isoformat(), symbol],
    )
