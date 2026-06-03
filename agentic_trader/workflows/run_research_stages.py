"""Research-stage orchestration for one-shot runs."""

from agentic_trader.schemas import (
    FundamentalAssessment,
    MacroAssessment,
    RegimeAssessment,
    ResearchCoordinatorBrief,
)
from agentic_trader.workflows.run_context import (
    ResearchStageOutputs,
    RunPipelineContext,
)
from agentic_trader.workflows.run_stage_dependencies import (
    ResearchStageDeps,
    StageResult,
)


def run_research_stages(
    pipeline: RunPipelineContext,
    deps: ResearchStageDeps,
) -> ResearchStageOutputs:
    coordinator, coordinator_context = _run_coordinator_stage(pipeline, deps)
    fundamental, fundamental_context = _run_fundamental_stage(
        pipeline, deps, coordinator=coordinator
    )
    macro, macro_context = _run_macro_stage(
        pipeline,
        deps,
        coordinator=coordinator,
        fundamental=fundamental,
    )
    regime, regime_context = _run_regime_stage(
        pipeline,
        deps,
        coordinator=coordinator,
        fundamental=fundamental,
        macro=macro,
    )
    return ResearchStageOutputs(
        coordinator=coordinator,
        coordinator_context=coordinator_context,
        fundamental=fundamental,
        fundamental_context=fundamental_context,
        macro=macro,
        macro_context=macro_context,
        regime=regime,
        regime_context=regime_context,
    )


def _run_coordinator_stage(
    pipeline: RunPipelineContext,
    deps: ResearchStageDeps,
) -> StageResult[ResearchCoordinatorBrief]:
    snapshot = pipeline.snapshot
    pipeline.emit(
        "coordinator",
        "started",
        f"Coordinator is setting research focus for {snapshot.symbol}.",
    )
    context = pipeline.agent_context(role="coordinator")
    coordinator = deps.coordinate_research(
        pipeline.llm,
        snapshot,
        allow_fallback=pipeline.allow_fallback,
        context=context,
    )
    pipeline.emit(
        "coordinator",
        "completed",
        f"Coordinator completed with focus {coordinator.market_focus}.",
    )
    pipeline.remember(
        role="coordinator",
        summary=f"Focus {coordinator.market_focus} with summary: {coordinator.summary}",
        payload=coordinator,
    )
    return coordinator, context


def _run_fundamental_stage(
    pipeline: RunPipelineContext,
    deps: ResearchStageDeps,
    *,
    coordinator: ResearchCoordinatorBrief,
) -> StageResult[FundamentalAssessment]:
    snapshot = pipeline.snapshot
    pipeline.emit(
        "fundamental",
        "started",
        f"Fundamental analyst is reviewing structured evidence for {snapshot.symbol}.",
    )
    context = pipeline.agent_context(
        role="fundamental",
        upstream_context={"coordinator": coordinator},
    )
    fundamental = deps.assess_fundamentals(
        pipeline.llm,
        snapshot,
        allow_fallback=pipeline.allow_fallback,
        context=context,
    )
    pipeline.emit(
        "fundamental",
        "completed",
        f"Fundamental analyst returned {fundamental.overall_bias}.",
    )
    pipeline.remember(
        role="fundamental",
        summary=f"Fundamental bias {fundamental.overall_bias}: {fundamental.summary}",
        payload=fundamental,
    )
    return fundamental, context


def _run_macro_stage(
    pipeline: RunPipelineContext,
    deps: ResearchStageDeps,
    *,
    coordinator: ResearchCoordinatorBrief,
    fundamental: FundamentalAssessment,
) -> StageResult[MacroAssessment]:
    snapshot = pipeline.snapshot
    pipeline.emit(
        "macro",
        "started",
        f"Macro/news analyst is reviewing context for {snapshot.symbol}.",
    )
    context = pipeline.agent_context(
        role="macro",
        upstream_context={
            "coordinator": coordinator,
            "fundamental": fundamental,
        },
    )
    macro = deps.assess_macro_context(
        pipeline.llm,
        snapshot,
        allow_fallback=pipeline.allow_fallback,
        context=context,
    )
    pipeline.emit(
        "macro", "completed", f"Macro/news analyst returned {macro.macro_signal}."
    )
    pipeline.remember(
        role="macro",
        summary=f"Macro signal {macro.macro_signal}: {macro.summary}",
        payload=macro,
    )
    return macro, context


def _run_regime_stage(
    pipeline: RunPipelineContext,
    deps: ResearchStageDeps,
    *,
    coordinator: ResearchCoordinatorBrief,
    fundamental: FundamentalAssessment,
    macro: MacroAssessment,
) -> StageResult[RegimeAssessment]:
    snapshot = pipeline.snapshot
    pipeline.emit(
        "regime",
        "started",
        f"Regime analyst is classifying the market for {snapshot.symbol}.",
    )
    context = pipeline.agent_context(
        role="regime",
        upstream_context={
            "coordinator": coordinator,
            "fundamental": fundamental,
            "macro": macro,
        },
    )
    regime = deps.assess_regime(
        pipeline.llm,
        snapshot,
        allow_fallback=pipeline.allow_fallback,
        context=context,
    )
    pipeline.emit(
        "regime",
        "completed",
        f"Regime analyst classified the market as {regime.regime}.",
    )
    pipeline.remember(
        role="regime",
        summary=f"Regime {regime.regime} with bias {regime.direction_bias}",
        payload=regime,
    )
    return regime, context
