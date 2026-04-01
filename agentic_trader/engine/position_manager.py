from agentic_trader.schemas import MarketSnapshot, PositionExitDecision, PositionPlanSnapshot, PositionSnapshot


def evaluate_position_exit(
    snapshot: MarketSnapshot,
    position: PositionSnapshot,
    plan: PositionPlanSnapshot,
) -> PositionExitDecision:
    if plan.side == "buy":
        if snapshot.last_close <= plan.stop_loss:
            return PositionExitDecision(
                should_exit=True,
                side="sell",
                symbol=snapshot.symbol,
                reason="stop_loss",
                rationale="Long position hit the configured stop loss.",
                exit_price=snapshot.last_close,
            )
        if snapshot.last_close >= plan.take_profit:
            return PositionExitDecision(
                should_exit=True,
                side="sell",
                symbol=snapshot.symbol,
                reason="take_profit",
                rationale="Long position reached the configured take profit.",
                exit_price=snapshot.last_close,
            )
        if plan.holding_bars >= plan.max_holding_bars:
            return PositionExitDecision(
                should_exit=True,
                side="sell",
                symbol=snapshot.symbol,
                reason="time_exit",
                rationale="Long position exceeded max holding bars.",
                exit_price=snapshot.last_close,
            )
        if snapshot.last_close < snapshot.ema_20 and snapshot.return_5 < 0:
            return PositionExitDecision(
                should_exit=True,
                side="sell",
                symbol=snapshot.symbol,
                reason="invalidation",
                rationale="Long position invalidated by price losing EMA20 with weakening momentum.",
                exit_price=snapshot.last_close,
            )
    else:
        if snapshot.last_close >= plan.stop_loss:
            return PositionExitDecision(
                should_exit=True,
                side="buy",
                symbol=snapshot.symbol,
                reason="stop_loss",
                rationale="Short position hit the configured stop loss.",
                exit_price=snapshot.last_close,
            )
        if snapshot.last_close <= plan.take_profit:
            return PositionExitDecision(
                should_exit=True,
                side="buy",
                symbol=snapshot.symbol,
                reason="take_profit",
                rationale="Short position reached the configured take profit.",
                exit_price=snapshot.last_close,
            )
        if plan.holding_bars >= plan.max_holding_bars:
            return PositionExitDecision(
                should_exit=True,
                side="buy",
                symbol=snapshot.symbol,
                reason="time_exit",
                rationale="Short position exceeded max holding bars.",
                exit_price=snapshot.last_close,
            )
        if snapshot.last_close > snapshot.ema_20 and snapshot.return_5 > 0:
            return PositionExitDecision(
                should_exit=True,
                side="buy",
                symbol=snapshot.symbol,
                reason="invalidation",
                rationale="Short position invalidated by price reclaiming EMA20 with strengthening momentum.",
                exit_price=snapshot.last_close,
            )

    return PositionExitDecision(
        should_exit=False,
        side="hold",
        symbol=position.symbol,
        reason="no_exit",
        rationale="No exit condition was triggered.",
        exit_price=snapshot.last_close,
    )
