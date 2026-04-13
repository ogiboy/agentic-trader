from agentic_trader.schemas import (
    ExecutionSide,
    MarketSnapshot,
    PositionExitReason,
    PositionExitDecision,
    PositionPlanSnapshot,
    PositionSnapshot,
)


def _exit_decision(
    *,
    side: ExecutionSide,
    symbol: str,
    reason: PositionExitReason,
    rationale: str,
    exit_price: float,
) -> PositionExitDecision:
    return PositionExitDecision(
        should_exit=True,
        side=side,
        symbol=symbol,
        reason=reason,
        rationale=rationale,
        exit_price=exit_price,
    )


def _long_exit(snapshot: MarketSnapshot, plan: PositionPlanSnapshot) -> PositionExitDecision | None:
    if snapshot.last_close <= plan.stop_loss:
        return _exit_decision(
            side="sell",
            symbol=snapshot.symbol,
            reason="stop_loss",
            rationale="Long position hit the configured stop loss.",
            exit_price=snapshot.last_close,
        )
    if snapshot.last_close >= plan.take_profit:
        return _exit_decision(
            side="sell",
            symbol=snapshot.symbol,
            reason="take_profit",
            rationale="Long position reached the configured take profit.",
            exit_price=snapshot.last_close,
        )
    if plan.holding_bars >= plan.max_holding_bars:
        return _exit_decision(
            side="sell",
            symbol=snapshot.symbol,
            reason="time_exit",
            rationale="Long position exceeded max holding bars.",
            exit_price=snapshot.last_close,
        )
    if snapshot.last_close < snapshot.ema_20 and snapshot.return_5 < 0:
        return _exit_decision(
            side="sell",
            symbol=snapshot.symbol,
            reason="invalidation",
            rationale="Long position invalidated by price losing EMA20 with weakening momentum.",
            exit_price=snapshot.last_close,
        )
    return None


def _short_exit(snapshot: MarketSnapshot, plan: PositionPlanSnapshot) -> PositionExitDecision | None:
    if snapshot.last_close >= plan.stop_loss:
        return _exit_decision(
            side="buy",
            symbol=snapshot.symbol,
            reason="stop_loss",
            rationale="Short position hit the configured stop loss.",
            exit_price=snapshot.last_close,
        )
    if snapshot.last_close <= plan.take_profit:
        return _exit_decision(
            side="buy",
            symbol=snapshot.symbol,
            reason="take_profit",
            rationale="Short position reached the configured take profit.",
            exit_price=snapshot.last_close,
        )
    if plan.holding_bars >= plan.max_holding_bars:
        return _exit_decision(
            side="buy",
            symbol=snapshot.symbol,
            reason="time_exit",
            rationale="Short position exceeded max holding bars.",
            exit_price=snapshot.last_close,
        )
    if snapshot.last_close > snapshot.ema_20 and snapshot.return_5 > 0:
        return _exit_decision(
            side="buy",
            symbol=snapshot.symbol,
            reason="invalidation",
            rationale="Short position invalidated by price reclaiming EMA20 with strengthening momentum.",
            exit_price=snapshot.last_close,
        )
    return None


def evaluate_position_exit(
    snapshot: MarketSnapshot,
    position: PositionSnapshot,
    plan: PositionPlanSnapshot,
) -> PositionExitDecision:
    exit_decision = (
        _long_exit(snapshot, plan) if plan.side == "buy" else _short_exit(snapshot, plan)
    )
    if exit_decision is not None:
        return exit_decision

    return PositionExitDecision(
        should_exit=False,
        side="hold",
        symbol=position.symbol,
        reason="no_exit",
        rationale="No exit condition was triggered.",
        exit_price=snapshot.last_close,
    )
