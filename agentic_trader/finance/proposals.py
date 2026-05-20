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
    limit_price: float | None = None
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
    """
    Return the current UTC time as an ISO 8601 formatted string.
    
    Returns:
        ISO 8601 string representing the current UTC time (includes timezone offset).
    """
    return datetime.now(timezone.utc).isoformat()


def prepare_trade_proposal(
    *, draft: TradeProposalDraft | None = None, **fields: Any
) -> TradeProposalRecord:
    """
    Constructs and returns a validated trade proposal record from a draft or equivalent fields.
    
    Accepts either a pre-built TradeProposalDraft or keyword fields used to construct one (providing both is an error). The draft is validated, the symbol is normalized (trimmed and uppercased), timestamps are set, and a unique `proposal_id` is generated.
    
    Parameters:
        draft (TradeProposalDraft | None): Optional pre-constructed proposal draft.
        **fields: Any: Keyword arguments to construct a TradeProposalDraft when `draft` is None.
    
    Returns:
        TradeProposalRecord: A proposal record populated from the validated draft with normalized symbol, `created_at`/`updated_at` timestamps, and a generated `proposal_id`.
    """
    proposal_draft = _coerce_trade_proposal_draft(draft=draft, fields=fields)
    _validate_trade_proposal_draft(proposal_draft)
    symbol = proposal_draft.symbol.strip().upper()
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
        limit_price=proposal_draft.limit_price,
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


def _validate_trade_proposal_draft(proposal_draft: TradeProposalDraft) -> None:
    """
    Validate a trade proposal draft for size, order parameters, confidence, and symbol format.
    
    Parameters:
        proposal_draft (TradeProposalDraft): Draft to validate; symbol will be normalized (trimmed and uppercased) for validation.
    
    Raises:
        ValueError: If size, order, or confidence constraints are violated, or if the normalized symbol is not a simple V1 US equity symbol.
    """
    _validate_trade_proposal_size(proposal_draft)
    _validate_trade_proposal_order(proposal_draft)
    _validate_trade_proposal_confidence(proposal_draft)
    symbol = proposal_draft.symbol.strip().upper()
    if not is_v1_us_equity_symbol(symbol):
        raise ValueError("Trade proposals require a simple V1 US equity symbol.")


def _validate_trade_proposal_size(proposal_draft: TradeProposalDraft) -> None:
    """
    Validate the sizing fields of a trade proposal draft.
    
    Ensures exactly one of `quantity` or `notional` is provided and that the provided value is greater than zero.
    
    Parameters:
        proposal_draft (TradeProposalDraft): Draft to validate.
    
    Raises:
        ValueError: If neither `quantity` nor `notional` is provided.
        ValueError: If both `quantity` and `notional` are provided.
        ValueError: If `quantity` is present and less than or equal to zero.
        ValueError: If `notional` is present and less than or equal to zero.
    """
    if proposal_draft.quantity is None and proposal_draft.notional is None:
        raise ValueError("Trade proposals require quantity or notional.")
    if proposal_draft.quantity is not None and proposal_draft.notional is not None:
        raise ValueError("Trade proposals require exactly one of quantity or notional.")
    if proposal_draft.quantity is not None and proposal_draft.quantity <= 0:
        raise ValueError("Trade proposals require quantity greater than zero.")
    if proposal_draft.notional is not None and proposal_draft.notional <= 0:
        raise ValueError("Trade proposals require notional greater than zero.")


def _validate_trade_proposal_order(proposal_draft: TradeProposalDraft) -> None:
    """
    Validate order-related fields of a trade proposal draft.
    
    Raises ValueError if:
    - order_type == "limit" and limit_price is missing.
    - order_type == "limit" and quantity is missing.
    - order_type != "limit" and limit_price is provided.
    - reference_price is less than or equal to zero.
    
    Parameters:
        proposal_draft (TradeProposalDraft): The draft whose order fields are being validated.
    """
    if proposal_draft.order_type == "limit":
        if proposal_draft.limit_price is None:
            raise ValueError("Limit trade proposals require limit_price.")
        if proposal_draft.quantity is None:
            raise ValueError("Limit trade proposals require quantity.")
    elif proposal_draft.limit_price is not None:
        raise ValueError("Market trade proposals must not include limit_price.")
    if proposal_draft.reference_price <= 0:
        raise ValueError("Trade proposals require reference_price greater than zero.")


def _validate_trade_proposal_confidence(proposal_draft: TradeProposalDraft) -> None:
    """
    Validate that the draft's confidence is within the inclusive range 0 to 1.
    
    Parameters:
        proposal_draft (TradeProposalDraft): Draft whose `confidence` field will be checked.
    
    Raises:
        ValueError: If `proposal_draft.confidence` is less than 0 or greater than 1.
    """
    if not 0 <= proposal_draft.confidence <= 1:
        raise ValueError("Trade proposals require confidence between 0 and 1.")


def create_trade_proposal(
    *,
    db: TradingDatabase,
    draft: TradeProposalDraft | None = None,
    **fields: Any,
) -> TradeProposalRecord:
    """
    Create and persist a trade proposal from a draft or provided fields.
    
    The draft is coerced and validated (mutually exclusive with `fields`), normalized (e.g., symbol uppercased), and augmented with generated metadata (id, created_at, updated_at) via prepare_trade_proposal before being stored.
    
    Parameters:
        draft (TradeProposalDraft | None): Optional pre-built draft; omit if supplying proposal fields as kwargs.
        **fields: Any: Proposal fields to construct a draft when `draft` is not provided.
    
    Returns:
        TradeProposalRecord: The stored proposal record including generated id and timestamps.
    """
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
    """
    Approve a pending trade proposal, send it to the broker, record the execution outcome, and persist resulting proposal state.
    
    This validates the proposal's risk controls, marks the proposal as approved, builds and submits an execution intent to the configured broker adapter, records the returned execution outcome, updates the proposal to its final status derived from the outcome, creates a trade journal entry, and (when applicable) saves a position plan derived from the outcome.
    
    Parameters:
        proposal_id (str): Identifier of the proposal to approve.
        review_notes (str): Non-empty review notes required for approval; trimmed and merged into the proposal's notes.
    
    Returns:
        tuple[TradeProposalRecord, ExecutionOutcome]: The updated proposal record (final, terminal status) and the recorded execution outcome.
    
    Raises:
        ValueError: If `review_notes` is empty, if the proposal is not in an approvable state, or if the proposal was changed concurrently such that attempting to record the approval or the final outcome failed.
    """
    clean_review_notes = _require_review_note("approval", review_notes)
    proposal = _load_mutable_proposal(db, proposal_id)
    _validate_proposal_risk_controls(proposal)
    approved_proposal = proposal.model_copy(
        update={
            "status": "approved",
            "updated_at": utc_now_iso(),
            "review_notes": _merge_notes(proposal.review_notes, clean_review_notes),
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
    """
    Reconcile an approved trade proposal using a previously recorded execution record to transition the proposal to a terminal state.
    
    This loads the execution record referenced by the proposal's `execution_intent_id`, validates the recorded outcome payload, merges the provided `review_notes`, updates and persists terminal proposal fields, and creates the associated trade journal and (if applicable) position plan.
    
    Parameters:
        proposal_id (str): ID of the trade proposal to reconcile.
        review_notes (str): Non-empty notes explaining the reconciliation; must not be empty.
    
    Returns:
        tuple[TradeProposalRecord, dict[str, object]]: The updated (terminal) proposal record and the raw execution record dict used for reconciliation.
    
    Raises:
        ValueError: If the proposal is not found, is already terminal, is not an in-flight approved proposal, has no recorded execution outcome or payload, or if the proposal changed concurrently before reconciliation completed.
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
    outcome_payload = record.get("outcome")
    if not isinstance(outcome_payload, dict):
        raise ValueError(
            f"Trade proposal {proposal_id} has no recorded execution outcome payload."
        )
    outcome = ExecutionOutcome.model_validate(outcome_payload)
    clean_review_notes = _require_review_note("reconciliation", review_notes)
    repaired = proposal.model_copy(
        update={
            "status": final_status,
            "updated_at": utc_now_iso(),
            "review_notes": _merge_notes(proposal.review_notes, clean_review_notes),
            "execution_order_id": _str_or_none(record.get("order_id")),
            "execution_outcome_status": outcome_status,
            "rejection_reason": _str_or_none(record.get("rejection_reason")),
        }
    )
    if not db.update_trade_proposal(repaired, expected_status="approved"):
        raise ValueError(
            f"Trade proposal {proposal_id} changed before reconciliation could finish."
        )
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
    """
    Refresh the broker-side order outcome for an already-accepted trade proposal without resubmitting the order.
    
    Updates the stored proposal and records the refreshed execution outcome from the broker; merges provided review notes into the proposal's review history.
    
    Parameters:
        review_notes (str): Non-empty notes describing the refresh operation; empty input will raise ValueError.
    
    Returns:
        tuple[TradeProposalRecord, ExecutionOutcome]: The updated trade proposal record and the refreshed execution outcome.
    
    Raises:
        ValueError: If the proposal is not found, lacks stored broker intent/order IDs, is not in an accepted state, the recorded intent payload is missing or malformed, the proposal changed concurrently while updating, or if `review_notes` is empty.
        RuntimeError: If the broker returned an order id that does not match the proposal's recorded order id.
    """

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
    clean_review_notes = _require_review_note("broker refresh", review_notes)
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
            "review_notes": _merge_notes(proposal.review_notes, clean_review_notes),
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
    """
    Mark a pending trade proposal as rejected and persist the update.
    
    Parameters:
        proposal_id (str): Identifier of the proposal to reject; must refer to a mutable (pending) proposal.
        reason (str): Rejection reason which is appended to the proposal's review notes and stored as the proposal's rejection reason.
    
    Returns:
        TradeProposalRecord: The updated proposal record with status set to "rejected", `updated_at` refreshed, merged `review_notes`, and `rejection_reason` set to `reason`.
    
    Raises:
        ValueError: If the proposal changed concurrently and the database update did not succeed.
    """
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
    """
    Backfills missing position exit plans for open positions using executed proposals that include valid stop-loss and take-profit controls.
    
    If apply_repair is False the function only returns candidate repair items; if True it also persists the created position plans to the database.
    
    Parameters:
        apply_repair (bool): When True, persist repaired position plans to the database; when False, perform a dry run.
        max_holding_bars (int): Maximum holding bars to set on any created position plan.
    
    Returns:
        list[PositionPlanRepairItem]: A list of repair items for each inspected open position. Each item has `status` set to `"created"` (if persisted) or `"candidate"`/`"skipped"`, includes the reason, and—when applicable—the originating proposal id, side, entry_price, stop_loss, and take_profit.
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
            "reason": (
                "repaired from executed proposal"
                if apply_repair
                else "dry-run candidate from executed proposal"
            ),
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
    """
    Mark a pending trade proposal as expired and persist the change.
    
    Parameters:
        proposal_id (str): Identifier of the trade proposal to expire.
    
    Returns:
        TradeProposalRecord: The updated proposal record with status set to "expired" and `updated_at` refreshed.
    
    Raises:
        ValueError: If the proposal changed before the expiry could be recorded.
    """
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
    """
    Builds an ExecutionIntent populated from a trade proposal and runtime settings.
    
    Parameters:
        proposal (TradeProposalRecord): Source trade proposal whose fields (symbol, side, order details, risk controls, thesis, confidence, and identifiers) populate the intent.
        settings (Settings): Runtime settings whose `runtime_mode` and `execution_backend` are copied into the intent and used as the adapter name.
    
    Returns:
        ExecutionIntent: An execution intent reflecting the proposal's execution parameters, marked approved and annotated with backend metadata including the proposal id and source.
    """
    return ExecutionIntent(
        symbol=proposal.symbol,
        side=proposal.side,
        order_type=proposal.order_type,
        quantity=proposal.quantity,
        notional=proposal.notional,
        limit_price=proposal.limit_price,
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
    """
    Append a trimmed note to existing notes, separated by a newline when both are present.
    
    Parameters:
        existing (str): The current notes; may be an empty string.
        note (str): The note to append; leading and trailing whitespace will be removed.
    
    Returns:
        str: The merged notes. If the trimmed `note` is empty, returns `existing`. If `existing` is empty, returns the trimmed `note`. Otherwise returns `existing` followed by a newline and the trimmed `note`.
    """
    cleaned = note.strip()
    if not cleaned:
        return existing
    if not existing:
        return cleaned
    return f"{existing}\n{cleaned}"


def _require_review_note(action: str, note: str) -> str:
    """
    Validate and return a non-empty review note for an action.
    
    Parameters:
    	action (str): Action name used in the error message when `note` is empty.
    	note (str): Candidate review note to validate and trim.
    
    Returns:
    	str: Trimmed review note.
    
    Raises:
    	ValueError: If `note` is empty after trimming.
    """
    cleaned = note.strip()
    if not cleaned:
        raise ValueError(f"Trade proposal {action} requires review_notes.")
    return cleaned


def _save_position_plan_from_proposal(
    db: TradingDatabase,
    *,
    proposal: TradeProposalRecord,
    outcome: ExecutionOutcome,
) -> None:
    """
    Create and persist a position exit plan when an executed proposal produced non-zero fills and includes stop-loss and take-profit controls.
    
    Parameters:
        db (TradingDatabase): Database used to persist the position plan.
        proposal (TradeProposalRecord): The trade proposal containing symbol, side, reference price, stop-loss, take-profit, and optional invalidation condition.
        outcome (ExecutionOutcome): The execution outcome whose `status`, `filled_quantity`, and `average_fill_price` determine whether a plan is created.
    
    Behavior:
        - Does nothing unless `outcome.status` is "filled" or "partially_filled", `outcome.filled_quantity` > 0, and both `proposal.stop_loss` and `proposal.take_profit` are present.
        - When conditions are met, saves a position plan with:
            - entry_price: `outcome.average_fill_price` if present, otherwise `proposal.reference_price`
            - stop_loss and take_profit from the proposal
            - max_holding_bars set to 20 and holding_bars set to 0
            - invalidation_logic set to `proposal.invalidation_condition` if present, otherwise a default manual-repair message
    """
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
    """
    Validate that a trade proposal includes coherent stop-loss and take-profit risk controls.
    
    Parameters:
        proposal (TradeProposalRecord): The trade proposal to validate; must include `side`, `reference_price`, `stop_loss`, and `take_profit`.
    
    Raises:
        ValueError: If either `stop_loss` or `take_profit` is missing, or if the controls do not satisfy the side-specific ordering:
            - For `side == "buy"`: requires stop_loss < reference_price < take_profit.
            - For `side == "sell"`: requires take_profit < reference_price < stop_loss.
    """
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
    """
    Finds the first proposal in the provided list for the symbol and inferred side that is executed and has valid stop-loss/take-profit risk controls.
    
    Parameters:
        symbol (str): The equity symbol to match.
        quantity (float): Position quantity used to infer expected side (`> 0` -> "buy", otherwise "sell").
        proposals (list[TradeProposalRecord]): Proposals to search, evaluated in the given order.
    
    Returns:
        TradeProposalRecord | None: The first matching executed proposal with valid risk controls, or `None` if none found.
    """
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
    """
    Convert the given value to its string representation, or return None if the value is None.
    
    Parameters:
        value (object): The input to convert.
    
    Returns:
        str | None: The string representation of `value`, or `None` when `value` is `None`.
    """
    if value is None:
        return None
    return str(value)


def _proposal_status_for_outcome(outcome_status: str) -> TradeProposalStatus:
    """
    Map a broker execution outcome status string to the corresponding trade proposal status.
    
    Parameters:
        outcome_status (str): Broker-provided execution outcome status.
    
    Returns:
        TradeProposalStatus: `'executed'` if `outcome_status` is one of the executed outcomes, `'approved'` if `outcome_status` is `'accepted'`, `'failed'` otherwise.
    """
    if outcome_status in _EXECUTED_OUTCOMES:
        return "executed"
    if outcome_status == "accepted":
        return "approved"
    return "failed"
