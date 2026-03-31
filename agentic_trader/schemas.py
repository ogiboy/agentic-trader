from typing import Literal, TypeAlias

from pydantic import BaseModel, Field

RiskProfile: TypeAlias = Literal["conservative", "balanced", "aggressive"]
TradeStyle: TypeAlias = Literal["swing", "position", "intraday"]


class LLMHealthStatus(BaseModel):
    provider: str
    base_url: str
    model_name: str
    service_reachable: bool
    model_available: bool
    message: str


class InvestmentPreferences(BaseModel):
    regions: list[str] = Field(default_factory=lambda: ["US"])
    exchanges: list[str] = Field(default_factory=lambda: ["NASDAQ", "NYSE"])
    currencies: list[str] = Field(default_factory=lambda: ["USD"])
    sectors: list[str] = Field(default_factory=list)
    risk_profile: RiskProfile = "balanced"
    trade_style: TradeStyle = "swing"
    notes: str = ""


class MarketSnapshot(BaseModel):
    symbol: str
    interval: str
    last_close: float
    ema_20: float
    ema_50: float
    atr_14: float
    rsi_14: float
    volatility_20: float
    return_5: float
    return_20: float
    volume_ratio_20: float
    bars_analyzed: int


class RegimeAssessment(BaseModel):
    regime: Literal[
        "trend_up",
        "trend_down",
        "range",
        "breakout_candidate",
        "high_volatility",
        "no_trade",
    ]
    direction_bias: Literal["long", "short", "flat"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    key_risks: list[str] = Field(default_factory=list)
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
    action: Literal["buy", "sell", "hold"]
    timeframe: str
    entry_logic: str
    invalidation_logic: str
    confidence: float = Field(ge=0.0, le=1.0)
    reason_codes: list[str] = Field(default_factory=list)
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
    side: Literal["buy", "sell", "hold"]
    symbol: str
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size_pct: float
    confidence: float
    rationale: str


class PortfolioSnapshot(BaseModel):
    cash: float
    market_value: float
    equity: float
    realized_pnl: float
    unrealized_pnl: float
    open_positions: int


class PositionSnapshot(BaseModel):
    symbol: str
    quantity: float
    average_price: float
    market_price: float
    market_value: float
    unrealized_pnl: float


class RunArtifacts(BaseModel):
    snapshot: MarketSnapshot
    regime: RegimeAssessment
    strategy: StrategyPlan
    risk: RiskPlan
    execution: ExecutionDecision

    def fallback_components(self) -> list[str]:
        components: list[str] = []
        if self.regime.source == "fallback":
            components.append("regime")
        if self.strategy.source == "fallback":
            components.append("strategy")
        if self.risk.source == "fallback":
            components.append("risk")
        return components

    def used_fallback(self) -> bool:
        return bool(self.fallback_components())
