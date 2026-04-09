import json
from pathlib import Path
import pytest

from typer.testing import CliRunner

from agentic_trader.cli import app
from agentic_trader.config import Settings
from agentic_trader.runtime_feed import append_chat_history
from agentic_trader.schemas import (
    AgentStageTrace,
    ChatHistoryEntry,
    ExecutionDecision,
    LLMHealthStatus,
    ManagerDecision,
    MarketSnapshot,
    RegimeAssessment,
    ResearchCoordinatorBrief,
    ReviewNote,
    RiskPlan,
    RunArtifacts,
    StrategyPlan,
)
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.workflows.run_once import persist_run


def _artifacts(symbol: str = "AAPL") -> RunArtifacts:
    return RunArtifacts(
        snapshot=MarketSnapshot(
            symbol=symbol,
            interval="1d",
            last_close=100.0,
            ema_20=102.0,
            ema_50=98.0,
            atr_14=2.0,
            rsi_14=58.0,
            volatility_20=0.12,
            return_5=0.03,
            return_20=0.09,
            volume_ratio_20=1.1,
            higher_timeframe="1wk",
            htf_last_close=108.0,
            htf_ema_20=105.0,
            htf_ema_50=101.0,
            htf_rsi_14=61.0,
            htf_return_5=0.04,
            mtf_alignment="bullish",
            mtf_confidence=0.72,
            bars_analyzed=160,
        ),
        coordinator=ResearchCoordinatorBrief(
            market_focus="trend_following",
            priority_signals=["trend_alignment"],
            caution_flags=[],
            summary="Coordinator summary",
        ),
        regime=RegimeAssessment(
            regime="trend_up",
            direction_bias="long",
            confidence=0.75,
            reasoning="Trend is aligned.",
        ),
        strategy=StrategyPlan(
            strategy_family="trend_following",
            action="buy",
            timeframe="swing",
            entry_logic="Buy while price stays above moving averages.",
            invalidation_logic="Exit on close below EMA20.",
            confidence=0.74,
        ),
        risk=RiskPlan(
            position_size_pct=0.1,
            stop_loss=95.0,
            take_profit=110.0,
            risk_reward_ratio=2.0,
            max_holding_bars=20,
            notes="Risk plan",
        ),
        manager=ManagerDecision(
            approved=True,
            action_bias="buy",
            confidence_cap=0.74,
            size_multiplier=1.0,
            rationale="Manager approved the trend setup.",
        ),
        execution=ExecutionDecision(
            approved=True,
            side="buy",
            symbol=symbol,
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=110.0,
            position_size_pct=0.1,
            confidence=0.74,
            rationale="Execution approved.",
        ),
        review=ReviewNote(
            summary="Review captured the approved long setup.",
            strengths=["Aligned trend"],
            warnings=[],
            next_checks=["Watch invalidation logic"],
        ),
        agent_traces=[
            AgentStageTrace(
                role="coordinator",
                model_name="qwen3:8b",
                context_json=json.dumps(
                    {
                        "market_session": {
                            "venue": "NASDAQ",
                            "session_state": "open",
                            "tradable_now": True,
                        },
                        "retrieved_memories": ["prior trend continuation"],
                        "memory_notes": ["last winner looked similar"],
                        "shared_memory_bus": [],
                        "recent_runs": ["run-123"],
                        "tool_outputs": ["market_session: venue=NASDAQ state=open"],
                        "upstream_context": {},
                    }
                ),
                output_json=json.dumps(
                    {
                        "market_focus": "trend_following",
                        "summary": "Coordinator summary",
                    }
                ),
            )
        ],
    )


def test_status_preferences_and_portfolio_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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


def test_doctor_and_logs_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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
    db.insert_service_event(
        level="info", event_type="service_started", message="Started."
    )
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


def test_preferences_and_portfolio_json_survive_db_lock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)
    monkeypatch.setattr(
        "agentic_trader.cli._open_db",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("db locked")),
    )

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


def test_journal_risk_review_and_trace_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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


def test_chat_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)
    monkeypatch.setattr("agentic_trader.cli.ensure_llm_ready", lambda settings: None)
    monkeypatch.setattr(
        "agentic_trader.cli.chat_with_persona", lambda **kwargs: "runtime is healthy"
    )

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


def test_dashboard_snapshot_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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
    db.close()
    persist_run(settings=settings, artifacts=_artifacts("AAPL"))
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
    db.insert_service_event(
        level="info",
        event_type="agent_regime_started",
        message="Regime started.",
        cycle_count=4,
        symbol="AAPL",
    )
    db.close()

    runner = CliRunner()
    result = runner.invoke(app, ["dashboard-snapshot"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["doctor"]["ollama_reachable"] is True
    assert payload["status"]["state"]["current_symbol"] == "AAPL"
    assert payload["supervisor"]["state"]["launch_count"] == 0
    assert payload["logs"][0]["event_type"] == "agent_regime_started"
    assert payload["agentActivity"]["current_stage"] == "regime"
    assert payload["agentActivity"]["current_stage_status"] == "running"
    assert payload["portfolio"]["available"] is True
    assert "memoryExplorer" in payload
    assert "retrievalInspection" in payload
    assert "tradeContext" in payload
    assert payload["tradeContext"]["record"]["symbol"] == "AAPL"
    assert payload["replay"]["available"] is True
    assert payload["replay"]["replay"]["snapshot"]["mtf_alignment"] == "bullish"


def test_memory_explorer_and_retrieval_inspection_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)

    db = TradingDatabase(settings)
    record = db.latest_run()
    assert record is None
    db.close()

    runner = CliRunner()

    memory_result = runner.invoke(app, ["memory-explorer", "--json"])
    assert memory_result.exit_code == 0
    memory_payload = json.loads(memory_result.stdout)
    assert memory_payload["available"] is False

    retrieval_result = runner.invoke(app, ["retrieval-inspection", "--json"])
    assert retrieval_result.exit_code == 0
    retrieval_payload = json.loads(retrieval_result.stdout)
    assert retrieval_payload["available"] is True
    assert retrieval_payload["stages"] == []


def test_replay_run_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)

    persist_run(settings=settings, artifacts=_artifacts("MSFT"))

    runner = CliRunner()
    result = runner.invoke(app, ["replay-run", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["available"] is True
    assert payload["replay"]["symbol"] == "MSFT"
    assert payload["replay"]["consensus"]["alignment_level"] == "mixed"
    assert payload["replay"]["snapshot"]["higher_timeframe"] == "1wk"
    assert payload["replay"]["manager_override_notes"] == [
        "Manager accepted the specialist plan without additional overrides."
    ]
    assert payload["replay"]["manager_conflicts"] == []
    assert payload["replay"]["manager_resolution_notes"] == [
        "Manager accepted the specialist plan without additional overrides."
    ]
    assert payload["replay"]["stages"][0]["shared_memory_bus"] == []
    assert payload["replay"]["stages"][0]["retrieved_memories"] == [
        "prior trend continuation"
    ]


def test_trade_context_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)

    persist_run(settings=settings, artifacts=_artifacts("NVDA"))

    runner = CliRunner()
    result = runner.invoke(app, ["trade-context", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["available"] is True
    assert payload["record"]["symbol"] == "NVDA"
    assert payload["record"]["execution_rationale"] == "Execution approved."


def test_supervisor_status_json_includes_log_tails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    stdout_path = tmp_path / "service.out.log"
    stderr_path = tmp_path / "service.err.log"
    stdout_path.write_text("line-1\nline-2\n", encoding="utf-8")
    stderr_path.write_text("err-1\n", encoding="utf-8")
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)

    db = TradingDatabase(settings)
    db.upsert_service_state(
        state="starting",
        continuous=True,
        poll_seconds=300,
        cycle_count=0,
        message="Background service spawned.",
        pid=4242,
        background_mode=True,
        launch_count=2,
        restart_count=1,
        stdout_log_path=str(stdout_path),
        stderr_log_path=str(stderr_path),
    )
    db.close()

    runner = CliRunner()
    result = runner.invoke(app, ["supervisor-status", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["state"]["background_mode"] is True
    assert payload["state"]["launch_count"] == 2
    assert payload["state"]["restart_count"] == 1
    assert payload["stdout_tail"][-1] == "line-2"
    assert payload["stderr_tail"][-1] == "err-1"


def test_calendar_status_and_dashboard_snapshot_include_calendar(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
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

    runner = CliRunner()

    calendar_result = runner.invoke(
        app, ["calendar-status", "--json", "--symbol", "THYAO.IS"]
    )
    assert calendar_result.exit_code == 0
    calendar_payload = json.loads(calendar_result.stdout)
    assert calendar_payload["available"] is True
    assert calendar_payload["session"]["venue"] == "BIST"
    append_chat_history(
        settings,
        ChatHistoryEntry(
            entry_id="chat-1",
            created_at="2026-01-01T00:00:00+00:00",
            persona="operator_liaison",
            user_message="What happened?",
            response_text="The system is waiting for the next cycle.",
        ),
    )

    snapshot_result = runner.invoke(app, ["dashboard-snapshot"])
    assert snapshot_result.exit_code == 0
    snapshot_payload = json.loads(snapshot_result.stdout)
    assert "calendar" in snapshot_payload
    assert snapshot_payload["calendar"]["available"] is True
    assert "news" in snapshot_payload
    assert snapshot_payload["news"]["mode"] == "off"
    assert "marketCache" in snapshot_payload
    assert snapshot_payload["chatHistory"]["entries"][0]["persona"] == "operator_liaison"


def test_market_cache_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        market_data_cache_dir=tmp_path / "snapshots",
    )
    settings.ensure_directories()
    (settings.market_data_cache_dir / "AAPL__1d__180d.csv").write_text(
        "date,open,high,low,close,volume\n", encoding="utf-8"
    )
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)

    runner = CliRunner()
    result = runner.invoke(app, ["market-cache", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["count"] == 1
    assert payload["entries"][0]["filename"] == "AAPL__1d__180d.csv"


def test_news_brief_json_defaults_to_tool_only_disabled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        news_mode="off",
    )
    settings.ensure_directories()
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)

    runner = CliRunner()
    result = runner.invoke(app, ["news-brief", "--json", "--symbol", "AAPL"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["mode"] == "off"
    assert payload["symbol"] == "AAPL"
    assert payload["headlines"] == []
