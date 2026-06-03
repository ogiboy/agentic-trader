from __future__ import annotations

from typing import Any

from agentic_trader.engine.alpaca_risk import (
    basic_preflight_outcome,
    gross_limit_outcome,
    limit_order_preflight_outcome,
    position_limit_outcome,
    risk_exposure_projection,
)
from agentic_trader.execution.intent import ExecutionIntent
from agentic_trader.schemas import PositionSnapshot


def _intent(**overrides: object) -> ExecutionIntent:
    payload: dict[str, Any] = {
        "intent_id": "intent-test",
        "timestamp": "2026-06-02T12:00:00Z",
        "created_at": "2026-06-02T12:00:00Z",
        "symbol": "AAPL",
        "side": "buy",
        "order_type": "market",
        "quantity": 10,
        "notional": None,
        "limit_price": None,
        "reference_price": 100,
        "confidence": 0.8,
        "thesis": "Alpaca paper risk test.",
        "approved": True,
        "execution_backend": "alpaca_paper",
        "adapter_name": "alpaca_paper",
    }
    payload.update(overrides)
    return ExecutionIntent.model_construct(**payload)


def test_alpaca_basic_preflight_blocks_unsupported_intents() -> None:
    hold = basic_preflight_outcome(
        _intent(side="hold", approved=False), backend_name="alpaca_paper"
    )
    unsupported_symbol = basic_preflight_outcome(
        _intent(symbol="AKBNK.IS"), backend_name="alpaca_paper"
    )
    missing_size = basic_preflight_outcome(
        _intent(quantity=None, notional=None), backend_name="alpaca_paper"
    )

    assert hold is not None
    assert hold.rejection_reason == "intent_not_approved"
    assert unsupported_symbol is not None
    assert unsupported_symbol.rejection_reason == "unsupported_symbol_scope"
    assert missing_size is not None
    assert missing_size.rejection_reason == "missing_size"
    assert basic_preflight_outcome(_intent(), backend_name="alpaca_paper") is None


def test_alpaca_limit_preflight_requires_limit_price_and_quantity() -> None:
    missing_price = limit_order_preflight_outcome(
        _intent(order_type="limit", limit_price=None),
        backend_name="alpaca_paper",
    )
    missing_quantity = limit_order_preflight_outcome(
        _intent(order_type="limit", limit_price=99.5, quantity=None, notional=1000),
        backend_name="alpaca_paper",
    )

    assert missing_price is not None
    assert missing_price.rejection_reason == "missing_limit_price"
    assert missing_quantity is not None
    assert missing_quantity.rejection_reason == "limit_quantity_required"
    assert (
        limit_order_preflight_outcome(
            _intent(order_type="limit", limit_price=99.5),
            backend_name="alpaca_paper",
        )
        is None
    )


def test_alpaca_risk_projection_blocks_position_and_gross_limits() -> None:
    positions = [
        PositionSnapshot(
            symbol="AAPL",
            quantity=5,
            average_price=100,
            market_price=100,
            market_value=500,
            unrealized_pnl=0,
        ),
        PositionSnapshot(
            symbol="MSFT",
            quantity=4,
            average_price=100,
            market_price=100,
            market_value=400,
            unrealized_pnl=0,
        ),
    ]
    projection = risk_exposure_projection(
        intent=_intent(quantity=20),
        positions=positions,
        equity=2000,
        max_position_pct=0.75,
        max_gross_exposure_pct=1.0,
    )

    assert projection.projected_symbol_exposure == 2500
    assert projection.projected_gross_exposure == 2900
    position_block = position_limit_outcome(
        _intent(quantity=20), projection, backend_name="alpaca_paper"
    )
    gross_block = gross_limit_outcome(
        _intent(quantity=20), projection, backend_name="alpaca_paper"
    )

    assert position_block is not None
    assert position_block.rejection_reason == "max_position_exceeded"
    assert gross_block is not None
    assert gross_block.rejection_reason == "max_gross_exposure_exceeded"
