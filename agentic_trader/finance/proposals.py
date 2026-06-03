from agentic_trader.config import Settings
from agentic_trader.engine.broker import get_broker_adapter, get_broker_order_reader
from agentic_trader.execution.intent import ExecutionOutcome
from agentic_trader.finance.proposal_drafts import (
    TradeProposalDraft,
    prepare_trade_proposal,
)
from agentic_trader.finance.proposal_order_actions import (
    approve_trade_proposal as _approve_trade_proposal,
)
from agentic_trader.finance.proposal_order_actions import (
    reconcile_trade_proposal,
)
from agentic_trader.finance.proposal_order_actions import (
    refresh_trade_proposal_order as _refresh_trade_proposal_order,
)
from agentic_trader.finance.proposal_position_repair import (
    repair_missing_position_plans,
)
from agentic_trader.finance.proposal_state_actions import (
    create_trade_proposal,
    expire_trade_proposal,
    reject_trade_proposal,
)
from agentic_trader.finance.proposal_types import (
    TERMINAL_PROPOSAL_STATUSES,
    PositionPlanRepairItem,
)
from agentic_trader.schemas import TradeProposalRecord
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.time_utils import utc_now_iso

__all__ = [
    "PositionPlanRepairItem",
    "TERMINAL_PROPOSAL_STATUSES",
    "TradeProposalDraft",
    "approve_trade_proposal",
    "create_trade_proposal",
    "expire_trade_proposal",
    "prepare_trade_proposal",
    "reconcile_trade_proposal",
    "refresh_trade_proposal_order",
    "reject_trade_proposal",
    "repair_missing_position_plans",
    "utc_now_iso",
]


def approve_trade_proposal(
    *,
    db: TradingDatabase,
    settings: Settings,
    proposal_id: str,
    review_notes: str = "",
) -> tuple[TradeProposalRecord, ExecutionOutcome]:
    return _approve_trade_proposal(
        db=db,
        settings=settings,
        proposal_id=proposal_id,
        review_notes=review_notes,
        broker_adapter_factory=get_broker_adapter,
    )


def refresh_trade_proposal_order(
    *,
    db: TradingDatabase,
    settings: Settings,
    proposal_id: str,
    review_notes: str = "",
) -> tuple[TradeProposalRecord, ExecutionOutcome]:
    return _refresh_trade_proposal_order(
        db=db,
        settings=settings,
        proposal_id=proposal_id,
        review_notes=review_notes,
        order_reader_factory=get_broker_order_reader,
    )
