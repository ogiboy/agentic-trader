from __future__ import annotations

from typing import Protocol

from agentic_trader.config import Settings
from agentic_trader.schemas import InvestmentPreferences
from agentic_trader.storage.db import TradingDatabase


class OpenDatabase(Protocol):
    def __call__(
        self, settings: Settings, *, read_only: bool = False
    ) -> TradingDatabase: ...


def preferences_payload(
    settings: Settings, *, open_db: OpenDatabase
) -> dict[str, object]:
    try:
        db = open_db(settings, read_only=True)
        try:
            preferences = db.load_preferences()
        finally:
            db.close()
        available = True
        error = None
    except Exception as exc:
        preferences = InvestmentPreferences()
        available = False
        error = str(exc)
    payload = preferences.model_dump(mode="json")
    payload["available"] = available
    payload["error"] = error
    return payload


def journal_payload(
    settings: Settings, *, open_db: OpenDatabase, limit: int
) -> dict[str, object]:
    try:
        db = open_db(settings, read_only=True)
        try:
            entries = db.list_trade_journal(limit=limit)
        finally:
            db.close()
        available = True
        error = None
    except Exception as exc:  # noqa: BLE001 - observer payload should degrade when DB reads fail
        entries = []
        available = False
        error = str(exc)
    return {
        "available": available,
        "error": error,
        "entries": [entry.model_dump(mode="json") for entry in entries],
    }


def recent_runs_payload(
    settings: Settings, *, open_db: OpenDatabase, limit: int
) -> dict[str, object]:
    try:
        db = open_db(settings, read_only=True)
        try:
            runs = db.list_recent_runs(limit=limit)
        finally:
            db.close()
        available = True
        error = None
    except Exception as exc:  # noqa: BLE001 - observer payload should degrade when DB reads fail
        runs = []
        available = False
        error = str(exc)
    return {
        "available": available,
        "error": error,
        "runs": [
            {
                "run_id": run_id,
                "created_at": created_at,
                "symbol": symbol,
                "interval": interval,
                "approved": approved,
            }
            for run_id, created_at, symbol, interval, approved in runs
        ],
    }


def run_record_payload(
    settings: Settings, *, open_db: OpenDatabase, run_id: str | None = None
) -> dict[str, object]:
    try:
        db = open_db(settings, read_only=True)
        try:
            record = db.get_run(run_id) if run_id is not None else db.latest_run()
        finally:
            db.close()
        available = True
        error = None
    except Exception as exc:
        record = None
        available = False
        error = str(exc)
    return {
        "available": available,
        "error": error,
        "record": record.model_dump(mode="json") if record is not None else None,
    }


def trade_context_payload(
    settings: Settings, *, open_db: OpenDatabase, trade_id: str | None = None
) -> dict[str, object]:
    try:
        db = open_db(settings, read_only=True)
        try:
            record = (
                db.get_trade_context(trade_id)
                if trade_id is not None
                else db.latest_trade_context()
            )
        finally:
            db.close()
        available = True
        error = None
    except Exception as exc:
        record = None
        available = False
        error = str(exc)
    return {
        "available": available,
        "error": error,
        "record": record.model_dump(mode="json") if record is not None else None,
    }


__all__ = (
    "journal_payload",
    "preferences_payload",
    "recent_runs_payload",
    "run_record_payload",
    "trade_context_payload",
)
