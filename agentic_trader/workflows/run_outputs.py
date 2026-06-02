"""Output assembly helpers for one-shot workflow runs."""

from __future__ import annotations

from pydantic import BaseModel

from agentic_trader.schemas import (
    AgentContext,
    AgentRole,
    AgentStageTrace,
    CanonicalAnalysisSnapshot,
    DecisionFeatureBundle,
    MarketSnapshot,
    RunArtifacts,
    SpecialistConsensus,
)
from agentic_trader.workflows.run_context import (
    JsonModel,
    PlanningStageOutputs,
    ResearchStageOutputs,
)


def build_run_artifacts(
    *,
    snapshot: MarketSnapshot,
    canonical_snapshot: CanonicalAnalysisSnapshot,
    decision_features: DecisionFeatureBundle,
    research: ResearchStageOutputs,
    planning: PlanningStageOutputs,
) -> RunArtifacts:
    return RunArtifacts(
        snapshot=snapshot,
        canonical_snapshot=canonical_snapshot,
        decision_features=decision_features,
        coordinator=research.coordinator,
        fundamental=research.fundamental,
        macro=research.macro,
        regime=research.regime,
        strategy=planning.strategy,
        risk=planning.risk,
        consensus=planning.consensus,
        manager=planning.manager,
        execution=planning.execution,
        review=planning.review,
        agent_traces=build_stage_traces(research, planning),
    )


def research_upstream_context(
    research: ResearchStageOutputs,
) -> dict[str, BaseModel | str]:
    return {
        "coordinator": research.coordinator,
        "fundamental": research.fundamental,
        "macro": research.macro,
        "regime": research.regime,
    }


def consensus_tool_output(consensus: SpecialistConsensus) -> str:
    support = ",".join(consensus.supporting_roles) or "-"
    dissent = ",".join(consensus.dissenting_roles) or "-"
    return (
        f"specialist_consensus: level={consensus.alignment_level} "
        f"support={support} dissent={dissent} summary={consensus.summary}"
    )


def build_stage_traces(
    research: ResearchStageOutputs, planning: PlanningStageOutputs
) -> list[AgentStageTrace]:
    return [
        _stage_trace(
            role="coordinator",
            context=research.coordinator_context,
            output=research.coordinator,
        ),
        _stage_trace(
            role="fundamental",
            context=research.fundamental_context,
            output=research.fundamental,
        ),
        _stage_trace(
            role="macro", context=research.macro_context, output=research.macro
        ),
        _stage_trace(
            role="regime", context=research.regime_context, output=research.regime
        ),
        _stage_trace(
            role="strategy",
            context=planning.strategy_context,
            output=planning.strategy,
        ),
        _stage_trace(role="risk", context=planning.risk_context, output=planning.risk),
        _stage_trace(
            role="manager",
            context=planning.manager_context,
            output=planning.manager,
        ),
    ]


def _stage_trace(
    *, role: AgentRole, context: AgentContext, output: JsonModel
) -> AgentStageTrace:
    return AgentStageTrace(
        role=role,
        model_name=context.model_name,
        context_json=context.model_dump_json(indent=2),
        output_json=output.model_dump_json(indent=2),
        used_fallback=getattr(output, "source", None) == "fallback",
    )
