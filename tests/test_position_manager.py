from agentic_trader.schemas import (
    MarketSnapshot,
    PositionPlanSnapshot,
    PositionSnapshot,
    TradeSide,
)
from agentic_trader.engine.position_manager import (
    _exit_decision,
    _long_exit,
    _short_exit,
    evaluate_position_exit,
)


# Helper functions to create test objects
def make_market_snapshot(
    symbol="AAPL",
    last_close=100.0,
    ema_20=98.0,
    ema_50=97.0,
    atr_14=2.0,
    rsi_14=55.0,
    volatility_20=0.15,
    return_5=0.02,
    return_20=0.05,
    volume_ratio_20=1.1,
    bars_analyzed=20,
    interval="1d",
) -> MarketSnapshot:
    return MarketSnapshot(
        symbol=symbol,
        interval=interval,
        last_close=last_close,
        ema_20=ema_20,
        ema_50=ema_50,
        atr_14=atr_14,
        rsi_14=rsi_14,
        volatility_20=volatility_20,
        return_5=return_5,
        return_20=return_20,
        volume_ratio_20=volume_ratio_20,
        bars_analyzed=bars_analyzed,
    )


def make_position_plan(
    side: TradeSide = "buy",
    stop_loss=95.0,
    take_profit=110.0,
    holding_bars=1,
    max_holding_bars=10,
    entry_price=100.0,
    invalidation_logic="price_below_ema20_with_weakening_momentum",
    updated_at="2025-01-01T00:00:00",
) -> PositionPlanSnapshot:
    return PositionPlanSnapshot(
        symbol="AAPL",
        side=side,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        max_holding_bars=max_holding_bars,
        holding_bars=holding_bars,
        invalidation_logic=invalidation_logic,
        updated_at=updated_at,
    )


def make_position_snapshot(
    symbol="AAPL",
    quantity=10.0,
    average_price=100.0,
    market_price=100.0,
    market_value=1000.0,
    unrealized_pnl=0.0,
) -> PositionSnapshot:
    return PositionSnapshot(
        symbol=symbol,
        quantity=quantity,
        average_price=average_price,
        market_price=market_price,
        market_value=market_value,
        unrealized_pnl=unrealized_pnl,
    )


# Tests for _exit_decision helper
def test_exit_decision_creates_correct_structure():
    decision = _exit_decision(
        side="sell",
        symbol="AAPL",
        reason="stop_loss",
        rationale="Test rationale",
        exit_price=95.0,
    )
    assert decision.should_exit is True
    assert decision.side == "sell"
    assert decision.symbol == "AAPL"
    assert decision.reason == "stop_loss"
    assert decision.rationale == "Test rationale"
    assert decision.exit_price == 95.0


# Tests for _long_exit
def test_long_exit_stop_loss_triggered():
    """Long position should exit when price hits stop loss."""
    snapshot = make_market_snapshot(last_close=94.0, ema_20=98.0, return_5=-0.05)
    plan = make_position_plan(side="buy", stop_loss=95.0)
    decision = _long_exit(snapshot, plan)
    assert decision is not None
    assert decision.should_exit is True
    assert decision.side == "sell"
    assert decision.reason == "stop_loss"
    assert decision.exit_price == 94.0


def test_long_exit_take_profit_triggered():
    """Long position should exit when price reaches take profit."""
    snapshot = make_market_snapshot(last_close=111.0, ema_20=98.0, return_5=0.10)
    plan = make_position_plan(side="buy", take_profit=110.0)
    decision = _long_exit(snapshot, plan)
    assert decision is not None
    assert decision.should_exit is True
    assert decision.side == "sell"
    assert decision.reason == "take_profit"
    assert decision.exit_price == 111.0


def test_long_exit_time_exit_triggered():
    """Long position should exit when holding bars exceed max."""
    snapshot = make_market_snapshot(last_close=100.0, ema_20=98.0, return_5=0.01)
    plan = make_position_plan(side="buy", holding_bars=10, max_holding_bars=10)
    decision = _long_exit(snapshot, plan)
    assert decision is not None
    assert decision.should_exit is True
    assert decision.side == "sell"
    assert decision.reason == "time_exit"
    assert decision.exit_price == 100.0


def test_long_exit_invalidation_triggered():
    """Long position should exit when price below EMA20 with negative momentum."""
    snapshot = make_market_snapshot(last_close=97.0, ema_20=98.0, return_5=-0.02)
    plan = make_position_plan(side="buy")
    decision = _long_exit(snapshot, plan)
    assert decision is not None
    assert decision.should_exit is True
    assert decision.side == "sell"
    assert decision.reason == "invalidation"
    assert decision.exit_price == 97.0


def test_long_exit_no_exit_when_conditions_not_met():
    """Long position should not exit when no conditions are triggered."""
    snapshot = make_market_snapshot(last_close=100.0, ema_20=98.0, return_5=0.01)
    plan = make_position_plan(side="buy", stop_loss=95.0, take_profit=110.0, holding_bars=1, max_holding_bars=10)
    decision = _long_exit(snapshot, plan)
    assert decision is None


# Tests for _short_exit
def test_short_exit_stop_loss_triggered():
    """Short position should exit when price hits stop loss (goes up)."""
    snapshot = make_market_snapshot(last_close=106.0, ema_20=102.0, return_5=0.05)
    plan = make_position_plan(side="sell", stop_loss=105.0)
    decision = _short_exit(snapshot, plan)
    assert decision is not None
    assert decision.should_exit is True
    assert decision.side == "buy"
    assert decision.reason == "stop_loss"
    assert decision.exit_price == 106.0


def test_short_exit_take_profit_triggered():
    """Short position should exit when price reaches take profit (goes down)."""
    snapshot = make_market_snapshot(last_close=94.0, ema_20=102.0, return_5=-0.05)
    plan = make_position_plan(side="sell", take_profit=95.0)
    decision = _short_exit(snapshot, plan)
    assert decision is not None
    assert decision.should_exit is True
    assert decision.side == "buy"
    assert decision.reason == "take_profit"
    assert decision.exit_price == 94.0


def test_short_exit_time_exit_triggered():
    """Short position should exit when holding bars exceed max."""
    snapshot = make_market_snapshot(last_close=100.0, ema_20=102.0, return_5=0.01)
    plan = make_position_plan(side="sell", stop_loss=105.0, take_profit=95.0, holding_bars=10, max_holding_bars=10)
    decision = _short_exit(snapshot, plan)
    assert decision is not None
    assert decision.should_exit is True
    assert decision.side == "buy"
    assert decision.reason == "time_exit"
    assert decision.exit_price == 100.0


def test_short_exit_invalidation_triggered():
    """Short position should exit when price above EMA20 with positive momentum."""
    snapshot = make_market_snapshot(last_close=103.0, ema_20=102.0, return_5=0.02)
    plan = make_position_plan(side="sell", stop_loss=105.0, take_profit=95.0)
    decision = _short_exit(snapshot, plan)
    assert decision is not None
    assert decision.should_exit is True
    assert decision.side == "buy"
    assert decision.reason == "invalidation"
    assert decision.exit_price == 103.0


def test_short_exit_no_exit_when_conditions_not_met():
    """Short position should not exit when no conditions are triggered."""
    snapshot = make_market_snapshot(last_close=100.0, ema_20=102.0, return_5=-0.01)
    plan = make_position_plan(side="sell", stop_loss=105.0, take_profit=95.0, holding_bars=1, max_holding_bars=10)
    decision = _short_exit(snapshot, plan)
    assert decision is None


# Tests for evaluate_position_exit
def test_evaluate_position_exit_long_position_with_exit():
    """Evaluate exit for long position where exit condition is met."""
    snapshot = make_market_snapshot(last_close=94.0, ema_20=98.0, return_5=-0.05)
    position = make_position_snapshot(symbol="AAPL")
    plan = make_position_plan(side="buy", stop_loss=95.0)
    decision = evaluate_position_exit(snapshot, position, plan)
    assert decision.should_exit is True
    assert decision.side == "sell"
    assert decision.symbol == "AAPL"
    assert decision.reason == "stop_loss"


def test_evaluate_position_exit_short_position_with_exit():
    """Evaluate exit for short position where exit condition is met."""
    snapshot = make_market_snapshot(last_close=106.0, ema_20=102.0, return_5=0.05)
    position = make_position_snapshot(symbol="AAPL")
    plan = make_position_plan(side="sell", stop_loss=105.0)
    decision = evaluate_position_exit(snapshot, position, plan)
    assert decision.should_exit is True
    assert decision.side == "buy"
    assert decision.symbol == "AAPL"
    assert decision.reason == "stop_loss"


def test_evaluate_position_exit_long_position_no_exit():
    """Evaluate exit for long position where no exit condition is met."""
    snapshot = make_market_snapshot(last_close=100.0, ema_20=98.0, return_5=0.01)
    position = make_position_snapshot(symbol="AAPL")
    plan = make_position_plan(side="buy", stop_loss=95.0, take_profit=110.0, holding_bars=1, max_holding_bars=10)
    decision = evaluate_position_exit(snapshot, position, plan)
    assert decision.should_exit is False
    assert decision.side == "hold"
    assert decision.symbol == "AAPL"
    assert decision.reason == "no_exit"
    assert decision.exit_price == 100.0


def test_evaluate_position_exit_short_position_no_exit():
    """Evaluate exit for short position where no exit condition is met."""
    snapshot = make_market_snapshot(last_close=100.0, ema_20=102.0, return_5=-0.01)
    position = make_position_snapshot(symbol="AAPL")
    plan = make_position_plan(side="sell", stop_loss=105.0, take_profit=95.0, holding_bars=1, max_holding_bars=10)
    decision = evaluate_position_exit(snapshot, position, plan)
    assert decision.should_exit is False
    assert decision.side == "hold"
    assert decision.symbol == "AAPL"
    assert decision.reason == "no_exit"
    assert decision.exit_price == 100.0


def test_evaluate_position_exit_uses_correct_side_for_long():
    """evaluate_position_exit should use _long_exit for buy side positions."""
    snapshot = make_market_snapshot(last_close=94.0)
    position = make_position_snapshot()
    plan = make_position_plan(side="buy", stop_loss=95.0)
    decision = evaluate_position_exit(snapshot, position, plan)
    # If it used _long_exit, stop loss should trigger
    assert decision.should_exit is True
    assert decision.side == "sell"


def test_evaluate_position_exit_uses_correct_side_for_short():
    """evaluate_position_exit should use _short_exit for sell side positions."""
    snapshot = make_market_snapshot(last_close=106.0)
    position = make_position_snapshot()
    plan = make_position_plan(side="sell", stop_loss=105.0)
    decision = evaluate_position_exit(snapshot, position, plan)
    # If it used _short_exit, stop loss should trigger
    assert decision.should_exit is True
    assert decision.side == "buy"
