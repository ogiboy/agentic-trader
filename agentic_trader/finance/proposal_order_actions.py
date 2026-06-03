from __future__ import annotations

from typing import Protocol

from agentic_trader.config import Settings
from agentic_trader.execution.intent import ExecutionIntent, ExecutionOutcome
from agentic_trader.finance.proposal_types import TERMINAL_PROPOSAL_STATUSES
from agentic_trader.finance.proposal_utils import (
    intent_from_proposal,
    load_mutable_proposal,
    merge_notes,
    proposal_status_for_outcome,
    require_review_note,
    save_position_plan_from_proposal,
    str_or_none,
    validate_proposal_risk_controls,
)
from agentic_trader.schemas import TradeProposalRecord
from agentic_trader.security import redact_sensitive_text
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.time_utils import utc_now_iso


class BrokerAdapterFactory(Protocol):
    def __call__(self, *, db: TradingDatabase, settings: Settings) -> BrokerAdapter: ...


class BrokerAdapter(Protocol):
    def place_order(self, intent: ExecutionIntent) -> ExecutionOutcome: ...


class OrderOutcomeReaderFactory(Protocol):
    def __call__(
        self, *, db: TradingDatabase, settings: Settings
    ) -> OrderOutcomeReader: ...


class OrderOutcomeReader(Protocol):
    def get_order_outcome(
        self, *, order_id: str, intent: ExecutionIntent
    ) -> ExecutionOutcome: ...


def approve_trade_proposal(
    *,
    db: TradingDatabase,
    settings: Settings,
    proposal_id: str,
    broker_adapter_factory: BrokerAdapterFactory,
    review_notes: str = "",
) -> tuple[TradeProposalRecord, ExecutionOutcome]:
    clean_review_notes = require_review_note("approval", review_notes)
    proposal = load_mutable_proposal(db, proposal_id)
    validate_proposal_risk_controls(proposal)
    approved_proposal = proposal.model_copy(
        update={
            "status": "approved",
            "updated_at": utc_now_iso(),
            "review_notes": merge_notes(proposal.review_notes, clean_review_notes),
        }
    )
    intent = intent_from_proposal(approved_proposal, settings=settings)
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
    adapter = broker_adapter_factory(db=db, settings=settings)
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
    final_status = proposal_status_for_outcome(outcome.status)
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
    db.create_trade_journal_from_proposal(proposal=final_proposal, outcome=outcome)
    save_position_plan_from_proposal(db, proposal=final_proposal, outcome=outcome)
    return final_proposal, outcome


def reconcile_trade_proposal(
    *,
    db: TradingDatabase,
    proposal_id: str,
    review_notes: str = "",
) -> tuple[TradeProposalRecord, dict[str, object]]:
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
    final_status = proposal_status_for_outcome(outcome_status)
    outcome_payload = record.get("outcome")
    if not isinstance(outcome_payload, dict):
        raise ValueError(
            f"Trade proposal {proposal_id} has no recorded execution outcome payload."
        )
    outcome = ExecutionOutcome.model_validate(outcome_payload)
    clean_review_notes = require_review_note("reconciliation", review_notes)
    repaired = proposal.model_copy(
        update={
            "status": final_status,
            "updated_at": utc_now_iso(),
            "review_notes": merge_notes(proposal.review_notes, clean_review_notes),
            "execution_order_id": str_or_none(record.get("order_id")),
            "execution_outcome_status": outcome_status,
            "rejection_reason": str_or_none(record.get("rejection_reason")),
        }
    )
    if not db.update_trade_proposal(repaired, expected_status="approved"):
        raise ValueError(
            f"Trade proposal {proposal_id} changed before reconciliation could finish."
        )
    db.create_trade_journal_from_proposal(proposal=repaired, outcome=outcome)
    save_position_plan_from_proposal(db, proposal=repaired, outcome=outcome)
    return repaired, record


def refresh_trade_proposal_order(
    *,
    db: TradingDatabase,
    settings: Settings,
    proposal_id: str,
    order_reader_factory: OrderOutcomeReaderFactory,
    review_notes: str = "",
) -> tuple[TradeProposalRecord, ExecutionOutcome]:
    proposal, record, intent = _refreshable_order(db=db, proposal_id=proposal_id)
    clean_review_notes = require_review_note("broker refresh", review_notes)
    outcome = _refreshed_order_outcome(
        db=db,
        settings=settings,
        proposal=proposal,
        intent=intent,
        order_reader_factory=order_reader_factory,
    )
    if outcome.order_id != proposal.execution_order_id:
        raise RuntimeError(
            f"Broker order refresh returned a different order id for {proposal_id}."
        )

    db.record_execution_outcome(
        run_id=str_or_none(record.get("run_id")),
        intent=intent,
        outcome=outcome,
    )
    refreshed = _refreshed_trade_proposal(
        proposal=proposal,
        outcome=outcome,
        review_notes=clean_review_notes,
    )
    if not db.update_trade_proposal(refreshed, expected_status=proposal.status):
        raise ValueError(
            f"Trade proposal {proposal_id} changed before broker refresh could finish."
        )
    db.create_trade_journal_from_proposal(proposal=refreshed, outcome=outcome)
    save_position_plan_from_proposal(db, proposal=refreshed, outcome=outcome)
    return refreshed, outcome


def _refreshable_order(
    *,
    db: TradingDatabase,
    proposal_id: str,
) -> tuple[TradeProposalRecord, dict[str, object], ExecutionIntent]:
    proposal = db.get_trade_proposal(proposal_id)
    if proposal is None:
        raise ValueError(f"Trade proposal not found: {proposal_id}")
    if proposal.execution_intent_id is None or proposal.execution_order_id is None:
        raise ValueError(
            f"Trade proposal {proposal_id} has no broker order to refresh."
        )
    if proposal.execution_outcome_status != "accepted":
        raise ValueError(
            f"Trade proposal {proposal_id} is not waiting on an accepted broker order."
        )
    record = db.get_execution_record(proposal.execution_intent_id)
    if record is None:
        raise ValueError(
            f"Trade proposal {proposal_id} has no recorded execution intent to refresh."
        )
    intent_payload = record.get("intent")
    if not isinstance(intent_payload, dict):
        raise ValueError(
            f"Trade proposal {proposal_id} has no refreshable execution intent payload."
        )
    return proposal, record, ExecutionIntent.model_validate(intent_payload)


def _refreshed_order_outcome(
    *,
    db: TradingDatabase,
    settings: Settings,
    proposal: TradeProposalRecord,
    intent: ExecutionIntent,
    order_reader_factory: OrderOutcomeReaderFactory,
) -> ExecutionOutcome:
    adapter_settings = settings.model_copy(
        update={"execution_backend": intent.execution_backend}
    )
    adapter = order_reader_factory(db=db, settings=adapter_settings)
    outcome = adapter.get_order_outcome(
        order_id=proposal.execution_order_id or "",
        intent=intent,
    )
    if outcome.order_id is None:
        return outcome.model_copy(update={"order_id": proposal.execution_order_id})
    return outcome


def _refreshed_trade_proposal(
    *,
    proposal: TradeProposalRecord,
    outcome: ExecutionOutcome,
    review_notes: str,
) -> TradeProposalRecord:
    return proposal.model_copy(
        update={
            "status": proposal_status_for_outcome(outcome.status),
            "updated_at": utc_now_iso(),
            "review_notes": merge_notes(proposal.review_notes, review_notes),
            "execution_order_id": outcome.order_id,
            "execution_outcome_status": outcome.status,
            "rejection_reason": outcome.rejection_reason,
        }
    )
