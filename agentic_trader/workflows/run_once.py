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
from agentic_trader.schemas import MarketSnapshot, RunArtifacts
from agentic_trader.storage.db import TradingDatabase


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
) -> RunArtifacts:
    llm = LocalLLM(settings)
    db = TradingDatabase(settings)
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
    regime = assess_regime(
        llm,
        snapshot,
        allow_fallback=allow_fallback,
        context=build_agent_context(
            role="regime",
            settings=settings,
            db=db,
            snapshot=snapshot,
            upstream_context={"coordinator": coordinator},
        ),
    )
    strategy = plan_trade(
        llm,
        snapshot,
        regime,
        allow_fallback=allow_fallback,
        context=build_agent_context(
            role="strategy",
            settings=settings,
            db=db,
            snapshot=snapshot,
            upstream_context={
                "coordinator": coordinator,
                "regime": regime,
            },
        ),
    )
    risk = build_risk_plan(
        llm,
        snapshot,
        regime,
        strategy,
        allow_fallback=allow_fallback,
        context=build_agent_context(
            role="risk",
            settings=settings,
            db=db,
            snapshot=snapshot,
            upstream_context={
                "coordinator": coordinator,
                "regime": regime,
                "strategy": strategy,
            },
        ),
    )
    manager = manage_trade_decision(
        llm,
        snapshot,
        coordinator,
        regime,
        strategy,
        risk,
        allow_fallback=allow_fallback,
        context=build_agent_context(
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
        ),
    )
    execution = evaluate_execution(settings, snapshot, strategy, risk, manager)
    review = build_review_note(regime, strategy, risk, manager, execution)

    return RunArtifacts(
        snapshot=snapshot,
        coordinator=coordinator,
        regime=regime,
        strategy=strategy,
        risk=risk,
        manager=manager,
        execution=execution,
        review=review,
    )


def run_once(
    *,
    settings: Settings,
    symbol: str,
    interval: str,
    lookback: str,
    allow_fallback: bool,
) -> RunArtifacts:
    frame = fetch_ohlcv(symbol, interval=interval, lookback=lookback)
    snapshot = build_snapshot(frame, symbol=symbol, interval=interval)
    return run_from_snapshot(
        settings=settings,
        snapshot=snapshot,
        allow_fallback=allow_fallback,
    )
