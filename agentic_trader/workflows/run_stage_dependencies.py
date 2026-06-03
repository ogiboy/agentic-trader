"""Dependency bundles for one-shot workflow stage runners."""

from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel

from agentic_trader.schemas import (
    AgentContext,
    ExecutionDecision,
    FundamentalAssessment,
    MacroAssessment,
    ManagerDecision,
    RegimeAssessment,
    ResearchCoordinatorBrief,
    ReviewNote,
    RiskPlan,
    SpecialistConsensus,
    StrategyPlan,
)
from agentic_trader.workflows.run_context import ResearchStageOutputs


@dataclass(frozen=True)
class ResearchStageDeps:
    coordinate_research: Callable[..., ResearchCoordinatorBrief]
    assess_fundamentals: Callable[..., FundamentalAssessment]
    assess_macro_context: Callable[..., MacroAssessment]
    assess_regime: Callable[..., RegimeAssessment]


@dataclass(frozen=True)
class PlanningStageDeps:
    plan_trade: Callable[..., StrategyPlan]
    build_risk_plan: Callable[..., RiskPlan]
    assess_specialist_consensus: Callable[..., SpecialistConsensus]
    manage_trade_decision: Callable[..., ManagerDecision]
    evaluate_execution: Callable[..., ExecutionDecision]
    build_review_note: Callable[
        [RegimeAssessment, StrategyPlan, RiskPlan, ManagerDecision, ExecutionDecision],
        ReviewNote,
    ]
    consensus_tool_output: Callable[[SpecialistConsensus], str]
    research_upstream_context: Callable[
        [ResearchStageOutputs], dict[str, BaseModel | str]
    ]


type StageResult[T] = tuple[T, AgentContext]
