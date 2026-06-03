"""Planning-stage orchestration for one-shot runs."""

from pydantic import BaseModel

from agentic_trader.schemas import (
    ExecutionDecision,
    ManagerDecision,
    RegimeAssessment,
    ReviewNote,
    RiskPlan,
    SpecialistConsensus,
    StrategyPlan,
)
from agentic_trader.workflows.run_context import (
    PlanningStageOutputs,
    ResearchStageOutputs,
    RunPipelineContext,
)
from agentic_trader.workflows.run_stage_dependencies import (
    PlanningStageDeps,
    StageResult,
)


def run_planning_stages(
    pipeline: RunPipelineContext,
    research: ResearchStageOutputs,
    deps: PlanningStageDeps,
) -> PlanningStageOutputs:
    strategy, strategy_context = _run_strategy_stage(pipeline, research, deps)
    risk, risk_context = _run_risk_stage(pipeline, research, strategy, deps)
    consensus = _assess_and_record_consensus(pipeline, research, strategy, risk, deps)
    manager, manager_context = _run_manager_stage(
        pipeline, research, strategy, risk, consensus, deps
    )
    execution = _run_execution_stage(pipeline, strategy, risk, manager, deps)
    review = _run_review_stage(
        pipeline, research.regime, strategy, risk, manager, execution, deps
    )
    return PlanningStageOutputs(
        strategy=strategy,
        strategy_context=strategy_context,
        risk=risk,
        risk_context=risk_context,
        consensus=consensus,
        manager=manager,
        manager_context=manager_context,
        execution=execution,
        review=review,
    )


def _run_strategy_stage(
    pipeline: RunPipelineContext,
    research: ResearchStageOutputs,
    deps: PlanningStageDeps,
) -> StageResult[StrategyPlan]:
    snapshot = pipeline.snapshot
    pipeline.emit(
        "strategy",
        "started",
        f"Strategy selector is planning the trade for {snapshot.symbol}.",
    )
    context = pipeline.agent_context(
        role="strategy",
        upstream_context=_research_upstream_context(research, deps),
    )
    strategy = deps.plan_trade(
        pipeline.llm,
        snapshot,
        research.regime,
        allow_fallback=pipeline.allow_fallback,
        context=context,
    )
    pipeline.emit(
        "strategy",
        "completed",
        f"Strategy selector chose {strategy.strategy_family} with action {strategy.action}.",
    )
    pipeline.remember(
        role="strategy",
        summary=(
            f"Strategy {strategy.strategy_family} chose {strategy.action} "
            f"at {strategy.confidence:.2f} confidence"
        ),
        payload=strategy,
    )
    return strategy, context


def _run_risk_stage(
    pipeline: RunPipelineContext,
    research: ResearchStageOutputs,
    strategy: StrategyPlan,
    deps: PlanningStageDeps,
) -> StageResult[RiskPlan]:
    snapshot = pipeline.snapshot
    pipeline.emit(
        "risk", "started", f"Risk steward is sizing the trade for {snapshot.symbol}."
    )
    context = pipeline.agent_context(
        role="risk",
        upstream_context={
            **_research_upstream_context(research, deps),
            "strategy": strategy,
        },
    )
    risk = deps.build_risk_plan(
        pipeline.llm,
        snapshot,
        research.regime,
        strategy,
        allow_fallback=pipeline.allow_fallback,
        context=context,
    )
    pipeline.emit(
        "risk",
        "completed",
        f"Risk steward set size {risk.position_size_pct:.2%} and RR {risk.risk_reward_ratio:.2f}.",
    )
    pipeline.remember(
        role="risk",
        summary=(
            f"Risk size {risk.position_size_pct:.2%}, "
            f"RR {risk.risk_reward_ratio:.2f}, max hold {risk.max_holding_bars}"
        ),
        payload=risk,
    )
    return risk, context


def _assess_and_record_consensus(
    pipeline: RunPipelineContext,
    research: ResearchStageOutputs,
    strategy: StrategyPlan,
    risk: RiskPlan,
    deps: PlanningStageDeps,
) -> SpecialistConsensus:
    consensus = deps.assess_specialist_consensus(
        research.coordinator,
        research.regime,
        strategy,
        risk,
        fundamental=research.fundamental,
        macro=research.macro,
    )
    pipeline.emit(
        "consensus",
        "completed",
        f"Specialist consensus assessed as {consensus.alignment_level}.",
    )
    pipeline.remember(role="consensus", summary=consensus.summary, payload=consensus)
    return consensus


def _run_manager_stage(
    pipeline: RunPipelineContext,
    research: ResearchStageOutputs,
    strategy: StrategyPlan,
    risk: RiskPlan,
    consensus: SpecialistConsensus,
    deps: PlanningStageDeps,
) -> StageResult[ManagerDecision]:
    snapshot = pipeline.snapshot
    pipeline.emit(
        "manager",
        "started",
        f"Manager agent is combining specialist outputs for {snapshot.symbol}.",
    )
    context = pipeline.agent_context(
        role="manager",
        tool_outputs=[deps.consensus_tool_output(consensus)],
        upstream_context={
            **_research_upstream_context(research, deps),
            "strategy": strategy,
            "risk": risk,
        },
    )
    manager = deps.manage_trade_decision(
        pipeline.llm,
        snapshot,
        research.coordinator,
        research.regime,
        strategy,
        risk,
        fundamental=research.fundamental,
        macro=research.macro,
        allow_fallback=pipeline.allow_fallback,
        context=context,
    )
    pipeline.emit(
        "manager",
        "completed",
        f"Manager agent returned bias {manager.action_bias} with approval {manager.approved}.",
    )
    pipeline.remember(
        role="manager",
        summary=(
            f"Manager bias {manager.action_bias}, approved={manager.approved}, "
            f"override={manager.override_applied}"
        ),
        payload=manager,
    )
    return manager, context


def _run_execution_stage(
    pipeline: RunPipelineContext,
    strategy: StrategyPlan,
    risk: RiskPlan,
    manager: ManagerDecision,
    deps: PlanningStageDeps,
) -> ExecutionDecision:
    snapshot = pipeline.snapshot
    pipeline.emit(
        "execution",
        "started",
        f"Execution guard is validating the plan for {snapshot.symbol}.",
    )
    execution = deps.evaluate_execution(
        pipeline.settings, snapshot, strategy, risk, manager
    )
    pipeline.emit(
        "execution",
        "completed",
        f"Execution guard {'approved' if execution.approved else 'rejected'} {execution.side}.",
    )
    return execution


def _run_review_stage(
    pipeline: RunPipelineContext,
    regime: RegimeAssessment,
    strategy: StrategyPlan,
    risk: RiskPlan,
    manager: ManagerDecision,
    execution: ExecutionDecision,
    deps: PlanningStageDeps,
) -> ReviewNote:
    pipeline.emit(
        "review",
        "started",
        f"Review agent is writing the post-trade note for {pipeline.snapshot.symbol}.",
    )
    review = deps.build_review_note(regime, strategy, risk, manager, execution)
    pipeline.emit("review", "completed", "Review note completed.")
    return review


def _research_upstream_context(
    research: ResearchStageOutputs,
    deps: PlanningStageDeps,
) -> dict[str, BaseModel | str]:
    return deps.research_upstream_context(research)
