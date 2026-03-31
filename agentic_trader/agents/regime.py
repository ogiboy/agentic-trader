from textwrap import dedent

from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import MarketSnapshot, RegimeAssessment


def _fallback_regime(snapshot: MarketSnapshot) -> RegimeAssessment:
    trend_gap = (snapshot.ema_20 - snapshot.ema_50) / snapshot.last_close

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

    if snapshot.last_close > snapshot.ema_20 > snapshot.ema_50 and snapshot.rsi_14 >= 52:
        return RegimeAssessment(
            regime="trend_up",
            direction_bias="long",
            confidence=0.72,
            reasoning="Fallback regime: price is above both trend averages with positive momentum.",
            key_risks=["trend_exhaustion", "pullback_risk"],
            source="fallback",
            fallback_reason="LLM unavailable or invalid structured response.",
        )

    if snapshot.last_close < snapshot.ema_20 < snapshot.ema_50 and snapshot.rsi_14 <= 48:
        return RegimeAssessment(
            regime="trend_down",
            direction_bias="short",
            confidence=0.72,
            reasoning="Fallback regime: price is below both trend averages with negative momentum.",
            key_risks=["short_squeeze", "news_reversal"],
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
        confidence=0.58,
        reasoning="Fallback regime: mixed trend signals with expansion potential.",
        key_risks=["mixed_signals", "low_conviction"],
        source="fallback",
        fallback_reason="LLM unavailable or invalid structured response.",
    )


def assess_regime(
    llm: LocalLLM,
    snapshot: MarketSnapshot,
    *,
    allow_fallback: bool,
) -> RegimeAssessment:
    system_prompt = (
        "You are a market regime classifier for a systematic trading engine. "
        "Be conservative. Prefer no_trade over low-conviction guesses."
    )
    user_prompt = dedent(
        f"""
        Classify the market for {snapshot.symbol} on interval {snapshot.interval}.

        Snapshot:
        - last_close: {snapshot.last_close}
        - ema_20: {snapshot.ema_20}
        - ema_50: {snapshot.ema_50}
        - atr_14: {snapshot.atr_14}
        - rsi_14: {snapshot.rsi_14}
        - volatility_20: {snapshot.volatility_20}
        - return_5: {snapshot.return_5}
        - return_20: {snapshot.return_20}
        - volume_ratio_20: {snapshot.volume_ratio_20}
        - bars_analyzed: {snapshot.bars_analyzed}
        """
    ).strip()
    try:
        return llm.complete_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=RegimeAssessment,
        )
    except Exception:
        if not allow_fallback:
            raise
        return _fallback_regime(snapshot)
