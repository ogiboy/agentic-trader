"""One-shot workflow entry points and compatibility facade."""

from agentic_trader.agents.consensus import assess_specialist_consensus
from agentic_trader.agents.coordinator import coordinate_research
from agentic_trader.agents.fundamental import assess_fundamentals
from agentic_trader.agents.macro import assess_macro_context
from agentic_trader.agents.manager import manage_trade_decision
from agentic_trader.agents.planner import plan_trade
from agentic_trader.agents.regime import assess_regime
from agentic_trader.agents.review import build_review_note
from agentic_trader.agents.risk import build_risk_plan
from agentic_trader.config import Settings
from agentic_trader.engine.guard import evaluate_execution
from agentic_trader.features import build_decision_feature_bundle
from agentic_trader.llm.client import LocalLLM
from agentic_trader.market.data import fetch_ohlcv
from agentic_trader.market.features import build_snapshot
from agentic_trader.market.news import fetch_news_brief
from agentic_trader.providers import build_canonical_analysis_snapshot
from agentic_trader.schemas import MarketSnapshot, RunArtifacts
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.workflows import run_outputs as _run_outputs
from agentic_trader.workflows import run_persistence as _run_persistence
from agentic_trader.workflows.run_context import (
    PlanningStageOutputs,
    ProgressCallback,
    ResearchStageOutputs,
    RunPipelineContext,
)
from agentic_trader.workflows.run_planning_stages import (
    run_planning_stages as _run_planning_stages_impl,
)
from agentic_trader.workflows.run_research_stages import (
    run_research_stages as _run_research_stages_impl,
)
from agentic_trader.workflows.run_stage_dependencies import (
    PlanningStageDeps,
    ResearchStageDeps,
)


def persist_position_plan(*, settings: Settings, artifacts: RunArtifacts) -> None:
    _run_persistence.persist_position_plan(settings=settings, artifacts=artifacts)


def persist_run(*, settings: Settings, artifacts: RunArtifacts) -> str:
    return _run_persistence.persist_run(settings=settings, artifacts=artifacts)


def run_from_snapshot(
    *,
    settings: Settings,
    snapshot: MarketSnapshot,
    allow_fallback: bool,
    memory_enabled: bool = True,
    progress_callback: ProgressCallback | None = None,
) -> RunArtifacts:
    """Run the full agent pipeline for an already-built market snapshot."""
    pipeline = _build_run_pipeline_context(
        settings=settings,
        snapshot=snapshot,
        allow_fallback=allow_fallback,
        memory_enabled=memory_enabled,
        progress_callback=progress_callback,
    )
    research = _run_research_stages(pipeline)
    planning = _run_planning_stages(pipeline, research)

    return _run_outputs.build_run_artifacts(
        snapshot=snapshot,
        canonical_snapshot=pipeline.canonical_snapshot,
        decision_features=pipeline.decision_features,
        research=research,
        planning=planning,
    )


def _build_run_pipeline_context(
    *,
    settings: Settings,
    snapshot: MarketSnapshot,
    allow_fallback: bool,
    memory_enabled: bool,
    progress_callback: ProgressCallback | None,
) -> RunPipelineContext:
    llm = LocalLLM(settings)
    db = TradingDatabase(settings)
    preferences = db.load_preferences()
    news_items = fetch_news_brief(snapshot.symbol, settings)
    canonical_snapshot = build_canonical_analysis_snapshot(
        snapshot,
        settings=settings,
        preferences=preferences,
        news_items=news_items,
        lookback=snapshot.context_pack.lookback if snapshot.context_pack else None,
    )
    decision_features = build_decision_feature_bundle(
        snapshot,
        settings=settings,
        preferences=preferences,
        news_items=news_items,
        canonical_snapshot=canonical_snapshot,
    )
    return RunPipelineContext(
        settings=settings,
        snapshot=snapshot,
        allow_fallback=allow_fallback,
        memory_enabled=memory_enabled,
        progress_callback=progress_callback,
        llm=llm,
        db=db,
        preferences=preferences,
        news_items=news_items,
        canonical_snapshot=canonical_snapshot,
        decision_features=decision_features,
        shared_memory_bus=[],
    )


def _run_research_stages(pipeline: RunPipelineContext) -> ResearchStageOutputs:
    return _run_research_stages_impl(pipeline, _research_stage_deps())


def _run_planning_stages(
    pipeline: RunPipelineContext,
    research: ResearchStageOutputs,
) -> PlanningStageOutputs:
    return _run_planning_stages_impl(pipeline, research, _planning_stage_deps())


def _research_stage_deps() -> ResearchStageDeps:
    return ResearchStageDeps(
        coordinate_research=coordinate_research,
        assess_fundamentals=assess_fundamentals,
        assess_macro_context=assess_macro_context,
        assess_regime=assess_regime,
    )


def _planning_stage_deps() -> PlanningStageDeps:
    return PlanningStageDeps(
        plan_trade=plan_trade,
        build_risk_plan=build_risk_plan,
        assess_specialist_consensus=assess_specialist_consensus,
        manage_trade_decision=manage_trade_decision,
        evaluate_execution=evaluate_execution,
        build_review_note=build_review_note,
        consensus_tool_output=_run_outputs.consensus_tool_output,
        research_upstream_context=_run_outputs.research_upstream_context,
    )


def run_once(
    *,
    settings: Settings,
    symbol: str,
    interval: str,
    lookback: str,
    allow_fallback: bool,
    memory_enabled: bool = True,
    progress_callback: ProgressCallback | None = None,
) -> RunArtifacts:
    """Fetch OHLCV data, build a snapshot, and run the one-shot agent pipeline."""
    frame = fetch_ohlcv(symbol, interval=interval, lookback=lookback, settings=settings)
    snapshot = build_snapshot(
        frame, symbol=symbol, interval=interval, lookback=lookback
    )
    return run_from_snapshot(
        settings=settings,
        snapshot=snapshot,
        allow_fallback=allow_fallback,
        memory_enabled=memory_enabled,
        progress_callback=progress_callback,
    )
