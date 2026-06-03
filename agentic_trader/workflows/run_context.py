"""Shared context objects for one-shot workflow orchestration."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel

from agentic_trader.agents.context import build_agent_context
from agentic_trader.config import Settings
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import (
    AgentContext,
    AgentRole,
    CanonicalAnalysisSnapshot,
    DecisionFeatureBundle,
    ExecutionDecision,
    FundamentalAssessment,
    InvestmentPreferences,
    MacroAssessment,
    ManagerDecision,
    MarketSnapshot,
    NewsSignal,
    RegimeAssessment,
    ResearchCoordinatorBrief,
    ReviewNote,
    RiskPlan,
    SharedMemoryEntry,
    SpecialistConsensus,
    StrategyPlan,
)
from agentic_trader.storage.db import TradingDatabase

type ProgressCallback = Callable[[str, str, str], None]


class JsonModel(Protocol):
    def model_dump_json(self, *, indent: int | None = None) -> str: ...


@dataclass
class RunPipelineContext:
    settings: Settings
    snapshot: MarketSnapshot
    allow_fallback: bool
    memory_enabled: bool
    progress_callback: ProgressCallback | None
    llm: LocalLLM
    db: TradingDatabase
    preferences: InvestmentPreferences
    news_items: list[NewsSignal]
    canonical_snapshot: CanonicalAnalysisSnapshot
    decision_features: DecisionFeatureBundle
    shared_memory_bus: list[SharedMemoryEntry]

    def emit(self, stage: str, status: str, message: str) -> None:
        if self.progress_callback is not None:
            self.progress_callback(stage, status, message)

    def agent_context(
        self,
        *,
        role: AgentRole,
        upstream_context: Mapping[str, BaseModel | str] | None = None,
        tool_outputs: list[str] | None = None,
    ) -> AgentContext:
        return build_agent_context(
            role=role,
            settings=self.settings,
            db=self.db,
            snapshot=self.snapshot,
            canonical_snapshot=self.canonical_snapshot,
            decision_features=self.decision_features,
            news_items=self.news_items,
            memory_enabled=self.memory_enabled,
            shared_memory_bus=self.shared_memory_bus,
            upstream_context=upstream_context,
            tool_outputs=tool_outputs,
        )

    def remember(self, *, role: str, summary: str, payload: JsonModel) -> None:
        self.shared_memory_bus.append(
            SharedMemoryEntry(
                role=role,
                summary=summary,
                payload_json=payload.model_dump_json(indent=2),
            )
        )


@dataclass(frozen=True)
class ResearchStageOutputs:
    coordinator: ResearchCoordinatorBrief
    coordinator_context: AgentContext
    fundamental: FundamentalAssessment
    fundamental_context: AgentContext
    macro: MacroAssessment
    macro_context: AgentContext
    regime: RegimeAssessment
    regime_context: AgentContext


@dataclass(frozen=True)
class PlanningStageOutputs:
    strategy: StrategyPlan
    strategy_context: AgentContext
    risk: RiskPlan
    risk_context: AgentContext
    consensus: SpecialistConsensus
    manager: ManagerDecision
    manager_context: AgentContext
    execution: ExecutionDecision
    review: ReviewNote
