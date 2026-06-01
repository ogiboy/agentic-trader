from __future__ import annotations

from pydantic import BaseModel, Field

from agentic_trader.schema_models.agent_workflow import (
    ManagerConflict,
    SpecialistConsensus,
)
from agentic_trader.schema_models.assessments import FundamentalAssessment
from agentic_trader.schema_models.market import MarketContextPack, MarketSnapshot
from agentic_trader.schema_models.providers import (
    CanonicalAnalysisSnapshot,
    DecisionFeatureBundle,
)
from agentic_trader.schema_models.types import (
    AgentRole,
    ChatPersona,
    CoordinatorFocus,
    ExecutionSide,
    JournalStatus,
)


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
    routed_models: dict[str, str] = Field(default_factory=dict[str, str])
    retrieved_memory_summary: dict[str, list[str]] = Field(
        default_factory=dict[str, list[str]]
    )
    retrieval_explanation_summary: dict[str, list[dict[str, object]]] = Field(
        default_factory=dict
    )
    tool_outputs: dict[str, list[str]] = Field(default_factory=dict[str, list[str]])
    shared_memory_summary: dict[str, list[str]] = Field(
        default_factory=dict[str, list[str]]
    )
    consensus: SpecialistConsensus = Field(default_factory=SpecialistConsensus)
    fundamental_assessment: FundamentalAssessment = Field(
        default_factory=FundamentalAssessment
    )
    fundamental_summary: str = ""
    macro_summary: str = ""
    manager_rationale: str = ""
    manager_conflicts: list[ManagerConflict] = Field(
        default_factory=list[ManagerConflict]
    )
    manager_resolution_notes: list[str] = Field(default_factory=list[str])
    execution_rationale: str = ""
    execution_backend: str | None = None
    execution_adapter: str | None = None
    execution_intent: dict[str, object] | None = None
    execution_outcome_status: str | None = None
    execution_rejection_reason: str | None = None
    execution_outcome: dict[str, object] | None = None
    simulated_fill_metadata: dict[str, object] = Field(
        default_factory=dict[str, object]
    )
    review_summary: str = ""
    review_warnings: list[str] = Field(default_factory=list[str])


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
    portfolio_hhi: float = 0.0
    top_position_symbols: list[str] = Field(default_factory=list[str])
    drawdown_from_peak_pct: float
    warnings: list[str] = Field(default_factory=list[str])


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
