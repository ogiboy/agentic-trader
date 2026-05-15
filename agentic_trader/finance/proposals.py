from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, cast
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


@dataclass(frozen=True, slots=True)
class TradeProposalDraft:
    symbol: str
    side: TradeSide
    reference_price: float
    confidence: float
    thesis: str
    order_type: Literal["market", "limit"] = "market"
    quantity: float | None = None
    notional: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    invalidation_condition: str | None = None
    source: str = "manual"
    review_notes: str = ""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_trade_proposal(
    *,
    db: TradingDatabase,
    draft: TradeProposalDraft | None = None,
    **fields: Any,
) -> TradeProposalRecord:
    proposal_draft = _coerce_trade_proposal_draft(draft=draft, fields=fields)
    if proposal_draft.quantity is None and proposal_draft.notional is None:
        raise ValueError("Trade proposals require quantity or notional.")
    if proposal_draft.quantity is not None and proposal_draft.notional is not None:
        raise ValueError("Trade proposals require exactly one of quantity or notional.")
    if proposal_draft.quantity is not None and proposal_draft.quantity <= 0:
        raise ValueError("Trade proposals require quantity greater than zero.")
    if proposal_draft.notional is not None and proposal_draft.notional <= 0:
        raise ValueError("Trade proposals require notional greater than zero.")
    if proposal_draft.reference_price <= 0:
        raise ValueError("Trade proposals require reference_price greater than zero.")
    if not 0 <= proposal_draft.confidence <= 1:
        raise ValueError("Trade proposals require confidence between 0 and 1.")
    now = utc_now_iso()
    proposal = TradeProposalRecord(
        proposal_id=f"proposal-{uuid4().hex[:12]}",
        created_at=now,
        updated_at=now,
        symbol=proposal_draft.symbol.strip().upper(),
        side=proposal_draft.side,
        order_type=proposal_draft.order_type,
        quantity=proposal_draft.quantity,
        notional=proposal_draft.notional,
        reference_price=proposal_draft.reference_price,
        confidence=proposal_draft.confidence,
        thesis=proposal_draft.thesis.strip(),
        stop_loss=proposal_draft.stop_loss,
        take_profit=proposal_draft.take_profit,
        invalidation_condition=proposal_draft.invalidation_condition,
        source=proposal_draft.source,
        review_notes=proposal_draft.review_notes,
    )
    db.insert_trade_proposal(proposal)
    return proposal


def _coerce_trade_proposal_draft(
    *,
    draft: TradeProposalDraft | None,
    fields: dict[str, Any],
) -> TradeProposalDraft:
    if draft is not None and fields:
        raise ValueError("Pass either draft or proposal fields, not both.")
    if draft is not None:
        return draft
    return TradeProposalDraft(**cast(dict[str, Any], fields))


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


def reconcile_trade_proposal(
    *,
    db: TradingDatabase,
    proposal_id: str,
    review_notes: str = "",
) -> tuple[TradeProposalRecord, dict[str, object]]:
    """Repair an in-flight proposal from an already recorded execution outcome.

    This function never calls a broker adapter. It only reconciles a proposal
    that already reached `approved` with an `execution_intent_id`, then uses the
    idempotent `execution_records` row for that intent to make the proposal
    terminal.
    """

    proposal = db.get_trade_proposal(proposal_id)
    if proposal is None:
        raise ValueError(f"Trade proposal not found: {proposal_id}")
    if proposal.status in TERMINAL_PROPOSAL_STATUSES:
        raise ValueError(
            f"Trade proposal {proposal_id} is already terminal: {proposal.status}."
        )
    if proposal.status != "approved" or proposal.execution_intent_id is None:
        raise ValueError(
            f"Trade proposal {proposal_id} is not an in-flight approved proposal."
        )
    record = db.get_execution_record(proposal.execution_intent_id)
    if record is None:
        raise ValueError(
            f"Trade proposal {proposal_id} has no recorded execution outcome to reconcile."
        )
    outcome_status = str(record["status"])
    final_status: TradeProposalStatus = (
        "executed" if outcome_status in _APPROVAL_SUCCESS_OUTCOMES else "failed"
    )
    repaired = proposal.model_copy(
        update={
            "status": final_status,
            "updated_at": utc_now_iso(),
            "review_notes": _merge_notes(proposal.review_notes, review_notes),
            "execution_order_id": _str_or_none(record.get("order_id")),
            "execution_outcome_status": outcome_status,
            "rejection_reason": _str_or_none(record.get("rejection_reason")),
        }
    )
    if not db.update_trade_proposal(repaired, expected_status="approved"):
        raise ValueError(
            f"Trade proposal {proposal_id} changed before reconciliation could finish."
        )
    return repaired, record


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


def expire_trade_proposal(
    *, db: TradingDatabase, proposal_id: str
) -> TradeProposalRecord:
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


def _str_or_none(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
