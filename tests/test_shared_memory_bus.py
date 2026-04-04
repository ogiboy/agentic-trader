import json
from pathlib import Path

from agentic_trader.config import Settings
from agentic_trader.schemas import (
    ManagerDecision,
    MarketSnapshot,
    RegimeAssessment,
    ResearchCoordinatorBrief,
    RiskPlan,
    StrategyPlan,
)
from agentic_trader.workflows.run_once import run_from_snapshot


def _snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        symbol="AAPL",
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
    )


def test_run_from_snapshot_propagates_shared_memory_bus(
    monkeypatch, tmp_path: Path
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()

    monkeypatch.setattr(
        "agentic_trader.workflows.run_once.coordinate_research",
        lambda *args, **kwargs: ResearchCoordinatorBrief(
            market_focus="trend_following",
            priority_signals=["trend_alignment"],
            caution_flags=[],
            summary="Coordinator summary",
        ),
    )
    monkeypatch.setattr(
        "agentic_trader.workflows.run_once.assess_regime",
        lambda *args, **kwargs: RegimeAssessment(
            regime="trend_up",
            direction_bias="long",
            confidence=0.74,
            reasoning="Regime summary",
        ),
    )
    monkeypatch.setattr(
        "agentic_trader.workflows.run_once.plan_trade",
        lambda *args, **kwargs: StrategyPlan(
            strategy_family="trend_following",
            action="buy",
            timeframe="swing",
            entry_logic="Buy above EMA20.",
            invalidation_logic="Exit below EMA20.",
            confidence=0.76,
        ),
    )
    monkeypatch.setattr(
        "agentic_trader.workflows.run_once.build_risk_plan",
        lambda *args, **kwargs: RiskPlan(
            position_size_pct=0.08,
            stop_loss=95.0,
            take_profit=110.0,
            risk_reward_ratio=2.0,
            max_holding_bars=20,
            notes="Risk summary",
        ),
    )
    monkeypatch.setattr(
        "agentic_trader.workflows.run_once.manage_trade_decision",
        lambda *args, **kwargs: ManagerDecision(
            approved=True,
            action_bias="buy",
            confidence_cap=0.76,
            size_multiplier=1.0,
            rationale="Manager summary",
        ),
    )

    artifacts = run_from_snapshot(
        settings=settings,
        snapshot=_snapshot(),
        allow_fallback=False,
    )

    strategy_trace = next(
        trace for trace in artifacts.agent_traces if trace.role == "strategy"
    )
    manager_trace = next(trace for trace in artifacts.agent_traces if trace.role == "manager")
    strategy_context = json.loads(strategy_trace.context_json)
    manager_context = json.loads(manager_trace.context_json)

    assert len(strategy_context["shared_memory_bus"]) == 2
    assert strategy_context["shared_memory_bus"][0]["role"] == "coordinator"
    assert len(manager_context["shared_memory_bus"]) == 5
    assert manager_context["shared_memory_bus"][-1]["role"] == "consensus"
