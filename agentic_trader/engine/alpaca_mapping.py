from uuid import uuid4

from agentic_trader.engine.broker_utils import (
    ALPACA_CANCELLED_STATUSES,
    ALPACA_NO_FILL_STATUSES,
    ALPACA_REJECTED_STATUSES,
    alpaca_client_order_id,
    coerce_float,
)
from agentic_trader.execution.intent import (
    ExecutionIntent,
    ExecutionOutcome,
    ExecutionOutcomeStatus,
    OpenOrderSnapshot,
)
from agentic_trader.schemas import PortfolioSnapshot, PositionSnapshot
from agentic_trader.security import redact_sensitive_text


def alpaca_order_kwargs(intent: ExecutionIntent) -> dict[str, object]:
    from alpaca.trading.enums import OrderSide, OrderType, TimeInForce

    order_type = OrderType.LIMIT if intent.order_type == "limit" else OrderType.MARKET
    kwargs: dict[str, object] = {
        "symbol": intent.symbol.upper(),
        "side": OrderSide.BUY if intent.side == "buy" else OrderSide.SELL,
        "type": order_type,
        "time_in_force": TimeInForce.DAY,
        "client_order_id": alpaca_client_order_id(intent.intent_id),
    }
    if intent.quantity is not None:
        kwargs["qty"] = intent.quantity
    elif intent.notional is not None:
        kwargs["notional"] = intent.notional
    if intent.order_type == "limit":
        kwargs["limit_price"] = intent.limit_price
    return kwargs


def outcome_from_alpaca_order(
    intent: ExecutionIntent,
    order: object,
    *,
    adapter_name: str,
    action: str = "submitted",
) -> ExecutionOutcome:
    filled_quantity = coerce_float(getattr(order, "filled_qty", 0.0))
    average_fill_price = coerce_float(
        getattr(order, "filled_avg_price", None), default=0.0
    )
    raw_status = str(getattr(order, "status", "accepted")).lower()
    status = _normalized_order_status(
        raw_status=raw_status,
        filled_quantity=filled_quantity,
    )
    raw_rejection_reason = str(getattr(order, "reject_reason", "")) or None
    safe_rejection_reason = (
        redact_sensitive_text(raw_rejection_reason, max_length=160)
        if raw_rejection_reason
        else None
    )
    return ExecutionOutcome(
        intent_id=intent.intent_id,
        order_id=str(getattr(order, "id", f"alpaca-paper-{uuid4().hex[:12]}")),
        status=status,
        adapter_name=adapter_name,
        execution_backend="alpaca_paper",
        filled_quantity=filled_quantity,
        average_fill_price=average_fill_price or None,
        rejection_reason=(
            safe_rejection_reason
            if status in {"cancelled", "no_fill", "rejected"}
            else None
        ),
        message=f"Alpaca paper order {action} with broker status {raw_status}.",
    )


def position_snapshot_from_alpaca_position(item: object) -> PositionSnapshot:
    return PositionSnapshot(
        symbol=str(getattr(item, "symbol", "")),
        quantity=coerce_float(getattr(item, "qty", 0.0)),
        average_price=coerce_float(getattr(item, "avg_entry_price", 0.0)),
        market_price=coerce_float(getattr(item, "current_price", 0.0)),
        market_value=coerce_float(getattr(item, "market_value", 0.0)),
        unrealized_pnl=coerce_float(getattr(item, "unrealized_pl", 0.0)),
    )


def portfolio_snapshot_from_alpaca_account(
    account: object,
    *,
    positions: list[PositionSnapshot],
) -> PortfolioSnapshot:
    return PortfolioSnapshot(
        cash=coerce_float(getattr(account, "cash", 0.0)),
        market_value=coerce_float(getattr(account, "long_market_value", 0.0))
        + coerce_float(getattr(account, "short_market_value", 0.0)),
        equity=coerce_float(getattr(account, "portfolio_value", 0.0)),
        realized_pnl=0.0,
        unrealized_pnl=sum(position.unrealized_pnl for position in positions),
        open_positions=len(positions),
    )


def open_order_snapshot_from_alpaca_order(item: object) -> OpenOrderSnapshot:
    raw_side = str(getattr(item, "side", "buy")).lower()
    side = "sell" if raw_side == "sell" else "buy"
    return OpenOrderSnapshot(
        order_id=str(getattr(item, "id", "")),
        intent_id=str(getattr(item, "client_order_id", "")) or None,
        symbol=str(getattr(item, "symbol", "")),
        side=side,
        quantity=coerce_float(getattr(item, "qty", 0.0)) or None,
        notional=coerce_float(getattr(item, "notional", 0.0)) or None,
        status=str(getattr(item, "status", "open")),
        created_at=str(getattr(item, "created_at", "")),
    )


def _normalized_order_status(
    *, raw_status: str, filled_quantity: float
) -> ExecutionOutcomeStatus:
    if raw_status in ALPACA_REJECTED_STATUSES:
        return "rejected"
    if filled_quantity > 0 and (
        raw_status in ALPACA_CANCELLED_STATUSES
        or raw_status in ALPACA_NO_FILL_STATUSES
        or raw_status == "partially_filled"
    ):
        return "partially_filled"
    if raw_status in ALPACA_CANCELLED_STATUSES:
        return "cancelled"
    if raw_status in ALPACA_NO_FILL_STATUSES:
        return "no_fill"
    if filled_quantity > 0:
        return "filled"
    return "accepted"
