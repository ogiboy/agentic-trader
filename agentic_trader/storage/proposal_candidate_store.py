"""Proposal candidate persistence helpers."""

import json
from typing import Literal, cast

import duckdb

from agentic_trader.schemas import (
    ProposalCandidateRecord,
    ProposalCandidateStatus,
    TradeSide,
)
from agentic_trader.storage.proposal_row_utils import (
    decode_object_payload,
    str_or_none,
)
from agentic_trader.storage.schema import table_exists


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
    rows = proposal_candidate_rows(
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
        return proposal_candidate_rows(
            conn,
            """
            select *
            from proposal_candidates
            order by created_at desc
            limit ?
            """,
            [limit],
        )
    return proposal_candidate_rows(
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
    execute_proposal_candidate_update(conn, candidate)
    return True


def execute_proposal_candidate_update(
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


def proposal_candidate_rows(
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
            invalidation_condition=str_or_none(row[15]),
            source=str(row[16]),
            status=cast(ProposalCandidateStatus, str(row[17])),
            materiality=str(row[18]),
            freshness=str(row[19]),
            liquidity=str(row[20]),
            spread_pct=float(row[21]),
            risk_notes=str(row[22]),
            evidence=decode_object_payload(row[23]),
            proposal_id=str_or_none(row[24]),
        )
        for row in rows
    ]
