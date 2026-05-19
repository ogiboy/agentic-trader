from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, NotRequired, TypedDict, cast
from uuid import uuid4

from agentic_trader.config import Settings
from agentic_trader.engine.broker import get_broker_adapter, get_broker_order_reader
from agentic_trader.execution.intent import ExecutionIntent, ExecutionOutcome
from agentic_trader.execution.symbols import is_v1_us_equity_symbol
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

_EXECUTED_OUTCOMES = {"filled", "partially_filled"}


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


class PositionPlanRepairItem(TypedDict):
    symbol: str
    status: Literal["created", "candidate", "skipped"]
    reason: str
    proposal_id: NotRequired[str]
    side: NotRequired[TradeSide]
    entry_price: NotRequired[float]
    stop_loss: NotRequired[float]
    take_profit: NotRequired[float]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def prepare_trade_proposal(
    *, draft: TradeProposalDraft | None = None, **fields: Any
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
    symbol = proposal_draft.symbol.strip().upper()
    if not is_v1_us_equity_symbol(symbol):
        raise ValueError("Trade proposals require a simple V1 US equity symbol.")
    now = utc_now_iso()
    proposal = TradeProposalRecord(
        proposal_id=f"proposal-{uuid4().hex[:12]}",
        created_at=now,
        updated_at=now,
        symbol=symbol,
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
    return proposal


def create_trade_proposal(
    *,
    db: TradingDatabase,
    draft: TradeProposalDraft | None = None,
    **fields: Any,
) -> TradeProposalRecord:
    proposal = prepare_trade_proposal(draft=draft, **fields)
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
    _validate_proposal_risk_controls(proposal)
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
    final_status = _proposal_status_for_outcome(outcome.status)
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
    _save_position_plan_from_proposal(db, proposal=final_proposal, outcome=outcome)
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
    final_status = _proposal_status_for_outcome(outcome_status)
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
    outcome_payload = record.get("outcome")
    if not isinstance(outcome_payload, dict):
        raise ValueError(
            f"Trade proposal {proposal_id} has no recorded execution outcome payload."
        )
    outcome = ExecutionOutcome.model_validate(outcome_payload)
    db.create_trade_journal_from_proposal(
        proposal=repaired,
        outcome=outcome,
    )
    _save_position_plan_from_proposal(db, proposal=repaired, outcome=outcome)
    return repaired, record


def refresh_trade_proposal_order(
    *,
    db: TradingDatabase,
    settings: Settings,
    proposal_id: str,
    review_notes: str = "",
) -> tuple[TradeProposalRecord, ExecutionOutcome]:
    """Refresh an accepted proposal order from the original broker without resubmitting."""

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
    intent = ExecutionIntent.model_validate(intent_payload)
    adapter_settings = settings.model_copy(
        update={"execution_backend": intent.execution_backend}
    )
    adapter = get_broker_order_reader(
        db=db,
        settings=adapter_settings,
    )
    outcome = adapter.get_order_outcome(
        order_id=proposal.execution_order_id,
        intent=intent,
    )
    if outcome.order_id is None:
        outcome = outcome.model_copy(update={"order_id": proposal.execution_order_id})
    if outcome.order_id != proposal.execution_order_id:
        raise RuntimeError(
            f"Broker order refresh returned a different order id for {proposal_id}."
        )

    db.record_execution_outcome(
        run_id=_str_or_none(record.get("run_id")),
        intent=intent,
        outcome=outcome,
    )
    final_status = _proposal_status_for_outcome(outcome.status)
    refreshed = proposal.model_copy(
        update={
            "status": final_status,
            "updated_at": utc_now_iso(),
            "review_notes": _merge_notes(proposal.review_notes, review_notes),
            "execution_order_id": outcome.order_id,
            "execution_outcome_status": outcome.status,
            "rejection_reason": outcome.rejection_reason,
        }
    )
    if not db.update_trade_proposal(refreshed, expected_status=proposal.status):
        raise ValueError(
            f"Trade proposal {proposal_id} changed before broker refresh could finish."
        )
    db.create_trade_journal_from_proposal(proposal=refreshed, outcome=outcome)
    _save_position_plan_from_proposal(db, proposal=refreshed, outcome=outcome)
    return refreshed, outcome


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


def repair_missing_position_plans(
    *,
    db: TradingDatabase,
    apply_repair: bool = False,
    max_holding_bars: int = 20,
) -> list[PositionPlanRepairItem]:
    """Backfill missing exit plans from executed proposal records.

    The repair is intentionally broker-free. It only considers open positions
    without a stored position plan and executed proposals that already carry
    valid stop-loss and take-profit controls.
    """

    open_positions = {position.symbol: position for position in db.list_positions()}
    planned_symbols = {plan.symbol for plan in db.list_position_plans()}
    executed_proposals = db.list_trade_proposals(status="executed", limit=500)
    repairs: list[PositionPlanRepairItem] = []

    for symbol, position in sorted(open_positions.items()):
        if symbol in planned_symbols:
            continue
        candidate = _latest_repairable_proposal(
            symbol=symbol,
            quantity=position.quantity,
            proposals=executed_proposals,
        )
        if candidate is None:
            repairs.append(
                {
                    "symbol": symbol,
                    "status": "skipped",
                    "reason": "no executed proposal with valid exit controls",
                }
            )
            continue
        entry_price = position.average_price or candidate.reference_price
        item: PositionPlanRepairItem = {
            "symbol": symbol,
            "status": "created" if apply_repair else "candidate",
            "reason": "repaired from executed proposal"
            if apply_repair
            else "dry-run candidate from executed proposal",
            "proposal_id": candidate.proposal_id,
            "side": candidate.side,
            "entry_price": entry_price,
            "stop_loss": cast(float, candidate.stop_loss),
            "take_profit": cast(float, candidate.take_profit),
        }
        repairs.append(item)
        if apply_repair:
            db.save_position_plan(
                symbol=symbol,
                side=candidate.side,
                entry_price=entry_price,
                stop_loss=cast(float, candidate.stop_loss),
                take_profit=cast(float, candidate.take_profit),
                max_holding_bars=max_holding_bars,
                holding_bars=0,
                invalidation_logic=(
                    candidate.invalidation_condition
                    or "Repaired from executed proposal risk plan."
                ),
            )
    return repairs


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


def _save_position_plan_from_proposal(
    db: TradingDatabase,
    *,
    proposal: TradeProposalRecord,
    outcome: ExecutionOutcome,
) -> None:
    if outcome.status not in {"filled", "partially_filled"}:
        return
    if outcome.filled_quantity <= 0:
        return
    if proposal.stop_loss is None or proposal.take_profit is None:
        return
    db.save_position_plan(
        symbol=proposal.symbol,
        side=proposal.side,
        entry_price=outcome.average_fill_price or proposal.reference_price,
        stop_loss=proposal.stop_loss,
        take_profit=proposal.take_profit,
        max_holding_bars=20,
        holding_bars=0,
        invalidation_logic=(
            proposal.invalidation_condition
            or "Manual proposal risk plan: exit on stop loss, take profit, or max holding period."
        ),
    )


def _validate_proposal_risk_controls(proposal: TradeProposalRecord) -> None:
    if proposal.stop_loss is None or proposal.take_profit is None:
        raise ValueError(
            "Trade proposal approval requires stop_loss and take_profit risk controls."
        )
    if proposal.side == "buy" and not (
        proposal.stop_loss < proposal.reference_price < proposal.take_profit
    ):
        raise ValueError(
            "Buy proposal risk controls must satisfy stop_loss < reference_price < take_profit."
        )
    if proposal.side == "sell" and not (
        proposal.take_profit < proposal.reference_price < proposal.stop_loss
    ):
        raise ValueError(
            "Sell proposal risk controls must satisfy take_profit < reference_price < stop_loss."
        )


def _latest_repairable_proposal(
    *,
    symbol: str,
    quantity: float,
    proposals: list[TradeProposalRecord],
) -> TradeProposalRecord | None:
    expected_side: TradeSide = "buy" if quantity > 0 else "sell"
    for proposal in proposals:
        if proposal.symbol != symbol or proposal.side != expected_side:
            continue
        if proposal.execution_outcome_status not in _EXECUTED_OUTCOMES:
            continue
        try:
            _validate_proposal_risk_controls(proposal)
        except ValueError:
            continue
        return proposal
    return None


def _str_or_none(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _proposal_status_for_outcome(outcome_status: str) -> TradeProposalStatus:
    if outcome_status in _EXECUTED_OUTCOMES:
        return "executed"
    if outcome_status == "accepted":
        return "approved"
    return "failed"
