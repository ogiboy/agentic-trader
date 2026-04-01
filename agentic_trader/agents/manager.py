from textwrap import dedent

from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import ManagerDecision, MarketSnapshot, RegimeAssessment, ResearchCoordinatorBrief, RiskPlan, StrategyPlan


def _fallback_manager(
    snapshot: MarketSnapshot,
    coordinator: ResearchCoordinatorBrief,
    regime: RegimeAssessment,
    strategy: StrategyPlan,
    risk: RiskPlan,
) -> ManagerDecision:
    approved = strategy.action != "hold" and strategy.confidence >= 0.6 and risk.risk_reward_ratio >= 1.5
    action_bias = strategy.action if approved else "hold"
    size_multiplier = 1.0
    flags: list[str] = []

    if coordinator.market_focus == "capital_preservation" or regime.regime == "high_volatility":
        size_multiplier = 0.5
        flags.append("defensive_posture")
    if strategy.confidence < 0.65:
        size_multiplier = min(size_multiplier, 0.75)
        flags.append("moderate_conviction")
    if action_bias == "hold":
        flags.append("manager_no_trade")

    return ManagerDecision(
        approved=approved,
        action_bias=action_bias if action_bias in {"buy", "sell"} else "hold",
        confidence_cap=min(strategy.confidence, regime.confidence),
        size_multiplier=size_multiplier,
        rationale="Fallback manager combined specialist outputs into a guarded execution posture.",
        escalation_flags=flags,
        source="fallback",
        fallback_reason="LLM unavailable or invalid structured response.",
    )


def manage_trade_decision(
    llm: LocalLLM,
    snapshot: MarketSnapshot,
    coordinator: ResearchCoordinatorBrief,
    regime: RegimeAssessment,
    strategy: StrategyPlan,
    risk: RiskPlan,
    *,
    allow_fallback: bool,
) -> ManagerDecision:
    system_prompt = (
        "You are the manager agent for a systematic trading engine. "
        "Combine coordinator, regime, strategy, and risk outputs into a final execution posture. "
        "You may approve, force hold, cap confidence, or reduce size."
    )
    user_prompt = dedent(
        f"""
        Symbol: {snapshot.symbol}

        Snapshot:
        {snapshot.model_dump_json(indent=2)}

        Coordinator:
        {coordinator.model_dump_json(indent=2)}

        Regime:
        {regime.model_dump_json(indent=2)}

        Strategy:
        {strategy.model_dump_json(indent=2)}

        Risk:
        {risk.model_dump_json(indent=2)}
        """
    ).strip()
    try:
        return llm.complete_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=ManagerDecision,
        )
    except Exception:
        if not allow_fallback:
            raise
        return _fallback_manager(snapshot, coordinator, regime, strategy, risk)
