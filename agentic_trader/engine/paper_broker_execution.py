"""Fill and close-position helpers for the paper broker."""

from uuid import uuid4

from agentic_trader.engine.paper_broker_fill import (
    FillProjection,
    apply_buy,
    apply_sell,
)
from agentic_trader.engine.paper_broker_intent import paper_outcome
from agentic_trader.engine.paper_broker_records import exit_order_record
from agentic_trader.execution.intent import ExecutionIntent, ExecutionOutcome
from agentic_trader.schemas import (
    ExecutionDecision,
    PositionExitDecision,
    PositionSnapshot,
)
from agentic_trader.storage.db import TradingDatabase


def would_exceed_cash(
    decision: ExecutionDecision,
    current_qty: float,
    projected_cash: float,
) -> bool:
    return decision.side == "buy" and current_qty >= 0 and projected_cash < 0


def projected_gross_exposure(
    *,
    current_gross_exposure: float,
    current_market_value: float,
    projection: FillProjection,
    entry_price: float,
) -> float:
    return (
        current_gross_exposure
        - current_market_value
        + abs(projection.new_quantity * entry_price)
    )


def would_exceed_open_position_limit(
    *,
    current_open_positions: int,
    current_qty: float,
    new_quantity: float,
    max_open_positions: int,
) -> bool:
    projected_open_positions = current_open_positions
    if current_qty == 0 and new_quantity != 0:
        projected_open_positions += 1
    elif current_qty != 0 and new_quantity == 0:
        projected_open_positions -= 1
    return projected_open_positions > max_open_positions


def guarded_no_fill_outcome(
    *,
    intent: ExecutionIntent,
    order_id: str,
    decision: ExecutionDecision,
    simulated_metadata: dict[str, object] | None,
) -> ExecutionOutcome | None:
    if decision.approved and decision.side != "hold":
        return None
    status = "rejected" if not decision.approved else "no_fill"
    return paper_outcome(
        intent,
        order_id=order_id,
        status=status,
        message=(
            "Execution guard rejected the intent."
            if status == "rejected"
            else "Hold intent recorded without a fill."
        ),
        rejection_reason=decision.rationale if status == "rejected" else None,
        simulated_metadata=simulated_metadata,
    )


def apply_projected_fill(
    db: TradingDatabase,
    *,
    intent: ExecutionIntent,
    order_id: str,
    decision: ExecutionDecision,
    quantity: float,
    projection: FillProjection,
    simulated_metadata: dict[str, object] | None,
) -> ExecutionOutcome:
    db.apply_fill(
        fill_id=f"fill-{uuid4().hex[:12]}",
        order_id=order_id,
        symbol=decision.symbol,
        side=decision.side,
        quantity=quantity,
        price=decision.entry_price,
        cash_delta=projection.cash_delta,
        realized_pnl_delta=projection.realized_pnl_delta,
        new_quantity=projection.new_quantity,
        new_average_price=projection.new_average_price,
    )
    return paper_outcome(
        intent,
        order_id=order_id,
        status="filled",
        message="Paper intent filled immediately.",
        filled_quantity=quantity,
        average_fill_price=decision.entry_price,
        simulated_metadata=simulated_metadata,
    )


def close_paper_position(
    db: TradingDatabase,
    decision: PositionExitDecision,
    position: PositionSnapshot | None,
) -> str:
    if position is None or position.quantity == 0:
        return f"paper-{uuid4().hex[:12]}"

    order_id = f"paper-{uuid4().hex[:12]}"
    quantity = abs(position.quantity)
    if decision.side == "buy":
        projection = apply_buy(
            quantity=quantity,
            price=decision.exit_price,
            current_qty=position.quantity,
            current_avg=position.average_price,
        )
    else:
        projection = apply_sell(
            quantity=quantity,
            price=decision.exit_price,
            current_qty=position.quantity,
            current_avg=position.average_price,
        )

    db.insert_order(exit_order_record(order_id, decision))
    db.apply_fill(
        fill_id=f"fill-{uuid4().hex[:12]}",
        order_id=order_id,
        symbol=decision.symbol,
        side=decision.side,
        quantity=quantity,
        price=decision.exit_price,
        cash_delta=projection.cash_delta,
        realized_pnl_delta=projection.realized_pnl_delta,
        new_quantity=projection.new_quantity,
        new_average_price=projection.new_average_price,
    )
    db.delete_position_plan(decision.symbol)
    db.close_trade_journal(
        symbol=decision.symbol,
        exit_order_id=order_id,
        exit_reason=decision.reason,
        exit_price=decision.exit_price,
        realized_pnl=projection.realized_pnl_delta,
        notes=decision.rationale,
    )
    db.record_account_mark(
        source="position_closed",
        note=f"{decision.symbol} exited via {decision.reason}.",
        symbol=decision.symbol,
    )
    return order_id
