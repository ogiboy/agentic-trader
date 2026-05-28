from __future__ import annotations

from datetime import datetime, timedelta, timezone

from agentic_trader.time_utils import utc_now_iso


def test_utc_now_iso_returns_parseable_utc_timestamp() -> None:
    timestamp = datetime.fromisoformat(utc_now_iso())

    assert timestamp.tzinfo is not None
    assert timestamp.utcoffset() is not None
    assert timestamp.utcoffset() == timedelta(0)
    assert timestamp.tzinfo == timezone.utc
