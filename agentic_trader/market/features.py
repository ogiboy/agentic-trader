import pandas as pd

from agentic_trader.schemas import MarketSnapshot, MTFAlignment


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Compute the Wilder-style Relative Strength Index (RSI) for a numeric price series.
    
    Uses exponential smoothing with alpha = 1/period to compute average gains and losses (Wilder smoothing).
    Edge-case overrides ensure deterministic values when averages are zero:
    - If average loss == 0 and average gain > 0 → RSI = 100.0
    - If average gain == 0 and average loss > 0 → RSI = 0.0
    - If both averages == 0 → RSI = 50.0
    
    Parameters:
        series (pd.Series): Numeric price series (typically closes) indexed by timestamp or integer index.
        period (int): Lookback period for RSI calculation (default: 14).
    
    Returns:
        pd.Series: RSI values in the range [0.0, 100.0] with the same index as `series`.
    """
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.where(~((avg_loss == 0) & (avg_gain > 0)), 100.0)
    rsi = rsi.where(~((avg_gain == 0) & (avg_loss > 0)), 0.0)
    rsi = rsi.where(~((avg_gain == 0) & (avg_loss == 0)), 50.0)
    return rsi


def _atr(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = frame["close"].shift(1)
    tr_components = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - prev_close).abs(),
            (frame["low"] - prev_close).abs(),
        ],
        axis=1,
    )
    true_range = tr_components.max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False).mean()


def _enrich_frame(frame: pd.DataFrame) -> pd.DataFrame:
    enriched = frame.copy()
    enriched["ema_20"] = enriched["close"].ewm(span=20, adjust=False).mean()
    enriched["ema_50"] = enriched["close"].ewm(span=50, adjust=False).mean()
    enriched["atr_14"] = _atr(enriched, 14)
    enriched["rsi_14"] = _rsi(enriched["close"], 14)
    enriched["returns"] = enriched["close"].pct_change()
    enriched["volatility_20"] = enriched["returns"].rolling(20).std() * (20**0.5)
    enriched["return_5"] = enriched["close"].pct_change(5)
    enriched["return_20"] = enriched["close"].pct_change(20)
    enriched["volume_ratio_20"] = (
        enriched["volume"] / enriched["volume"].rolling(20).mean()
    )
    return enriched


def _higher_timeframe_frame(
    frame: pd.DataFrame, *, interval: str
) -> tuple[pd.DataFrame, str]:
    """
    Resample an OHLCV DataFrame to a higher timeframe when a datetime index and sufficient data are available.
    
    If `frame.index` is not a pandas DatetimeIndex, or if the resampled timeframe contains fewer than 30 rows, the function returns a copy of the input frame and the label "same_as_base". For minute- or hour-based `interval` values (ending with "m" or "h") the function resamples to daily bars (label "1d", rule "1D"); otherwise it resamples to weekly bars ending on Friday (label "1wk", rule "W-FRI"). Resampling aggregates columns as: open = first, high = max, low = min, close = last, volume = sum, and drops rows with missing values.
    
    Parameters:
        frame (pd.DataFrame): OHLCV frame indexed by timestamps (expected columns: "open", "high", "low", "close", "volume").
        interval (str): Lower timeframe label (e.g., "1m", "5m", "1h", "1d") used to decide the higher timeframe.
    
    Returns:
        tuple[pd.DataFrame, str]: A tuple of (resampled_frame, higher_timeframe_label). The label is "1d", "1wk", or "same_as_base".
    """
    if not isinstance(frame.index, pd.DatetimeIndex):
        return frame.copy(), "same_as_base"

    lower_interval = interval.lower()
    if lower_interval.endswith("m") or lower_interval.endswith("h"):
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


def _mtf_alignment(
    base_last: pd.Series, higher_last: pd.Series
) -> tuple[MTFAlignment, float]:
    """
    Determine multi-timeframe trend alignment between a base timeframe row and a higher timeframe row.
    
    Parameters:
        base_last (pd.Series): The most recent enriched base-timeframe row; must contain `close`, `ema_20`, and `ema_50`.
        higher_last (pd.Series): The most recent enriched higher-timeframe row; must contain `close`, `ema_20`, `ema_50`, and `rsi_14`.
    
    Returns:
        tuple[MTFAlignment, float]: A pair where the first element is the alignment — `"bullish"`, `"bearish"`, or `"mixed"` — and the second is a confidence score in [0.0, 1.0]. For aligned bullish/bearish signals the confidence is computed from the higher-timeframe RSI (rounded to 4 decimals); for mixed alignment the confidence is 0.35.
    """
    base_bullish = bool(base_last["close"] > base_last["ema_20"] > base_last["ema_50"])
    base_bearish = bool(base_last["close"] < base_last["ema_20"] < base_last["ema_50"])
    higher_bullish = bool(
        higher_last["close"] > higher_last["ema_20"] > higher_last["ema_50"]
    )
    higher_bearish = bool(
        higher_last["close"] < higher_last["ema_20"] < higher_last["ema_50"]
    )

    if base_bullish and higher_bullish:
        confidence = min(
            1.0, 0.55 + max(0.0, (float(higher_last["rsi_14"]) - 50.0) / 100.0)
        )
        return "bullish", round(confidence, 4)
    if base_bearish and higher_bearish:
        confidence = min(
            1.0, 0.55 + max(0.0, (50.0 - float(higher_last["rsi_14"])) / 100.0)
        )
        return "bearish", round(confidence, 4)
    return "mixed", 0.35


def build_snapshot(
    frame: pd.DataFrame, *, symbol: str, interval: str
) -> MarketSnapshot:
    if len(frame) < 60:
        raise ValueError("At least 60 bars are required to build the market snapshot")

    enriched = _enrich_frame(frame)

    clean = enriched.dropna()
    if clean.empty:
        raise ValueError("Feature engineering produced no valid rows")

    last = clean.iloc[-1]
    higher_frame, higher_timeframe = _higher_timeframe_frame(frame, interval=interval)
    higher_enriched = _enrich_frame(higher_frame)
    higher_clean = higher_enriched.dropna()
    higher_last = higher_clean.iloc[-1] if not higher_clean.empty else last
    mtf_alignment, mtf_confidence = _mtf_alignment(last, higher_last)

    return MarketSnapshot(
        symbol=symbol,
        interval=interval,
        last_close=float(last["close"]),
        ema_20=float(last["ema_20"]),
        ema_50=float(last["ema_50"]),
        atr_14=float(last["atr_14"]),
        rsi_14=float(last["rsi_14"]),
        volatility_20=float(last["volatility_20"]),
        return_5=float(last["return_5"]),
        return_20=float(last["return_20"]),
        volume_ratio_20=float(last["volume_ratio_20"]),
        higher_timeframe=higher_timeframe,
        htf_last_close=float(higher_last["close"]),
        htf_ema_20=float(higher_last["ema_20"]),
        htf_ema_50=float(higher_last["ema_50"]),
        htf_rsi_14=float(higher_last["rsi_14"]),
        htf_return_5=float(higher_last["return_5"]),
        mtf_alignment=mtf_alignment,
        mtf_confidence=mtf_confidence,
        bars_analyzed=int(len(enriched)),
    )
