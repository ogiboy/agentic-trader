from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from agentic_trader.config import Settings
from agentic_trader.engine.broker import get_broker_adapter
from agentic_trader.execution.intent import ExecutionIntent, ExecutionOutcome
from agentic_trader.schemas import (
    TradeProposalRecord,
    TradeProposalStatus,
    TradeSide,
)
from agentic_trader.security import redact_sensitive_text
from agentic_trader.storage.db import TradingDatabase

TERMINAL_PROPOSAL_STATUSES: set[TradeProposalStatus] = {
    "executed",
    "rejected",
    "failed",
    "expired",
}

_APPROVAL_SUCCESS_OUTCOMES = {"accepted", "filled", "partially_filled"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_trade_proposal(
    *,
    db: TradingDatabase,
    symbol: str,
    side: TradeSide,
    reference_price: float,
    confidence: float,
    thesis: str,
    order_type: Literal["market", "limit"] = "market",
    quantity: float | None = None,
    notional: float | None = None,
    stop_loss: float | None = None,
    take_profit: float | None = None,
    invalidation_condition: str | None = None,
    source: str = "manual",
    review_notes: str = "",
) -> TradeProposalRecord:
    if quantity is None and notional is None:
        raise ValueError("Trade proposals require quantity or notional.")
    if quantity is not None and notional is not None:
        raise ValueError("Trade proposals require exactly one of quantity or notional.")
    if quantity is not None and quantity <= 0:
        raise ValueError("Trade proposals require quantity greater than zero.")
    if notional is not None and notional <= 0:
        raise ValueError("Trade proposals require notional greater than zero.")
    if reference_price <= 0:
        raise ValueError("Trade proposals require reference_price greater than zero.")
    if not 0 <= confidence <= 1:
        raise ValueError("Trade proposals require confidence between 0 and 1.")
    now = utc_now_iso()
    proposal = TradeProposalRecord(
        proposal_id=f"proposal-{uuid4().hex[:12]}",
        created_at=now,
        updated_at=now,
        symbol=symbol.strip().upper(),
        side=side,
        order_type=order_type,
        quantity=quantity,
        notional=notional,
        reference_price=reference_price,
        confidence=confidence,
        thesis=thesis.strip(),
        stop_loss=stop_loss,
        take_profit=take_profit,
        invalidation_condition=invalidation_condition,
        source=source,
        review_notes=review_notes,
    )
    db.insert_trade_proposal(proposal)
    return proposal


def approve_trade_proposal(
    *,
    db: TradingDatabase,
    settings: Settings,
    proposal_id: str,
    review_notes: str = "",
) -> tuple[TradeProposalRecord, ExecutionOutcome]:
    proposal = _load_mutable_proposal(db, proposal_id)
    approved_proposal = proposal.model_copy(
        update={
            "status": "approved",
            "updated_at": utc_now_iso(),
            "review_notes": _merge_notes(proposal.review_notes, review_notes),
        }
    )
    intent = _intent_from_proposal(approved_proposal, settings=settings)
    approved_proposal = approved_proposal.model_copy(
        update={
            "updated_at": utc_now_iso(),
            "execution_intent_id": intent.intent_id,
        }
    )
    if not db.update_trade_proposal(approved_proposal, expected_status="pending"):
        raise ValueError(
            f"Trade proposal {proposal_id} changed before approval could be recorded."
        )
    adapter = get_broker_adapter(db=db, settings=settings)
    try:
        outcome = adapter.place_order(intent)
    except Exception as exc:
        outcome = ExecutionOutcome(
            intent_id=intent.intent_id,
            status="rejected",
            adapter_name=intent.adapter_name,
            execution_backend=settings.execution_backend,
            rejection_reason="adapter_exception",
            message=(
                "Proposal broker adapter failed: "
                f"{redact_sensitive_text(exc, max_length=160)}"
            ),
        )
    db.record_execution_outcome(run_id=None, intent=intent, outcome=outcome)
    final_status: TradeProposalStatus = (
        "executed" if outcome.status in _APPROVAL_SUCCESS_OUTCOMES else "failed"
    )
    final_proposal = approved_proposal.model_copy(
        update={
            "status": final_status,
            "updated_at": utc_now_iso(),
            "execution_intent_id": intent.intent_id,
            "execution_order_id": outcome.order_id,
            "execution_outcome_status": outcome.status,
            "rejection_reason": outcome.rejection_reason,
        }
    )
    if not db.update_trade_proposal(final_proposal, expected_status="approved"):
        raise ValueError(
            f"Trade proposal {proposal_id} changed before broker outcome could be recorded."
        )
    return final_proposal, outcome


def reject_trade_proposal(
    *, db: TradingDatabase, proposal_id: str, reason: str
) -> TradeProposalRecord:
    proposal = _load_mutable_proposal(db, proposal_id)
    rejected = proposal.model_copy(
        update={
            "status": "rejected",
            "updated_at": utc_now_iso(),
            "review_notes": _merge_notes(proposal.review_notes, reason),
            "rejection_reason": reason,
        }
    )
    if not db.update_trade_proposal(rejected, expected_status="pending"):
        raise ValueError(
            f"Trade proposal {proposal_id} changed before rejection could be recorded."
        )
    return rejected


def expire_trade_proposal(*, db: TradingDatabase, proposal_id: str) -> TradeProposalRecord:
    proposal = _load_mutable_proposal(db, proposal_id)
    expired = proposal.model_copy(
        update={"status": "expired", "updated_at": utc_now_iso()}
    )
    if not db.update_trade_proposal(expired, expected_status="pending"):
        raise ValueError(
            f"Trade proposal {proposal_id} changed before expiry could be recorded."
        )
    return expired


def _load_mutable_proposal(
    db: TradingDatabase, proposal_id: str
) -> TradeProposalRecord:
    proposal = db.get_trade_proposal(proposal_id)
    if proposal is None:
        raise ValueError(f"Trade proposal not found: {proposal_id}")
    if proposal.status in TERMINAL_PROPOSAL_STATUSES:
        raise ValueError(
            f"Trade proposal {proposal_id} is {proposal.status}, not pending."
        )
    if proposal.status == "approved" or proposal.execution_intent_id is not None:
        raise ValueError(
            f"Trade proposal {proposal_id} is already in-flight, not pending."
        )
    if proposal.status != "pending":
        raise ValueError(
            f"Trade proposal {proposal_id} is {proposal.status}, not pending."
        )
    return proposal


def _intent_from_proposal(
    proposal: TradeProposalRecord, *, settings: Settings
) -> ExecutionIntent:
    return ExecutionIntent(
        symbol=proposal.symbol,
        side=proposal.side,
        order_type=proposal.order_type,
        quantity=proposal.quantity,
        notional=proposal.notional,
        reference_price=proposal.reference_price,
        confidence=proposal.confidence,
        thesis=proposal.thesis,
        stop_loss=proposal.stop_loss,
        take_profit=proposal.take_profit,
        invalidation_condition=proposal.invalidation_condition,
        approved=True,
        runtime_mode=settings.runtime_mode,
        execution_backend=settings.execution_backend,
        adapter_name=settings.execution_backend,
        backend_metadata={
            "source": "proposal_queue",
            "proposal_id": proposal.proposal_id,
        },
    )


def _merge_notes(existing: str, note: str) -> str:
    cleaned = note.strip()
    if not cleaned:
        return existing
    if not existing:
        return cleaned
    return f"{existing}\n{cleaned}"
