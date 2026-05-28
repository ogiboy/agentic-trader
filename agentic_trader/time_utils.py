"""Shared time helpers for runtime metadata."""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now_iso() -> str:
    """
    Get the current UTC time as an ISO-8601 formatted string.
    
    Returns:
        iso_ts (str): ISO-8601 formatted UTC timestamp including the `+00:00` offset.
    """

    return datetime.now(UTC).isoformat()
