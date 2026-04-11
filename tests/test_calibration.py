from pathlib import Path
import pytest

from agentic_trader.agents.calibration import build_confidence_calibration
from agentic_trader.agents.manager import manage_trade_decision
from agentic_trader.config import Settings
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import (
    ExecutionDecision,
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
from agentic_trader.workflows.run_once import persist_run
from agentic_trader.agents.context import build_agent_context


def _artifacts(symbol: str = "AAPL", *, approved: bool = True) -> RunArtifacts:
    side = "buy" if approved else "hold"
    return RunArtifacts(
        snapshot=MarketSnapshot(
            symbol=symbol,
            interval="1d",
            last_close=100.0,
            ema_20=101.0,
            ema_50=98.0,
            atr_14=2.0,
            rsi_14=58.0,
            volatility_20=0.12,
            return_5=0.03,
            return_20=0.09,
            volume_ratio_20=1.1,
            bars_analyzed=160,
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
            confidence=0.72,
            reasoning="Trend aligns.",
        ),
        strategy=StrategyPlan(
            strategy_family="trend_following",
            action="buy",
            timeframe="swing",
            entry_logic="Buy pullbacks above EMA20.",
            invalidation_logic="Exit below EMA20.",
            confidence=0.76,
        ),
        risk=RiskPlan(
            position_size_pct=0.08,
            stop_loss=95.0,
            take_profit=110.0,
            risk_reward_ratio=2.0,
            max_holding_bars=20,
            notes="Risk plan",
        ),
        manager=ManagerDecision(
            approved=approved,
            action_bias=side,
            confidence_cap=0.76,
            size_multiplier=1.0,
            rationale="Manager base decision.",
        ),
        execution=ExecutionDecision(
            approved=approved,
            side=side,
            symbol=symbol,
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=110.0,
            position_size_pct=0.08,
            confidence=0.76,
            rationale="Execution.",
        ),
        review=ReviewNote(
            summary="Review summary",
            strengths=["trend aligned"],
            warnings=[],
            next_checks=["watch invalidation"],
        ),
    )


def _close_recent_trade(
    db: TradingDatabase, artifacts: RunArtifacts, *, pnl: float
) -> None:
    trade_id = db.create_trade_journal(
        run_id="historic-run",
        order_id="order-historic",
        artifacts=artifacts,
        journal_status="open",
        notes="historic trade",
    )
    assert trade_id.startswith("trade-")
    db.close_trade_journal(
        symbol=artifacts.snapshot.symbol,
        exit_order_id="exit-historic",
        exit_reason="time_exit",
        exit_price=artifacts.snapshot.last_close,
        realized_pnl=pnl,
        notes="closed for calibration",
    )


def test_build_confidence_calibration_detects_underperformance(tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    losing = _artifacts("AAPL")
    _close_recent_trade(db, losing, pnl=-120.0)
    _close_recent_trade(db, losing, pnl=-45.0)

    calibration = build_confidence_calibration(
        db, losing.snapshot, strategy_family="trend_following"
    )

    assert calibration.closed_trades == 2
    assert calibration.confidence_multiplier < 1.0
    assert calibration.win_rate == pytest.approx(0.0)


def test_manager_applies_historical_calibration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    persist_run(settings=settings, artifacts=_artifacts("AAPL"))
    db = TradingDatabase(settings)
    losing = _artifacts("AAPL")
    _close_recent_trade(db, losing, pnl=-90.0)
    _close_recent_trade(db, losing, pnl=-30.0)

    snapshot = losing.snapshot
    coordinator = losing.coordinator
    regime = losing.regime
    strategy = losing.strategy
    risk = losing.risk
    context = build_agent_context(
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
    raw_manager = ManagerDecision(
        approved=True,
        action_bias="buy",
        confidence_cap=0.76,
        size_multiplier=1.0,
        rationale="Manager base decision.",
    )
    monkeypatch.setattr(
        "agentic_trader.agents.manager.LocalLLM.complete_structured",
        lambda self, **kwargs: raw_manager,
    )

    decision = manage_trade_decision(
        llm=LocalLLM(settings),
        snapshot=snapshot,
        coordinator=coordinator,
        regime=regime,
        strategy=strategy,
        risk=risk,
        allow_fallback=False,
        context=context,
    )

    assert decision.confidence_cap < strategy.confidence
    assert decision.size_multiplier < 1.0
    assert "historical_underperformance" in decision.escalation_flags
