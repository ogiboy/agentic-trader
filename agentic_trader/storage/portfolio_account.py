"""Account marks and account snapshot helpers for the paper portfolio store."""

from datetime import datetime, timezone
from uuid import uuid4

import duckdb

from agentic_trader.schemas import AccountMark, PortfolioSnapshot
from agentic_trader.storage.portfolio_positions import list_positions


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
