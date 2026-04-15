import re

import pandas as pd

from agentic_trader.schemas import (
    MarketContextHorizon,
    MarketContextPack,
    MarketSnapshot,
    MTFAlignment,
    TrendVote,
)

MIN_REQUIRED_BARS = 60
CONTEXT_HORIZONS = (5, 20, 60, 120, 180)
_LOOKBACK_RE = re.compile(r"^(?P<count>\d+)(?P<unit>d|wk|mo|y)$", re.IGNORECASE)
_INTERVAL_RE = re.compile(r"^(?P<count>\d+)(?P<unit>m|h|d|wk)$", re.IGNORECASE)


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


def _round_float(value: float | None, digits: int = 6) -> float | None:
    """Round finite values while preserving missing context-pack metrics."""
    if value is None or pd.isna(value):
        return None
    return round(float(value), digits)


def _index_label(value: object) -> str | None:
    """Render a frame index value for persisted context-pack window boundaries."""
    if value is None:
        return None
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return str(isoformat())
    return str(value)


def _lookback_days(lookback: str | None) -> int | None:
    """Convert yfinance-style lookback strings into approximate calendar days."""
    if not lookback:
        return None
    match = _LOOKBACK_RE.match(lookback.strip())
    if match is None:
        return None
    count = int(match.group("count"))
    unit = match.group("unit").lower()
    if unit == "d":
        return count
    if unit == "wk":
        return count * 7
    if unit == "mo":
        return count * 30
    if unit == "y":
        return count * 365
    return None


def _estimate_expected_bars(
    *, lookback: str | None, interval: str
) -> tuple[int | None, str]:
    """Estimate expected bars and describe the uncertainty behind that estimate."""
    days = _lookback_days(lookback)
    interval_match = _INTERVAL_RE.match(interval.strip())
    if days is None or interval_match is None:
        return None, "unknown; provider-specific lookback or interval"

    count = int(interval_match.group("count"))
    unit = interval_match.group("unit").lower()
    trading_days = max(1.0, days * (5.0 / 7.0))
    if unit == "d":
        return max(1, int(trading_days / max(count, 1))), "business-day approximation"
    if unit == "wk":
        return max(1, int(days / (7 * max(count, 1)))), "calendar-week approximation"
    if unit == "h":
        bars_per_day = 6.5 / max(count, 1)
        return (
            max(1, int(trading_days * bars_per_day)),
            "exchange-session intraday approximation; holidays and provider limits may reduce bars",
        )
    minutes = max(count, 1)
    bars_per_day = 390 / minutes
    return (
        max(1, int(trading_days * bars_per_day)),
        "exchange-session minute approximation; holidays and provider limits may reduce bars",
    )


def _trend_vote(last: pd.Series, *, enough_data: bool) -> TrendVote:
    """Classify a horizon trend using the latest close/EMA alignment."""
    if not enough_data:
        return "insufficient"
    close = float(last["close"])
    ema_20 = float(last["ema_20"])
    ema_50 = float(last["ema_50"])
    if close > ema_20 > ema_50:
        return "bullish"
    if close < ema_20 < ema_50:
        return "bearish"
    return "mixed"


def _max_drawdown_pct(values: pd.Series) -> float | None:
    """Return the worst peak-to-trough drawdown for a close-price window."""
    if len(values) < 2:
        return None
    running_peak = values.cummax()
    drawdowns = (values / running_peak.replace(0, pd.NA)) - 1.0
    minimum = drawdowns.min()
    if pd.isna(minimum):
        return None
    return float(minimum)


def _horizon_context(
    clean: pd.DataFrame, *, horizon_bars: int, last: pd.Series
) -> MarketContextHorizon:
    """Build one multi-horizon summary row for the Market Context Pack."""
    close = clean["close"].astype(float)
    returns = clean["returns"].astype(float)
    high = clean["high"].astype(float)
    low = clean["low"].astype(float)
    available_bars = max(0, min(horizon_bars, len(clean) - 1))
    enough_data = len(clean) > horizon_bars
    current_close = float(last["close"])
    horizon_return = None
    if enough_data:
        start_close = float(close.iloc[-(horizon_bars + 1)])
        if start_close != 0:
            horizon_return = (current_close / start_close) - 1.0

    close_window = close.tail(max(available_bars, 1))
    high_window = high.tail(max(available_bars, 1))
    low_window = low.tail(max(available_bars, 1))
    support = float(low_window.min()) if not low_window.empty else None
    resistance = float(high_window.max()) if not high_window.empty else None
    range_position = None
    if support is not None and resistance is not None and resistance > support:
        range_position = (current_close - support) / (resistance - support)
        range_position = max(0.0, min(1.0, range_position))

    volatility = None
    return_window = returns.tail(max(available_bars, 1)).dropna()
    if len(return_window) >= 2:
        volatility = float(return_window.std() * (available_bars**0.5))

    atr_pct = None
    if current_close != 0:
        atr_pct = float(last["atr_14"]) / current_close

    return MarketContextHorizon(
        horizon_bars=horizon_bars,
        available_bars=available_bars,
        return_pct=_round_float(horizon_return),
        volatility_pct=_round_float(volatility),
        max_drawdown_pct=_round_float(_max_drawdown_pct(close_window)),
        trend_vote=_trend_vote(last, enough_data=enough_data),
        support=_round_float(support),
        resistance=_round_float(resistance),
        range_position=_round_float(range_position),
        atr_pct=_round_float(atr_pct),
        volume_ratio=_round_float(float(last["volume_ratio_20"])),
    )


def _build_context_summary(
    *,
    symbol: str,
    bars_analyzed: int,
    coverage_ratio: float | None,
    horizons: list[MarketContextHorizon],
) -> str:
    """Render a compact operator-facing summary of the market context pack."""
    horizon_votes = ", ".join(
        f"{item.horizon_bars}b={item.trend_vote}" for item in horizons[:4]
    )
    coverage = f"{coverage_ratio:.0%}" if coverage_ratio is not None else "unknown"
    return f"{symbol}: {bars_analyzed} bars analyzed, coverage={coverage}, trend votes: {horizon_votes}"


def _build_context_pack(
    frame: pd.DataFrame,
    clean: pd.DataFrame,
    *,
    symbol: str,
    interval: str,
    lookback: str | None,
    higher_timeframe: str,
    last: pd.Series,
) -> MarketContextPack:
    """Create the persisted, operator-verifiable context derived from the full lookback window."""
    expected_bars, interval_semantics = _estimate_expected_bars(
        lookback=lookback, interval=interval
    )
    bars_analyzed = int(len(frame))
    coverage_ratio = (
        min(1.0, bars_analyzed / expected_bars)
        if expected_bars and expected_bars > 0
        else None
    )
    horizons = [
        _horizon_context(clean, horizon_bars=horizon, last=last)
        for horizon in CONTEXT_HORIZONS
    ]
    data_quality_flags: list[str] = []
    anomaly_flags: list[str] = []
    if bars_analyzed >= MIN_REQUIRED_BARS:
        data_quality_flags.append("minimum_bar_requirement_met")
    if coverage_ratio is not None:
        if coverage_ratio < 0.6:
            data_quality_flags.append("low_lookback_coverage")
        elif coverage_ratio < 0.85:
            data_quality_flags.append("partial_lookback_coverage")
        else:
            data_quality_flags.append("lookback_coverage_ok")
    if higher_timeframe == "same_as_base":
        data_quality_flags.append("higher_timeframe_fallback")
    if abs(float(last["return_5"])) >= 0.08:
        anomaly_flags.append("large_5_bar_move")
    if float(last["volume_ratio_20"]) >= 2.5:
        anomaly_flags.append("volume_spike")
    if float(last["volatility_20"]) >= 0.12:
        anomaly_flags.append("high_recent_volatility")

    pack = MarketContextPack(
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        interval_semantics=interval_semantics,
        window_start=_index_label(frame.index[0]) if len(frame.index) else None,
        window_end=_index_label(frame.index[-1]) if len(frame.index) else None,
        bars_required=MIN_REQUIRED_BARS,
        bars_expected=expected_bars,
        bars_analyzed=bars_analyzed,
        coverage_ratio=_round_float(coverage_ratio, digits=4),
        higher_timeframe=higher_timeframe,
        higher_timeframe_used=higher_timeframe != "same_as_base",
        horizons=horizons,
        data_quality_flags=data_quality_flags,
        anomaly_flags=anomaly_flags,
    )
    pack.summary = _build_context_summary(
        symbol=symbol,
        bars_analyzed=bars_analyzed,
        coverage_ratio=pack.coverage_ratio,
        horizons=horizons,
    )
    return pack


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
    frame: pd.DataFrame, *, symbol: str, interval: str, lookback: str | None = None
) -> MarketSnapshot:
    if len(frame) < MIN_REQUIRED_BARS:
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
    context_pack = _build_context_pack(
        frame,
        clean,
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        higher_timeframe=higher_timeframe,
        last=last,
    )

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
        context_pack=context_pack,
    )
