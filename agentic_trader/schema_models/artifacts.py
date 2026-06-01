from __future__ import annotations

from pydantic import BaseModel, Field

from agentic_trader.schema_models.agent_workflow import (
    ManagerConflict,
    ManagerDecision,
    ResearchCoordinatorBrief,
    ReviewNote,
    SpecialistConsensus,
)
from agentic_trader.schema_models.assessments import (
    FundamentalAssessment,
    MacroAssessment,
)
from agentic_trader.schema_models.journal import AgentStageTrace
from agentic_trader.schema_models.market import MarketSnapshot
from agentic_trader.schema_models.memory import SharedMemoryEntry
from agentic_trader.schema_models.providers import (
    CanonicalAnalysisSnapshot,
    DecisionFeatureBundle,
)
from agentic_trader.schema_models.trading import (
    ExecutionDecision,
    RegimeAssessment,
    RiskPlan,
    StrategyPlan,
)


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
    agent_traces: list[AgentStageTrace] = Field(default_factory=list[AgentStageTrace])

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


class RunReplayStage(BaseModel):
    role: str
    model_name: str
    used_fallback: bool = False
    market_session: dict[str, object] | None = None
    retrieved_memories: list[str] = Field(default_factory=list[str])
    memory_notes: list[str] = Field(default_factory=list[str])
    shared_memory_bus: list[SharedMemoryEntry] = Field(
        default_factory=list[SharedMemoryEntry]
    )
    recent_runs: list[str] = Field(default_factory=list[str])
    tool_outputs: list[str] = Field(default_factory=list[str])
    upstream_context: dict[str, str] = Field(default_factory=dict[str, str])
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
    manager_override_notes: list[str] = Field(default_factory=list[str])
    manager_conflicts: list[ManagerConflict] = Field(
        default_factory=list[ManagerConflict]
    )
    manager_resolution_notes: list[str] = Field(default_factory=list[str])
    stages: list[RunReplayStage] = Field(default_factory=list[RunReplayStage])
