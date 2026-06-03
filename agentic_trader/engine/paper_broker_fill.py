from dataclasses import dataclass

from agentic_trader.schemas import ExecutionDecision


@dataclass(frozen=True)
class FillProjection:
    cash_delta: float
    realized_pnl_delta: float
    new_quantity: float
    new_average_price: float


def weighted_average(
    current_qty: float, current_avg: float, fill_qty: float, fill_price: float
) -> float:
    total_qty = current_qty + fill_qty
    if total_qty == 0:
        return 0.0
    return ((current_qty * current_avg) + (fill_qty * fill_price)) / total_qty


def apply_buy(
    *, quantity: float, price: float, current_qty: float, current_avg: float
) -> FillProjection:
    cash_delta = -(quantity * price)
    realized_pnl_delta = 0.0

    if current_qty < 0:
        cover_qty = min(quantity, abs(current_qty))
        realized_pnl_delta += (current_avg - price) * cover_qty
        remaining_buy = quantity - cover_qty
        new_qty = current_qty + quantity
        if new_qty > 0:
            new_avg = price if remaining_buy > 0 else 0.0
        elif new_qty == 0:
            new_avg = 0.0
        else:
            new_avg = current_avg
        return FillProjection(
            cash_delta=cash_delta,
            realized_pnl_delta=realized_pnl_delta,
            new_quantity=new_qty,
            new_average_price=new_avg,
        )

    new_qty = current_qty + quantity
    new_avg = weighted_average(current_qty, current_avg, quantity, price)
    return FillProjection(
        cash_delta=cash_delta,
        realized_pnl_delta=realized_pnl_delta,
        new_quantity=new_qty,
        new_average_price=new_avg,
    )


def apply_sell(
    *, quantity: float, price: float, current_qty: float, current_avg: float
) -> FillProjection:
    cash_delta = quantity * price
    realized_pnl_delta = 0.0

    if current_qty > 0:
        close_qty = min(quantity, current_qty)
        realized_pnl_delta += (price - current_avg) * close_qty
        remaining_sell = quantity - close_qty
        new_qty = current_qty - quantity
        if new_qty < 0:
            new_avg = price if remaining_sell > 0 else 0.0
        elif new_qty == 0:
            new_avg = 0.0
        else:
            new_avg = current_avg
        return FillProjection(
            cash_delta=cash_delta,
            realized_pnl_delta=realized_pnl_delta,
            new_quantity=new_qty,
            new_average_price=new_avg,
        )

    new_qty = current_qty - quantity
    new_avg = weighted_average(abs(current_qty), current_avg, quantity, price)
    return FillProjection(
        cash_delta=cash_delta,
        realized_pnl_delta=realized_pnl_delta,
        new_quantity=new_qty,
        new_average_price=new_avg,
    )


def project_fill(
    decision: ExecutionDecision,
    *,
    quantity: float,
    current_qty: float,
    current_avg: float,
    allow_short: bool,
) -> FillProjection | None:
    if decision.side == "buy":
        return apply_buy(
            quantity=quantity,
            price=decision.entry_price,
            current_qty=current_qty,
            current_avg=current_avg,
        )
    if allow_short or (current_qty > 0 and quantity <= current_qty):
        return apply_sell(
            quantity=quantity,
            price=decision.entry_price,
            current_qty=current_qty,
            current_avg=current_avg,
        )
    return None


def rejects_same_direction(decision: ExecutionDecision, current_qty: float) -> bool:
    return (decision.side == "buy" and current_qty > 0) or (
        decision.side == "sell" and current_qty < 0
    )
