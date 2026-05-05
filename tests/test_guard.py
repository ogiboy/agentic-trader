from agentic_trader.config import Settings
from agentic_trader.engine.guard import evaluate_execution
from agentic_trader.schemas import (
    ManagerDecision,
    MarketSnapshot,
    RiskPlan,
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


def test_guard_uses_manager_action_bias_hold() -> None:
    """When manager action_bias is 'hold', effective_action should be 'hold'."""
    settings = Settings(min_confidence=0.6, max_position_pct=0.1, min_risk_reward=1.5)
    strategy = StrategyPlan(
        strategy_family="trend_following",
        action="buy",
        timeframe="swing",
        entry_logic="Test.",
        invalidation_logic="Test.",
        confidence=0.75,
        reason_codes=[],
    )
    risk = RiskPlan(
        position_size_pct=0.05,
        stop_loss=95.0,
        take_profit=110.0,
        risk_reward_ratio=2.0,
        max_holding_bars=20,
        notes="Test.",
    )
    manager = ManagerDecision(
        approved=True,
        action_bias="hold",
        confidence_cap=0.75,
        size_multiplier=1.0,
        rationale="Manager said hold.",
    )
    decision = evaluate_execution(settings, _snapshot(), strategy, risk, manager)
    assert decision.approved is False
    assert "no-trade" in decision.rationale.lower() or "hold" in decision.rationale.lower()


def test_guard_uses_manager_action_bias_sell() -> None:
    """When manager action_bias is 'sell', side should be 'sell'."""
    settings = Settings(min_confidence=0.6, max_position_pct=0.1, min_risk_reward=1.5)
    strategy = StrategyPlan(
        strategy_family="trend_following",
        action="buy",
        timeframe="swing",
        entry_logic="Test.",
        invalidation_logic="Test.",
        confidence=0.75,
        reason_codes=[],
    )
    risk = RiskPlan(
        position_size_pct=0.05,
        stop_loss=110.0,
        take_profit=95.0,
        risk_reward_ratio=2.0,
        max_holding_bars=20,
        notes="Test.",
    )
    manager = ManagerDecision(
        approved=True,
        action_bias="sell",
        confidence_cap=0.75,
        size_multiplier=1.0,
        rationale="Manager said sell.",
    )
    snapshot = _snapshot()
    decision = evaluate_execution(settings, snapshot, strategy, risk, manager)
    assert decision.side == "sell"
    assert decision.approved is True


def test_guard_rejects_no_trade_strategy() -> None:
    """Strategy with no_trade family should be rejected."""
    settings = Settings(min_confidence=0.6)
    strategy = StrategyPlan(
        strategy_family="no_trade",
        action="hold",
        timeframe="swing",
        entry_logic="No trade.",
        invalidation_logic="N/A.",
        confidence=0.75,
        reason_codes=[],
    )
    risk = RiskPlan(
        position_size_pct=0.05,
        stop_loss=95.0,
        take_profit=110.0,
        risk_reward_ratio=2.0,
        max_holding_bars=20,
        notes="Test.",
    )
    manager = ManagerDecision(
        approved=True,
        action_bias="buy",
        confidence_cap=0.75,
        size_multiplier=1.0,
        rationale="Test.",
    )
    decision = evaluate_execution(settings, _snapshot(), strategy, risk, manager)
    assert decision.approved is False
    assert "no-trade" in decision.rationale.lower()


def test_guard_rejects_position_size_exceeds_max() -> None:
    """Position size exceeding max should be rejected."""
    settings = Settings(min_confidence=0.6, max_position_pct=0.1)
    strategy = StrategyPlan(
        strategy_family="trend_following",
        action="buy",
        timeframe="swing",
        entry_logic="Test.",
        invalidation_logic="Test.",
        confidence=0.75,
        reason_codes=[],
    )
    risk = RiskPlan(
        position_size_pct=0.15,  # Exceeds max_position_pct of 0.1
        stop_loss=95.0,
        take_profit=110.0,
        risk_reward_ratio=2.0,
        max_holding_bars=20,
        notes="Test.",
    )
    manager = ManagerDecision(
        approved=True,
        action_bias="buy",
        confidence_cap=0.75,
        size_multiplier=1.0,
        rationale="Test.",
    )
    decision = evaluate_execution(settings, _snapshot(), strategy, risk, manager)
    assert decision.approved is False
    assert "exceeds max" in decision.rationale.lower()


def test_guard_rejects_low_risk_reward() -> None:
    """Risk/reward ratio below minimum should be rejected."""
    settings = Settings(min_confidence=0.6, min_risk_reward=2.0)
    strategy = StrategyPlan(
        strategy_family="trend_following",
        action="buy",
        timeframe="swing",
        entry_logic="Test.",
        invalidation_logic="Test.",
        confidence=0.75,
        reason_codes=[],
    )
    risk = RiskPlan(
        position_size_pct=0.05,
        stop_loss=95.0,
        take_profit=100.0,  # Low risk/reward
        risk_reward_ratio=1.0,  # Below minimum
        max_holding_bars=20,
        notes="Test.",
    )
    manager = ManagerDecision(
        approved=True,
        action_bias="buy",
        confidence_cap=0.75,
        size_multiplier=1.0,
        rationale="Test.",
    )
    decision = evaluate_execution(settings, _snapshot(), strategy, risk, manager)
    assert decision.approved is False
    assert "risk/reward" in decision.rationale.lower()


def test_guard_rejects_manager_disapproval() -> None:
    """When manager rejects, trade should be rejected."""
    settings = Settings(min_confidence=0.6)
    strategy = StrategyPlan(
        strategy_family="trend_following",
        action="buy",
        timeframe="swing",
        entry_logic="Test.",
        invalidation_logic="Test.",
        confidence=0.75,
        reason_codes=[],
    )
    risk = RiskPlan(
        position_size_pct=0.05,
        stop_loss=95.0,
        take_profit=110.0,
        risk_reward_ratio=2.0,
        max_holding_bars=20,
        notes="Test.",
    )
    manager = ManagerDecision(
        approved=False,
        action_bias="buy",
        confidence_cap=0.75,
        size_multiplier=1.0,
        rationale="Manager rejected this trade.",
    )
    decision = evaluate_execution(settings, _snapshot(), strategy, risk, manager)
    assert decision.approved is False
    assert "manager rejected" in decision.rationale.lower()


def test_guard_rejects_buy_inconsistent_stops() -> None:
    """Buy setup with inconsistent stop/take-profit should be rejected."""
    settings = Settings(min_confidence=0.6)
    strategy = StrategyPlan(
        strategy_family="trend_following",
        action="buy",
        timeframe="swing",
        entry_logic="Test.",
        invalidation_logic="Test.",
        confidence=0.75,
        reason_codes=[],
    )
    risk = RiskPlan(
        position_size_pct=0.05,
        stop_loss=110.0,  # Above last_close for buy
        take_profit=120.0,
        risk_reward_ratio=2.0,
        max_holding_bars=20,
        notes="Test.",
    )
    manager = ManagerDecision(
        approved=True,
        action_bias="buy",
        confidence_cap=0.75,
        size_multiplier=1.0,
        rationale="Test.",
    )
    snapshot = _snapshot()  # last_close=100.0
    decision = evaluate_execution(settings, snapshot, strategy, risk, manager)
    assert decision.approved is False
    assert "inconsistent" in decision.rationale.lower()


def test_guard_rejects_sell_inconsistent_stops() -> None:
    """Sell setup with inconsistent stop/take-profit should be rejected."""
    settings = Settings(min_confidence=0.6)
    strategy = StrategyPlan(
        strategy_family="trend_following",
        action="sell",
        timeframe="swing",
        entry_logic="Test.",
        invalidation_logic="Test.",
        confidence=0.75,
        reason_codes=[],
    )
    risk = RiskPlan(
        position_size_pct=0.05,
        stop_loss=95.0,  # Below last_close for sell
        take_profit=85.0,
        risk_reward_ratio=2.0,
        max_holding_bars=20,
        notes="Test.",
    )
    manager = ManagerDecision(
        approved=True,
        action_bias="sell",
        confidence_cap=0.75,
        size_multiplier=1.0,
        rationale="Test.",
    )
    snapshot = _snapshot()  # last_close=100.0
    decision = evaluate_execution(settings, snapshot, strategy, risk, manager)
    assert decision.approved is False
    assert "inconsistent" in decision.rationale.lower()
