import re

import pandas as pd

from agentic_trader.market.feature_utils import as_float, index_label, round_float
from agentic_trader.schemas import MarketContextHorizon, MarketContextPack, TrendVote

MIN_REQUIRED_BARS = 60
MIN_LOOKBACK_COVERAGE_RATIO = 0.6
PARTIAL_LOOKBACK_COVERAGE_RATIO = 0.85
CONTEXT_HORIZONS = (5, 20, 60, 120, 180)
_LOOKBACK_RE = re.compile(r"^(?P<count>\d+)(?P<unit>d|wk|mo|y)$", re.IGNORECASE)
_INTERVAL_RE = re.compile(r"^(?P<count>\d+)(?P<unit>m|h|d|wk)$", re.IGNORECASE)


def lookback_days(lookback: str | None) -> int | None:
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


def estimate_expected_bars(
    *, lookback: str | None, interval: str
) -> tuple[int | None, str]:
    days = lookback_days(lookback)
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


def trend_vote(last: pd.Series, *, enough_data: bool) -> TrendVote:
    if not enough_data:
        return "insufficient"
    close = as_float(last["close"])
    ema_20 = as_float(last["ema_20"])
    ema_50 = as_float(last["ema_50"])
    if close > ema_20 > ema_50:
        return "bullish"
    if close < ema_20 < ema_50:
        return "bearish"
    return "mixed"


def max_drawdown_pct(values: pd.Series) -> float | None:
    if len(values) < 2:
        return None
    running_peak = values.cummax()
    drawdowns = (values / running_peak.replace(0, pd.NA)) - 1.0
    minimum = drawdowns.min()
    if pd.isna(minimum):
        return None
    return float(minimum)


def horizon_context(
    clean: pd.DataFrame, *, horizon_bars: int, last: pd.Series
) -> MarketContextHorizon:
    close = clean["close"].astype(float)
    returns = clean["returns"].astype(float)
    high = clean["high"].astype(float)
    low = clean["low"].astype(float)
    available_bars = max(0, min(horizon_bars, len(clean) - 1))
    enough_data = len(clean) > horizon_bars
    current_close = as_float(last["close"])
    horizon_return = None
    if enough_data:
        start_close = as_float(close.iloc[-(horizon_bars + 1)])
        if start_close != 0:
            horizon_return = (current_close / start_close) - 1.0

    close_window = close.tail(max(available_bars, 1))
    high_window = high.tail(max(available_bars, 1))
    low_window = low.tail(max(available_bars, 1))
    support = as_float(low_window.min()) if not low_window.empty else None
    resistance = as_float(high_window.max()) if not high_window.empty else None
    range_position = None
    if support is not None and resistance is not None and resistance > support:
        range_position = (current_close - support) / (resistance - support)
        range_position = max(0.0, min(1.0, range_position))

    volatility = None
    return_window = returns.tail(max(available_bars, 1)).dropna()
    if len(return_window) >= 2:
        volatility = as_float(return_window.std() * (available_bars**0.5))

    atr_pct = None
    if current_close != 0:
        atr_pct = as_float(last["atr_14"]) / current_close

    return MarketContextHorizon(
        horizon_bars=horizon_bars,
        available_bars=available_bars,
        return_pct=round_float(horizon_return),
        volatility_pct=round_float(volatility),
        max_drawdown_pct=round_float(max_drawdown_pct(close_window)),
        trend_vote=trend_vote(last, enough_data=enough_data),
        support=round_float(support),
        resistance=round_float(resistance),
        range_position=round_float(range_position),
        atr_pct=round_float(atr_pct),
        volume_ratio=round_float(as_float(last["volume_ratio_20"])),
    )


def build_context_summary(
    *,
    symbol: str,
    bars_analyzed: int,
    coverage_ratio: float | None,
    horizons: list[MarketContextHorizon],
) -> str:
    horizon_votes = ", ".join(
        f"{item.horizon_bars}b={item.trend_vote}" for item in horizons[:4]
    )
    coverage = f"{coverage_ratio:.0%}" if coverage_ratio is not None else "unknown"
    return f"{symbol}: {bars_analyzed} bars analyzed, coverage={coverage}, trend votes: {horizon_votes}"


def build_context_pack(
    frame: pd.DataFrame,
    clean: pd.DataFrame,
    *,
    symbol: str,
    interval: str,
    lookback: str | None,
    higher_timeframe: str,
    last: pd.Series,
) -> MarketContextPack:
    expected_bars, interval_semantics = estimate_expected_bars(
        lookback=lookback, interval=interval
    )
    bars_analyzed = int(len(frame))
    coverage_ratio = (
        min(1.0, bars_analyzed / expected_bars)
        if expected_bars and expected_bars > 0
        else None
    )
    horizons = [
        horizon_context(clean, horizon_bars=horizon, last=last)
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
    if abs(as_float(last["return_5"])) >= 0.08:
        anomaly_flags.append("large_5_bar_move")
    if as_float(last["volume_ratio_20"]) >= 2.5:
        anomaly_flags.append("volume_spike")
    if as_float(last["volatility_20"]) >= 0.12:
        anomaly_flags.append("high_recent_volatility")

    pack = MarketContextPack(
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        interval_semantics=interval_semantics,
        window_start=index_label(frame.index[0]) if len(frame.index) else None,
        window_end=index_label(frame.index[-1]) if len(frame.index) else None,
        bars_required=MIN_REQUIRED_BARS,
        bars_expected=expected_bars,
        bars_analyzed=bars_analyzed,
        coverage_ratio=round_float(coverage_ratio, digits=4),
        higher_timeframe=higher_timeframe,
        higher_timeframe_used=higher_timeframe != "same_as_base",
        horizons=horizons,
        data_quality_flags=data_quality_flags,
        anomaly_flags=anomaly_flags,
    )
    pack.summary = build_context_summary(
        symbol=symbol,
        bars_analyzed=bars_analyzed,
        coverage_ratio=pack.coverage_ratio,
        horizons=horizons,
    )
    return pack


def validate_context_pack_for_execution(pack: MarketContextPack) -> None:
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
