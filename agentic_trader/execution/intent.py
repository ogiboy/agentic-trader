from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Self
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator
from agentic_trader.config import Settings
from agentic_trader.schemas import ExecutionBackend, ExecutionDecision, ExecutionSide

OrderType = Literal["market", "limit", "stop", "stop_limit"]
ExecutionOutcomeStatus = Literal[
    "accepted",
    "filled",
    "partially_filled",
    "rejected",
    "blocked",
    "cancelled",
    "no_fill",
    "unsupported",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ExecutionIntent(BaseModel):
    """Broker-facing intent derived from agent decisions and guard output."""

    intent_id: str = Field(default_factory=lambda: f"intent-{uuid4().hex[:12]}")
    timestamp: str = Field(default_factory=_utc_now)
    created_at: str | None = None
    symbol: str
    side: ExecutionSide
    order_type: OrderType = "market"
    quantity: float | None = Field(default=None, gt=0.0)
    notional: float | None = Field(default=None, gt=0.0)
    reference_price: float = Field(gt=0.0)
    confidence: float = Field(ge=0.0, le=1.0)
    thesis: str
    stop_loss: float | None = Field(default=None, gt=0.0)
    take_profit: float | None = Field(default=None, gt=0.0)
    invalidation_condition: str | None = None
    approved: bool = False
    source_run_id: str | None = None
    reasoning_id: str | None = None
    trace_link: str | None = None
    runtime_mode: Literal["training", "operation"] = "operation"
    execution_backend: ExecutionBackend = "paper"
    adapter_name: str = "paper"
    backend_metadata: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _sync_timestamp_fields(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        timestamp = data.get("timestamp")
        created_at = data.get("created_at")
        if timestamp is None and created_at is not None:
            data["timestamp"] = created_at
        elif created_at is None and timestamp is not None:
            data["created_at"] = timestamp
        elif timestamp is not None and created_at is not None and timestamp != created_at:
            raise ValueError("Execution intent timestamp and created_at must match.")
        return data

    @model_validator(mode="after")
    def _require_size_for_approved_trade(self) -> Self:
        if self.created_at is None:
            self.created_at = self.timestamp
        missing_size = self.quantity is None and self.notional is None
        if self.approved and self.side != "hold" and missing_size:
            raise ValueError("Approved execution intents require quantity or notional.")
        return self


class ExecutionOutcome(BaseModel):
    """Result returned by a broker adapter after handling an execution intent."""

    intent_id: str
    order_id: str | None = None
    created_at: str = Field(default_factory=_utc_now)
    status: ExecutionOutcomeStatus
    adapter_name: str
    execution_backend: ExecutionBackend
    filled_quantity: float = Field(default=0.0, ge=0.0)
    average_fill_price: float | None = Field(default=None, gt=0.0)
    rejection_reason: str | None = None
    message: str = ""
    simulated_metadata: dict[str, object] = Field(default_factory=dict)


class BrokerHealthcheck(BaseModel):
    """Small broker-adapter health summary for CLI and observer surfaces."""

    adapter_name: str
    execution_backend: ExecutionBackend
    ok: bool
    simulated: bool = False
    live: bool = False
    blocked: bool = False
    message: str


class OpenOrderSnapshot(BaseModel):
    """Minimal open-order projection for future broker adapters."""

    order_id: str
    intent_id: str | None = None
    symbol: str
    side: ExecutionSide
    quantity: float | None = None
    notional: float | None = None
    status: str
    created_at: str


def build_execution_intent(
    *,
    decision: ExecutionDecision,
    settings: Settings,
    run_id: str | None = None,
    reasoning_id: str | None = None,
    trace_link: str | None = None,
    invalidation_condition: str | None = None,
    reference_equity: float | None = None,
    adapter_name: str | None = None,
) -> ExecutionIntent:
    """Translate the current guard decision into the broker-facing intent contract."""

    notional: float | None = None
    if decision.side != "hold" and reference_equity is not None:
        notional = max(0.0, reference_equity * decision.position_size_pct) or None

    return ExecutionIntent(
        symbol=decision.symbol,
        side=decision.side,
        order_type="market",
        quantity=None,
        notional=notional,
        reference_price=decision.entry_price,
        confidence=decision.confidence,
        thesis=decision.rationale,
        stop_loss=decision.stop_loss,
        take_profit=decision.take_profit,
        invalidation_condition=invalidation_condition,
        approved=decision.approved,
        source_run_id=run_id,
        reasoning_id=reasoning_id,
        trace_link=trace_link,
        runtime_mode=settings.runtime_mode,
        execution_backend=settings.execution_backend,
        adapter_name=adapter_name or settings.execution_backend,
        backend_metadata={
            "position_size_pct": decision.position_size_pct,
            "source": "execution_guard",
        },
    )
