import pandas as pd

from agentic_trader.market.features import build_snapshot


def test_build_snapshot_returns_expected_fields() -> None:
    frame = pd.DataFrame(
        {
            "open": [100 + i for i in range(80)],
            "high": [101 + i for i in range(80)],
            "low": [99 + i for i in range(80)],
            "close": [100 + i for i in range(80)],
            "volume": [1_000 + (i * 10) for i in range(80)],
        }
    )

    snapshot = build_snapshot(frame, symbol="TEST", interval="1d")

    assert snapshot.symbol == "TEST"
    assert snapshot.interval == "1d"
    assert snapshot.bars_analyzed == 80
    assert snapshot.last_close > 0
    assert snapshot.ema_20 > 0
    assert snapshot.ema_50 > 0
    assert snapshot.higher_timeframe == "same_as_base"
    assert snapshot.htf_last_close > 0
    assert snapshot.mtf_alignment in {"bullish", "bearish", "mixed"}
    assert 0.0 <= snapshot.mtf_confidence <= 1.0


def test_build_snapshot_computes_higher_timeframe_alignment() -> None:
    index = pd.date_range("2025-01-01", periods=260, freq="B")
    frame = pd.DataFrame(
        {
            "open": [100 + (i * 0.8) for i in range(260)],
            "high": [101 + (i * 0.8) for i in range(260)],
            "low": [99 + (i * 0.8) for i in range(260)],
            "close": [100 + (i * 0.8) for i in range(260)],
            "volume": [1_000 + (i * 20) for i in range(260)],
        },
        index=index,
    )

    snapshot = build_snapshot(frame, symbol="TREND", interval="1d")

    assert snapshot.higher_timeframe == "1wk"
    assert snapshot.htf_last_close > 0
    assert snapshot.htf_ema_20 > 0
    assert snapshot.htf_ema_50 > 0
    assert snapshot.mtf_alignment == "bullish"
    assert snapshot.mtf_confidence > 0.55
