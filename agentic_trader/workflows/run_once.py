from collections.abc import Callable
from agentic_trader.agents.context import build_agent_context
from uuid import uuid4

from agentic_trader.agents.coordinator import coordinate_research
from agentic_trader.agents.consensus import assess_specialist_consensus
from agentic_trader.agents.fundamental import assess_fundamentals
from agentic_trader.agents.macro import assess_macro_context
from agentic_trader.agents.manager import manage_trade_decision
from agentic_trader.agents.planner import plan_trade
from agentic_trader.agents.regime import assess_regime
from agentic_trader.agents.review import build_review_note
from agentic_trader.agents.risk import build_risk_plan
from agentic_trader.config import Settings
from agentic_trader.engine.broker import get_broker_adapter
from agentic_trader.engine.guard import evaluate_execution
from agentic_trader.execution.intent import build_execution_intent
from agentic_trader.features import build_decision_feature_bundle
from agentic_trader.llm.client import LocalLLM
from agentic_trader.market.data import fetch_ohlcv
from agentic_trader.market.features import build_snapshot
from agentic_trader.market.news import fetch_news_brief
from agentic_trader.providers import build_canonical_analysis_snapshot
from agentic_trader.schemas import (
    AgentStageTrace,
    MarketSnapshot,
    RunArtifacts,
    SharedMemoryEntry,
)
from agentic_trader.storage.db import TradingDatabase

type ProgressCallback = Callable[[str, str, str], None]


def persist_position_plan(*, settings: Settings, artifacts: RunArtifacts) -> None:
    db = TradingDatabase(settings)
    try:
        broker = get_broker_adapter(db=db, settings=settings)
        broker.record_position_plan(
            symbol=artifacts.snapshot.symbol,
            decision=artifacts.execution,
            strategy=artifacts.strategy,
            max_holding_bars=artifacts.risk.max_holding_bars,
        )
    finally:
        db.close()


def persist_run(*, settings: Settings, artifacts: RunArtifacts) -> str:
    db = TradingDatabase(settings)
    try:
        broker = get_broker_adapter(db=db, settings=settings)
        run_id = f"run-{uuid4().hex[:12]}"
        db.insert_run(run_id, artifacts)
        account = broker.get_account_state()
        intent = build_execution_intent(
            decision=artifacts.execution,
            settings=settings,
            run_id=run_id,
            reasoning_id="manager",
            trace_link=f"run:{run_id}/trace",
            invalidation_condition=artifacts.strategy.invalidation_logic,
            reference_equity=account.equity,
            adapter_name=broker.backend_name,
        )
        outcome = broker.place_order(intent)
        if outcome.order_id is None:
            raise RuntimeError("Broker adapter did not return an order id.")
        order_id = outcome.order_id
        db.record_execution_outcome(run_id=run_id, intent=intent, outcome=outcome)
        if not artifacts.execution.approved or artifacts.execution.side == "hold":
            journal_status = "rejected"
        elif db.order_has_fill(order_id):
            journal_status = "open"
        else:
            journal_status = "no_fill"
        trade_id = db.create_trade_journal(
            run_id=run_id,
            order_id=order_id,
            artifacts=artifacts,
            journal_status=journal_status,
            notes=artifacts.review.summary,
        )
        db.persist_trade_context(
            trade_id=trade_id,
            run_id=run_id,
            artifacts=artifacts,
            execution_intent=intent,
            execution_outcome=outcome,
        )
        broker.record_position_plan(
            symbol=artifacts.snapshot.symbol,
            decision=artifacts.execution,
            strategy=artifacts.strategy,
            max_holding_bars=artifacts.risk.max_holding_bars,
        )
        db.record_account_mark(
            source="run_persisted",
            note=f"Run persisted for {artifacts.snapshot.symbol} with order {order_id}.",
            symbol=artifacts.snapshot.symbol,
        )
        return order_id
    finally:
        db.close()


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
    shared_memory_bus: list[SharedMemoryEntry] = []

    def emit(stage: str, status: str, message: str) -> None:
        if progress_callback is not None:
            progress_callback(stage, status, message)

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
    emit(
        "coordinator",
        "started",
        f"Coordinator is setting research focus for {snapshot.symbol}.",
    )
    coordinator_context = build_agent_context(
        role="coordinator",
        settings=settings,
        db=db,
        snapshot=snapshot,
        canonical_snapshot=canonical_snapshot,
        decision_features=decision_features,
        news_items=news_items,
        memory_enabled=memory_enabled,
        shared_memory_bus=shared_memory_bus,
    )
    coordinator = coordinate_research(
        llm,
        snapshot,
        allow_fallback=allow_fallback,
        context=coordinator_context,
    )
    emit(
        "coordinator",
        "completed",
        f"Coordinator completed with focus {coordinator.market_focus}.",
    )
    shared_memory_bus.append(
        SharedMemoryEntry(
            role="coordinator",
            summary=f"Focus {coordinator.market_focus} with summary: {coordinator.summary}",
            payload_json=coordinator.model_dump_json(indent=2),
        )
    )
    emit(
        "fundamental",
        "started",
        f"Fundamental analyst is reviewing structured evidence for {snapshot.symbol}.",
    )
    fundamental_context = build_agent_context(
        role="fundamental",
        settings=settings,
        db=db,
        snapshot=snapshot,
        canonical_snapshot=canonical_snapshot,
        decision_features=decision_features,
        news_items=news_items,
        memory_enabled=memory_enabled,
        shared_memory_bus=shared_memory_bus,
        upstream_context={"coordinator": coordinator},
    )
    fundamental = assess_fundamentals(
        llm,
        snapshot,
        allow_fallback=allow_fallback,
        context=fundamental_context,
    )
    emit(
        "fundamental",
        "completed",
        f"Fundamental analyst returned {fundamental.overall_bias}.",
    )
    shared_memory_bus.append(
        SharedMemoryEntry(
            role="fundamental",
            summary=(
                f"Fundamental bias {fundamental.overall_bias}: {fundamental.summary}"
            ),
            payload_json=fundamental.model_dump_json(indent=2),
        )
    )
    emit(
        "macro",
        "started",
        f"Macro/news analyst is reviewing context for {snapshot.symbol}.",
    )
    macro_context = build_agent_context(
        role="macro",
        settings=settings,
        db=db,
        snapshot=snapshot,
        canonical_snapshot=canonical_snapshot,
        decision_features=decision_features,
        news_items=news_items,
        memory_enabled=memory_enabled,
        shared_memory_bus=shared_memory_bus,
        upstream_context={
            "coordinator": coordinator,
            "fundamental": fundamental,
        },
    )
    macro = assess_macro_context(
        llm,
        snapshot,
        allow_fallback=allow_fallback,
        context=macro_context,
    )
    emit(
        "macro",
        "completed",
        f"Macro/news analyst returned {macro.macro_signal}.",
    )
    shared_memory_bus.append(
        SharedMemoryEntry(
            role="macro",
            summary=f"Macro signal {macro.macro_signal}: {macro.summary}",
            payload_json=macro.model_dump_json(indent=2),
        )
    )
    emit(
        "regime",
        "started",
        f"Regime analyst is classifying the market for {snapshot.symbol}.",
    )
    regime_context = build_agent_context(
        role="regime",
        settings=settings,
        db=db,
        snapshot=snapshot,
        canonical_snapshot=canonical_snapshot,
        decision_features=decision_features,
        news_items=news_items,
        memory_enabled=memory_enabled,
        shared_memory_bus=shared_memory_bus,
        upstream_context={
            "coordinator": coordinator,
            "fundamental": fundamental,
            "macro": macro,
        },
    )
    regime = assess_regime(
        llm,
        snapshot,
        allow_fallback=allow_fallback,
        context=regime_context,
    )
    emit(
        "regime",
        "completed",
        f"Regime analyst classified the market as {regime.regime}.",
    )
    shared_memory_bus.append(
        SharedMemoryEntry(
            role="regime",
            summary=f"Regime {regime.regime} with bias {regime.direction_bias}",
            payload_json=regime.model_dump_json(indent=2),
        )
    )
    emit(
        "strategy",
        "started",
        f"Strategy selector is planning the trade for {snapshot.symbol}.",
    )
    strategy_context = build_agent_context(
        role="strategy",
        settings=settings,
        db=db,
        snapshot=snapshot,
        canonical_snapshot=canonical_snapshot,
        decision_features=decision_features,
        news_items=news_items,
        memory_enabled=memory_enabled,
        shared_memory_bus=shared_memory_bus,
        upstream_context={
            "coordinator": coordinator,
            "fundamental": fundamental,
            "macro": macro,
            "regime": regime,
        },
    )
    strategy = plan_trade(
        llm,
        snapshot,
        regime,
        allow_fallback=allow_fallback,
        context=strategy_context,
    )
    emit(
        "strategy",
        "completed",
        f"Strategy selector chose {strategy.strategy_family} with action {strategy.action}.",
    )
    shared_memory_bus.append(
        SharedMemoryEntry(
            role="strategy",
            summary=(
                f"Strategy {strategy.strategy_family} chose {strategy.action} at {strategy.confidence:.2f} confidence"
            ),
            payload_json=strategy.model_dump_json(indent=2),
        )
    )
    emit("risk", "started", f"Risk steward is sizing the trade for {snapshot.symbol}.")
    risk_context = build_agent_context(
        role="risk",
        settings=settings,
        db=db,
        snapshot=snapshot,
        canonical_snapshot=canonical_snapshot,
        decision_features=decision_features,
        news_items=news_items,
        memory_enabled=memory_enabled,
        shared_memory_bus=shared_memory_bus,
        upstream_context={
            "coordinator": coordinator,
            "fundamental": fundamental,
            "macro": macro,
            "regime": regime,
            "strategy": strategy,
        },
    )
    risk = build_risk_plan(
        llm,
        snapshot,
        regime,
        strategy,
        allow_fallback=allow_fallback,
        context=risk_context,
    )
    emit(
        "risk",
        "completed",
        f"Risk steward set size {risk.position_size_pct:.2%} and RR {risk.risk_reward_ratio:.2f}.",
    )
    shared_memory_bus.append(
        SharedMemoryEntry(
            role="risk",
            summary=(
                f"Risk size {risk.position_size_pct:.2%}, RR {risk.risk_reward_ratio:.2f}, max hold {risk.max_holding_bars}"
            ),
            payload_json=risk.model_dump_json(indent=2),
        )
    )
    consensus = assess_specialist_consensus(
        coordinator,
        regime,
        strategy,
        risk,
        fundamental=fundamental,
        macro=macro,
    )
    emit(
        "consensus",
        "completed",
        f"Specialist consensus assessed as {consensus.alignment_level}.",
    )
    shared_memory_bus.append(
        SharedMemoryEntry(
            role="consensus",
            summary=consensus.summary,
            payload_json=consensus.model_dump_json(indent=2),
        )
    )
    emit(
        "manager",
        "started",
        f"Manager agent is combining specialist outputs for {snapshot.symbol}.",
    )
    manager_context = build_agent_context(
        role="manager",
        settings=settings,
        db=db,
        snapshot=snapshot,
        canonical_snapshot=canonical_snapshot,
        decision_features=decision_features,
        news_items=news_items,
        memory_enabled=memory_enabled,
        shared_memory_bus=shared_memory_bus,
        tool_outputs=[
            f"specialist_consensus: level={consensus.alignment_level} support={','.join(consensus.supporting_roles) or '-'} dissent={','.join(consensus.dissenting_roles) or '-'} summary={consensus.summary}"
        ],
        upstream_context={
            "coordinator": coordinator,
            "fundamental": fundamental,
            "macro": macro,
            "regime": regime,
            "strategy": strategy,
            "risk": risk,
        },
    )
    manager = manage_trade_decision(
        llm,
        snapshot,
        coordinator,
        regime,
        strategy,
        risk,
        fundamental=fundamental,
        macro=macro,
        allow_fallback=allow_fallback,
        context=manager_context,
    )
    emit(
        "manager",
        "completed",
        f"Manager agent returned bias {manager.action_bias} with approval {manager.approved}.",
    )
    shared_memory_bus.append(
        SharedMemoryEntry(
            role="manager",
            summary=(
                f"Manager bias {manager.action_bias}, approved={manager.approved}, override={manager.override_applied}"
            ),
            payload_json=manager.model_dump_json(indent=2),
        )
    )
    emit(
        "execution",
        "started",
        f"Execution guard is validating the plan for {snapshot.symbol}.",
    )
    execution = evaluate_execution(settings, snapshot, strategy, risk, manager)
    emit(
        "execution",
        "completed",
        f"Execution guard {'approved' if execution.approved else 'rejected'} {execution.side}.",
    )
    emit(
        "review",
        "started",
        f"Review agent is writing the post-trade note for {snapshot.symbol}.",
    )
    review = build_review_note(regime, strategy, risk, manager, execution)
    emit("review", "completed", "Review note completed.")
    traces = [
        AgentStageTrace(
            role="coordinator",
            model_name=coordinator_context.model_name,
            context_json=coordinator_context.model_dump_json(indent=2),
            output_json=coordinator.model_dump_json(indent=2),
            used_fallback=coordinator.source == "fallback",
        ),
        AgentStageTrace(
            role="fundamental",
            model_name=fundamental_context.model_name,
            context_json=fundamental_context.model_dump_json(indent=2),
            output_json=fundamental.model_dump_json(indent=2),
            used_fallback=fundamental.source == "fallback",
        ),
        AgentStageTrace(
            role="macro",
            model_name=macro_context.model_name,
            context_json=macro_context.model_dump_json(indent=2),
            output_json=macro.model_dump_json(indent=2),
            used_fallback=macro.source == "fallback",
        ),
    ]
    traces.extend(
        [
            AgentStageTrace(
                role="regime",
                model_name=regime_context.model_name,
                context_json=regime_context.model_dump_json(indent=2),
                output_json=regime.model_dump_json(indent=2),
                used_fallback=regime.source == "fallback",
            ),
            AgentStageTrace(
                role="strategy",
                model_name=strategy_context.model_name,
                context_json=strategy_context.model_dump_json(indent=2),
                output_json=strategy.model_dump_json(indent=2),
                used_fallback=strategy.source == "fallback",
            ),
            AgentStageTrace(
                role="risk",
                model_name=risk_context.model_name,
                context_json=risk_context.model_dump_json(indent=2),
                output_json=risk.model_dump_json(indent=2),
                used_fallback=risk.source == "fallback",
            ),
            AgentStageTrace(
                role="manager",
                model_name=manager_context.model_name,
                context_json=manager_context.model_dump_json(indent=2),
                output_json=manager.model_dump_json(indent=2),
                used_fallback=manager.source == "fallback",
            ),
        ]
    )

    return RunArtifacts(
        snapshot=snapshot,
        canonical_snapshot=canonical_snapshot,
        decision_features=decision_features,
        coordinator=coordinator,
        fundamental=fundamental,
        macro=macro,
        regime=regime,
        strategy=strategy,
        risk=risk,
        consensus=consensus,
        manager=manager,
        execution=execution,
        review=review,
        agent_traces=traces,
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
