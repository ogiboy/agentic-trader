from dataclasses import dataclass
from typing import Any, Literal
from uuid import uuid4

from agentic_trader.execution.symbols import is_v1_us_equity_symbol
from agentic_trader.schemas import TradeProposalRecord, TradeSide
from agentic_trader.time_utils import utc_now_iso


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


def prepare_trade_proposal(
    *, draft: TradeProposalDraft | None = None, **fields: Any
) -> TradeProposalRecord:
    proposal_draft = coerce_trade_proposal_draft(draft=draft, fields=fields)
    validate_trade_proposal_draft(proposal_draft)
    symbol = proposal_draft.symbol.strip().upper()
    now = utc_now_iso()
    return TradeProposalRecord(
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


def validate_trade_proposal_draft(proposal_draft: TradeProposalDraft) -> None:
    validate_trade_proposal_size(proposal_draft)
    validate_trade_proposal_order(proposal_draft)
    validate_trade_proposal_confidence(proposal_draft)
    symbol = proposal_draft.symbol.strip().upper()
    if not is_v1_us_equity_symbol(symbol):
        raise ValueError("Trade proposals require a simple V1 US equity symbol.")


def validate_trade_proposal_size(proposal_draft: TradeProposalDraft) -> None:
    if proposal_draft.quantity is None and proposal_draft.notional is None:
        raise ValueError("Trade proposals require quantity or notional.")
    if proposal_draft.quantity is not None and proposal_draft.notional is not None:
        raise ValueError("Trade proposals require exactly one of quantity or notional.")
    if proposal_draft.quantity is not None and proposal_draft.quantity <= 0:
        raise ValueError("Trade proposals require quantity greater than zero.")
    if proposal_draft.notional is not None and proposal_draft.notional <= 0:
        raise ValueError("Trade proposals require notional greater than zero.")


def validate_trade_proposal_order(proposal_draft: TradeProposalDraft) -> None:
    if proposal_draft.order_type not in {"limit", "market"}:
        raise ValueError("Trade proposals require order_type to be limit or market.")
    if proposal_draft.order_type == "limit":
        if proposal_draft.limit_price is None:
            raise ValueError("Limit trade proposals require limit_price.")
        if proposal_draft.limit_price <= 0:
            raise ValueError(
                "Limit trade proposals require limit_price greater than zero."
            )
        if proposal_draft.quantity is None:
            raise ValueError("Limit trade proposals require quantity.")
    elif proposal_draft.limit_price is not None:
        raise ValueError("Market trade proposals must not include limit_price.")
    if proposal_draft.reference_price <= 0:
        raise ValueError("Trade proposals require reference_price greater than zero.")


def validate_trade_proposal_confidence(proposal_draft: TradeProposalDraft) -> None:
    if not 0 <= proposal_draft.confidence <= 1:
        raise ValueError("Trade proposals require confidence between 0 and 1.")


def coerce_trade_proposal_draft(
    *,
    draft: TradeProposalDraft | None,
    fields: dict[str, Any],
) -> TradeProposalDraft:
    if draft is not None and fields:
        raise ValueError("Pass either draft or proposal fields, not both.")
    if draft is not None:
        return draft
    return TradeProposalDraft(**fields)
