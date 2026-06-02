from pydantic import BaseModel

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
from agentic_trader.schemas import (
    AgentContext,
    ExecutionDecision,
    FundamentalAssessment,
    MacroAssessment,
    ManagerDecision,
    MarketSnapshot,
    RegimeAssessment,
    ResearchCoordinatorBrief,
    ReviewNote,
    RiskPlan,
    RunArtifacts,
    SpecialistConsensus,
    StrategyPlan,
)
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.workflows import run_outputs as _run_outputs
from agentic_trader.workflows.run_context import (
    PlanningStageOutputs,
    ProgressCallback,
    ResearchStageOutputs,
    RunPipelineContext,
)
from agentic_trader.workflows import run_persistence as _run_persistence


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
    """
    Orchestrates the multi-stage agent pipeline for a given market snapshot and returns the aggregated run artifacts.

    Parameters:
        settings (Settings): Configuration and environment for LLMs, database, and adapters.
        snapshot (MarketSnapshot): Market data and contextual pack for the target symbol and interval.
        allow_fallback (bool): If True, agents may use fallback behavior when primary models fail or are unavailable.
        memory_enabled (bool): If True, stages may read from and append to the shared in-memory bus between stages.
        progress_callback (ProgressCallback | None): Optional callback invoked with (stage, status, message) to report stage progress.

    Returns:
        RunArtifacts: Aggregated outputs including the original snapshot, canonical snapshot, decision features, each stage's outputs (coordinator, fundamental, macro, regime, strategy, risk, consensus, manager, execution, review) and agent stage traces.
    """
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
    coordinator, coordinator_context = _run_coordinator_stage(pipeline)
    fundamental, fundamental_context = _run_fundamental_stage(
        pipeline, coordinator=coordinator
    )
    macro, macro_context = _run_macro_stage(
        pipeline,
        coordinator=coordinator,
        fundamental=fundamental,
    )
    regime, regime_context = _run_regime_stage(
        pipeline,
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
) -> tuple[ResearchCoordinatorBrief, AgentContext]:
    snapshot = pipeline.snapshot
    pipeline.emit(
        "coordinator",
        "started",
        f"Coordinator is setting research focus for {snapshot.symbol}.",
    )
    context = pipeline.agent_context(role="coordinator")
    coordinator = coordinate_research(
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
    pipeline: RunPipelineContext, *, coordinator: ResearchCoordinatorBrief
) -> tuple[FundamentalAssessment, AgentContext]:
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
    fundamental = assess_fundamentals(
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
    *,
    coordinator: ResearchCoordinatorBrief,
    fundamental: FundamentalAssessment,
) -> tuple[MacroAssessment, AgentContext]:
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
    macro = assess_macro_context(
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
    *,
    coordinator: ResearchCoordinatorBrief,
    fundamental: FundamentalAssessment,
    macro: MacroAssessment,
) -> tuple[RegimeAssessment, AgentContext]:
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
    regime = assess_regime(
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


def _run_planning_stages(
    pipeline: RunPipelineContext, research: ResearchStageOutputs
) -> PlanningStageOutputs:
    strategy, strategy_context = _run_strategy_stage(pipeline, research)
    risk, risk_context = _run_risk_stage(pipeline, research, strategy)
    consensus = _assess_and_record_consensus(pipeline, research, strategy, risk)
    manager, manager_context = _run_manager_stage(
        pipeline, research, strategy, risk, consensus
    )
    execution = _run_execution_stage(pipeline, strategy, risk, manager)
    review = _run_review_stage(
        pipeline, research.regime, strategy, risk, manager, execution
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
    pipeline: RunPipelineContext, research: ResearchStageOutputs
) -> tuple[StrategyPlan, AgentContext]:
    snapshot = pipeline.snapshot
    pipeline.emit(
        "strategy",
        "started",
        f"Strategy selector is planning the trade for {snapshot.symbol}.",
    )
    context = pipeline.agent_context(
        role="strategy",
        upstream_context=_research_upstream_context(research),
    )
    strategy = plan_trade(
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
) -> tuple[RiskPlan, AgentContext]:
    snapshot = pipeline.snapshot
    pipeline.emit(
        "risk", "started", f"Risk steward is sizing the trade for {snapshot.symbol}."
    )
    context = pipeline.agent_context(
        role="risk",
        upstream_context={
            **_research_upstream_context(research),
            "strategy": strategy,
        },
    )
    risk = build_risk_plan(
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
) -> SpecialistConsensus:
    consensus = assess_specialist_consensus(
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
) -> tuple[ManagerDecision, AgentContext]:
    snapshot = pipeline.snapshot
    pipeline.emit(
        "manager",
        "started",
        f"Manager agent is combining specialist outputs for {snapshot.symbol}.",
    )
    context = pipeline.agent_context(
        role="manager",
        tool_outputs=[_run_outputs.consensus_tool_output(consensus)],
        upstream_context={
            **_research_upstream_context(research),
            "strategy": strategy,
            "risk": risk,
        },
    )
    manager = manage_trade_decision(
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
) -> ExecutionDecision:
    snapshot = pipeline.snapshot
    pipeline.emit(
        "execution",
        "started",
        f"Execution guard is validating the plan for {snapshot.symbol}.",
    )
    execution = evaluate_execution(pipeline.settings, snapshot, strategy, risk, manager)
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
) -> ReviewNote:
    pipeline.emit(
        "review",
        "started",
        f"Review agent is writing the post-trade note for {pipeline.snapshot.symbol}.",
    )
    review = build_review_note(regime, strategy, risk, manager, execution)
    pipeline.emit("review", "completed", "Review note completed.")
    return review


def _research_upstream_context(
    research: ResearchStageOutputs,
) -> dict[str, BaseModel | str]:
    return _run_outputs.research_upstream_context(research)


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
    """
    Run the agent pipeline once for a given market symbol and interval using freshly fetched OHLCV data.

    Fetches market data with the specified lookback, builds a MarketSnapshot, and executes the full run pipeline returning the resulting artifacts.

    Parameters:
        settings (Settings): Runtime and environment configuration.
        symbol (str): Market symbol to run the pipeline for (e.g., "AAPL").
        interval (str): Candlestick interval (e.g., "1h", "1d").
        lookback (str): Historical window to fetch (e.g., "30d", "90m") used to build the snapshot.
        allow_fallback (bool): If True, agents may use fallback behaviour when primary methods fail.
        memory_enabled (bool): If True, enable shared memory bus entries between stages.
        progress_callback (ProgressCallback | None): Optional callback invoked with stage, status, and message updates.

    Returns:
        RunArtifacts: Object containing the snapshot, all agent outputs (coordinator, regime, strategy, risk, consensus, manager, execution), the review note, and agent stage traces.
    """
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
