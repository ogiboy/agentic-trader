from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from agentic_trader.schema_models.types import (
    ExecutionSide,
    ProposalCandidateStatus,
    RegimeName,
    TradeProposalStatus,
    TradeSide,
)

class RegimeAssessment(BaseModel):
    regime: RegimeName
    direction_bias: Literal["long", "short", "flat"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    key_risks: list[str] = Field(default_factory=list[str])
    source: Literal["llm", "fallback"] = "llm"
    fallback_reason: str | None = None

class StrategyPlan(BaseModel):
    strategy_family: Literal[
        "trend_following",
        "pullback",
        "breakout",
        "mean_reversion",
        "no_trade",
    ]
    action: ExecutionSide
    timeframe: str
    entry_logic: str
    invalidation_logic: str
    confidence: float = Field(ge=0.0, le=1.0)
    reason_codes: list[str] = Field(default_factory=list[str])
    source: Literal["llm", "fallback"] = "llm"
    fallback_reason: str | None = None

class RiskPlan(BaseModel):
    position_size_pct: float = Field(gt=0.0, le=1.0)
    stop_loss: float = Field(gt=0.0)
    take_profit: float = Field(gt=0.0)
    risk_reward_ratio: float = Field(gt=0.0)
    max_holding_bars: int = Field(gt=0)
    notes: str
    source: Literal["llm", "fallback"] = "llm"
    fallback_reason: str | None = None

class ExecutionDecision(BaseModel):
    approved: bool
    side: ExecutionSide
    symbol: str
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size_pct: float
    confidence: float
    rationale: str

class TradeProposalRecord(BaseModel):
    proposal_id: str
    created_at: str
    updated_at: str
    symbol: str
    side: TradeSide
    order_type: Literal["market", "limit"] = "market"
    quantity: float | None = Field(default=None, gt=0.0)
    notional: float | None = Field(default=None, gt=0.0)
    limit_price: float | None = Field(default=None, gt=0.0)
    reference_price: float = Field(gt=0.0)
    confidence: float = Field(ge=0.0, le=1.0)
    thesis: str
    stop_loss: float | None = Field(default=None, gt=0.0)
    take_profit: float | None = Field(default=None, gt=0.0)
    invalidation_condition: str | None = None
    source: str = "manual"
    status: TradeProposalStatus = "pending"
    review_notes: str = ""
    rejection_reason: str | None = None
    execution_intent_id: str | None = None
    execution_order_id: str | None = None
    execution_outcome_status: str | None = None

    @model_validator(mode="after")
    def require_quantity_or_notional(self) -> "TradeProposalRecord":
        """
        Ensure exactly one of `quantity` or `notional` is provided and that `limit_price` is consistent with `order_type`.

        Raises:
            ValueError: if both or neither of `quantity` and `notional` are set; if `order_type == "limit"` and `limit_price` is missing or `quantity` is missing; if `order_type != "limit"` and `limit_price` is provided.

        Returns:
            TradeProposalRecord: the validated instance (`self`).
        """
        if self.quantity is None and self.notional is None:
            raise ValueError("Trade proposals require quantity or notional.")
        if self.quantity is not None and self.notional is not None:
            raise ValueError(
                "Trade proposals require exactly one of quantity or notional."
            )
        if self.order_type == "limit":
            if self.limit_price is None:
                raise ValueError("Limit trade proposals require limit_price.")
            if self.quantity is None:
                raise ValueError("Limit trade proposals require quantity.")
        elif self.limit_price is not None:
            raise ValueError("Market trade proposals must not include limit_price.")
        return self

class ProposalCandidateRecord(BaseModel):
    candidate_id: str
    created_at: str
    updated_at: str
    symbol: str
    preset: str
    signal: Literal["buy", "sell", "watch"]
    side: TradeSide | None = None
    score: float = Field(ge=0.0, le=100.0)
    reference_price: float = Field(gt=0.0)
    confidence: float = Field(ge=0.0, le=1.0)
    quantity: float | None = Field(default=None, gt=0.0)
    notional: float | None = Field(default=None, gt=0.0)
    thesis: str
    stop_loss: float | None = Field(default=None, gt=0.0)
    take_profit: float | None = Field(default=None, gt=0.0)
    invalidation_condition: str | None = None
    source: str = "idea-scanner"
    status: ProposalCandidateStatus = "candidate"
    materiality: str
    freshness: str
    liquidity: str
    spread_pct: float = Field(ge=0.0)
    risk_notes: str
    evidence: dict[str, object] = Field(default_factory=dict[str, object])
    proposal_id: str | None = None

    @model_validator(mode="after")
    def validate_sizing(self) -> "ProposalCandidateRecord":
        """
        Validate sizing constraints for a proposal candidate.

        Ensures exactly one of `quantity` or `notional` is provided. If `side` is specified, requires one of `quantity` or `notional` to be present.

        Returns:
            ProposalCandidateRecord: The instance (`self`) when validation succeeds.

        Raises:
            ValueError: If both `quantity` and `notional` are set, or if `side` is provided without either sizing field.
        """
        if self.quantity is not None and self.notional is not None:
            raise ValueError(
                "Proposal candidates require exactly one of quantity or notional."
            )
        if self.side is not None and self.quantity is None and self.notional is None:
            raise ValueError(
                "Proposal candidates with a side require quantity or notional."
            )
        return self

class PortfolioSnapshot(BaseModel):
    cash: float
    market_value: float
    equity: float
    realized_pnl: float
    unrealized_pnl: float
    open_positions: int
