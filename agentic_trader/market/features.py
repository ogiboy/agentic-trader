import pandas as pd

from agentic_trader.schemas import MarketSnapshot


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
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


def build_snapshot(frame: pd.DataFrame, *, symbol: str, interval: str) -> MarketSnapshot:
    if len(frame) < 60:
        raise ValueError("At least 60 bars are required to build the market snapshot")

    enriched = frame.copy()
    enriched["ema_20"] = enriched["close"].ewm(span=20, adjust=False).mean()
    enriched["ema_50"] = enriched["close"].ewm(span=50, adjust=False).mean()
    enriched["atr_14"] = _atr(enriched, 14)
    enriched["rsi_14"] = _rsi(enriched["close"], 14)
    enriched["returns"] = enriched["close"].pct_change()
    enriched["volatility_20"] = enriched["returns"].rolling(20).std() * (20**0.5)
    enriched["return_5"] = enriched["close"].pct_change(5)
    enriched["return_20"] = enriched["close"].pct_change(20)
    enriched["volume_ratio_20"] = enriched["volume"] / enriched["volume"].rolling(20).mean()

    clean = enriched.dropna()
    if clean.empty:
        raise ValueError("Feature engineering produced no valid rows")

    last = clean.iloc[-1]

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
        bars_analyzed=int(len(enriched)),
    )
