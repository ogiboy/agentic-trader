from typing import cast

from agentic_trader.finance.proposal_types import (
    EXECUTED_OUTCOMES,
    REPAIRED_RISK_PLAN_INVALIDATION,
    PositionPlanRepairItem,
)
from agentic_trader.finance.proposal_utils import validate_proposal_risk_controls
from agentic_trader.schemas import TradeProposalRecord, TradeSide
from agentic_trader.storage.db import TradingDatabase


def repair_missing_position_plans(
    *,
    db: TradingDatabase,
    apply_repair: bool = False,
    max_holding_bars: int = 20,
) -> list[PositionPlanRepairItem]:
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
                    candidate.invalidation_condition or REPAIRED_RISK_PLAN_INVALIDATION
                ),
            )
    return repairs


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
        if proposal.execution_outcome_status not in EXECUTED_OUTCOMES:
            continue
        try:
            validate_proposal_risk_controls(proposal)
        except ValueError:
            continue
        return proposal
    return None
