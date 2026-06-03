"""Position read helpers for the paper portfolio store."""

import duckdb

from agentic_trader.schemas import PositionSnapshot


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
