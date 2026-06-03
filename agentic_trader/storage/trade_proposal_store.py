"""Trade proposal persistence helpers."""

from collections.abc import Sequence
from typing import Any, Literal, cast

import duckdb

from agentic_trader.schemas import (
    TradeProposalRecord,
    TradeProposalStatus,
    TradeSide,
)
from agentic_trader.storage.proposal_row_utils import str_or_none
from agentic_trader.storage.schema import table_exists


def insert_trade_proposal(
    conn: duckdb.DuckDBPyConnection,
    proposal: TradeProposalRecord,
) -> None:
    execute_trade_proposal_insert(conn, proposal)


def get_trade_proposal(
    conn: duckdb.DuckDBPyConnection,
    proposal_id: str,
) -> TradeProposalRecord | None:
    if not table_exists(conn, "trade_proposals"):
        return None
    rows = trade_proposal_rows(
        conn,
        """
        select *
        from trade_proposals
        where proposal_id = ?
        """,
        [proposal_id],
    )
    return rows[0] if rows else None


def list_trade_proposals(
    conn: duckdb.DuckDBPyConnection,
    *,
    status: TradeProposalStatus | None = None,
    limit: int = 50,
) -> list[TradeProposalRecord]:
    if not table_exists(conn, "trade_proposals"):
        return []
    if status is None:
        return trade_proposal_rows(
            conn,
            """
            select *
            from trade_proposals
            order by created_at desc
            limit ?
            """,
            [limit],
        )
    return trade_proposal_rows(
        conn,
        """
        select *
        from trade_proposals
        where status = ?
        order by created_at desc
        limit ?
        """,
        [status, limit],
    )


def update_trade_proposal(
    conn: duckdb.DuckDBPyConnection,
    proposal: TradeProposalRecord,
    *,
    expected_status: TradeProposalStatus | None = None,
) -> bool:
    if not table_exists(conn, "trade_proposals"):
        return False
    if expected_status is not None:
        conn.execute("begin transaction")
        try:
            current = conn.execute(
                """
                select status
                from trade_proposals
                where proposal_id = ?
                """,
                [proposal.proposal_id],
            ).fetchone()
            if current is None or str(current[0]) != expected_status:
                conn.execute("commit")
                return False
            execute_trade_proposal_update(conn, proposal)
            conn.execute("commit")
            return True
        except Exception:
            conn.execute("rollback")
            raise
    execute_trade_proposal_update(conn, proposal)
    return True


def execute_trade_proposal_insert(
    conn: duckdb.DuckDBPyConnection,
    proposal: TradeProposalRecord,
) -> None:
    conn.execute(
        """
        insert into trade_proposals (
            proposal_id, created_at, updated_at, symbol, side, order_type,
            quantity, notional, reference_price, confidence, thesis, stop_loss,
            take_profit, invalidation_condition, source, status, review_notes,
            rejection_reason, execution_intent_id, execution_order_id,
            execution_outcome_status, limit_price
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            proposal.proposal_id,
            proposal.created_at,
            proposal.updated_at,
            proposal.symbol,
            proposal.side,
            proposal.order_type,
            proposal.quantity,
            proposal.notional,
            proposal.reference_price,
            proposal.confidence,
            proposal.thesis,
            proposal.stop_loss,
            proposal.take_profit,
            proposal.invalidation_condition,
            proposal.source,
            proposal.status,
            proposal.review_notes,
            proposal.rejection_reason,
            proposal.execution_intent_id,
            proposal.execution_order_id,
            proposal.execution_outcome_status,
            proposal.limit_price,
        ],
    )


def execute_trade_proposal_update(
    conn: duckdb.DuckDBPyConnection,
    proposal: TradeProposalRecord,
) -> None:
    conn.execute(
        """
        update trade_proposals
        set updated_at = ?,
            status = ?,
            review_notes = ?,
            rejection_reason = ?,
            execution_intent_id = ?,
            execution_order_id = ?,
            execution_outcome_status = ?
        where proposal_id = ?
        """,
        [
            proposal.updated_at,
            proposal.status,
            proposal.review_notes,
            proposal.rejection_reason,
            proposal.execution_intent_id,
            proposal.execution_order_id,
            proposal.execution_outcome_status,
            proposal.proposal_id,
        ],
    )


def trade_proposal_rows(
    conn: duckdb.DuckDBPyConnection,
    query: str,
    params: list[object],
) -> list[TradeProposalRecord]:
    rows = conn.execute(query, params).fetchall()
    return [trade_proposal_record_from_row(row) for row in rows]


def trade_proposal_record_from_row(row: object) -> TradeProposalRecord:
    values = list(cast(Sequence[Any], row))
    return TradeProposalRecord(
        proposal_id=str(values[0]),
        created_at=str(values[1]),
        updated_at=str(values[2]),
        symbol=str(values[3]),
        side=cast(TradeSide, str(values[4])),
        order_type=cast(Literal["market", "limit"], str(values[5])),
        quantity=float(values[6]) if values[6] is not None else None,
        notional=float(values[7]) if values[7] is not None else None,
        limit_price=(
            float(values[21]) if len(values) > 21 and values[21] is not None else None
        ),
        reference_price=float(values[8]),
        confidence=float(values[9]),
        thesis=str(values[10]),
        stop_loss=float(values[11]) if values[11] is not None else None,
        take_profit=float(values[12]) if values[12] is not None else None,
        invalidation_condition=str_or_none(values[13]),
        source=str(values[14]),
        status=cast(TradeProposalStatus, str(values[15])),
        review_notes=str(values[16]),
        rejection_reason=str_or_none(values[17]),
        execution_intent_id=str_or_none(values[18]),
        execution_order_id=str_or_none(values[19]),
        execution_outcome_status=str_or_none(values[20]),
    )
