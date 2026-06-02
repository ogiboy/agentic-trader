from typing import Literal, NotRequired, TypedDict

from agentic_trader.schemas import TradeProposalStatus, TradeSide

TERMINAL_PROPOSAL_STATUSES: set[TradeProposalStatus] = {
    "executed",
    "rejected",
    "failed",
    "expired",
}

EXECUTED_OUTCOMES = frozenset({"filled", "partially_filled"})

MANUAL_RISK_PLAN_INVALIDATION = (
    "Manual proposal risk plan: exit on stop loss, take profit, or max holding period."
)

REPAIRED_RISK_PLAN_INVALIDATION = "Repaired from executed proposal risk plan."


class PositionPlanRepairItem(TypedDict):
    symbol: str
    status: Literal["created", "candidate", "skipped"]
    reason: str
    proposal_id: NotRequired[str]
    side: NotRequired[TradeSide]
    entry_price: NotRequired[float]
    stop_loss: NotRequired[float]
    take_profit: NotRequired[float]
