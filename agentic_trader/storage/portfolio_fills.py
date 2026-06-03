"""Fill and price-mark write helpers for the paper portfolio store."""

from datetime import datetime, timezone

import duckdb


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
