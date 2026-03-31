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
        notes="Test preferences",
    )
    db.save_preferences(prefs)
    loaded = db.load_preferences()

    assert loaded == prefs
