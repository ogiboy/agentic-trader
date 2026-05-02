from pathlib import Path

from rich.console import Console

from agentic_trader.config import Settings
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.tui import _agent_activity_table, build_monitor_renderable


def test_build_monitor_renderable_contains_core_sections(tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    db.upsert_service_state(
        state="running",
        continuous=True,
        poll_seconds=60,
        cycle_count=3,
        current_symbol="AAPL",
        message="Monitoring AAPL",
    )
    db.insert_service_event(
        level="info",
        event_type="cycle_started",
        message="Cycle started",
        cycle_count=3,
        symbol="AAPL",
    )
    db.insert_service_event(
        level="info",
        event_type="agent_regime_started",
        message="Regime analyst started.",
        cycle_count=3,
        symbol="AAPL",
    )

    renderable = build_monitor_renderable(settings, db)
    console = Console(record=True, width=140)
    console.print(renderable)
    output = console.export_text()

    assert "Agentic Trader Live Monitor" in output
    assert "Current Cycle" in output
    assert "Interval / Lookback" in output
    assert "Broker Backend" in output
    assert "V1 Paper Gate" in output
    assert "Current Stage" in output
    assert "Stage Status" in output
    assert "System Status" in output
    assert "Runtime Status" in output
    assert "Portfolio" in output
    assert "Runtime Events" in output
    assert "Live Agent Activity" in output


def test_agent_activity_table_filters_to_current_runtime_cycle(tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    db.upsert_service_state(
        state="running",
        continuous=True,
        poll_seconds=60,
        cycle_count=3,
        current_symbol="AAPL",
        message="Cycle 3 is active.",
    )
    db.insert_service_event(
        level="info",
        event_type="agent_regime_started",
        message="Old cycle regime event.",
        cycle_count=2,
        symbol="AAPL",
    )

    state = db.get_service_state()
    events = db.list_service_events(limit=20)
    console = Console(record=True, width=120)
    console.print(_agent_activity_table(state, events))
    output = console.export_text()

    assert "Old cycle regime event." not in output
    assert "Waiting for this stage to start." in output
