from typing import Any

from agentic_trader.finance.proposal_drafts import (
    TradeProposalDraft,
    prepare_trade_proposal,
)
from agentic_trader.finance.proposal_utils import (
    load_mutable_proposal,
    merge_notes,
    require_review_note,
)
from agentic_trader.schemas import TradeProposalRecord
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.time_utils import utc_now_iso


def create_trade_proposal(
    *,
    db: TradingDatabase,
    draft: TradeProposalDraft | None = None,
    **fields: Any,
) -> TradeProposalRecord:
    proposal = prepare_trade_proposal(draft=draft, **fields)
    db.insert_trade_proposal(proposal)
    return proposal


def reject_trade_proposal(
    *, db: TradingDatabase, proposal_id: str, reason: str
) -> TradeProposalRecord:
    proposal = load_mutable_proposal(db, proposal_id)
    clean_reason = require_review_note("rejection", reason)
    rejected = proposal.model_copy(
        update={
            "status": "rejected",
            "updated_at": utc_now_iso(),
            "review_notes": merge_notes(proposal.review_notes, clean_reason),
            "rejection_reason": clean_reason,
        }
    )
    if not db.update_trade_proposal(rejected, expected_status="pending"):
        raise ValueError(
            f"Trade proposal {proposal_id} changed before rejection could be recorded."
        )
    return rejected


def expire_trade_proposal(
    *, db: TradingDatabase, proposal_id: str
) -> TradeProposalRecord:
    proposal = load_mutable_proposal(db, proposal_id)
    expired = proposal.model_copy(
        update={"status": "expired", "updated_at": utc_now_iso()}
    )
    if not db.update_trade_proposal(expired, expected_status="pending"):
        raise ValueError(
            f"Trade proposal {proposal_id} changed before expiry could be recorded."
        )
    return expired
