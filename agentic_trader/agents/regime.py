from agentic_trader.agents.context import render_agent_context
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import AgentContext, MarketSnapshot, RegimeAssessment


def _fallback_regime(snapshot: MarketSnapshot) -> RegimeAssessment:
    trend_gap = (snapshot.ema_20 - snapshot.ema_50) / snapshot.last_close
    mtf_penalty = 0.1 if snapshot.mtf_alignment == "mixed" else 0.0
    mtf_bonus = min(0.1, snapshot.mtf_confidence * 0.1)

    if snapshot.volatility_20 > 0.08:
        return RegimeAssessment(
            regime="high_volatility",
            direction_bias="flat",
            confidence=0.6,
            reasoning="Fallback regime: volatility is elevated, so trading should stay defensive.",
            key_risks=["high_volatility", "unstable_conditions"],
            source="fallback",
            fallback_reason="LLM unavailable or invalid structured response.",
        )

    if (
        snapshot.last_close > snapshot.ema_20 > snapshot.ema_50
        and snapshot.rsi_14 >= 52
    ):
        return RegimeAssessment(
            regime="trend_up",
            direction_bias="long",
            confidence=max(0.55, min(0.85, 0.72 + mtf_bonus - mtf_penalty)),
            reasoning=(
                "Fallback regime: price is above both trend averages with positive momentum. "
                f"Higher timeframe alignment is {snapshot.mtf_alignment}."
            ),
            key_risks=["trend_exhaustion", "pullback_risk"]
            + (
                ["higher_timeframe_conflict"]
                if snapshot.mtf_alignment == "mixed"
                else []
            ),
            source="fallback",
            fallback_reason="LLM unavailable or invalid structured response.",
        )

    if (
        snapshot.last_close < snapshot.ema_20 < snapshot.ema_50
        and snapshot.rsi_14 <= 48
    ):
        return RegimeAssessment(
            regime="trend_down",
            direction_bias="short",
            confidence=max(0.55, min(0.85, 0.72 + mtf_bonus - mtf_penalty)),
            reasoning=(
                "Fallback regime: price is below both trend averages with negative momentum. "
                f"Higher timeframe alignment is {snapshot.mtf_alignment}."
            ),
            key_risks=["short_squeeze", "news_reversal"]
            + (
                ["higher_timeframe_conflict"]
                if snapshot.mtf_alignment == "mixed"
                else []
            ),
            source="fallback",
            fallback_reason="LLM unavailable or invalid structured response.",
        )

    if abs(trend_gap) < 0.01:
        return RegimeAssessment(
            regime="range",
            direction_bias="flat",
            confidence=0.62,
            reasoning="Fallback regime: moving averages are compressed, suggesting range behavior.",
            key_risks=["false_breakout", "low_edge"],
            source="fallback",
            fallback_reason="LLM unavailable or invalid structured response.",
        )

    return RegimeAssessment(
        regime="breakout_candidate",
        direction_bias="long" if snapshot.return_5 >= 0 else "short",
        confidence=max(0.5, 0.58 - mtf_penalty),
        reasoning=f"Fallback regime: mixed trend signals with expansion potential and {snapshot.mtf_alignment} higher timeframe alignment.",
        key_risks=["mixed_signals", "low_conviction"],
        source="fallback",
        fallback_reason="LLM unavailable or invalid structured response.",
    )


def assess_regime(
    llm: LocalLLM,
    snapshot: MarketSnapshot,
    *,
    allow_fallback: bool,
    context: AgentContext | None = None,
) -> RegimeAssessment:
    system_prompt = (
        "You are a market regime classifier for a systematic trading engine. "
        "Be conservative. Prefer no_trade over low-conviction guesses."
    )
    routed_llm = llm.for_role("regime")
    user_prompt = (
        render_agent_context(
            context,
            task="Classify the current market regime with a conservative bias and prefer no_trade when conviction is weak.",
        )
        if context is not None
        else (
            f"Classify the market for {snapshot.symbol} on interval {snapshot.interval}.\n\nSnapshot:\n{snapshot.model_dump_json(indent=2)}"
        )
    )
    try:
        return routed_llm.complete_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=RegimeAssessment,
        )
    except Exception:
        if not allow_fallback:
            raise
        return _fallback_regime(snapshot)
