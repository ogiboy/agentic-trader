from agentic_trader.config import Settings
from agentic_trader.engine.guard import evaluate_execution
from agentic_trader.schemas import ManagerDecision, MarketSnapshot, RiskPlan, StrategyPlan


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


def test_guard_rejects_low_confidence_trade() -> None:
    settings = Settings(min_confidence=0.6)
    strategy = StrategyPlan(
        strategy_family="trend_following",
        action="buy",
        timeframe="swing",
        entry_logic="Buy a pullback into EMA20.",
        invalidation_logic="Trend breaks.",
        confidence=0.4,
        reason_codes=["trend_alignment"],
    )
    risk = RiskPlan(
        position_size_pct=0.05,
        stop_loss=95.0,
        take_profit=110.0,
        risk_reward_ratio=2.0,
        max_holding_bars=20,
        notes="Tight risk.",
    )

    manager = ManagerDecision(
        approved=True,
        action_bias="buy",
        confidence_cap=0.4,
        size_multiplier=1.0,
        rationale="Manager allowed test trade.",
    )
    decision = evaluate_execution(settings, _snapshot(), strategy, risk, manager)
    assert decision.approved is False


def test_guard_approves_consistent_trade() -> None:
    settings = Settings(min_confidence=0.6, max_position_pct=0.1, min_risk_reward=1.5)
    strategy = StrategyPlan(
        strategy_family="trend_following",
        action="buy",
        timeframe="swing",
        entry_logic="Buy a pullback into EMA20.",
        invalidation_logic="Trend breaks.",
        confidence=0.75,
        reason_codes=["trend_alignment", "momentum"],
    )
    risk = RiskPlan(
        position_size_pct=0.05,
        stop_loss=95.0,
        take_profit=110.0,
        risk_reward_ratio=2.0,
        max_holding_bars=20,
        notes="Tight risk.",
    )

    manager = ManagerDecision(
        approved=True,
        action_bias="buy",
        confidence_cap=0.75,
        size_multiplier=1.0,
        rationale="Manager allowed test trade.",
    )
    decision = evaluate_execution(settings, _snapshot(), strategy, risk, manager)
    assert decision.approved is True
