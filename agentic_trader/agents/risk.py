from agentic_trader.agents.context import render_agent_context
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import (
    AgentContext,
    MarketSnapshot,
    RegimeAssessment,
    RiskPlan,
    StrategyPlan,
)


def _fallback_risk(snapshot: MarketSnapshot, strategy: StrategyPlan) -> RiskPlan:
    atr = max(snapshot.atr_14, snapshot.last_close * 0.01)

    if strategy.action == "buy":
        stop = snapshot.last_close - (1.5 * atr)
        take_profit = snapshot.last_close + (3.0 * atr)
        return RiskPlan(
            position_size_pct=min(0.08, max(0.02, strategy.confidence * 0.08)),
            stop_loss=round(stop, 4),
            take_profit=round(take_profit, 4),
            risk_reward_ratio=2.0,
            max_holding_bars=20,
            notes="Fallback risk model for long setup.",
            source="fallback",
            fallback_reason="LLM unavailable or invalid structured response.",
        )

    if strategy.action == "sell":
        stop = snapshot.last_close + (1.5 * atr)
        take_profit = snapshot.last_close - (3.0 * atr)
        return RiskPlan(
            position_size_pct=min(0.08, max(0.02, strategy.confidence * 0.08)),
            stop_loss=round(stop, 4),
            take_profit=round(take_profit, 4),
            risk_reward_ratio=2.0,
            max_holding_bars=20,
            notes="Fallback risk model for short setup.",
            source="fallback",
            fallback_reason="LLM unavailable or invalid structured response.",
        )

    return RiskPlan(
        position_size_pct=0.01,
        stop_loss=round(snapshot.last_close - atr, 4),
        take_profit=round(snapshot.last_close + atr, 4),
        risk_reward_ratio=1.0,
        max_holding_bars=5,
        notes="Fallback no-trade risk plan.",
        source="fallback",
        fallback_reason="LLM unavailable or invalid structured response.",
    )


def build_risk_plan(
    llm: LocalLLM,
    snapshot: MarketSnapshot,
    regime: RegimeAssessment,
    strategy: StrategyPlan,
    *,
    allow_fallback: bool,
    context: AgentContext | None = None,
) -> RiskPlan:
    system_prompt = (
        "You are a risk agent for a paper trading system. "
        "Use smaller sizing when volatility or uncertainty is elevated. "
        "The stop loss and take profit must be concrete numeric price levels."
    )
    routed_llm = llm.for_role("risk")
    user_prompt = (
        render_agent_context(
            context,
            task="Set position sizing, stop loss, take profit, and holding horizon with smaller sizing when volatility or uncertainty is elevated.",
        )
        if context is not None
        else (
            f"Symbol: {snapshot.symbol}\n\nSnapshot:\n{snapshot.model_dump_json(indent=2)}\n\nRegime:\n{regime.model_dump_json(indent=2)}\n\nStrategy:\n{strategy.model_dump_json(indent=2)}"
        )
    )
    try:
        return routed_llm.complete_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=RiskPlan,
        )
    except Exception:
        if not allow_fallback:
            raise
        return _fallback_risk(snapshot, strategy)
