from pathlib import Path

from agentic_trader.config import Settings
from agentic_trader.engine.paper_broker import PaperBroker
from agentic_trader.schemas import (
    ExecutionDecision,
    LLMHealthStatus,
    ManagerDecision,
    MarketSnapshot,
    RegimeAssessment,
    ResearchCoordinatorBrief,
    RiskPlan,
    ReviewNote,
    RunArtifacts,
    StrategyPlan,
)
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.workflows.service import run_service


def _artifacts(symbol: str, last_close: float, take_profit: float) -> RunArtifacts:
    return RunArtifacts(
        snapshot=MarketSnapshot(
            symbol=symbol,
            interval="1d",
            last_close=last_close,
            ema_20=105.0,
            ema_50=100.0,
            atr_14=2.0,
            rsi_14=60.0,
            volatility_20=0.1,
            return_5=0.03,
            return_20=0.08,
            volume_ratio_20=1.1,
            bars_analyzed=120,
        ),
        coordinator=ResearchCoordinatorBrief(
            market_focus="trend_following",
            priority_signals=["trend_alignment"],
            caution_flags=[],
            summary="Coordinator summary",
        ),
        regime=RegimeAssessment(
            regime="trend_up",
            direction_bias="long",
            confidence=0.75,
            reasoning="Trend up",
        ),
        strategy=StrategyPlan(
            strategy_family="trend_following",
            action="buy",
            timeframe="swing",
            entry_logic="Buy strength",
            invalidation_logic="Exit on weakness",
            confidence=0.75,
        ),
        risk=RiskPlan(
            position_size_pct=0.05,
            stop_loss=95.0,
            take_profit=take_profit,
            risk_reward_ratio=2.0,
            max_holding_bars=20,
            notes="Test risk",
        ),
        manager=ManagerDecision(
            approved=True,
            action_bias="buy",
            confidence_cap=0.75,
            size_multiplier=1.0,
            rationale="Manager approved",
        ),
        execution=ExecutionDecision(
            approved=True,
            side="buy",
            symbol=symbol,
            entry_price=last_close,
            stop_loss=95.0,
            take_profit=take_profit,
            position_size_pct=0.05,
            confidence=0.75,
            rationale="Approved",
        ),
        review=ReviewNote(
            summary="Review summary",
            strengths=["x"],
            warnings=[],
            next_checks=["y"],
        ),
    )


def test_service_closes_position_when_take_profit_is_hit(
    monkeypatch, tmp_path: Path
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        default_cash=10_000.0,
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    broker = PaperBroker(db, settings)

    initial = _artifacts("AAPL", 100.0, 110.0)
    entry_order_id = broker.submit(initial.execution)
    broker.record_position_plan(
        symbol="AAPL",
        decision=initial.execution,
        strategy=initial.strategy,
        max_holding_bars=initial.risk.max_holding_bars,
    )
    assert entry_order_id.startswith("paper-")

    monkeypatch.setattr(
        "agentic_trader.workflows.service.ensure_llm_ready",
        lambda current_settings: LLMHealthStatus(
            provider="ollama",
            base_url=current_settings.base_url,
            model_name=current_settings.model_name,
            service_reachable=True,
            model_available=True,
            message="ok",
        ),
    )
    monkeypatch.setattr(
        "agentic_trader.workflows.service.run_once",
        lambda **kwargs: _artifacts(kwargs["symbol"], 111.0, 120.0),
    )
    monkeypatch.setattr(
        "agentic_trader.workflows.service.persist_run",
        lambda **kwargs: "paper-new-order",
    )

    run_service(
        settings=settings,
        symbols=["AAPL"],
        interval="1d",
        lookback="180d",
        poll_seconds=1,
        continuous=False,
        max_cycles=None,
    )

    position = db.get_position("AAPL")
    plan = db.get_position_plan("AAPL")
    events = db.list_service_events(limit=10)

    assert position is not None
    assert position.quantity == 0
    assert plan is None
    assert any(event.event_type == "position_closed" for event in events)
