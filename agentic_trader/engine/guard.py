from agentic_trader.config import Settings
from agentic_trader.schemas import ExecutionDecision, ManagerDecision, MarketSnapshot, RiskPlan, StrategyPlan


def evaluate_execution(
    settings: Settings,
    snapshot: MarketSnapshot,
    strategy: StrategyPlan,
    risk: RiskPlan,
    manager: ManagerDecision,
) -> ExecutionDecision:
    approved = True
    reasons: list[str] = []

    side = "hold"
    effective_action = strategy.action
    if manager.action_bias == "hold":
        effective_action = "hold"
    elif manager.action_bias in {"buy", "sell"}:
        effective_action = manager.action_bias

    if effective_action == "buy":
        side = "buy"
    elif effective_action == "sell":
        side = "sell"

    if effective_action == "hold" or strategy.strategy_family == "no_trade":
        approved = False
        reasons.append("Strategy selected no-trade path.")

    if strategy.confidence < settings.min_confidence:
        approved = False
        reasons.append(
            f"Confidence {strategy.confidence:.2f} is below threshold {settings.min_confidence:.2f}."
        )

    if risk.position_size_pct > settings.max_position_pct:
        approved = False
        reasons.append(
            f"Position size {risk.position_size_pct:.2%} exceeds max {settings.max_position_pct:.2%}."
        )

    if risk.risk_reward_ratio < settings.min_risk_reward:
        approved = False
        reasons.append(
            f"Risk/reward {risk.risk_reward_ratio:.2f} is below minimum {settings.min_risk_reward:.2f}."
        )

    if not manager.approved:
        approved = False
        reasons.append(f"Manager rejected the trade: {manager.rationale}")

    if side == "buy" and not (risk.stop_loss < snapshot.last_close < risk.take_profit):
        approved = False
        reasons.append("Buy setup has inconsistent stop or take-profit levels.")

    if side == "sell" and not (risk.take_profit < snapshot.last_close < risk.stop_loss):
        approved = False
        reasons.append("Sell setup has inconsistent stop or take-profit levels.")

    return ExecutionDecision(
        approved=approved,
        side=side,
        symbol=snapshot.symbol,
        entry_price=snapshot.last_close,
        stop_loss=risk.stop_loss,
        take_profit=risk.take_profit,
        position_size_pct=min(risk.position_size_pct * manager.size_multiplier, settings.max_position_pct),
        confidence=min(strategy.confidence, manager.confidence_cap),
        rationale=" ".join(reasons) if reasons else "Execution guard approved the trade.",
    )
