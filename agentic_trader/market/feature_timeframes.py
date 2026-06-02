import pandas as pd

from agentic_trader.market.feature_utils import as_float
from agentic_trader.market.technical_indicators import enrich_frame
from agentic_trader.schemas import MTFAlignment


def higher_timeframe_frame(
    frame: pd.DataFrame, *, interval: str
) -> tuple[pd.DataFrame, str]:
    if not isinstance(frame.index, pd.DatetimeIndex):
        return frame.copy(), "same_as_base"

    lower_interval = interval.lower()
    if lower_interval.endswith(("m", "h")):
        rule = "1D"
        higher_timeframe = "1d"
    else:
        rule = "W-FRI"
        higher_timeframe = "1wk"

    resampled = (
        frame.resample(rule)
        .agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )
        .dropna()
    )
    if len(resampled) < 30:
        return frame.copy(), "same_as_base"
    return resampled, higher_timeframe


def mtf_alignment(base_last: pd.Series, higher_last: pd.Series) -> tuple[MTFAlignment, float]:
    base_bullish = bool(base_last["close"] > base_last["ema_20"] > base_last["ema_50"])
    base_bearish = bool(base_last["close"] < base_last["ema_20"] < base_last["ema_50"])
    higher_bullish = bool(
        higher_last["close"] > higher_last["ema_20"] > higher_last["ema_50"]
    )
    higher_bearish = bool(
        higher_last["close"] < higher_last["ema_20"] < higher_last["ema_50"]
    )

    if base_bullish and higher_bullish:
        higher_rsi = as_float(higher_last["rsi_14"])
        confidence = min(1.0, 0.55 + max(0.0, (higher_rsi - 50.0) / 100.0))
        return "bullish", round(confidence, 4)
    if base_bearish and higher_bearish:
        higher_rsi = as_float(higher_last["rsi_14"])
        confidence = min(1.0, 0.55 + max(0.0, (50.0 - higher_rsi) / 100.0))
        return "bearish", round(confidence, 4)
    return "mixed", 0.35


def clean_enriched_frame(frame: pd.DataFrame) -> pd.DataFrame:
    enriched = enrich_frame(frame)
    clean = enriched.dropna()
    if clean.empty:
        raise ValueError("Feature engineering produced no valid rows")
    return clean


def higher_timeframe_last(
    frame: pd.DataFrame,
    *,
    interval: str,
    fallback: pd.Series,
) -> tuple[pd.Series, str]:
    higher_frame, higher_timeframe = higher_timeframe_frame(frame, interval=interval)
    higher_clean = enrich_frame(higher_frame).dropna()
    return (
        higher_clean.iloc[-1] if not higher_clean.empty else fallback,
        higher_timeframe,
    )
