from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from agentic_trader.execution.intent import ExecutionIntent, ExecutionOutcome
from agentic_trader.execution.symbols import is_v1_us_equity_symbol
from agentic_trader.schemas import PositionSnapshot


@dataclass(frozen=True)
class RiskExposureProjection:
    projected_symbol_exposure: float
    projected_gross_exposure: float
    max_position_value: float
    max_gross_value: float


def blocked_alpaca_outcome(
    intent: ExecutionIntent, *, backend_name: str, reason: str, message: str
) -> ExecutionOutcome:
    return ExecutionOutcome(
        intent_id=intent.intent_id,
        order_id=f"alpaca-paper-blocked-{uuid4().hex[:12]}",
        status="blocked",
        adapter_name=backend_name,
        execution_backend="alpaca_paper",
        rejection_reason=reason,
        message=message,
    )


def basic_preflight_outcome(
    intent: ExecutionIntent, *, backend_name: str
) -> ExecutionOutcome | None:
    if not intent.approved or intent.side == "hold":
        return blocked_alpaca_outcome(
            intent,
            backend_name=backend_name,
            reason="intent_not_approved",
            message="Alpaca paper adapter did not submit an unapproved or hold intent.",
        )
    if not is_v1_us_equity_symbol(intent.symbol):
        return blocked_alpaca_outcome(
            intent,
            backend_name=backend_name,
            reason="unsupported_symbol_scope",
            message="V1 Alpaca paper adapter only accepts simple US equity symbols.",
        )
    if intent.order_type not in {"market", "limit"}:
        return blocked_alpaca_outcome(
            intent,
            backend_name=backend_name,
            reason="unsupported_order_type",
            message="V1 Alpaca paper adapter only accepts market or limit orders.",
        )
    if intent.quantity is None and intent.notional is None:
        return blocked_alpaca_outcome(
            intent,
            backend_name=backend_name,
            reason="missing_size",
            message="Alpaca paper adapter requires quantity or notional.",
        )
    return None


def limit_order_preflight_outcome(
    intent: ExecutionIntent, *, backend_name: str
) -> ExecutionOutcome | None:
    if intent.order_type != "limit":
        return None
    if intent.limit_price is None:
        return blocked_alpaca_outcome(
            intent,
            backend_name=backend_name,
            reason="missing_limit_price",
            message="Alpaca paper limit orders require limit_price.",
        )
    if intent.quantity is None:
        return blocked_alpaca_outcome(
            intent,
            backend_name=backend_name,
            reason="limit_quantity_required",
            message="Alpaca paper limit orders require quantity.",
        )
    return None


def risk_exposure_projection(
    *,
    intent: ExecutionIntent,
    positions: list[PositionSnapshot],
    equity: float,
    max_position_pct: float,
    max_gross_exposure_pct: float,
) -> RiskExposureProjection:
    reference_price = intent.reference_price
    order_quantity = (
        intent.quantity
        if intent.quantity is not None
        else (intent.notional or 0.0) / reference_price
    )
    signed_order_quantity = order_quantity if intent.side == "buy" else -order_quantity
    current_position = next(
        (
            position
            for position in positions
            if position.symbol.upper() == intent.symbol.upper()
        ),
        None,
    )
    current_quantity = current_position.quantity if current_position else 0.0
    projected_quantity = current_quantity + signed_order_quantity
    current_symbol_exposure = (
        abs(current_position.market_value) if current_position else 0.0
    )
    projected_symbol_exposure = abs(projected_quantity * reference_price)
    current_gross_exposure = sum(abs(position.market_value) for position in positions)
    return RiskExposureProjection(
        projected_symbol_exposure=projected_symbol_exposure,
        projected_gross_exposure=(
            current_gross_exposure - current_symbol_exposure + projected_symbol_exposure
        ),
        max_position_value=equity * max_position_pct,
        max_gross_value=equity * max_gross_exposure_pct,
    )


def position_limit_outcome(
    intent: ExecutionIntent,
    projection: RiskExposureProjection,
    *,
    backend_name: str,
) -> ExecutionOutcome | None:
    if projection.projected_symbol_exposure <= projection.max_position_value:
        return None
    return blocked_alpaca_outcome(
        intent,
        backend_name=backend_name,
        reason="max_position_exceeded",
        message=(
            "Alpaca paper order would exceed max position size: "
            f"projected {projection.projected_symbol_exposure:.2f} > "
            f"limit {projection.max_position_value:.2f}."
        ),
    )


def gross_limit_outcome(
    intent: ExecutionIntent,
    projection: RiskExposureProjection,
    *,
    backend_name: str,
) -> ExecutionOutcome | None:
    if projection.projected_gross_exposure <= projection.max_gross_value:
        return None
    return blocked_alpaca_outcome(
        intent,
        backend_name=backend_name,
        reason="max_gross_exposure_exceeded",
        message=(
            "Alpaca paper order would exceed max gross exposure: "
            f"projected {projection.projected_gross_exposure:.2f} > "
            f"limit {projection.max_gross_value:.2f}."
        ),
    )
