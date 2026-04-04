from agentic_trader.agents.manager import manage_trade_decision
from agentic_trader.config import Settings
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import (
    ManagerDecision,
    MarketSnapshot,
    RegimeAssessment,
    ResearchCoordinatorBrief,
    RiskPlan,
    StrategyPlan,
)


def _snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        symbol="AAPL",
        interval="1d",
        last_close=100.0,
        ema_20=102.0,
        ema_50=98.0,
        atr_14=2.0,
        rsi_14=57.0,
        volatility_20=0.14,
        return_5=0.03,
        return_20=0.08,
        volume_ratio_20=1.1,
        bars_analyzed=160,
    )


def test_manager_finalization_derives_conflicts_and_resolution_notes(monkeypatch) -> None:
    settings = Settings()
    snapshot = _snapshot()
    coordinator = ResearchCoordinatorBrief(
        market_focus="capital_preservation",
        priority_signals=["trend_alignment"],
        caution_flags=[],
        summary="Protect capital while a setup is still present.",
    )
    regime = RegimeAssessment(
        regime="high_volatility",
        direction_bias="long",
        confidence=0.72,
        reasoning="Volatility is elevated even though direction is constructive.",
    )
    strategy = StrategyPlan(
        strategy_family="trend_following",
        action="buy",
        timeframe="swing",
        entry_logic="Buy pullbacks above EMA20.",
        invalidation_logic="Exit on a close below EMA20.",
        confidence=0.78,
    )
    risk = RiskPlan(
        position_size_pct=0.08,
        stop_loss=95.0,
        take_profit=110.0,
        risk_reward_ratio=2.0,
        max_holding_bars=20,
        notes="Baseline risk plan.",
    )

    raw_manager = ManagerDecision(
        approved=True,
        action_bias="buy",
        confidence_cap=0.65,
        size_multiplier=0.5,
        rationale="Let the trade pass, but with smaller size and tighter conviction.",
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
        context=None,
    )

    assert decision.override_applied is True
    conflict_types = {conflict.conflict_type for conflict in decision.conflicts}
    assert {"focus", "confidence", "size"} <= conflict_types
    assert "Manager reduced exposure before execution." in decision.resolution_notes
