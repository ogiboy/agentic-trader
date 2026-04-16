import sys

import pandas as pd
import pytest

from agentic_trader.market.data import fetch_ohlcv


def test_fetch_ohlcv_suppresses_provider_console_noise(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def _noisy_download(*_args: object, **_kwargs: object) -> pd.DataFrame:
        print("1 Failed download:")
        print("raw provider traceback-ish detail", file=sys.stderr)
        return pd.DataFrame()

    monkeypatch.setattr("agentic_trader.market.data.yf.download", _noisy_download)

    with pytest.raises(ValueError, match="No market data returned for NOISE"):
        fetch_ohlcv("NOISE", interval="1d", lookback="180d")

    captured = capsys.readouterr()
    assert "Failed download" not in captured.out
    assert "raw provider" not in captured.err
