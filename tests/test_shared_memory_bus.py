import json
from pathlib import Path

import pytest

from agentic_trader.config import Settings
from agentic_trader.schemas import (
    FundamentalAssessment,
    MacroAssessment,
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
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()

    def _coordinate_research(
        *_args: object, **_kwargs: object
    ) -> ResearchCoordinatorBrief:
        return ResearchCoordinatorBrief(
            market_focus="trend_following",
            priority_signals=["trend_alignment"],
            caution_flags=[],
            summary="Coordinator summary",
        )

    def _assess_fundamentals(
        *_args: object, **_kwargs: object
    ) -> FundamentalAssessment:
        return FundamentalAssessment(
            overall_bias="neutral",
            confidence=0.5,
            summary="Fundamental summary",
        )

    def _assess_macro_context(*_args: object, **_kwargs: object) -> MacroAssessment:
        return MacroAssessment(
            macro_signal="neutral",
            confidence=0.5,
            summary="Macro summary",
        )

    def _assess_regime(*_args: object, **_kwargs: object) -> RegimeAssessment:
        return RegimeAssessment(
            regime="trend_up",
            direction_bias="long",
            confidence=0.74,
            reasoning="Regime summary",
        )

    def _plan_trade(*_args: object, **_kwargs: object) -> StrategyPlan:
        return StrategyPlan(
            strategy_family="trend_following",
            action="buy",
            timeframe="swing",
            entry_logic="Buy above EMA20.",
            invalidation_logic="Exit below EMA20.",
            confidence=0.76,
        )

    def _build_risk_plan(*_args: object, **_kwargs: object) -> RiskPlan:
        return RiskPlan(
            position_size_pct=0.08,
            stop_loss=95.0,
            take_profit=110.0,
            risk_reward_ratio=2.0,
            max_holding_bars=20,
            notes="Risk summary",
        )

    def _manage_trade_decision(*_args: object, **_kwargs: object) -> ManagerDecision:
        return ManagerDecision(
            approved=True,
            action_bias="buy",
            confidence_cap=0.76,
            size_multiplier=1.0,
            rationale="Manager summary",
        )

    monkeypatch.setattr(
        "agentic_trader.workflows.run_once.coordinate_research",
        _coordinate_research,
    )
    monkeypatch.setattr(
        "agentic_trader.workflows.run_once.assess_fundamentals",
        _assess_fundamentals,
    )
    monkeypatch.setattr(
        "agentic_trader.workflows.run_once.assess_macro_context",
        _assess_macro_context,
    )
    monkeypatch.setattr(
        "agentic_trader.workflows.run_once.assess_regime",
        _assess_regime,
    )
    monkeypatch.setattr(
        "agentic_trader.workflows.run_once.plan_trade",
        _plan_trade,
    )
    monkeypatch.setattr(
        "agentic_trader.workflows.run_once.build_risk_plan",
        _build_risk_plan,
    )
    monkeypatch.setattr(
        "agentic_trader.workflows.run_once.manage_trade_decision",
        _manage_trade_decision,
    )

    artifacts = run_from_snapshot(
        settings=settings,
        snapshot=_snapshot(),
        allow_fallback=False,
    )

    strategy_trace = next(
        trace for trace in artifacts.agent_traces if trace.role == "strategy"
    )
    manager_trace = next(
        trace for trace in artifacts.agent_traces if trace.role == "manager"
    )
    strategy_context = json.loads(strategy_trace.context_json)
    manager_context = json.loads(manager_trace.context_json)

    assert len(strategy_context["shared_memory_bus"]) == 4
    assert strategy_context["shared_memory_bus"][0]["role"] == "coordinator"
    assert strategy_context["decision_features"]["technical"]["symbol"] == "AAPL"
    assert len(manager_context["shared_memory_bus"]) == 7
    assert manager_context["shared_memory_bus"][-1]["role"] == "consensus"
