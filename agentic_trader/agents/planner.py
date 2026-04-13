from agentic_trader.agents.context import render_agent_context
from agentic_trader.agents.constants import LLM_FALLBACK_REASON
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import (
    AgentContext,
    MarketSnapshot,
    RegimeAssessment,
    StrategyPlan,
)


def _fallback_plan(snapshot: MarketSnapshot, regime: RegimeAssessment) -> StrategyPlan:
    if regime.regime == "trend_up":
        return StrategyPlan(
            strategy_family="trend_following",
            action="buy",
            timeframe="swing",
            entry_logic="Buy only while price remains above EMA20 and EMA50.",
            invalidation_logic="Exit if price closes below EMA20 and momentum weakens.",
            confidence=max(0.6, regime.confidence),
            reason_codes=["fallback", "trend_alignment", "positive_momentum"],
            source="fallback",
            fallback_reason=LLM_FALLBACK_REASON,
        )

    if regime.regime == "trend_down":
        return StrategyPlan(
            strategy_family="trend_following",
            action="sell",
            timeframe="swing",
            entry_logic="Sell only while price remains below EMA20 and EMA50.",
            invalidation_logic="Exit if price closes back above EMA20.",
            confidence=max(0.6, regime.confidence),
            reason_codes=["fallback", "trend_alignment", "negative_momentum"],
            source="fallback",
            fallback_reason=LLM_FALLBACK_REASON,
        )

    if regime.regime == "breakout_candidate" and snapshot.volume_ratio_20 > 1.1:
        action = "buy" if regime.direction_bias == "long" else "sell"
        return StrategyPlan(
            strategy_family="breakout",
            action=action,
            timeframe="swing",
            entry_logic="Participate only on continuation with above-average volume.",
            invalidation_logic="Abort if breakout fails and price snaps back into prior range.",
            confidence=0.61,
            reason_codes=["fallback", "breakout_candidate", "volume_confirmation"],
            source="fallback",
            fallback_reason=LLM_FALLBACK_REASON,
        )

    return StrategyPlan(
        strategy_family="no_trade",
        action="hold",
        timeframe="flat",
        entry_logic="No valid entry.",
        invalidation_logic="Wait for clearer alignment.",
        confidence=min(0.55, regime.confidence),
        reason_codes=["fallback", "no_trade"],
        source="fallback",
        fallback_reason=LLM_FALLBACK_REASON,
    )


def plan_trade(
    llm: LocalLLM,
    snapshot: MarketSnapshot,
    regime: RegimeAssessment,
    *,
    allow_fallback: bool,
    context: AgentContext | None = None,
) -> StrategyPlan:
    system_prompt = (
        "You are a strategy selection agent for a systematic trading engine. "
        "Select the strategy family that best fits the regime. "
        "If conviction is weak, choose no_trade and action hold."
    )
    routed_llm = llm.for_role("strategy")
    user_prompt = (
        render_agent_context(
            context,
            task="Choose the best strategy family and directional action for this cycle. If conviction is weak, choose no_trade and hold.",
        )
        if context is not None
        else (
            f"Symbol: {snapshot.symbol}\nInterval: {snapshot.interval}\n\nMarket snapshot:\n{snapshot.model_dump_json(indent=2)}\n\nRegime assessment:\n{regime.model_dump_json(indent=2)}"
        )
    )
    try:
        return routed_llm.complete_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=StrategyPlan,
        )
    except Exception:
        if not allow_fallback:
            raise
        return _fallback_plan(snapshot, regime)
