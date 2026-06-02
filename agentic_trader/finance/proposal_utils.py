from agentic_trader.config import Settings
from agentic_trader.execution.intent import ExecutionIntent, ExecutionOutcome
from agentic_trader.finance.proposal_types import (
    EXECUTED_OUTCOMES,
    MANUAL_RISK_PLAN_INVALIDATION,
    TERMINAL_PROPOSAL_STATUSES,
)
from agentic_trader.schemas import TradeProposalRecord, TradeProposalStatus
from agentic_trader.storage.db import TradingDatabase


def load_mutable_proposal(
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


def intent_from_proposal(
    proposal: TradeProposalRecord, *, settings: Settings
) -> ExecutionIntent:
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


def merge_notes(existing: str, note: str) -> str:
    cleaned = note.strip()
    if not cleaned:
        return existing
    if not existing:
        return cleaned
    return f"{existing}\n{cleaned}"


def require_review_note(action: str, note: str) -> str:
    cleaned = note.strip()
    if not cleaned:
        raise ValueError(f"Trade proposal {action} requires review_notes.")
    return cleaned


def save_position_plan_from_proposal(
    db: TradingDatabase,
    *,
    proposal: TradeProposalRecord,
    outcome: ExecutionOutcome,
) -> None:
    if outcome.status not in EXECUTED_OUTCOMES:
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
            proposal.invalidation_condition or MANUAL_RISK_PLAN_INVALIDATION
        ),
    )


def validate_proposal_risk_controls(proposal: TradeProposalRecord) -> None:
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


def str_or_none(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def proposal_status_for_outcome(outcome_status: str) -> TradeProposalStatus:
    if outcome_status in EXECUTED_OUTCOMES:
        return "executed"
    if outcome_status == "accepted":
        return "approved"
    return "failed"
