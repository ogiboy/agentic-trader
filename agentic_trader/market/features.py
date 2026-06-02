import pandas as pd

from agentic_trader.market.feature_context import (
    MIN_REQUIRED_BARS,
    build_context_pack,
    validate_context_pack_for_execution,
)
from agentic_trader.market.feature_timeframes import (
    clean_enriched_frame,
    higher_timeframe_last,
    mtf_alignment,
)
from agentic_trader.market.feature_utils import index_label
from agentic_trader.schemas import MarketSnapshot


def build_snapshot(
    frame: pd.DataFrame,
    *,
    symbol: str,
    interval: str,
    lookback: str | None = None,
    enforce_lookback_coverage: bool = True,
) -> MarketSnapshot:
    """Build a MarketSnapshot and MarketContextPack from an OHLCV frame."""
    if len(frame) < MIN_REQUIRED_BARS:
        raise ValueError(
            f"At least {MIN_REQUIRED_BARS} bars are required to build the market snapshot"
        )

    clean = clean_enriched_frame(frame)
    last = clean.iloc[-1]
    higher_last, higher_timeframe = higher_timeframe_last(
        frame,
        interval=interval,
        fallback=last,
    )
    alignment, alignment_confidence = mtf_alignment(last, higher_last)
    context_pack = build_context_pack(
        frame,
        clean,
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        higher_timeframe=higher_timeframe,
        last=last,
    )
    if enforce_lookback_coverage:
        validate_context_pack_for_execution(context_pack)
    as_of_index = last.name if last.name is not None else clean.index[-1]

    return MarketSnapshot(
        symbol=symbol,
        interval=interval,
        as_of=index_label(as_of_index),
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
        mtf_alignment=alignment,
        mtf_confidence=alignment_confidence,
        bars_analyzed=int(len(frame)),
        context_pack=context_pack,
    )
