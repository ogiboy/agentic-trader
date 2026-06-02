import pandas as pd


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    values = 100 - (100 / (1 + rs))
    values = values.where(~((avg_loss == 0) & (avg_gain > 0)), 100.0)
    values = values.where(~((avg_gain == 0) & (avg_loss > 0)), 0.0)
    values = values.where(~((avg_gain == 0) & (avg_loss == 0)), 50.0)
    return values


def atr(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    high = frame["high"]
    low = frame["low"]
    close = frame["close"]
    prev_close = close.shift(1)
    tr_components = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    )
    true_range = tr_components.max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False).mean()


def enrich_frame(frame: pd.DataFrame) -> pd.DataFrame:
    enriched = frame.copy()
    close = enriched["close"]
    volume = enriched["volume"]
    enriched["ema_20"] = close.ewm(span=20, adjust=False).mean()
    enriched["ema_50"] = close.ewm(span=50, adjust=False).mean()
    enriched["atr_14"] = atr(enriched, 14)
    enriched["rsi_14"] = rsi(close, 14)
    enriched["returns"] = close.pct_change()
    returns = enriched["returns"]
    enriched["volatility_20"] = returns.rolling(20).std() * (20**0.5)
    enriched["return_5"] = close.pct_change(5)
    enriched["return_20"] = close.pct_change(20)
    enriched["volume_ratio_20"] = volume / volume.rolling(20).mean()
    return enriched
