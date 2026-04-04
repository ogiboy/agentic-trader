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


def _snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        symbol="TEST",
        interval="1d",
        last_close=100.0,
        ema_20=101.0,
        ema_50=99.0,
        atr_14=2.0,
        rsi_14=58.0,
        volatility_20=0.2,
        return_5=0.03,
        return_20=0.09,
        volume_ratio_20=1.2,
        bars_analyzed=120,
    )


def test_run_artifacts_reports_fallback_components() -> None:
    artifacts = RunArtifacts(
        snapshot=_snapshot(),
        coordinator=ResearchCoordinatorBrief(
            market_focus="trend_following",
            priority_signals=["trend_alignment"],
            caution_flags=[],
            summary="Coordinator summary",
            source="fallback",
            fallback_reason="Test fallback",
        ),
        regime=RegimeAssessment(
            regime="trend_up",
            direction_bias="long",
            confidence=0.7,
            reasoning="Test regime",
            source="fallback",
            fallback_reason="Test fallback",
        ),
        strategy=StrategyPlan(
            strategy_family="trend_following",
            action="buy",
            timeframe="swing",
            entry_logic="Test entry",
            invalidation_logic="Test invalidation",
            confidence=0.7,
            source="llm",
        ),
        risk=RiskPlan(
            position_size_pct=0.05,
            stop_loss=95.0,
            take_profit=110.0,
            risk_reward_ratio=2.0,
            max_holding_bars=20,
            notes="Test risk",
            source="fallback",
            fallback_reason="Test fallback",
        ),
        manager=ManagerDecision(
            approved=True,
            action_bias="buy",
            confidence_cap=0.7,
            size_multiplier=1.0,
            rationale="Manager approved",
            escalation_flags=[],
            source="fallback",
            fallback_reason="Test fallback",
        ),
        execution=ExecutionDecision(
            approved=True,
            side="buy",
            symbol="TEST",
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=110.0,
            position_size_pct=0.05,
            confidence=0.7,
            rationale="Test",
        ),
        review=ReviewNote(
            summary="Review summary",
            strengths=["x"],
            warnings=[],
            next_checks=["y"],
        ),
    )

    assert artifacts.used_fallback() is True
    assert artifacts.fallback_components() == [
        "coordinator",
        "regime",
        "risk",
        "manager",
    ]
