from typing import Literal

RiskProfile = Literal["conservative", "balanced", "aggressive"]
TradeStyle = Literal["swing", "position", "intraday"]
BehaviorPreset = Literal[
    "balanced_core", "trend_biased", "contrarian", "capital_preservation"
]
AgentProfile = Literal["neutral", "disciplined", "aggressive", "explanatory"]
AgentTone = Literal["neutral", "supportive", "direct", "forensic"]
StrictnessPreset = Literal["standard", "strict", "paranoid"]
InterventionStyle = Literal["hands_off", "balanced", "protective"]
ChatPersona = Literal[
    "operator_liaison",
    "regime_analyst",
    "strategy_selector",
    "risk_steward",
    "portfolio_manager",
]
CoordinatorFocus = Literal[
    "trend_following", "breakout", "mean_reversion", "capital_preservation", "no_trade"
]
AgentRole = Literal[
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
ExecutionSide = Literal["buy", "sell", "hold"]
TradeSide = Literal["buy", "sell"]
PositionExitReason = Literal[
    "stop_loss", "take_profit", "invalidation", "time_exit", "no_exit"
]
MarketSessionState = Literal["open", "closed", "always_open", "weekend"]
MTFAlignment = Literal["bullish", "bearish", "mixed"]
TrendVote = Literal["bullish", "bearish", "mixed", "insufficient"]
RuntimeMode = Literal["training", "operation"]
ResearchMode = Literal["off", "training", "live_prep"]
ExecutionBackend = Literal["paper", "simulated_real", "alpaca_paper", "live"]
TradeProposalStatus = Literal[
    "pending", "approved", "rejected", "executed", "failed", "expired"
]
ProposalCandidateStatus = Literal["candidate", "promoted", "rejected", "expired"]
NewsClassification = Literal["company_specific", "sector_level", "macro_level"]
AnalysisSignal = Literal["supportive", "neutral", "cautious", "avoid"]
DataProviderKind = Literal[
    "market", "fundamental", "news", "disclosure", "macro", "social"
]
DataSourceRole = Literal["primary", "fallback", "inferred", "missing"]
FreshnessStatus = Literal["fresh", "stale", "unknown", "missing"]
ResearchEvidenceKind = Literal[
    "disclosure",
    "news",
    "macro",
    "social",
    "provider_status",
]
ResearchSignalDirection = Literal[
    "supportive", "neutral", "cautious", "contradictory", "unknown"
]
ResearchCycleControlAction = Literal["idle", "pause", "resume", "trigger_now"]
ResearchCycleControlStatus = Literal["running", "paused"]
DisclosureKind = Literal[
    "sec_filing",
    "kap_disclosure",
    "earnings",
    "management",
    "material_event",
    "other",
]
ServiceState = Literal[
    "idle",
    "starting",
    "running",
    "stopping",
    "stopped",
    "completed",
    "failed",
    "blocked",
]
ServiceEventLevel = Literal["info", "warning", "error"]
JournalStatus = Literal["open", "closed", "rejected", "no_fill"]
RegimeName = Literal[
    "trend_up",
    "trend_down",
    "range",
    "breakout_candidate",
    "high_volatility",
    "no_trade",
]
