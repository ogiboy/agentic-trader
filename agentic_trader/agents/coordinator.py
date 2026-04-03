from agentic_trader.agents.context import render_agent_context
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import AgentContext, MarketSnapshot, ResearchCoordinatorBrief


def _fallback_coordinator(snapshot: MarketSnapshot) -> ResearchCoordinatorBrief:
    if snapshot.volatility_20 > 0.08:
        return ResearchCoordinatorBrief(
            market_focus="capital_preservation",
            priority_signals=["volatility_control", "risk_reduction"],
            caution_flags=["high_volatility", "unstable_conditions"],
            summary="Fallback coordinator: market is unstable, prioritize defense and capital preservation.",
            source="fallback",
            fallback_reason="LLM unavailable or invalid structured response.",
        )
    if snapshot.last_close > snapshot.ema_20 > snapshot.ema_50:
        return ResearchCoordinatorBrief(
            market_focus="trend_following",
            priority_signals=["trend_alignment", "momentum_confirmation"],
            caution_flags=["trend_exhaustion"],
            summary="Fallback coordinator: trend-following setups deserve priority.",
            source="fallback",
            fallback_reason="LLM unavailable or invalid structured response.",
        )
    if snapshot.last_close < snapshot.ema_20 < snapshot.ema_50:
        return ResearchCoordinatorBrief(
            market_focus="trend_following",
            priority_signals=["downtrend_alignment", "negative_momentum"],
            caution_flags=["short_squeeze"],
            summary="Fallback coordinator: short-biased trend setups deserve priority.",
            source="fallback",
            fallback_reason="LLM unavailable or invalid structured response.",
        )
    return ResearchCoordinatorBrief(
        market_focus="no_trade",
        priority_signals=["wait_for_clarity"],
        caution_flags=["mixed_signals", "low_conviction"],
        summary="Fallback coordinator: conditions are mixed, so selectivity should stay high.",
        source="fallback",
        fallback_reason="LLM unavailable or invalid structured response.",
    )


def coordinate_research(
    llm: LocalLLM,
    snapshot: MarketSnapshot,
    *,
    allow_fallback: bool,
    context: AgentContext | None = None,
) -> ResearchCoordinatorBrief:
    system_prompt = (
        "You are the research coordinator for a systematic trading engine. "
        "Set the focus for downstream specialists and highlight caution flags."
    )
    routed_llm = llm.for_role("coordinator")
    user_prompt = render_agent_context(
        context,
        task="Set the downstream research focus, priority signals, and caution flags for this cycle.",
    ) if context is not None else (
        f"Symbol: {snapshot.symbol}\nInterval: {snapshot.interval}\n\nMarket snapshot:\n{snapshot.model_dump_json(indent=2)}"
    )
    try:
        return routed_llm.complete_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=ResearchCoordinatorBrief,
        )
    except Exception:
        if not allow_fallback:
            raise
        return _fallback_coordinator(snapshot)
