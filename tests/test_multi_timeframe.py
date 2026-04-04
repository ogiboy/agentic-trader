from agentic_trader.agents.coordinator import _fallback_coordinator
from agentic_trader.agents.regime import _fallback_regime
from agentic_trader.schemas import MarketSnapshot


def _snapshot(**overrides: object) -> MarketSnapshot:
    payload: dict[str, object] = {
        "symbol": "TEST",
        "interval": "1d",
        "last_close": 100.0,
        "ema_20": 102.0,
        "ema_50": 98.0,
        "atr_14": 2.0,
        "rsi_14": 58.0,
        "volatility_20": 0.04,
        "return_5": 0.03,
        "return_20": 0.08,
        "volume_ratio_20": 1.2,
        "higher_timeframe": "1wk",
        "htf_last_close": 130.0,
        "htf_ema_20": 125.0,
        "htf_ema_50": 120.0,
        "htf_rsi_14": 63.0,
        "htf_return_5": 0.06,
        "mtf_alignment": "bullish",
        "mtf_confidence": 0.7,
        "bars_analyzed": 180,
    }
    payload.update(overrides)
    return MarketSnapshot.model_validate(payload)


def test_fallback_coordinator_prefers_defense_when_timeframes_conflict() -> None:
    brief = _fallback_coordinator(_snapshot(mtf_alignment="mixed", mtf_confidence=0.35))

    assert brief.market_focus == "capital_preservation"
    assert "multi_timeframe_conflict" in brief.caution_flags
    assert "higher_timeframe_confirmation" in brief.priority_signals


def test_fallback_regime_rewards_aligned_higher_timeframe() -> None:
    aligned = _fallback_regime(
        _snapshot(
            last_close=105.0,
            ema_20=102.0,
            ema_50=98.0,
            rsi_14=58.0,
            mtf_alignment="bullish",
            mtf_confidence=0.9,
        )
    )
    mixed = _fallback_regime(
        _snapshot(
            last_close=105.0,
            ema_20=102.0,
            ema_50=98.0,
            rsi_14=58.0,
            mtf_alignment="mixed",
            mtf_confidence=0.35,
        )
    )

    assert aligned.regime == "trend_up"
    assert mixed.regime == "trend_up"
    assert aligned.confidence > mixed.confidence
    assert "higher_timeframe_conflict" in mixed.key_risks
