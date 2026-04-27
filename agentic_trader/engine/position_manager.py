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
    """
    Create a PositionExitDecision representing an exit with the provided side, symbol, reason, rationale, and exit price.

    Returns:
        PositionExitDecision: A decision object with `should_exit` set to True and the supplied fields populated.
    """
    return PositionExitDecision(
        should_exit=True,
        side=side,
        symbol=symbol,
        reason=reason,
        rationale=rationale,
        exit_price=exit_price,
    )


def _long_exit(
    snapshot: MarketSnapshot, plan: PositionPlanSnapshot
) -> PositionExitDecision | None:
    """
    Determine whether a long position should be exited based on the provided market snapshot and position plan.

    Checks, in order, for stop-loss, take-profit, time-based exit (holding duration), and invalidation (price below EMA20 with weakening momentum). If any condition is met, returns a PositionExitDecision representing a sell exit at the snapshot's last_close; otherwise returns None.

    Parameters:
        snapshot (MarketSnapshot): Current market data for the position (including last_close, ema_20, return_5, symbol).
        plan (PositionPlanSnapshot): Active position plan (including stop_loss, take_profit, holding_bars, max_holding_bars).

    Returns:
        PositionExitDecision | None: A decision with `side="sell"` and `exit_price` equal to `snapshot.last_close` when an exit condition is triggered, or `None` if no exit is appropriate.
    """
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


def _short_exit(
    snapshot: MarketSnapshot, plan: PositionPlanSnapshot
) -> PositionExitDecision | None:
    """
    Evaluate short-position exit conditions and return a PositionExitDecision for the first triggered rule.

    Checks the following conditions in order and returns a decision when a condition is met:
    1. stop_loss: snapshot.last_close >= plan.stop_loss
    2. take_profit: snapshot.last_close <= plan.take_profit
    3. time_exit: plan.holding_bars >= plan.max_holding_bars
    4. invalidation: snapshot.last_close > snapshot.ema_20 and snapshot.return_5 > 0

    Parameters:
        snapshot (MarketSnapshot): Market state for the position; uses `symbol`, `last_close`, `ema_20`, and `return_5`.
        plan (PositionPlanSnapshot): Position plan; uses `stop_loss`, `take_profit`, `holding_bars`, and `max_holding_bars`.

    Returns:
        PositionExitDecision | None: A decision with `should_exit=True`, `side="buy"`, `symbol` from the snapshot, `exit_price` = snapshot.last_close, and an appropriate `reason`/`rationale` when a condition is triggered; `None` if no exit condition is met.
    """
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
    """
    Determine whether an open position should be exited based on the latest market snapshot and the position plan.

    Parameters:
        snapshot (MarketSnapshot): Latest market values used to evaluate exit conditions (e.g., last_close, ema_20, return_5).
        position (PositionSnapshot): Current position details; used primarily for the returned symbol.
        plan (PositionPlanSnapshot): Exit plan containing side, stop_loss, take_profit, holding_bars, and max_holding_bars.

    Returns:
        PositionExitDecision: Decision describing whether to exit and why. If an exit condition is met for a long position the decision will use side `"sell"`, for a short position `"buy"`. Possible `reason` values include `"stop_loss"`, `"take_profit"`, `"time_exit"`, `"invalidation"`, and `"no_exit"`. When no condition is triggered the decision has `should_exit=False`, `side="hold"`, and `exit_price` set to `snapshot.last_close`.
    """
    exit_decision = (
        _long_exit(snapshot, plan)
        if plan.side == "buy"
        else _short_exit(snapshot, plan)
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
