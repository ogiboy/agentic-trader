"""Order persistence helpers."""

from __future__ import annotations

from typing import Any

import duckdb

type OrderRow = tuple[str, str, str, str, bool, float, float, float, float, float]


def insert_order(conn: duckdb.DuckDBPyConnection, order: dict[str, Any]) -> None:
    conn.execute(
        """
        insert into orders (
            order_id, created_at, symbol, side, approved, entry_price,
            stop_loss, take_profit, position_size_pct, confidence, rationale
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            order["order_id"],
            order["created_at"],
            order["symbol"],
            order["side"],
            order["approved"],
            order["entry_price"],
            order["stop_loss"],
            order["take_profit"],
            order["position_size_pct"],
            order["confidence"],
            order["rationale"],
        ],
    )


def latest_order(conn: duckdb.DuckDBPyConnection) -> OrderRow | None:
    row = conn.execute("""
        select order_id, created_at, symbol, side, approved, entry_price,
               stop_loss, take_profit, position_size_pct, confidence
        from orders
        order by created_at desc
        limit 1
        """).fetchone()
    if row is None:
        return None

    return (
        str(row[0]),
        str(row[1]),
        str(row[2]),
        str(row[3]),
        bool(row[4]),
        float(row[5]),
        float(row[6]),
        float(row[7]),
        float(row[8]),
        float(row[9]),
    )
