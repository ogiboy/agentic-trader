from textwrap import dedent

from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import MarketSnapshot, RegimeAssessment, RiskPlan, StrategyPlan


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
) -> RiskPlan:
    system_prompt = (
        "You are a risk agent for a paper trading system. "
        "Use smaller sizing when volatility or uncertainty is elevated. "
        "The stop loss and take profit must be concrete numeric price levels."
    )
    user_prompt = dedent(
        f"""
        Symbol: {snapshot.symbol}

        Snapshot:
        {snapshot.model_dump_json(indent=2)}

        Regime:
        {regime.model_dump_json(indent=2)}

        Strategy:
        {strategy.model_dump_json(indent=2)}
        """
    ).strip()
    try:
        return llm.complete_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=RiskPlan,
        )
    except Exception:
        if not allow_fallback:
            raise
        return _fallback_risk(snapshot, strategy)
