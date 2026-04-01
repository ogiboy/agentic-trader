from typing import Literal, TypeAlias

from pydantic import BaseModel, Field

RiskProfile: TypeAlias = Literal["conservative", "balanced", "aggressive"]
TradeStyle: TypeAlias = Literal["swing", "position", "intraday"]
BehaviorPreset: TypeAlias = Literal["balanced_core", "trend_biased", "contrarian", "capital_preservation"]
AgentProfile: TypeAlias = Literal["neutral", "disciplined", "aggressive", "explanatory"]
ChatPersona: TypeAlias = Literal["operator_liaison", "regime_analyst", "strategy_selector", "risk_steward", "portfolio_manager"]
CoordinatorFocus: TypeAlias = Literal["trend_following", "breakout", "mean_reversion", "capital_preservation", "no_trade"]


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
    behavior_preset: BehaviorPreset = "balanced_core"
    agent_profile: AgentProfile = "explanatory"
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


class AccountMark(BaseModel):
    mark_id: str
    created_at: str
    source: str
    note: str
    cycle_count: int | None = None
    symbol: str | None = None
    cash: float
    market_value: float
    equity: float
    realized_pnl: float
    unrealized_pnl: float
    open_positions: int


class ServiceStateSnapshot(BaseModel):
    service_name: str
    state: Literal["idle", "starting", "running", "stopping", "stopped", "completed", "failed", "blocked"]
    updated_at: str
    started_at: str | None = None
    last_heartbeat_at: str | None = None
    continuous: bool = False
    poll_seconds: int | None = None
    cycle_count: int = 0
    current_symbol: str | None = None
    last_error: str | None = None
    pid: int | None = None
    stop_requested: bool = False
    message: str = ""


class ServiceEvent(BaseModel):
    event_id: str
    created_at: str
    level: Literal["info", "warning", "error"]
    event_type: str
    message: str
    cycle_count: int | None = None
    symbol: str | None = None


class PositionSnapshot(BaseModel):
    symbol: str
    quantity: float
    average_price: float
    market_price: float
    market_value: float
    unrealized_pnl: float


class PositionPlanSnapshot(BaseModel):
    symbol: str
    side: Literal["buy", "sell"]
    entry_price: float
    stop_loss: float
    take_profit: float
    max_holding_bars: int
    holding_bars: int
    invalidation_logic: str
    updated_at: str


class PositionExitDecision(BaseModel):
    should_exit: bool
    side: Literal["buy", "sell", "hold"]
    symbol: str
    reason: Literal["stop_loss", "take_profit", "invalidation", "time_exit", "no_exit"]
    rationale: str
    exit_price: float


class ResearchCoordinatorBrief(BaseModel):
    market_focus: CoordinatorFocus
    priority_signals: list[str] = Field(default_factory=list)
    caution_flags: list[str] = Field(default_factory=list)
    summary: str
    source: Literal["llm", "fallback"] = "llm"
    fallback_reason: str | None = None


class ManagerDecision(BaseModel):
    approved: bool
    action_bias: Literal["buy", "sell", "hold"]
    confidence_cap: float = Field(ge=0.0, le=1.0)
    size_multiplier: float = Field(gt=0.0, le=1.0)
    rationale: str
    escalation_flags: list[str] = Field(default_factory=list)
    source: Literal["llm", "fallback"] = "llm"
    fallback_reason: str | None = None


class ReviewNote(BaseModel):
    summary: str
    strengths: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_checks: list[str] = Field(default_factory=list)


class PreferenceUpdate(BaseModel):
    regions: list[str] | None = None
    exchanges: list[str] | None = None
    currencies: list[str] | None = None
    sectors: list[str] | None = None
    risk_profile: RiskProfile | None = None
    trade_style: TradeStyle | None = None
    behavior_preset: BehaviorPreset | None = None
    agent_profile: AgentProfile | None = None
    notes: str | None = None


class OperatorInstruction(BaseModel):
    summary: str
    should_update_preferences: bool = False
    preference_update: PreferenceUpdate = Field(default_factory=PreferenceUpdate)
    requires_confirmation: bool = True
    rationale: str


class TradeJournalEntry(BaseModel):
    trade_id: str
    opened_at: str
    closed_at: str | None = None
    symbol: str
    run_id: str | None = None
    entry_order_id: str
    exit_order_id: str | None = None
    planned_side: Literal["buy", "sell", "hold"]
    approved: bool
    journal_status: Literal["open", "closed", "rejected", "no_fill"]
    entry_price: float
    exit_price: float | None = None
    stop_loss: float
    take_profit: float
    position_size_pct: float
    confidence: float
    coordinator_focus: CoordinatorFocus
    strategy_family: str
    manager_bias: Literal["buy", "sell", "hold"]
    review_summary: str
    exit_reason: str | None = None
    realized_pnl: float | None = None
    notes: str = ""


class DailyRiskReport(BaseModel):
    report_date: str
    generated_at: str
    cash: float
    market_value: float
    equity: float
    realized_pnl: float
    unrealized_pnl: float
    open_positions: int
    fills_today: int
    marks_recorded: int
    daily_realized_pnl: float
    gross_exposure_pct: float
    largest_position_pct: float
    drawdown_from_peak_pct: float
    warnings: list[str] = Field(default_factory=list)


class BacktestTrade(BaseModel):
    symbol: str
    entry_at: str
    exit_at: str | None = None
    side: Literal["buy", "sell"]
    entry_price: float
    exit_price: float | None = None
    quantity: float
    status: Literal["open", "closed"]
    exit_reason: str | None = None
    pnl: float | None = None
    used_fallback: bool = False


class BacktestReport(BaseModel):
    symbol: str
    interval: str
    lookback: str
    warmup_bars: int
    total_cycles: int
    total_trades: int
    closed_trades: int
    win_rate: float
    expectancy: float
    total_return_pct: float
    max_drawdown_pct: float
    exposure_pct: float
    fallback_cycles: int
    starting_equity: float
    ending_equity: float
    trades: list[BacktestTrade] = Field(default_factory=list)


class RunArtifacts(BaseModel):
    snapshot: MarketSnapshot
    coordinator: ResearchCoordinatorBrief
    regime: RegimeAssessment
    strategy: StrategyPlan
    risk: RiskPlan
    manager: ManagerDecision
    execution: ExecutionDecision
    review: ReviewNote

    def fallback_components(self) -> list[str]:
        components: list[str] = []
        if self.coordinator.source == "fallback":
            components.append("coordinator")
        if self.regime.source == "fallback":
            components.append("regime")
        if self.strategy.source == "fallback":
            components.append("strategy")
        if self.risk.source == "fallback":
            components.append("risk")
        if self.manager.source == "fallback":
            components.append("manager")
        return components

    def used_fallback(self) -> bool:
        return bool(self.fallback_components())


class RunRecord(BaseModel):
    run_id: str
    created_at: str
    symbol: str
    interval: str
    approved: bool
    artifacts: RunArtifacts
