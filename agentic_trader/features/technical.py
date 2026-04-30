from agentic_trader.schemas import (
    MarketContextHorizon,
    MarketSnapshot,
    TechnicalFeatureSet,
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
    return supported[-1] if supported else snapshot.context_pack.horizons[-1]


def get_market_features(snapshot: MarketSnapshot) -> TechnicalFeatureSet:
    """Summarize price action into the technical feature set consumed by agents."""
    returns_by_window: dict[str, float | None] = {
        "5b": snapshot.return_5,
        "20b": snapshot.return_20,
        "30d": snapshot.return_20,
        "90d": None,
        "180d": None,
    }
    data_quality_flags: list[str] = []
    context_summary = ""
    trend_classification = "insufficient"
    max_drawdown_pct = None
    support = None
    resistance = None

    if snapshot.context_pack is not None:
        context_summary = snapshot.context_pack.summary
        data_quality_flags = list(snapshot.context_pack.data_quality_flags)
        for horizon in snapshot.context_pack.horizons:
            returns_by_window[_horizon_key(horizon)] = horizon.return_pct
        _add_calendar_return_windows(
            returns_by_window,
            snapshot.context_pack.horizons,
        )
        structural_horizon = _last_structural_horizon(snapshot)
        if structural_horizon is not None:
            support = structural_horizon.support
            resistance = structural_horizon.resistance
        drawdown_values = [
            horizon.max_drawdown_pct
            for horizon in snapshot.context_pack.horizons
            if horizon.max_drawdown_pct is not None
        ]
        if drawdown_values:
            max_drawdown_pct = min(drawdown_values)
        trend_votes = [
            horizon.trend_vote
            for horizon in snapshot.context_pack.horizons
            if horizon.trend_vote != "insufficient"
        ]
        if trend_votes:
            bullish = trend_votes.count("bullish")
            bearish = trend_votes.count("bearish")
            if bullish > bearish:
                trend_classification = "bullish"
            elif bearish > bullish:
                trend_classification = "bearish"
            else:
                trend_classification = "mixed"

    if trend_classification == "insufficient":
        if snapshot.last_close > snapshot.ema_20 > snapshot.ema_50:
            trend_classification = "bullish"
        elif snapshot.last_close < snapshot.ema_20 < snapshot.ema_50:
            trend_classification = "bearish"
        else:
            trend_classification = "mixed"

    return TechnicalFeatureSet(
        symbol=snapshot.symbol,
        interval=snapshot.interval,
        as_of=snapshot.as_of,
        price_anchor=snapshot.last_close,
        returns_by_window=returns_by_window,
        volatility_20=snapshot.volatility_20,
        max_drawdown_pct=max_drawdown_pct,
        support=support,
        resistance=resistance,
        trend_classification=trend_classification,
        momentum_indicators={
            "rsi_14": snapshot.rsi_14,
            "return_5": snapshot.return_5,
            "return_20": snapshot.return_20,
            "volume_ratio_20": snapshot.volume_ratio_20,
            "mtf_confidence": snapshot.mtf_confidence,
        },
        context_summary=context_summary,
        data_quality_flags=data_quality_flags,
    )
