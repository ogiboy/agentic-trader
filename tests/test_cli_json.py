import json
from pathlib import Path

from typer.testing import CliRunner

from agentic_trader.cli import app
from agentic_trader.config import Settings
from agentic_trader.schemas import LLMHealthStatus
from agentic_trader.storage.db import TradingDatabase


def test_status_preferences_and_portfolio_json(monkeypatch, tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)

    db = TradingDatabase(settings)
    db.upsert_service_state(
        state="completed",
        continuous=False,
        poll_seconds=300,
        cycle_count=2,
        current_symbol=None,
        message="Completed.",
    )
    db.conn.close()

    runner = CliRunner()

    status_result = runner.invoke(app, ["status", "--json"])
    assert status_result.exit_code == 0
    status_payload = json.loads(status_result.stdout)
    assert status_payload["runtime_state"] == "inactive"
    assert status_payload["state"]["state"] == "completed"

    preferences_result = runner.invoke(app, ["preferences", "--json"])
    assert preferences_result.exit_code == 0
    preferences_payload = json.loads(preferences_result.stdout)
    assert preferences_payload["risk_profile"] == "balanced"

    portfolio_result = runner.invoke(app, ["portfolio", "--json"])
    assert portfolio_result.exit_code == 0
    portfolio_payload = json.loads(portfolio_result.stdout)
    assert portfolio_payload["snapshot"]["cash"] == settings.default_cash
    assert portfolio_payload["positions"] == []


def test_doctor_and_logs_json(monkeypatch, tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)
    monkeypatch.setattr(
        "agentic_trader.cli.LocalLLM.health_check",
        lambda self: LLMHealthStatus(
            provider="ollama",
            base_url=self.settings.base_url,
            model_name=self.settings.model_name,
            service_reachable=True,
            model_available=True,
            message="ready",
        ),
    )

    db = TradingDatabase(settings)
    db.insert_service_event(level="info", event_type="service_started", message="Started.")
    db.conn.close()

    runner = CliRunner()

    doctor_result = runner.invoke(app, ["doctor", "--json"])
    assert doctor_result.exit_code == 0
    doctor_payload = json.loads(doctor_result.stdout)
    assert doctor_payload["ollama_reachable"] is True
    assert doctor_payload["model_available"] is True

    logs_result = runner.invoke(app, ["logs", "--json", "--limit", "5"])
    assert logs_result.exit_code == 0
    logs_payload = json.loads(logs_result.stdout)
    assert logs_payload[0]["event_type"] == "service_started"
