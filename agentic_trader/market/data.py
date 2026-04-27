from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path

import pandas as pd
import yfinance as yf

from agentic_trader.config import Settings


def _snapshot_path(cache_dir: Path, symbol: str, interval: str, lookback: str) -> Path:
    safe_symbol = symbol.replace("/", "_").replace("-", "_").replace(".", "_")
    safe_interval = interval.replace("/", "_")
    safe_lookback = lookback.replace("/", "_")
    return cache_dir / f"{safe_symbol}__{safe_interval}__{safe_lookback}.csv"


def _normalize_ohlcv(data: pd.DataFrame, *, symbol: str) -> pd.DataFrame:
    if data.empty:
        raise ValueError(f"No market data returned for {symbol}")

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    normalized = data.rename(columns=str.lower)
    required = {"open", "high", "low", "close", "volume"}
    missing = required.difference(normalized.columns)
    if missing:
        raise ValueError(f"Missing columns from market data: {sorted(missing)}")

    return normalized.dropna().copy()


def _read_cached_snapshot(path: Path, *, symbol: str) -> pd.DataFrame:
    cached = pd.read_csv(path, index_col=0, parse_dates=True)
    if cached.index.name is None:
        cached.index.name = "date"
    return _normalize_ohlcv(cached, symbol=symbol)


def _download_ohlcv(
    symbol: str, *, interval: str, lookback: str
) -> pd.DataFrame | None:
    buffer = io.StringIO()
    with redirect_stdout(buffer), redirect_stderr(buffer):
        raw_data = yf.download(  # type: ignore[reportUnknownMemberType]
            tickers=symbol,
            period=lookback,
            interval=interval,
            auto_adjust=False,
            progress=False,
        )
    return raw_data


def fetch_ohlcv(
    symbol: str,
    *,
    interval: str,
    lookback: str,
    settings: Settings | None = None,
) -> pd.DataFrame:
    cache_dir: Path | None = None
    cache_mode = "live"
    if settings is not None:
        cache_dir = settings.market_data_cache_dir
        cache_mode = settings.market_data_mode

    cache_path = (
        _snapshot_path(cache_dir, symbol, interval, lookback)
        if cache_dir is not None
        else None
    )
    if cache_mode == "prefer_cache" and cache_path is not None and cache_path.exists():
        return _read_cached_snapshot(cache_path, symbol=symbol)

    raw_data = _download_ohlcv(symbol, interval=interval, lookback=lookback)
    if raw_data is None:
        raise ValueError(f"No market data returned for {symbol}")

    data: pd.DataFrame = _normalize_ohlcv(raw_data, symbol=symbol)
    if cache_mode in {"prefer_cache", "refresh_cache"} and cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        data.to_csv(cache_path)
    return data
