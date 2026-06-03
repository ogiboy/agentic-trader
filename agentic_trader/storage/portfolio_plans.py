"""Position-plan persistence helpers for the paper portfolio store."""

from datetime import datetime, timezone
from typing import Any, cast

import duckdb

from agentic_trader.schemas import PositionPlanSnapshot, TradeSide


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
    return _position_plan_snapshot(row)


def list_position_plans(
    conn: duckdb.DuckDBPyConnection,
) -> list[PositionPlanSnapshot]:
    rows = conn.execute("""
        select symbol, side, entry_price, stop_loss, take_profit,
               max_holding_bars, holding_bars, invalidation_logic, updated_at
        from position_plans
        order by symbol
        """).fetchall()
    return [_position_plan_snapshot(row) for row in rows]


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


def _position_plan_snapshot(row: tuple[Any, ...]) -> PositionPlanSnapshot:
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
