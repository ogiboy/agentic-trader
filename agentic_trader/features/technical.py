from agentic_trader.schemas import (
    MarketContextHorizon,
    MarketSnapshot,
    TechnicalFeatureSet,
    TrendVote,
)

CALENDAR_RETURN_WINDOWS = {
    "30d": 20,
    "90d": 60,
    "180d": 120,
}


def _horizon_key(horizon: MarketContextHorizon) -> str:
    return f"{horizon.horizon_bars}b"


def _nearest_horizon_return(
    horizons: list[MarketContextHorizon], target_bars: int
) -> float | None:
    candidates = [
        horizon
        for horizon in horizons
        if horizon.return_pct is not None and horizon.available_bars > 0
    ]
    if not candidates:
        return None
    exact = next(
        (horizon for horizon in candidates if horizon.horizon_bars == target_bars),
        None,
    )
    if exact is not None:
        return exact.return_pct
    eligible = [
        horizon for horizon in candidates if horizon.horizon_bars >= target_bars
    ]
    if not eligible:
        return None
    nearest = min(
        eligible,
        key=lambda horizon: (
            abs(horizon.horizon_bars - target_bars),
            horizon.horizon_bars,
        ),
    )
    return nearest.return_pct


def _add_calendar_return_windows(
    returns_by_window: dict[str, float | None],
    horizons: list[MarketContextHorizon],
) -> None:
    for label, target_bars in CALENDAR_RETURN_WINDOWS.items():
        returns_by_window[label] = _nearest_horizon_return(horizons, target_bars)


def _last_structural_horizon(snapshot: MarketSnapshot) -> MarketContextHorizon | None:
    if snapshot.context_pack is None or not snapshot.context_pack.horizons:
        return None
    supported = [
        horizon
        for horizon in snapshot.context_pack.horizons
        if horizon.support is not None and horizon.resistance is not None
    ]
    if supported:
        return supported[-1]
    return snapshot.context_pack.horizons[-1]


def _base_returns_by_window(snapshot: MarketSnapshot) -> dict[str, float | None]:
    return {
        "5b": snapshot.return_5,
        "20b": snapshot.return_20,
        "30d": snapshot.return_20,
        "90d": None,
        "180d": None,
    }


def _context_returns_by_window(snapshot: MarketSnapshot) -> dict[str, float | None]:
    returns_by_window = _base_returns_by_window(snapshot)
    if snapshot.context_pack is None:
        return returns_by_window

    for horizon in snapshot.context_pack.horizons:
        returns_by_window[_horizon_key(horizon)] = horizon.return_pct
    _add_calendar_return_windows(
        returns_by_window,
        snapshot.context_pack.horizons,
    )
    return returns_by_window


def _structural_levels(snapshot: MarketSnapshot) -> tuple[float | None, float | None]:
    structural_horizon = _last_structural_horizon(snapshot)
    if structural_horizon is None:
        return None, None
    return structural_horizon.support, structural_horizon.resistance


def _max_context_drawdown(snapshot: MarketSnapshot) -> float | None:
    if snapshot.context_pack is None:
        return None
    drawdown_values = [
        horizon.max_drawdown_pct
        for horizon in snapshot.context_pack.horizons
        if horizon.max_drawdown_pct is not None
    ]
    if not drawdown_values:
        return None
    return min(drawdown_values)


def _context_trend_classification(snapshot: MarketSnapshot) -> TrendVote:
    if snapshot.context_pack is None:
        return "insufficient"
    trend_votes = [
        horizon.trend_vote
        for horizon in snapshot.context_pack.horizons
        if horizon.trend_vote != "insufficient"
    ]
    if not trend_votes:
        return "insufficient"

    bullish = trend_votes.count("bullish")
    bearish = trend_votes.count("bearish")
    if bullish > bearish:
        return "bullish"
    if bearish > bullish:
        return "bearish"
    return "mixed"


def _average_trend_classification(snapshot: MarketSnapshot) -> TrendVote:
    if snapshot.last_close > snapshot.ema_20 > snapshot.ema_50:
        return "bullish"
    if snapshot.last_close < snapshot.ema_20 < snapshot.ema_50:
        return "bearish"
    return "mixed"


def _data_quality_flags(snapshot: MarketSnapshot) -> list[str]:
    if snapshot.context_pack is None:
        return []
    return list(snapshot.context_pack.data_quality_flags)


def _context_summary(snapshot: MarketSnapshot) -> str:
    if snapshot.context_pack is None:
        return ""
    return snapshot.context_pack.summary


def _trend_classification(snapshot: MarketSnapshot) -> TrendVote:
    trend = _context_trend_classification(snapshot)
    if trend != "insufficient":
        return trend
    return _average_trend_classification(snapshot)


def get_market_features(snapshot: MarketSnapshot) -> TechnicalFeatureSet:
    """Summarize price action into the technical feature set consumed by agents."""
    support, resistance = _structural_levels(snapshot)

    return TechnicalFeatureSet(
        symbol=snapshot.symbol,
        interval=snapshot.interval,
        as_of=snapshot.as_of,
        price_anchor=snapshot.last_close,
        returns_by_window=_context_returns_by_window(snapshot),
        volatility_20=snapshot.volatility_20,
        max_drawdown_pct=_max_context_drawdown(snapshot),
        support=support,
        resistance=resistance,
        trend_classification=_trend_classification(snapshot),
        momentum_indicators={
            "rsi_14": snapshot.rsi_14,
            "return_5": snapshot.return_5,
            "return_20": snapshot.return_20,
            "volume_ratio_20": snapshot.volume_ratio_20,
            "mtf_confidence": snapshot.mtf_confidence,
        },
        context_summary=_context_summary(snapshot),
        data_quality_flags=_data_quality_flags(snapshot),
    )
