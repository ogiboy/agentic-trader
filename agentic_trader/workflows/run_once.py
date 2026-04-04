from collections.abc import Callable
from agentic_trader.agents.context import build_agent_context
from uuid import uuid4

from agentic_trader.agents.coordinator import coordinate_research
from agentic_trader.agents.manager import manage_trade_decision
from agentic_trader.agents.planner import plan_trade
from agentic_trader.agents.regime import assess_regime
from agentic_trader.agents.review import build_review_note
from agentic_trader.agents.risk import build_risk_plan
from agentic_trader.config import Settings
from agentic_trader.engine.guard import evaluate_execution
from agentic_trader.engine.paper_broker import PaperBroker
from agentic_trader.llm.client import LocalLLM
from agentic_trader.market.data import fetch_ohlcv
from agentic_trader.market.features import build_snapshot
from agentic_trader.schemas import AgentStageTrace, MarketSnapshot, RunArtifacts
from agentic_trader.storage.db import TradingDatabase

type ProgressCallback = Callable[[str, str, str], None]


def persist_position_plan(*, settings: Settings, artifacts: RunArtifacts) -> None:
    db = TradingDatabase(settings)
    broker = PaperBroker(db, settings)
    broker.record_position_plan(
        symbol=artifacts.snapshot.symbol,
        decision=artifacts.execution,
        strategy=artifacts.strategy,
        max_holding_bars=artifacts.risk.max_holding_bars,
    )


def persist_run(*, settings: Settings, artifacts: RunArtifacts) -> str:
    db = TradingDatabase(settings)
    broker = PaperBroker(db, settings)
    run_id = f"run-{uuid4().hex[:12]}"
    db.insert_run(run_id, artifacts)
    order_id = broker.submit(artifacts.execution)
    if not artifacts.execution.approved or artifacts.execution.side == "hold":
        journal_status = "rejected"
    elif db.order_has_fill(order_id):
        journal_status = "open"
    else:
        journal_status = "no_fill"
    db.create_trade_journal(
        run_id=run_id,
        order_id=order_id,
        artifacts=artifacts,
        journal_status=journal_status,
        notes=artifacts.review.summary,
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


def run_from_snapshot(
    *,
    settings: Settings,
    snapshot: MarketSnapshot,
    allow_fallback: bool,
    progress_callback: ProgressCallback | None = None,
) -> RunArtifacts:
    def emit(stage: str, status: str, message: str) -> None:
        if progress_callback is not None:
            progress_callback(stage, status, message)

    llm = LocalLLM(settings)
    db = TradingDatabase(settings)
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
        upstream_context={"coordinator": coordinator},
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
        upstream_context={
            "coordinator": coordinator,
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
    emit("risk", "started", f"Risk steward is sizing the trade for {snapshot.symbol}.")
    risk_context = build_agent_context(
        role="risk",
        settings=settings,
        db=db,
        snapshot=snapshot,
        upstream_context={
            "coordinator": coordinator,
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
        upstream_context={
            "coordinator": coordinator,
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
        allow_fallback=allow_fallback,
        context=manager_context,
    )
    emit(
        "manager",
        "completed",
        f"Manager agent returned bias {manager.action_bias} with approval {manager.approved}.",
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
        coordinator=coordinator,
        regime=regime,
        strategy=strategy,
        risk=risk,
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
    progress_callback: ProgressCallback | None = None,
) -> RunArtifacts:
    frame = fetch_ohlcv(symbol, interval=interval, lookback=lookback, settings=settings)
    snapshot = build_snapshot(frame, symbol=symbol, interval=interval)
    return run_from_snapshot(
        settings=settings,
        snapshot=snapshot,
        allow_fallback=allow_fallback,
        progress_callback=progress_callback,
    )
