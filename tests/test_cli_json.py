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


def test_preferences_and_portfolio_json_survive_db_lock(monkeypatch, tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)
    monkeypatch.setattr("agentic_trader.cli._open_db", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("db locked")))

    runner = CliRunner()

    preferences_result = runner.invoke(app, ["preferences", "--json"])
    assert preferences_result.exit_code == 0
    preferences_payload = json.loads(preferences_result.stdout)
    assert preferences_payload["available"] is False
    assert preferences_payload["risk_profile"] == "balanced"

    portfolio_result = runner.invoke(app, ["portfolio", "--json"])
    assert portfolio_result.exit_code == 0
    portfolio_payload = json.loads(portfolio_result.stdout)
    assert portfolio_payload["available"] is False
    assert portfolio_payload["positions"] == []


def test_journal_risk_review_and_trace_json(monkeypatch, tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)

    runner = CliRunner()

    journal_result = runner.invoke(app, ["journal", "--json", "--limit", "5"])
    assert journal_result.exit_code == 0
    journal_payload = json.loads(journal_result.stdout)
    assert journal_payload["available"] is True
    assert journal_payload["entries"] == []

    risk_result = runner.invoke(app, ["risk-report", "--json"])
    assert risk_result.exit_code == 0
    risk_payload = json.loads(risk_result.stdout)
    assert risk_payload["available"] is True
    assert risk_payload["report"]["equity"] == settings.default_cash

    review_result = runner.invoke(app, ["review-run", "--json"])
    assert review_result.exit_code == 0
    review_payload = json.loads(review_result.stdout)
    assert review_payload["available"] is True
    assert review_payload["record"] is None

    trace_result = runner.invoke(app, ["trace-run", "--json"])
    assert trace_result.exit_code == 0
    trace_payload = json.loads(trace_result.stdout)
    assert trace_payload["available"] is True
    assert trace_payload["record"] is None


def test_chat_json(monkeypatch, tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)
    monkeypatch.setattr("agentic_trader.cli.ensure_llm_ready", lambda settings: None)
    monkeypatch.setattr("agentic_trader.cli.chat_with_persona", lambda **kwargs: "runtime is healthy")

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["chat", "--json", "--persona", "operator_liaison", "--message", "status?"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["persona"] == "operator_liaison"
    assert payload["message"] == "status?"
    assert payload["response"] == "runtime is healthy"


def test_dashboard_snapshot_json(monkeypatch, tmp_path: Path) -> None:
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
    db.upsert_service_state(
        state="running",
        continuous=True,
        poll_seconds=300,
        cycle_count=4,
        current_symbol="AAPL",
        message="Working.",
        pid=1234,
    )
    db.insert_service_event(level="info", event_type="agent_regime_started", message="Regime started.", cycle_count=4, symbol="AAPL")
    db.close()

    runner = CliRunner()
    result = runner.invoke(app, ["dashboard-snapshot"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["doctor"]["ollama_reachable"] is True
    assert payload["status"]["state"]["current_symbol"] == "AAPL"
    assert payload["logs"][0]["event_type"] == "agent_regime_started"
    assert payload["portfolio"]["available"] is True
