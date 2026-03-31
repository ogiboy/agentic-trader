from uuid import uuid4

from agentic_trader.agents.planner import plan_trade
from agentic_trader.agents.regime import assess_regime
from agentic_trader.agents.risk import build_risk_plan
from agentic_trader.config import Settings
from agentic_trader.engine.guard import evaluate_execution
from agentic_trader.engine.paper_broker import PaperBroker
from agentic_trader.llm.client import LocalLLM
from agentic_trader.market.data import fetch_ohlcv
from agentic_trader.market.features import build_snapshot
from agentic_trader.schemas import RunArtifacts
from agentic_trader.storage.db import TradingDatabase


def persist_run(*, settings: Settings, artifacts: RunArtifacts) -> str:
    db = TradingDatabase(settings)
    broker = PaperBroker(db, settings)
    run_id = f"run-{uuid4().hex[:12]}"
    db.insert_run(run_id, artifacts)
    return broker.submit(artifacts.execution)


def run_once(
    *,
    settings: Settings,
    symbol: str,
    interval: str,
    lookback: str,
    allow_fallback: bool,
) -> RunArtifacts:
    llm = LocalLLM(settings)

    frame = fetch_ohlcv(symbol, interval=interval, lookback=lookback)
    snapshot = build_snapshot(frame, symbol=symbol, interval=interval)
    regime = assess_regime(llm, snapshot, allow_fallback=allow_fallback)
    strategy = plan_trade(llm, snapshot, regime, allow_fallback=allow_fallback)
    risk = build_risk_plan(
        llm,
        snapshot,
        regime,
        strategy,
        allow_fallback=allow_fallback,
    )
    execution = evaluate_execution(settings, snapshot, strategy, risk)

    artifacts = RunArtifacts(
        snapshot=snapshot,
        regime=regime,
        strategy=strategy,
        risk=risk,
        execution=execution,
    )
    return artifacts
