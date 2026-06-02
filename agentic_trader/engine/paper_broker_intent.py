from agentic_trader.execution.intent import (
    ExecutionIntent,
    ExecutionOutcome,
    ExecutionOutcomeStatus,
)
from agentic_trader.schemas import ExecutionDecision


def position_size_pct_from_intent(intent: ExecutionIntent) -> float:
    value = intent.backend_metadata.get("position_size_pct")
    if isinstance(value, int | float | str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def decision_from_intent(intent: ExecutionIntent) -> ExecutionDecision:
    return ExecutionDecision(
        approved=intent.approved,
        side=intent.side,
        symbol=intent.symbol,
        entry_price=intent.reference_price,
        stop_loss=intent.stop_loss or intent.reference_price,
        take_profit=intent.take_profit or intent.reference_price,
        position_size_pct=position_size_pct_from_intent(intent),
        confidence=intent.confidence,
        rationale=intent.thesis,
    )


def quantity_from_intent(
    intent: ExecutionIntent,
    *,
    account_equity: float,
    position_size_pct: float,
) -> float:
    if intent.quantity is not None:
        return round(intent.quantity, 6)
    notional = intent.notional
    if notional is None:
        notional = max(0.0, account_equity * position_size_pct)
    return round(notional / intent.reference_price, 6)


def paper_outcome(
    intent: ExecutionIntent,
    *,
    order_id: str,
    status: ExecutionOutcomeStatus,
    message: str,
    filled_quantity: float = 0.0,
    average_fill_price: float | None = None,
    rejection_reason: str | None = None,
    simulated_metadata: dict[str, object] | None = None,
) -> ExecutionOutcome:
    return ExecutionOutcome(
        intent_id=intent.intent_id,
        order_id=order_id,
        status=status,
        adapter_name=intent.adapter_name,
        execution_backend=intent.execution_backend,
        filled_quantity=filled_quantity,
        average_fill_price=average_fill_price,
        rejection_reason=rejection_reason,
        message=message,
        simulated_metadata=simulated_metadata or {},
    )
