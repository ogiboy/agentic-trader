from datetime import UTC, datetime
from typing import Literal, TypeAlias

from pydantic import BaseModel, Field, model_validator

RiskProfile: TypeAlias = Literal["conservative", "balanced", "aggressive"]
TradeStyle: TypeAlias = Literal["swing", "position", "intraday"]
BehaviorPreset: TypeAlias = Literal[
    "balanced_core", "trend_biased", "contrarian", "capital_preservation"
]
AgentProfile: TypeAlias = Literal["neutral", "disciplined", "aggressive", "explanatory"]
AgentTone: TypeAlias = Literal["neutral", "supportive", "direct", "forensic"]
StrictnessPreset: TypeAlias = Literal["standard", "strict", "paranoid"]
InterventionStyle: TypeAlias = Literal["hands_off", "balanced", "protective"]
ChatPersona: TypeAlias = Literal[
    "operator_liaison",
    "regime_analyst",
    "strategy_selector",
    "risk_steward",
    "portfolio_manager",
]
CoordinatorFocus: TypeAlias = Literal[
    "trend_following", "breakout", "mean_reversion", "capital_preservation", "no_trade"
]
AgentRole: TypeAlias = Literal[
    "coordinator",
    "fundamental",
    "macro",
    "regime",
    "strategy",
    "risk",
    "manager",
    "explainer",
    "instruction",
]
ExecutionSide: TypeAlias = Literal["buy", "sell", "hold"]
TradeSide: TypeAlias = Literal["buy", "sell"]
PositionExitReason: TypeAlias = Literal[
    "stop_loss", "take_profit", "invalidation", "time_exit", "no_exit"
]
MarketSessionState: TypeAlias = Literal["open", "closed", "always_open", "weekend"]
MTFAlignment: TypeAlias = Literal["bullish", "bearish", "mixed"]
TrendVote: TypeAlias = Literal["bullish", "bearish", "mixed", "insufficient"]
RuntimeMode: TypeAlias = Literal["training", "operation"]
ResearchMode: TypeAlias = Literal["off", "training", "live_prep"]
ExecutionBackend: TypeAlias = Literal["paper", "simulated_real", "alpaca_paper", "live"]
type NewsClassification = Literal[
    "company_specific", "sector_level", "macro_level"
]
AnalysisSignal: TypeAlias = Literal["supportive", "neutral", "cautious", "avoid"]
DataProviderKind: TypeAlias = Literal[
    "market", "fundamental", "news", "disclosure", "macro", "social"
]
DataSourceRole: TypeAlias = Literal["primary", "fallback", "inferred", "missing"]
FreshnessStatus: TypeAlias = Literal["fresh", "stale", "unknown", "missing"]
type ResearchEvidenceKind = Literal[
    "disclosure",
    "news",
    "macro",
    "social",
    "provider_status",
]
type ResearchSignalDirection = Literal[
    "supportive", "neutral", "cautious", "contradictory", "unknown"
]
DisclosureKind: TypeAlias = Literal[
    "sec_filing",
    "kap_disclosure",
    "earnings",
    "management",
    "material_event",
    "other",
]
ServiceState: TypeAlias = Literal[
    "idle",
    "starting",
    "running",
    "stopping",
    "stopped",
    "completed",
    "failed",
    "blocked",
]
ServiceEventLevel: TypeAlias = Literal["info", "warning", "error"]
JournalStatus: TypeAlias = Literal["open", "closed", "rejected", "no_fill"]
RegimeName: TypeAlias = Literal[
    "trend_up",
    "trend_down",
    "range",
    "breakout_candidate",
    "high_volatility",
    "no_trade",
]


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
    agent_tone: AgentTone = "supportive"
    strictness_preset: StrictnessPreset = "standard"
    intervention_style: InterventionStyle = "balanced"
    notes: str = ""


class RegimeAssessment(BaseModel):
    regime: RegimeName
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
    action: ExecutionSide
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
    side: ExecutionSide
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


class MarketSessionStatus(BaseModel):
    symbol: str
    venue: str
    asset_class: Literal["equity", "crypto"]
    timezone: str
    session_state: MarketSessionState
    tradable_now: bool
    note: str


class MarketContextHorizon(BaseModel):
    horizon_bars: int
    available_bars: int
    return_pct: float | None = None
    volatility_pct: float | None = None
    max_drawdown_pct: float | None = None
    trend_vote: TrendVote = "insufficient"
    support: float | None = None
    resistance: float | None = None
    range_position: float | None = Field(default=None, ge=0.0, le=1.0)
    atr_pct: float | None = None
    volume_ratio: float | None = None


class MarketContextPack(BaseModel):
    symbol: str
    interval: str
    lookback: str | None = None
    interval_semantics: str
    window_start: str | None = None
    window_end: str | None = None
    bars_required: int = 60
    bars_expected: int | None = None
    bars_analyzed: int
    coverage_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    higher_timeframe: str
    higher_timeframe_used: bool
    horizons: list[MarketContextHorizon] = Field(default_factory=list)
    data_quality_flags: list[str] = Field(default_factory=list)
    anomaly_flags: list[str] = Field(default_factory=list)
    summary: str = ""


class MarketSnapshot(BaseModel):
    symbol: str
    interval: str
    as_of: str | None = None
    last_close: float
    ema_20: float
    ema_50: float
    atr_14: float
    rsi_14: float
    volatility_20: float
    return_5: float
    return_20: float
    volume_ratio_20: float
    higher_timeframe: str = "same_as_base"
    htf_last_close: float = 0.0
    htf_ema_20: float = 0.0
    htf_ema_50: float = 0.0
    htf_rsi_14: float = 50.0
    htf_return_5: float = 0.0
    mtf_alignment: MTFAlignment = "mixed"
    mtf_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    bars_analyzed: int
    context_pack: MarketContextPack | None = None


class SymbolIdentity(BaseModel):
    symbol: str
    exchange: str | None = None
    currency: str = "USD"
    region: str = "US"
    asset_class: Literal["equity", "crypto", "fx", "unknown"] = "equity"


class TechnicalFeatureSet(BaseModel):
    symbol: str
    interval: str
    as_of: str | None = None
    price_anchor: float | None = None
    returns_by_window: dict[str, float | None] = Field(default_factory=dict)
    volatility_20: float | None = None
    max_drawdown_pct: float | None = None
    support: float | None = None
    resistance: float | None = None
    trend_classification: TrendVote = "insufficient"
    momentum_indicators: dict[str, float] = Field(default_factory=dict)
    context_summary: str = ""
    data_quality_flags: list[str] = Field(default_factory=list)


class FundamentalFeatureSet(BaseModel):
    symbol: str
    as_of: str | None = None
    revenue_growth: float | None = None
    profitability_stability: float | None = Field(default=None, ge=0.0, le=1.0)
    cash_flow_alignment: float | None = Field(default=None, ge=0.0, le=1.0)
    debt_risk: float | None = Field(default=None, ge=0.0, le=1.0)
    fx_exposure: str = "unknown"
    reinvestment_potential: float | None = Field(default=None, ge=0.0, le=1.0)
    data_sources: list[str] = Field(default_factory=list)
    quality_flags: list[str] = Field(default_factory=list)
    summary: str = ""


class StructuredNewsSignal(BaseModel):
    symbol: str | None = None
    title: str
    category: NewsClassification
    source: str
    published_at: str | None = None
    summary: str
    relevance_score: float = Field(ge=0.0, le=1.0)


class MacroContext(BaseModel):
    symbol: str
    as_of: str | None = None
    region: str = "US"
    currency: str = "USD"
    sector: str | None = None
    rates_bias: Literal["tailwind", "neutral", "headwind", "unknown"] = "unknown"
    inflation_bias: Literal["tailwind", "neutral", "headwind", "unknown"] = "unknown"
    fx_risk: Literal["low", "medium", "high", "unknown"] = "unknown"
    sector_risk_score: float | None = Field(default=None, ge=0.0, le=1.0)
    political_risk_score: float | None = Field(default=None, ge=0.0, le=1.0)
    news_signals: list[StructuredNewsSignal] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)
    summary: str = ""


class ProviderMetadata(BaseModel):
    provider_id: str
    name: str
    provider_type: DataProviderKind
    role: DataSourceRole
    priority: int = 100
    enabled: bool = True
    requires_network: bool = False
    notes: list[str] = Field(default_factory=list)


class DataSourceAttribution(BaseModel):
    source_name: str
    provider_type: DataProviderKind
    source_role: DataSourceRole
    fetched_at: str | None = None
    freshness: FreshnessStatus = "unknown"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    completeness: float = Field(default=0.0, ge=0.0, le=1.0)
    notes: list[str] = Field(default_factory=list)


class MarketDataSnapshot(BaseModel):
    symbol_identity: SymbolIdentity
    interval: str
    lookback: str | None = None
    rows: int = 0
    columns: list[str] = Field(default_factory=list)
    window_start: str | None = None
    window_end: str | None = None
    last_close: float | None = None
    attribution: DataSourceAttribution
    missing_fields: list[str] = Field(default_factory=list)
    summary: str = ""


class FundamentalSnapshot(BaseModel):
    symbol_identity: SymbolIdentity
    revenue_growth: float | None = None
    profitability_stability: float | None = Field(default=None, ge=0.0, le=1.0)
    cash_flow_alignment: float | None = Field(default=None, ge=0.0, le=1.0)
    debt_risk: float | None = Field(default=None, ge=0.0, le=1.0)
    fx_exposure: str = "unknown"
    reinvestment_potential: float | None = Field(default=None, ge=0.0, le=1.0)
    attribution: DataSourceAttribution
    missing_fields: list[str] = Field(default_factory=list)
    summary: str = ""


class EvidenceInferenceBreakdown(BaseModel):
    evidence: list[str] = Field(default_factory=list)
    inference: list[str] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)


class NewsEvent(BaseModel):
    symbol: str
    title: str
    category: NewsClassification
    source: str
    published_at: str | None = None
    summary: str = ""
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    url: str | None = None
    attribution: DataSourceAttribution
    observed_at: str | None = None
    last_verified_at: str | None = None
    stale_after: str | None = None
    evidence_vs_inference: EvidenceInferenceBreakdown = Field(
        default_factory=EvidenceInferenceBreakdown
    )
    missing_fields: list[str] = Field(default_factory=list)


class DisclosureEvent(BaseModel):
    symbol: str
    region: str
    disclosure_type: DisclosureKind = "other"
    title: str
    published_at: str | None = None
    summary: str = ""
    url: str | None = None
    attribution: DataSourceAttribution
    observed_at: str | None = None
    last_verified_at: str | None = None
    stale_after: str | None = None
    evidence_vs_inference: EvidenceInferenceBreakdown = Field(
        default_factory=EvidenceInferenceBreakdown
    )
    missing_fields: list[str] = Field(default_factory=list)


class MacroSnapshot(BaseModel):
    region: str
    currency: str
    rates_bias: Literal["tailwind", "neutral", "headwind", "unknown"] = "unknown"
    inflation_bias: Literal["tailwind", "neutral", "headwind", "unknown"] = "unknown"
    fx_risk: Literal["low", "medium", "high", "unknown"] = "unknown"
    sector_risk_score: float | None = Field(default=None, ge=0.0, le=1.0)
    political_risk_score: float | None = Field(default=None, ge=0.0, le=1.0)
    attribution: DataSourceAttribution
    missing_fields: list[str] = Field(default_factory=list)
    summary: str = ""


class CanonicalAnalysisSnapshot(BaseModel):
    symbol_identity: SymbolIdentity
    generated_at: str
    market: MarketDataSnapshot
    fundamental: FundamentalSnapshot
    news_events: list[NewsEvent] = Field(default_factory=list)
    disclosures: list[DisclosureEvent] = Field(default_factory=list)
    macro: MacroSnapshot
    source_attributions: list[DataSourceAttribution] = Field(default_factory=list)
    missing_sections: list[str] = Field(default_factory=list)
    completeness_score: float = Field(default=0.0, ge=0.0, le=1.0)
    summary: str = ""


class DecisionFeatureBundle(BaseModel):
    symbol_identity: SymbolIdentity
    technical: TechnicalFeatureSet
    fundamental: FundamentalFeatureSet
    macro: MacroContext


class ResearchTimedRecord(BaseModel):
    source_attributions: list[DataSourceAttribution] = Field(default_factory=list)
    observed_at: str
    last_verified_at: str | None = None
    stale_after: str | None = None
    evidence_vs_inference: EvidenceInferenceBreakdown = Field(
        default_factory=EvidenceInferenceBreakdown
    )
    missing_fields: list[str] = Field(default_factory=list)

    def is_stale(self, reference_time: str | None = None) -> bool:
        if self.stale_after is None:
            return False
        stale_after = datetime.fromisoformat(self.stale_after.replace("Z", "+00:00"))
        reference = (
            datetime.fromisoformat(reference_time.replace("Z", "+00:00"))
            if reference_time
            else datetime.now(UTC)
        )
        return stale_after <= reference


class RawEvidenceRecord(ResearchTimedRecord):
    record_id: str
    source_kind: ResearchEvidenceKind
    source_name: str
    title: str
    symbol: str | None = None
    entity_name: str | None = None
    region: str | None = None
    url: str | None = None
    normalized_summary: str = ""
    source_payload_ref: str | None = None


class MacroEvent(ResearchTimedRecord):
    event_id: str
    region: str
    currency: str | None = None
    title: str
    summary: str = ""
    direction: ResearchSignalDirection = "unknown"
    affected_channels: list[str] = Field(default_factory=list)


class SocialSignal(ResearchTimedRecord):
    signal_id: str
    platform: str
    query: str
    symbol: str | None = None
    entity_name: str | None = None
    summary: str = ""
    direction: ResearchSignalDirection = "unknown"
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    source_count: int = Field(default=0, ge=0)


class ResearchFinding(ResearchTimedRecord):
    finding_id: str
    subject: str
    title: str
    thesis: str = ""
    verified_facts: list[str] = Field(default_factory=list)
    inferences: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    market_channels: list[str] = Field(default_factory=list)
    horizon: str = "unknown"
    watch_next: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class EntityDossier(ResearchTimedRecord):
    entity_id: str
    entity_name: str
    symbol: str | None = None
    region: str | None = None
    timeline: list[str] = Field(default_factory=list)
    current_thesis: str = ""
    key_findings: list[ResearchFinding] = Field(default_factory=list)
    contradiction_file: list[str] = Field(default_factory=list)
    source_diversity_score: float = Field(default=0.0, ge=0.0, le=1.0)


class WorldStateSnapshot(ResearchTimedRecord):
    snapshot_id: str
    mode: ResearchMode = "off"
    generated_at: str
    watched_symbols: list[str] = Field(default_factory=list)
    entity_dossiers: list[EntityDossier] = Field(default_factory=list)
    macro_events: list[MacroEvent] = Field(default_factory=list)
    social_signals: list[SocialSignal] = Field(default_factory=list)
    findings: list[ResearchFinding] = Field(default_factory=list)
    summary: str = ""


class ResearchProviderHealth(BaseModel):
    provider_id: str
    name: str
    provider_type: DataProviderKind
    enabled: bool
    requires_network: bool = False
    source_role: DataSourceRole
    freshness: FreshnessStatus = "unknown"
    last_successful_update_at: str | None = None
    message: str = ""
    notes: list[str] = Field(default_factory=list)


class ResearchSidecarState(BaseModel):
    mode: ResearchMode = "off"
    enabled: bool = False
    backend: str = "noop"
    status: Literal["disabled", "idle", "running", "completed", "failed"] = "disabled"
    updated_at: str
    last_started_at: str | None = None
    last_successful_update_at: str | None = None
    last_error: str | None = None
    watched_symbols: list[str] = Field(default_factory=list)
    provider_health: list[ResearchProviderHealth] = Field(default_factory=list)
    source_health_summary: dict[str, int] = Field(default_factory=dict)


class ResearchSnapshotRecord(BaseModel):
    snapshot_id: str
    created_at: str
    mode: ResearchMode
    backend: str = "noop"
    status: Literal["disabled", "idle", "running", "completed", "failed"] = "disabled"
    watched_symbols: list[str] = Field(default_factory=list)
    raw_evidence: list[RawEvidenceRecord] = Field(default_factory=list)
    world_state: WorldStateSnapshot | None = None
    state: ResearchSidecarState
    memory_update: dict[str, object] = Field(default_factory=dict)


class FundamentalAssessment(BaseModel):
    growth_quality: AnalysisSignal = "neutral"
    profitability_quality: AnalysisSignal = "neutral"
    cash_flow_quality: AnalysisSignal = "neutral"
    balance_sheet_quality: AnalysisSignal = "neutral"
    fx_risk: Literal["low", "medium", "high", "unknown"] = "unknown"
    business_quality: AnalysisSignal = "neutral"
    macro_fit: AnalysisSignal = "neutral"
    forward_outlook: AnalysisSignal = "neutral"
    red_flags: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    evidence_vs_inference: EvidenceInferenceBreakdown = Field(
        default_factory=EvidenceInferenceBreakdown
    )
    overall_bias: AnalysisSignal = "neutral"
    revenue_growth_quality: AnalysisSignal = "neutral"
    debt_quality: AnalysisSignal = "neutral"
    fx_exposure_risk: Literal["low", "medium", "high", "unknown"] = "unknown"
    reinvestment_quality: AnalysisSignal = "neutral"
    overall_signal: AnalysisSignal = "neutral"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    summary: str = "Fundamental evidence is not available yet."
    risk_flags: list[str] = Field(default_factory=list)
    source: Literal["llm", "fallback"] = "fallback"
    fallback_reason: str | None = None

    @model_validator(mode="after")
    def sync_legacy_fields(self) -> "FundamentalAssessment":
        """
        Synchronize legacy and current field names so both representations remain consistent after model initialization.

        Copies values between legacy and new field pairs when only one of each pair was provided, ensuring fields such as `growth_quality`/`revenue_growth_quality`, `balance_sheet_quality`/`debt_quality`, `fx_risk`/`fx_exposure_risk`, `overall_bias`/`overall_signal`, and `red_flags`/`risk_flags` are aligned.

        Returns:
                self (FundamentalAssessment): The model instance with synchronized fields.
        """
        fields = set(self.model_fields_set)

        def _sync_pair(current: str, legacy: str) -> None:
            current_present = current in fields
            legacy_present = legacy in fields
            current_value = getattr(self, current)
            legacy_value = getattr(self, legacy)

            def _copy_mutable(value: object) -> object:
                return list(value) if isinstance(value, list) else value

            if current_present and legacy_present and current_value != legacy_value:
                raise ValueError(
                    f"Conflicting fundamental assessment fields: {current} != {legacy}."
                )
            if not current_present and legacy_present:
                setattr(self, current, _copy_mutable(legacy_value))
            elif not legacy_present and current_present:
                setattr(self, legacy, _copy_mutable(current_value))

        _sync_pair("growth_quality", "revenue_growth_quality")
        _sync_pair("balance_sheet_quality", "debt_quality")
        _sync_pair("fx_risk", "fx_exposure_risk")
        _sync_pair("overall_bias", "overall_signal")
        _sync_pair("red_flags", "risk_flags")
        return self


class MacroAssessment(BaseModel):
    macro_signal: AnalysisSignal = "neutral"
    sector_risk: Literal["low", "medium", "high", "unknown"] = "unknown"
    news_risk: Literal["low", "medium", "high", "unknown"] = "unknown"
    fx_risk: Literal["low", "medium", "high", "unknown"] = "unknown"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    summary: str = "Macro and news evidence is not available yet."
    risk_flags: list[str] = Field(default_factory=list)
    source: Literal["llm", "fallback"] = "fallback"
    fallback_reason: str | None = None


class AgentContext(BaseModel):
    role: AgentRole
    model_name: str
    snapshot: MarketSnapshot
    canonical_snapshot: CanonicalAnalysisSnapshot | None = None
    decision_features: DecisionFeatureBundle | None = None
    preferences: InvestmentPreferences
    portfolio: PortfolioSnapshot
    market_session: MarketSessionStatus | None = None
    service_state: "ServiceStateSnapshot | None" = None
    recent_runs: list[str] = Field(default_factory=list)
    memory_notes: list[str] = Field(default_factory=list)
    retrieved_memories: list[str] = Field(default_factory=list)
    retrieval_explanations: list["HistoricalMemoryMatch"] = Field(default_factory=list)
    calibration: "ConfidenceCalibration | None" = None
    shared_memory_bus: list["SharedMemoryEntry"] = Field(default_factory=list)
    tool_outputs: list[str] = Field(default_factory=list)
    upstream_context: dict[str, str] = Field(default_factory=dict)


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
    state: ServiceState
    runtime_mode: RuntimeMode = "operation"
    updated_at: str
    started_at: str | None = None
    last_heartbeat_at: str | None = None
    continuous: bool = False
    poll_seconds: int | None = None
    cycle_count: int = 0
    symbols: list[str] = Field(default_factory=list)
    interval: str | None = None
    lookback: str | None = None
    max_cycles: int | None = None
    current_symbol: str | None = None
    last_error: str | None = None
    pid: int | None = None
    stop_requested: bool = False
    background_mode: bool = False
    launch_count: int = 0
    restart_count: int = 0
    last_terminal_state: str | None = None
    last_terminal_at: str | None = None
    stdout_log_path: str | None = None
    stderr_log_path: str | None = None
    message: str = ""


class ServiceEvent(BaseModel):
    event_id: str
    created_at: str
    level: ServiceEventLevel
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
    side: TradeSide
    entry_price: float
    stop_loss: float
    take_profit: float
    max_holding_bars: int
    holding_bars: int
    invalidation_logic: str
    updated_at: str


class PositionExitDecision(BaseModel):
    should_exit: bool
    side: ExecutionSide
    symbol: str
    reason: PositionExitReason
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
    action_bias: ExecutionSide
    confidence_cap: float = Field(ge=0.0, le=1.0)
    size_multiplier: float = Field(gt=0.0, le=1.0)
    rationale: str
    escalation_flags: list[str] = Field(default_factory=list)
    override_applied: bool = False
    conflicts: list["ManagerConflict"] = Field(default_factory=list)
    resolution_notes: list[str] = Field(default_factory=list)
    source: Literal["llm", "fallback"] = "llm"
    fallback_reason: str | None = None


class ManagerConflict(BaseModel):
    conflict_type: Literal["focus", "action", "approval", "confidence", "size"]
    severity: Literal["low", "medium", "high"] = "medium"
    summary: str
    specialist_view: str
    manager_resolution: str


class SpecialistConsensus(BaseModel):
    alignment_level: Literal["aligned", "mixed", "conflicted"] = "mixed"
    summary: str = ""
    supporting_roles: list[str] = Field(default_factory=list)
    dissenting_roles: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


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
    agent_tone: AgentTone | None = None
    strictness_preset: StrictnessPreset | None = None
    intervention_style: InterventionStyle | None = None
    notes: str | None = None


class OperatorInstruction(BaseModel):
    summary: str
    should_update_preferences: bool = False
    preference_update: PreferenceUpdate = Field(default_factory=PreferenceUpdate)
    requires_confirmation: bool = True
    rationale: str


class RuntimeModeTransitionCheck(BaseModel):
    name: str
    passed: bool
    details: str
    blocking: bool = True


class RuntimeModeTransitionPlan(BaseModel):
    current_mode: RuntimeMode
    target_mode: RuntimeMode
    allowed: bool
    checks: list[RuntimeModeTransitionCheck] = Field(default_factory=list)
    summary: str


class AgentStageTrace(BaseModel):
    role: AgentRole
    model_name: str
    context_json: str
    output_json: str
    used_fallback: bool = False


class TradeJournalEntry(BaseModel):
    trade_id: str
    opened_at: str
    closed_at: str | None = None
    symbol: str
    run_id: str | None = None
    entry_order_id: str
    exit_order_id: str | None = None
    planned_side: ExecutionSide
    approved: bool
    journal_status: JournalStatus
    entry_price: float
    exit_price: float | None = None
    stop_loss: float
    take_profit: float
    position_size_pct: float
    confidence: float
    coordinator_focus: CoordinatorFocus
    strategy_family: str
    manager_bias: ExecutionSide
    review_summary: str
    exit_reason: str | None = None
    realized_pnl: float | None = None
    notes: str = ""


class TradeContextRecord(BaseModel):
    trade_id: str
    created_at: str
    run_id: str | None = None
    symbol: str
    market_snapshot: MarketSnapshot
    market_context_pack: MarketContextPack | None = None
    canonical_snapshot: CanonicalAnalysisSnapshot | None = None
    decision_features: DecisionFeatureBundle | None = None
    routed_models: dict[str, str] = Field(default_factory=dict)
    retrieved_memory_summary: dict[str, list[str]] = Field(default_factory=dict)
    retrieval_explanation_summary: dict[str, list[dict[str, object]]] = Field(
        default_factory=dict
    )
    tool_outputs: dict[str, list[str]] = Field(default_factory=dict)
    shared_memory_summary: dict[str, list[str]] = Field(default_factory=dict)
    consensus: SpecialistConsensus = Field(default_factory=SpecialistConsensus)
    fundamental_assessment: FundamentalAssessment = Field(
        default_factory=FundamentalAssessment
    )
    fundamental_summary: str = ""
    macro_summary: str = ""
    manager_rationale: str = ""
    manager_conflicts: list[ManagerConflict] = Field(default_factory=list)
    manager_resolution_notes: list[str] = Field(default_factory=list)
    execution_rationale: str = ""
    execution_backend: str | None = None
    execution_adapter: str | None = None
    execution_intent: dict[str, object] | None = None
    execution_outcome_status: str | None = None
    execution_rejection_reason: str | None = None
    execution_outcome: dict[str, object] | None = None
    simulated_fill_metadata: dict[str, object] = Field(default_factory=dict)
    review_summary: str = ""
    review_warnings: list[str] = Field(default_factory=list)


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


class ConfidenceCalibration(BaseModel):
    sample_size: int = 0
    closed_trades: int = 0
    win_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    average_pnl: float = 0.0
    confidence_multiplier: float = Field(default=1.0, gt=0.0, le=1.0)
    notes: list[str] = Field(default_factory=list)


class SharedMemoryEntry(BaseModel):
    role: str
    summary: str
    payload_json: str


class ChatHistoryEntry(BaseModel):
    entry_id: str
    created_at: str
    persona: ChatPersona
    user_message: str
    response_text: str


class NewsSignal(BaseModel):
    symbol: str
    title: str
    publisher: str
    published_at: str | None = None
    link: str | None = None


class BacktestTrade(BaseModel):
    symbol: str
    entry_at: str
    exit_at: str | None = None
    side: TradeSide
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
    data_start_at: str | None = None
    data_end_at: str | None = None
    first_decision_at: str | None = None
    last_decision_at: str | None = None
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


class BacktestSummary(BaseModel):
    label: str
    total_trades: int
    closed_trades: int
    win_rate: float
    expectancy: float
    total_return_pct: float
    max_drawdown_pct: float
    exposure_pct: float
    starting_equity: float
    ending_equity: float


class BacktestComparisonReport(BaseModel):
    symbol: str
    interval: str
    lookback: str
    warmup_bars: int
    agent: BacktestSummary
    baseline: BacktestSummary
    ending_equity_delta: float
    total_return_delta_pct: float


class BacktestAblationReport(BaseModel):
    symbol: str
    interval: str
    lookback: str
    warmup_bars: int
    with_memory: BacktestSummary
    without_memory: BacktestSummary
    ending_equity_delta: float
    total_return_delta_pct: float


class RunArtifacts(BaseModel):
    snapshot: MarketSnapshot
    canonical_snapshot: CanonicalAnalysisSnapshot | None = None
    decision_features: DecisionFeatureBundle | None = None
    coordinator: ResearchCoordinatorBrief
    fundamental: FundamentalAssessment = Field(default_factory=FundamentalAssessment)
    macro: MacroAssessment = Field(default_factory=MacroAssessment)
    regime: RegimeAssessment
    strategy: StrategyPlan
    risk: RiskPlan
    consensus: SpecialistConsensus = Field(default_factory=SpecialistConsensus)
    manager: ManagerDecision
    execution: ExecutionDecision
    review: ReviewNote
    agent_traces: list[AgentStageTrace] = Field(default_factory=list)

    def fallback_components(self) -> list[str]:
        components: list[str] = []
        if self.coordinator.source == "fallback":
            components.append("coordinator")
        if self.fundamental.source == "fallback":
            components.append("fundamental")
        if self.macro.source == "fallback":
            components.append("macro")
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


class HistoricalMemoryMatch(BaseModel):
    run_id: str
    created_at: str
    symbol: str
    similarity_score: float = Field(ge=0.0)
    heuristic_score: float | None = None
    vector_score: float | None = None
    retrieval_source: Literal["heuristic", "vector", "hybrid"] = "heuristic"
    regime: str
    strategy_family: str
    manager_bias: str
    approved: bool
    summary: str
    explanation: "MemoryRetrievalExplanation" = Field(
        default_factory=lambda: MemoryRetrievalExplanation()
    )


class MemoryRetrievalExplanation(BaseModel):
    eligibility_reason: str = "candidate_run_record"
    score_components: dict[str, float] = Field(default_factory=dict)
    as_of: str | None = None
    freshness: FreshnessStatus = "unknown"
    outcome_tag: str = "unknown"
    regime_alignment: str = "unknown"
    strategy_alignment: str = "unknown"
    diversity_bucket: str = "unknown"
    notes: list[str] = Field(default_factory=list)


class RunReplayStage(BaseModel):
    role: str
    model_name: str
    used_fallback: bool = False
    market_session: dict[str, object] | None = None
    retrieved_memories: list[str] = Field(default_factory=list)
    memory_notes: list[str] = Field(default_factory=list)
    shared_memory_bus: list[SharedMemoryEntry] = Field(default_factory=list)
    recent_runs: list[str] = Field(default_factory=list)
    tool_outputs: list[str] = Field(default_factory=list)
    upstream_context: dict[str, str] = Field(default_factory=dict)
    output: dict[str, object] | str


class RunReplay(BaseModel):
    run_id: str
    created_at: str
    symbol: str
    interval: str
    approved: bool
    final_side: str
    final_rationale: str
    snapshot: MarketSnapshot
    consensus: SpecialistConsensus = Field(default_factory=SpecialistConsensus)
    manager_override_notes: list[str] = Field(default_factory=list)
    manager_conflicts: list[ManagerConflict] = Field(default_factory=list)
    manager_resolution_notes: list[str] = Field(default_factory=list)
    stages: list[RunReplayStage] = Field(default_factory=list)
