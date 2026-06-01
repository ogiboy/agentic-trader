import json
from collections.abc import Sequence
from typing import Any, Literal, cast

import duckdb

from agentic_trader.schemas import (
    ProposalCandidateRecord,
    ProposalCandidateStatus,
    TradeProposalRecord,
    TradeProposalStatus,
    TradeSide,
)
from agentic_trader.storage.schema import table_exists


def _str_or_none(value: Any) -> str | None:
    return str(value) if value is not None else None


def _decode_object_payload(value: Any) -> dict[str, object]:
    if value is None:
        return {}
    try:
        payload = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return {str(key): item for key, item in cast(dict[object, object], payload).items()}


def insert_trade_proposal(
    conn: duckdb.DuckDBPyConnection,
    proposal: TradeProposalRecord,
) -> None:
    _execute_trade_proposal_insert(conn, proposal)


def insert_proposal_candidate(
    conn: duckdb.DuckDBPyConnection,
    candidate: ProposalCandidateRecord,
) -> None:
    conn.execute(
        """
        insert into proposal_candidates (
            candidate_id, created_at, updated_at, symbol, preset, signal, side,
            score, reference_price, confidence, quantity, notional, thesis,
            stop_loss, take_profit, invalidation_condition, source, status,
            materiality, freshness, liquidity, spread_pct, risk_notes,
            evidence_json, proposal_id
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            candidate.candidate_id,
            candidate.created_at,
            candidate.updated_at,
            candidate.symbol,
            candidate.preset,
            candidate.signal,
            candidate.side,
            candidate.score,
            candidate.reference_price,
            candidate.confidence,
            candidate.quantity,
            candidate.notional,
            candidate.thesis,
            candidate.stop_loss,
            candidate.take_profit,
            candidate.invalidation_condition,
            candidate.source,
            candidate.status,
            candidate.materiality,
            candidate.freshness,
            candidate.liquidity,
            candidate.spread_pct,
            candidate.risk_notes,
            json.dumps(candidate.evidence),
            candidate.proposal_id,
        ],
    )


def get_proposal_candidate(
    conn: duckdb.DuckDBPyConnection,
    candidate_id: str,
) -> ProposalCandidateRecord | None:
    if not table_exists(conn, "proposal_candidates"):
        return None
    rows = _proposal_candidate_rows(
        conn,
        """
        select *
        from proposal_candidates
        where candidate_id = ?
        """,
        [candidate_id],
    )
    return rows[0] if rows else None


def list_proposal_candidates(
    conn: duckdb.DuckDBPyConnection,
    *,
    status: ProposalCandidateStatus | None = None,
    limit: int = 50,
) -> list[ProposalCandidateRecord]:
    if not table_exists(conn, "proposal_candidates"):
        return []
    if status is None:
        return _proposal_candidate_rows(
            conn,
            """
            select *
            from proposal_candidates
            order by created_at desc
            limit ?
            """,
            [limit],
        )
    return _proposal_candidate_rows(
        conn,
        """
        select *
        from proposal_candidates
        where status = ?
        order by created_at desc
        limit ?
        """,
        [status, limit],
    )


def update_proposal_candidate(
    conn: duckdb.DuckDBPyConnection,
    candidate: ProposalCandidateRecord,
) -> bool:
    if not table_exists(conn, "proposal_candidates"):
        return False
    _execute_proposal_candidate_update(conn, candidate)
    return True


def promote_proposal_candidate_with_proposal(
    conn: duckdb.DuckDBPyConnection,
    *,
    candidate: ProposalCandidateRecord,
    proposal: TradeProposalRecord,
    expected_status: ProposalCandidateStatus = "candidate",
) -> bool:
    if not table_exists(conn, "proposal_candidates") or not table_exists(
        conn,
        "trade_proposals",
    ):
        return False
    conn.execute("begin transaction")
    try:
        current = conn.execute(
            """
            select status
            from proposal_candidates
            where candidate_id = ?
            """,
            [candidate.candidate_id],
        ).fetchone()
        if current is None or str(current[0]) != expected_status:
            conn.execute("commit")
            return False
        _execute_trade_proposal_insert(conn, proposal)
        _execute_proposal_candidate_update(conn, candidate)
        conn.execute("commit")
        return True
    except Exception:
        conn.execute("rollback")
        raise


def get_trade_proposal(
    conn: duckdb.DuckDBPyConnection,
    proposal_id: str,
) -> TradeProposalRecord | None:
    if not table_exists(conn, "trade_proposals"):
        return None
    rows = _trade_proposal_rows(
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
        return _trade_proposal_rows(
            conn,
            """
            select *
            from trade_proposals
            order by created_at desc
            limit ?
            """,
            [limit],
        )
    return _trade_proposal_rows(
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
            _execute_trade_proposal_update(conn, proposal)
            conn.execute("commit")
            return True
        except Exception:
            conn.execute("rollback")
            raise
    _execute_trade_proposal_update(conn, proposal)
    return True


def _execute_trade_proposal_insert(
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


def _execute_proposal_candidate_update(
    conn: duckdb.DuckDBPyConnection,
    candidate: ProposalCandidateRecord,
) -> None:
    conn.execute(
        """
        update proposal_candidates
        set updated_at = ?,
            status = ?,
            evidence_json = ?,
            proposal_id = ?
        where candidate_id = ?
        """,
        [
            candidate.updated_at,
            candidate.status,
            json.dumps(candidate.evidence),
            candidate.proposal_id,
            candidate.candidate_id,
        ],
    )


def _execute_trade_proposal_update(
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


def _trade_proposal_rows(
    conn: duckdb.DuckDBPyConnection,
    query: str,
    params: list[object],
) -> list[TradeProposalRecord]:
    rows = conn.execute(query, params).fetchall()
    return [_trade_proposal_record_from_row(row) for row in rows]


def _trade_proposal_record_from_row(row: object) -> TradeProposalRecord:
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
        invalidation_condition=_str_or_none(values[13]),
        source=str(values[14]),
        status=cast(TradeProposalStatus, str(values[15])),
        review_notes=str(values[16]),
        rejection_reason=_str_or_none(values[17]),
        execution_intent_id=_str_or_none(values[18]),
        execution_order_id=_str_or_none(values[19]),
        execution_outcome_status=_str_or_none(values[20]),
    )


def _proposal_candidate_rows(
    conn: duckdb.DuckDBPyConnection,
    query: str,
    params: list[object],
) -> list[ProposalCandidateRecord]:
    rows = conn.execute(query, params).fetchall()
    return [
        ProposalCandidateRecord(
            candidate_id=str(row[0]),
            created_at=str(row[1]),
            updated_at=str(row[2]),
            symbol=str(row[3]),
            preset=str(row[4]),
            signal=cast(Literal["buy", "sell", "watch"], str(row[5])),
            side=cast(TradeSide, str(row[6])) if row[6] is not None else None,
            score=float(row[7]),
            reference_price=float(row[8]),
            confidence=float(row[9]),
            quantity=float(row[10]) if row[10] is not None else None,
            notional=float(row[11]) if row[11] is not None else None,
            thesis=str(row[12]),
            stop_loss=float(row[13]) if row[13] is not None else None,
            take_profit=float(row[14]) if row[14] is not None else None,
            invalidation_condition=_str_or_none(row[15]),
            source=str(row[16]),
            status=cast(ProposalCandidateStatus, str(row[17])),
            materiality=str(row[18]),
            freshness=str(row[19]),
            liquidity=str(row[20]),
            spread_pct=float(row[21]),
            risk_notes=str(row[22]),
            evidence=_decode_object_payload(row[23]),
            proposal_id=_str_or_none(row[24]),
        )
        for row in rows
    ]
