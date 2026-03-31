from typing import cast

import pandas as pd
import yfinance as yf  # type: ignore[reportMissingTypeStubs]


def fetch_ohlcv(symbol: str, *, interval: str, lookback: str) -> pd.DataFrame:
    raw_data = yf.download(
        tickers=symbol,
        period=lookback,
        interval=interval,
        auto_adjust=False,
        progress=False,
    )
    if raw_data is None:
        raise ValueError(f"No market data returned for {symbol}")

    data = cast(pd.DataFrame, raw_data)
    if data.empty:
        raise ValueError(f"No market data returned for {symbol}")

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data = data.rename(columns=str.lower)
    required = {"open", "high", "low", "close", "volume"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Missing columns from market data: {sorted(missing)}")

    return data.dropna().copy()
