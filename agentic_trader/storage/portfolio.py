"""Paper portfolio storage facade."""

from agentic_trader.storage.portfolio_account import (
    get_account_snapshot,
    list_account_marks,
    record_account_mark,
)
from agentic_trader.storage.portfolio_fills import apply_fill, mark_price
from agentic_trader.storage.portfolio_plans import (
    delete_position_plan,
    get_position_plan,
    list_position_plans,
    save_position_plan,
    update_position_plan_holding,
)
from agentic_trader.storage.portfolio_positions import get_position, list_positions
from agentic_trader.storage.portfolio_risk import build_daily_risk_report

__all__ = [
    "apply_fill",
    "build_daily_risk_report",
    "delete_position_plan",
    "get_account_snapshot",
    "get_position",
    "get_position_plan",
    "list_account_marks",
    "list_position_plans",
    "list_positions",
    "mark_price",
    "record_account_mark",
    "save_position_plan",
    "update_position_plan_holding",
]
