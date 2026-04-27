import re
from typing import cast

import pandas as pd

from agentic_trader.schemas import (
    MarketContextHorizon,
    MarketContextPack,
    MarketSnapshot,
    MTFAlignment,
    TrendVote,
)

MIN_REQUIRED_BARS = 60
MIN_LOOKBACK_COVERAGE_RATIO = 0.6
PARTIAL_LOOKBACK_COVERAGE_RATIO = 0.85
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
    rsi = cast(pd.Series, 100 - (100 / (1 + rs)))
    rsi = rsi.where(~((avg_loss == 0) & (avg_gain > 0)), 100.0)
    rsi = rsi.where(~((avg_gain == 0) & (avg_loss > 0)), 0.0)
    rsi = rsi.where(~((avg_gain == 0) & (avg_loss == 0)), 50.0)
    return rsi


def _atr(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Compute the Wilder-style Average True Range (ATR) from an OHLC frame.
    
    Parameters:
        frame (pd.DataFrame): DataFrame containing at least `high`, `low`, and `close` columns indexed by time.
        period (int): Lookback period used for Wilder smoothing (default 14).
    
    Returns:
        pd.Series: ATR values aligned to the input frame's index, computed with Wilder smoothing (EWMA alpha = 1/period).
    """
    high = cast(pd.Series, frame["high"])
    low = cast(pd.Series, frame["low"])
    close = cast(pd.Series, frame["close"])
    prev_close = close.shift(1)
    tr_components = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    )
    true_range = cast(pd.Series, tr_components.max(axis=1))
    return cast(pd.Series, true_range.ewm(alpha=1 / period, adjust=False).mean())


def _round_float(value: float | None, digits: int = 6) -> float | None:
    """
    Round a float to a specified number of decimal places, preserving None/NaN as None.
    
    Parameters:
        value (float | None): The numeric value to round; returns None if this is None or NaN.
        digits (int): Number of decimal places to keep (default 6).
    
    Returns:
        float | None: The rounded value, or None when input was None or NaN.
    """
    if value is None or pd.isna(value):
        return None
    return round(float(value), digits)


def _as_float(value: object) -> float:
    """
    Convert an input to a floating-point numeric value.
    
    Parameters:
        value (object): The input to convert; may be any object accepted by Python's float() constructor.
    
    Returns:
        float_value (float): The numeric floating-point representation of `value`.
    
    Raises:
        ValueError: If `value` cannot be converted to a float.
        TypeError: If `value` is of a type not supported by float().
    """
    return float(cast(float, value))


def _index_label(value: object) -> str | None:
    """
    Format an index value for use as a persisted context-pack window boundary label.
    
    If `value` is a datetime-like object, returns its ISO 8601 representation as a string; otherwise returns `str(value)`. Returns `None` when `value` is `None`.
    
    Parameters:
        value (object): The index value to format; may be a datetime-like object.
    
    Returns:
        str | None: The formatted label string or `None` if `value` is `None`.
    """
    if value is None:
        return None
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return str(isoformat())
    return str(value)


def _lookback_days(lookback: str | None) -> int | None:
    """
    Parse a yfinance-style lookback string and return its approximate length in calendar days.
    
    Parameters:
        lookback (str | None): Lookback in the form "<count><unit>" where unit is one of:
            - "d"  for days
            - "wk" for weeks (7 days)
            - "mo" for months (30 days)
            - "y"  for years (365 days)
            Whitespace is ignored. If falsy or not matching the pattern, the function returns None.
    
    Returns:
        days (int | None): Approximate number of calendar days represented by `lookback`, or
        `None` if `lookback` is falsy or cannot be parsed.
    """
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
    """
    Estimate the approximate number of bars covered by a given lookback and interval, and provide a short description of the estimate's uncertainty.
    
    Parameters:
        lookback (str | None): Lookback string like "30d", "12wk", "3mo", "1y" (or None). If falsy or unparseable, the estimate is unknown.
        interval (str): Interval string like "1m", "5m", "1h", "1d", "1wk".
    
    Returns:
        expected_bars (int | None): Approximate expected number of bars for the provided lookback and interval, or `None` if the lookback or interval cannot be interpreted.
        uncertainty_text (str): Human-readable note describing the approximation method and any caveats (e.g., business-day vs. calendar approximations, session/holiday/provider limits).
    """
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
    """
    Determine the horizon trend label from the latest row.
    
    Parameters:
        last (pd.Series): The most-recent row containing at least `close`, `ema_20`, and `ema_50`.
        enough_data (bool): Whether there is sufficient historical data to evaluate the horizon.
    
    Returns:
        trend (TrendVote): `"insufficient"` if `enough_data` is false; otherwise `"bullish"` if `close > ema_20 > ema_50`, `"bearish"` if `close < ema_20 < ema_50`, or `"mixed"` otherwise.
    """
    if not enough_data:
        return "insufficient"
    close = _as_float(last["close"])
    ema_20 = _as_float(last["ema_20"])
    ema_50 = _as_float(last["ema_50"])
    if close > ema_20 > ema_50:
        return "bullish"
    if close < ema_20 < ema_50:
        return "bearish"
    return "mixed"


def _max_drawdown_pct(values: pd.Series) -> float | None:
    """
    Compute the worst peak-to-trough drawdown for a series of price or value observations.
    
    Returns:
        The largest drawdown as a negative float (e.g., -0.25), or `None` if fewer than two values or the result is not a number.
    """
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
    """
    Builds per-horizon derived metrics (returns, volatility, support/resistance, trend vote, etc.) for inclusion in the MarketContextPack.
    
    Parameters:
        clean (pd.DataFrame): Enriched OHLCV frame containing `close`, `returns`, `high`, and `low` used to compute windowed statistics.
        horizon_bars (int): Horizon length in bars for which metrics are computed.
        last (pd.Series): The most recent non-NaN row from the enriched frame; used as the reference/current values.
    
    Returns:
        MarketContextHorizon: Container with these fields:
          - horizon_bars: requested horizon size.
          - available_bars: number of bars available within the horizon (clamped to data length).
          - return_pct: percent return from the horizon start to `last.close`, or `None` if insufficient history.
          - volatility_pct: scaled volatility over the horizon (std * sqrt(available_bars)), or `None` if fewer than 2 returns.
          - max_drawdown_pct: worst peak-to-trough drawdown in the window, or `None`.
          - trend_vote: horizon trend label (`"bullish"`, `"bearish"`, `"mixed"`, or `"insufficient"`).
          - support / resistance: window low/high values, or `None` if not available.
          - range_position: normalized position of `last.close` within support–resistance (0–1), or `None`.
          - atr_pct: `atr_14` divided by `last.close`, or `None` if `last.close` is zero or undefined.
          - volume_ratio: latest `volume_ratio_20` value (or `None`).
    """
    close = cast(pd.Series, clean["close"]).astype(float)
    returns = cast(pd.Series, clean["returns"]).astype(float)
    high = cast(pd.Series, clean["high"]).astype(float)
    low = cast(pd.Series, clean["low"]).astype(float)
    available_bars = max(0, min(horizon_bars, len(clean) - 1))
    enough_data = len(clean) > horizon_bars
    current_close = _as_float(last["close"])
    horizon_return = None
    if enough_data:
        start_close = _as_float(close.iloc[-(horizon_bars + 1)])
        if start_close != 0:
            horizon_return = (current_close / start_close) - 1.0

    close_window = close.tail(max(available_bars, 1))
    high_window = high.tail(max(available_bars, 1))
    low_window = low.tail(max(available_bars, 1))
    support = _as_float(low_window.min()) if not low_window.empty else None
    resistance = _as_float(high_window.max()) if not high_window.empty else None
    range_position = None
    if support is not None and resistance is not None and resistance > support:
        range_position = (current_close - support) / (resistance - support)
        range_position = max(0.0, min(1.0, range_position))

    volatility = None
    return_window = returns.tail(max(available_bars, 1)).dropna()
    if len(return_window) >= 2:
        volatility = _as_float(return_window.std() * (available_bars**0.5))

    atr_pct = None
    if current_close != 0:
        atr_pct = _as_float(last["atr_14"]) / current_close

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
        volume_ratio=_round_float(_as_float(last["volume_ratio_20"])),
    )


def _build_context_summary(
    *,
    symbol: str,
    bars_analyzed: int,
    coverage_ratio: float | None,
    horizons: list[MarketContextHorizon],
) -> str:
    """
    Build a concise operator-facing summary string for a market context pack.
    
    The summary includes the symbol, number of bars analyzed, lookback coverage as a percentage (or "unknown"), and trend votes for the first four horizons formatted as "{horizon_bars}b={trend_vote}".
    
    Parameters:
    	symbol (str): Ticker or symbol identifier.
    	bars_analyzed (int): Number of bars examined to produce the context.
    	coverage_ratio (float | None): Fraction of expected bars covered by the analyzed window, or `None` if unknown.
    	horizons (list[MarketContextHorizon]): Horizon objects whose `horizon_bars` and `trend_vote` are used; only the first four are shown.
    
    Returns:
    	summary (str): Single-line human-readable summary containing symbol, bars analyzed, coverage, and up to four horizon trend votes.
    """
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
    """
    Builds a MarketContextPack summarizing data quality, anomalies, horizon metrics, and coverage for the provided lookback window.
    
    Constructs per-horizon derived metrics, estimates expected bars from the requested lookback/interval, computes a coverage ratio, and aggregates data quality and anomaly flags (including minimum-bar requirement, coverage tiers, higher-timeframe fallback, large recent moves, volume spikes, and elevated recent volatility). The returned pack includes window boundary labels, required/expected/analyzed bar counts, rounded coverage, higher-timeframe usage, the list of horizon contexts, and a human-readable summary string.
    
    Returns:
        MarketContextPack: A populated context pack ready for persistence and operator inspection.
    """
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
        if coverage_ratio < MIN_LOOKBACK_COVERAGE_RATIO:
            data_quality_flags.append("low_lookback_coverage")
        elif coverage_ratio < PARTIAL_LOOKBACK_COVERAGE_RATIO:
            data_quality_flags.append("partial_lookback_coverage")
        else:
            data_quality_flags.append("lookback_coverage_ok")
    if higher_timeframe == "same_as_base":
        data_quality_flags.append("higher_timeframe_fallback")
    if abs(_as_float(last["return_5"])) >= 0.08:
        anomaly_flags.append("large_5_bar_move")
    if _as_float(last["volume_ratio_20"]) >= 2.5:
        anomaly_flags.append("volume_spike")
    if _as_float(last["volatility_20"]) >= 0.12:
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


def _validate_context_pack_for_execution(pack: MarketContextPack) -> None:
    """
    Validate that a context pack provides sufficient lookback coverage for safe execution.
    
    Does nothing when `coverage_ratio` or `bars_expected` is unknown. If both are known and
    `coverage_ratio` is below `MIN_LOOKBACK_COVERAGE_RATIO`, raises a `ValueError` that
    includes the pack's symbol, analyzed and expected bar counts, coverage percentage,
    lookback, and interval.
    
    Parameters:
        pack (MarketContextPack): Context pack containing `coverage_ratio`, `bars_expected`,
            `symbol`, `bars_analyzed`, `lookback`, and `interval`.
    
    Raises:
        ValueError: If coverage is known and below the minimum required lookback coverage.
    """
    if pack.coverage_ratio is None or pack.bars_expected is None:
        return
    if pack.coverage_ratio >= MIN_LOOKBACK_COVERAGE_RATIO:
        return

    coverage_pct = round(pack.coverage_ratio * 100, 1)
    raise ValueError(
        "Market data coverage is too thin for "
        f"{pack.symbol}: analyzed {pack.bars_analyzed}/{pack.bars_expected} "
        f"expected bars ({coverage_pct}%) for lookback {pack.lookback or 'unknown'} "
        f"at interval {pack.interval}. Refusing to run agents on an under-covered window."
    )


def _enrich_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """
    Add common technical indicators and derived features to an OHLCV DataFrame.
    
    Parameters:
        frame (pd.DataFrame): OHLCV dataframe indexed by timestamp with columns
            `open`, `high`, `low`, `close`, and `volume`.
    
    Returns:
        pd.DataFrame: A copy of `frame` with the following additional columns:
            - `ema_20`: 20-period exponential moving average of `close`.
            - `ema_50`: 50-period exponential moving average of `close`.
            - `atr_14`: 14-period Average True Range (Wilder-style).
            - `rsi_14`: 14-period Relative Strength Index (Wilder-style).
            - `returns`: period-to-period percent change of `close`.
            - `volatility_20`: volatility estimated from `returns` over 20 periods (scaled).
            - `return_5`: 5-period percent change of `close`.
            - `return_20`: 20-period percent change of `close`.
            - `volume_ratio_20`: `volume` divided by its 20-period moving average.
    """
    enriched = frame.copy()
    close = cast(pd.Series, enriched["close"])
    volume = cast(pd.Series, enriched["volume"])
    enriched["ema_20"] = close.ewm(span=20, adjust=False).mean()
    enriched["ema_50"] = close.ewm(span=50, adjust=False).mean()
    enriched["atr_14"] = _atr(enriched, 14)
    enriched["rsi_14"] = _rsi(close, 14)
    enriched["returns"] = close.pct_change()
    returns = cast(pd.Series, enriched["returns"])
    enriched["volatility_20"] = returns.rolling(20).std() * (20**0.5)
    enriched["return_5"] = close.pct_change(5)
    enriched["return_20"] = close.pct_change(20)
    enriched["volume_ratio_20"] = volume / volume.rolling(20).mean()
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

    resampled = cast(
        pd.DataFrame,
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
        .dropna(),
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
        higher_rsi = _as_float(higher_last["rsi_14"])
        confidence = min(
            1.0, 0.55 + max(0.0, (higher_rsi - 50.0) / 100.0)
        )
        return "bullish", round(confidence, 4)
    if base_bearish and higher_bearish:
        higher_rsi = _as_float(higher_last["rsi_14"])
        confidence = min(
            1.0, 0.55 + max(0.0, (50.0 - higher_rsi) / 100.0)
        )
        return "bearish", round(confidence, 4)
    return "mixed", 0.35


def build_snapshot(
    frame: pd.DataFrame,
    *,
    symbol: str,
    interval: str,
    lookback: str | None = None,
    enforce_lookback_coverage: bool = True,
) -> MarketSnapshot:
    """
    Build a MarketSnapshot and associated MarketContextPack from an OHLCV DataFrame.
    
    Processes the input frame to compute indicators, an optional higher timeframe view, multi-timeframe alignment, and a context pack describing horizon metrics and data-quality flags. Optionally enforces lookback coverage validation that will refuse execution when coverage is insufficient.
    
    Parameters:
        frame (pd.DataFrame): Raw OHLCV frame indexed by timestamps (or other index) used to compute indicators and context.
        symbol (str): Market symbol identifier to include in the snapshot and context pack.
        interval (str): Base timeframe interval string (e.g., "1m", "1d") used for higher-timeframe estimation and context semantics.
        lookback (str | None): Optional lookback descriptor (e.g., "6mo") used to estimate expected bars and coverage; pass None when unknown.
        enforce_lookback_coverage (bool): If True, validate the context pack's coverage against minimum thresholds and raise on insufficient coverage; if False, skip this validation.
    
    Returns:
        MarketSnapshot: Snapshot containing last-period indicators, higher-timeframe summary, multi-timeframe alignment/confidence, bars analyzed, and the constructed MarketContextPack.
    
    Raises:
        ValueError: If the input frame has fewer than the minimum required bars or if feature engineering yields no valid rows. Also raised when coverage validation is enabled and the context pack indicates insufficient lookback coverage.
    """
    if len(frame) < MIN_REQUIRED_BARS:
        raise ValueError(
            f"At least {MIN_REQUIRED_BARS} bars are required to build the market snapshot"
        )

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
    if enforce_lookback_coverage:
        _validate_context_pack_for_execution(context_pack)
    as_of_index = last.name if last.name is not None else clean.index[-1]

    return MarketSnapshot(
        symbol=symbol,
        interval=interval,
        as_of=_index_label(as_of_index),
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
