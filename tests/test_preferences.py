from pathlib import Path

from agentic_trader.config import Settings
from agentic_trader.schemas import InvestmentPreferences
from agentic_trader.storage.db import TradingDatabase


def test_preferences_round_trip(tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)

    prefs = InvestmentPreferences(
        regions=["US", "EU"],
        exchanges=["NASDAQ", "XETRA"],
        currencies=["USD", "EUR"],
        sectors=["TECH", "HEALTHCARE"],
        risk_profile="aggressive",
        trade_style="position",
        behavior_preset="trend_biased",
        agent_profile="disciplined",
        notes="Test preferences",
    )
    db.save_preferences(prefs)
    loaded = db.load_preferences()

    assert loaded == prefs


def test_service_state_and_events_round_trip(tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)

    db.upsert_service_state(
        state="running",
        continuous=True,
        poll_seconds=300,
        cycle_count=2,
        current_symbol="AAPL",
        message="Cycle 2 is running.",
    )
    db.insert_service_event(
        level="info",
        event_type="cycle_started",
        message="Cycle 2 started.",
        cycle_count=2,
        symbol="AAPL",
    )

    state = db.get_service_state()
    events = db.list_service_events(limit=5)

    assert state is not None
    assert state.state == "running"
    assert state.cycle_count == 2
    assert state.current_symbol == "AAPL"
    assert len(events) == 1
    assert events[0].event_type == "cycle_started"
