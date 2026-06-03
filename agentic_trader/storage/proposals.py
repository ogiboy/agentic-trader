"""Trade proposal storage facade and cross-record transactions."""

import duckdb

from agentic_trader.schemas import (
    ProposalCandidateRecord,
    ProposalCandidateStatus,
    TradeProposalRecord,
)
from agentic_trader.storage.proposal_candidate_store import (
    execute_proposal_candidate_update,
    get_proposal_candidate,
    insert_proposal_candidate,
    list_proposal_candidates,
    update_proposal_candidate,
)
from agentic_trader.storage.schema import table_exists
from agentic_trader.storage.trade_proposal_store import (
    execute_trade_proposal_insert,
    get_trade_proposal,
    insert_trade_proposal,
    list_trade_proposals,
    update_trade_proposal,
)

__all__ = [
    "get_proposal_candidate",
    "get_trade_proposal",
    "insert_proposal_candidate",
    "insert_trade_proposal",
    "list_proposal_candidates",
    "list_trade_proposals",
    "promote_proposal_candidate_with_proposal",
    "update_proposal_candidate",
    "update_trade_proposal",
]


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
        execute_trade_proposal_insert(conn, proposal)
        execute_proposal_candidate_update(conn, candidate)
        conn.execute("commit")
        return True
    except Exception:
        conn.execute("rollback")
        raise
