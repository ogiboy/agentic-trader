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
