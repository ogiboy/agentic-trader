from __future__ import annotations

from typing import Protocol

from agentic_trader.cli_modules.common import open_db
from agentic_trader.config import Settings
from agentic_trader.engine.broker_contracts import ExecutionOutcome
from agentic_trader.finance.proposal_candidates import promote_proposal_candidate
from agentic_trader.finance.proposals import (
    approve_trade_proposal,
    reconcile_trade_proposal,
    refresh_trade_proposal_order,
    reject_trade_proposal,
)
from agentic_trader.schemas import TradeProposalRecord
from agentic_trader.storage.db import TradingDatabase


class OpenDbProvider(Protocol):
    def __call__(
        self, settings: Settings, *, read_only: bool = False
    ) -> TradingDatabase: ...


class RefreshProposalOrder(Protocol):
    def __call__(
        self,
        *,
        db: TradingDatabase,
        settings: Settings,
        proposal_id: str,
        review_notes: str,
    ) -> tuple[TradeProposalRecord, ExecutionOutcome]: ...


def promote_candidate_payload(
    *,
    settings: Settings,
    candidate_id: str,
    review_notes: str,
    open_db_provider: OpenDbProvider = open_db,
) -> dict[str, object]:
    db = open_db_provider(settings)
    try:
        candidate, proposal = promote_proposal_candidate(
            db=db,
            candidate_id=candidate_id,
            review_notes=review_notes,
        )
    finally:
        db.close()
    return {
        "candidate": candidate.model_dump(mode="json"),
        "proposal": proposal.model_dump(mode="json"),
        "submitted_to_broker": False,
    }


def approve_proposal_payload(
    *,
    settings: Settings,
    proposal_id: str,
    review_notes: str,
    open_db_provider: OpenDbProvider = open_db,
) -> dict[str, object]:
    db = open_db_provider(settings)
    try:
        proposal, outcome = approve_trade_proposal(
            db=db,
            settings=settings,
            proposal_id=proposal_id,
            review_notes=review_notes,
        )
    finally:
        db.close()
    return {
        "proposal": proposal.model_dump(mode="json"),
        "outcome": outcome.model_dump(mode="json"),
    }


def reconcile_proposal_payload(
    *,
    settings: Settings,
    proposal_id: str,
    review_notes: str,
    open_db_provider: OpenDbProvider = open_db,
) -> dict[str, object]:
    db = open_db_provider(settings)
    try:
        proposal, execution_record = reconcile_trade_proposal(
            db=db,
            proposal_id=proposal_id,
            review_notes=review_notes,
        )
    finally:
        db.close()
    return {
        "proposal": proposal.model_dump(mode="json"),
        "execution_record": execution_record,
        "resubmitted": False,
    }


def refresh_proposal_payload(
    *,
    settings: Settings,
    proposal_id: str,
    review_notes: str,
    open_db_provider: OpenDbProvider = open_db,
    refresh_trade_proposal_order_provider: RefreshProposalOrder = (
        refresh_trade_proposal_order
    ),
) -> dict[str, object]:
    db = open_db_provider(settings)
    try:
        proposal, outcome = refresh_trade_proposal_order_provider(
            db=db,
            settings=settings,
            proposal_id=proposal_id,
            review_notes=review_notes,
        )
    finally:
        db.close()
    return {
        "proposal": proposal.model_dump(mode="json"),
        "outcome": outcome.model_dump(mode="json"),
        "resubmitted": False,
        "refreshed": True,
    }


def reject_proposal_payload(
    *,
    settings: Settings,
    proposal_id: str,
    reason: str,
    open_db_provider: OpenDbProvider = open_db,
) -> dict[str, object]:
    db = open_db_provider(settings)
    try:
        proposal = reject_trade_proposal(db=db, proposal_id=proposal_id, reason=reason)
    finally:
        db.close()
    return proposal.model_dump(mode="json")
