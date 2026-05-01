import json
from pathlib import Path
import pytest

from typer.testing import CliRunner

from agentic_trader.cli import app
from agentic_trader.config import Settings
from agentic_trader.runtime_feed import (
    append_chat_history,
    research_latest_snapshot_path,
)
from agentic_trader.schemas import (
    AgentStageTrace,
    BacktestReport,
    ChatHistoryEntry,
    ExecutionDecision,
    LLMHealthStatus,
    ManagerDecision,
    MarketSnapshot,
    OperatorInstruction,
    PreferenceUpdate,
    RegimeAssessment,
    ResearchCoordinatorBrief,
    ReviewNote,
    RiskPlan,
    RunArtifacts,
    StrategyPlan,
)
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.workflows.run_once import persist_run


def _raise_db_locked(*_args: object, **_kwargs: object) -> None:
    """
    Raise a RuntimeError to simulate a database lock.

    This helper always raises RuntimeError("db locked") and is intended for use in tests to emulate a locked or unavailable database.

    Raises:
        RuntimeError: with the message "db locked".
    """
    raise RuntimeError("db locked")


def test_cli_help_supports_short_and_long_forms() -> None:
    """
    Verifies that CLI commands accept both short (-h) and long (--help) help options.

    Asserts each tested subcommand exits with code 0 and its help output contains the "Usage:" header.
    """
    runner = CliRunner()

    for args in (
        ["--help"],
        ["-h"],
        ["run", "--help"],
        ["run", "-h"],
        ["broker-status", "--help"],
        ["broker-status", "-h"],
        ["provider-diagnostics", "--help"],
        ["provider-diagnostics", "-h"],
        ["v1-readiness", "--help"],
        ["v1-readiness", "-h"],
        ["evidence-bundle", "--help"],
        ["evidence-bundle", "-h"],
        ["hardware-profile", "--help"],
        ["hardware-profile", "-h"],
        ["research-status", "--help"],
        ["research-status", "-h"],
        ["research-refresh", "--help"],
        ["research-refresh", "-h"],
        ["research-flow-setup", "--help"],
        ["research-flow-setup", "-h"],
        ["research-crewai-setup", "--help"],
        ["research-crewai-setup", "-h"],
        ["trade-context", "--help"],
        ["trade-context", "-h"],
        ["tui", "--help"],
        ["tui", "-h"],
        ["menu", "--help"],
        ["menu", "-h"],
    ):
        result = runner.invoke(app, args)

        assert result.exit_code == 0
        assert "Usage:" in result.stdout


def _artifacts(symbol: str = "AAPL") -> RunArtifacts:
    """
    Builds a fully populated RunArtifacts instance with realistic sample data for use in tests.

    Parameters:
        symbol (str): Ticker symbol to apply to the snapshot and execution sections (defaults to "AAPL").

    Returns:
        RunArtifacts: An object containing a MarketSnapshot, ResearchCoordinatorBrief, RegimeAssessment,
        StrategyPlan, RiskPlan, ManagerDecision, ExecutionDecision, ReviewNote, and a single AgentStageTrace
        whose context_json and output_json are JSON-encoded strings.
    """
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


def test_status_preferences_and_portfolio_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """
    Verify status, preferences, and portfolio CLI JSON outputs reflect a completed service state and default settings.

    Sets up a temporary Settings and TradingDatabase with a service state of "completed", runs the CLI commands `status --json`, `preferences --json`, and `portfolio --json`, and asserts:
    - the runtime is reported as inactive and the service state is "completed";
    - the preferences report a "balanced" risk profile;
    - the portfolio snapshot cash equals the settings' default cash and there are no positions.
    """
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
    assert status_payload["runtime_mode"] == "operation"
    assert status_payload["state"]["state"] == "completed"
    assert status_payload["state"]["runtime_mode"] == "operation"

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
    """
    Verify the CLI `doctor --json` and `logs --json` outputs reflect LLM health and recent service/order records.

    Sets up a temporary Settings and monkeypatches the CLI to report a healthy LocalLLM, inserts a service event and an order into the test database, then invokes the `doctor` and `logs` CLI commands and asserts:
    - the doctor payload reports the provider reachable and model available,
    - the doctor payload contains `runtime_mode == "operation"`,
    - the latest order string begins with the inserted order summary and contains no parentheses,
    - the first entry returned by `logs --json` has `event_type == "service_started"`.
    """
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
    db.insert_order(
        {
            "order_id": "paper-test",
            "created_at": "2026-04-11T00:00:00+00:00",
            "symbol": "AAPL",
            "side": "buy",
            "approved": True,
            "entry_price": 100.0,
            "stop_loss": 95.0,
            "take_profit": 110.0,
            "position_size_pct": 0.05,
            "confidence": 0.72,
            "rationale": "Test order.",
        }
    )
    db.conn.close()

    runner = CliRunner()

    doctor_result = runner.invoke(app, ["doctor", "--json"])
    assert doctor_result.exit_code == 0
    doctor_payload = json.loads(doctor_result.stdout)
    assert doctor_payload["ollama_reachable"] is True
    assert doctor_payload["model_available"] is True
    assert doctor_payload["runtime_mode"] == "operation"
    assert doctor_payload["latest_order"].startswith("paper-test | AAPL buy")
    assert "(" not in doctor_payload["latest_order"]

    logs_result = runner.invoke(app, ["logs", "--json", "--limit", "5"])
    assert logs_result.exit_code == 0
    logs_payload = json.loads(logs_result.stdout)
    assert logs_payload[0]["event_type"] == "service_started"


def test_runtime_mode_checklist_blocks_operation_without_strict_gate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        strict_llm=False,
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

    result = CliRunner().invoke(app, ["runtime-mode-checklist", "operation", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["target_mode"] == "operation"
    assert payload["allowed"] is False
    strict_check = next(
        check for check in payload["checks"] if check["name"] == "strict_llm_enabled"
    )
    assert strict_check["passed"] is False


def test_runtime_mode_checklist_blocks_operation_when_provider_check_skipped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        runtime_mode="training",
        strict_llm=True,
    )
    settings.ensure_directories()
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)

    result = CliRunner().invoke(
        app,
        ["runtime-mode-checklist", "operation", "--skip-provider-check", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["target_mode"] == "operation"
    assert payload["allowed"] is False
    provider_check = next(
        check for check in payload["checks"] if check["name"] == "provider_reachable"
    )
    assert provider_check["passed"] is False
    assert provider_check["blocking"] is True


def test_runtime_mode_checklist_allows_training_without_provider_check(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        runtime_mode="operation",
    )
    settings.ensure_directories()
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)

    result = CliRunner().invoke(app, ["runtime-mode-checklist", "training", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["current_mode"] == "operation"
    assert payload["target_mode"] == "training"
    assert payload["allowed"] is True
    assert {check["name"] for check in payload["checks"]} >= {
        "diagnostic_scope",
        "runtime_no_hidden_trades",
    }


def test_rich_menu_eof_exits_cleanly(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)
    monkeypatch.setattr("agentic_trader.tui.get_settings", lambda: settings)
    monkeypatch.setattr(
        "agentic_trader.tui.LocalLLM.health_check",
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
    result = runner.invoke(app, ["menu"], input="2\n1\n")

    assert result.exit_code == 0
    assert "Control room closed cleanly" in result.stdout


def test_preferences_and_portfolio_json_survive_db_lock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """
    Ensures preferences and portfolio CLI JSON commands handle a locked database and return fallback responses.

    Monkeypatches the CLI settings and replaces the database opener with a function that raises RuntimeError("db locked"), then invokes the `preferences --json` and `portfolio --json` commands and asserts both exit successfully with `available == False` and expected fallback values (`risk_profile == "balanced"`, `positions == []`).
    """
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)
    monkeypatch.setattr(
        "agentic_trader.cli._open_db",
        _raise_db_locked,
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


def test_journal_risk_review_and_trace_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
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
    """
    Integration test that verifies the CLI 'chat' command returns the expected JSON for a persona message.

    Mocks CLI settings and LLM/chat dependencies, invokes `chat --json --persona operator_liaison --message status?`, and asserts the returned JSON contains the requested `persona`, `message`, and the `response` value.
    """
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


def test_training_backtest_allows_diagnostic_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """
    Verifies that running the backtest CLI in training mode falls back to a diagnostic execution when the LLM gate fails.

    Runs the `backtest` command with training runtime_mode while mocking `ensure_llm_ready` to raise `RuntimeError("model unavailable")` and stubbing the backtest runner to capture the `allow_fallback` flag. Asserts the CLI exits successfully, that the backtest was invoked with `allow_fallback == True`, and that stdout contains the phrase "Training Diagnostic Mode".
    """
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        runtime_mode="training",
    )
    settings.ensure_directories()
    captured: dict[str, object] = {}
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)

    def _blocked_llm(_settings: Settings) -> None:
        """
        Always raises a RuntimeError indicating the LLM model is unavailable.

        Raises:
            RuntimeError: with message "model unavailable".
        """
        raise RuntimeError("model unavailable")

    def _backtest(**kwargs: object) -> BacktestReport:
        """
        Test stub that constructs a deterministic BacktestReport for the given run parameters and records whether fallback was allowed.

        Parameters:
            kwargs: Expected keys:
                - symbol (str): Ticker symbol for the backtest.
                - interval (str): Data interval (e.g., "1d").
                - lookback (str): Lookback window descriptor (e.g., "180d").
                - warmup_bars (int): Number of warmup bars; must be an int.
                - allow_fallback (bool): Whether diagnostic fallback was permitted; recorded to `captured["allow_fallback"]`.

        Returns:
            BacktestReport: A report populated with the provided identifiers, the given warmup_bars, deterministic zeroed metrics, and starting/ending equity of 100000.0.
        """
        captured["allow_fallback"] = kwargs["allow_fallback"]
        warmup_bars = kwargs["warmup_bars"]
        assert isinstance(warmup_bars, int)
        return BacktestReport(
            symbol=str(kwargs["symbol"]),
            interval=str(kwargs["interval"]),
            lookback=str(kwargs["lookback"]),
            warmup_bars=warmup_bars,
            total_cycles=0,
            total_trades=0,
            closed_trades=0,
            win_rate=0.0,
            expectancy=0.0,
            total_return_pct=0.0,
            max_drawdown_pct=0.0,
            exposure_pct=0.0,
            fallback_cycles=0,
            starting_equity=100_000.0,
            ending_equity=100_000.0,
            trades=[],
        )

    monkeypatch.setattr("agentic_trader.cli.ensure_llm_ready", _blocked_llm)
    monkeypatch.setattr("agentic_trader.cli.run_walk_forward_backtest", _backtest)

    result = CliRunner().invoke(
        app,
        [
            "backtest",
            "--symbol",
            "AAPL",
            "--interval",
            "1d",
            "--lookback",
            "180d",
        ],
    )

    assert result.exit_code == 0
    assert captured["allow_fallback"] is True
    assert "Training Diagnostic Mode" in result.stdout


def test_operation_backtest_blocks_when_llm_gate_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """
    Verifies that running backtest in "operation" runtime mode fails when the LLM readiness gate raises an error.

    Invokes the CLI backtest command with a mocked settings object whose runtime_mode is "operation" and a patched `ensure_llm_ready` that raises RuntimeError("model unavailable"), then asserts the command exits with a non-zero code and that the raised exception contains "model unavailable".
    """
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        runtime_mode="operation",
    )
    settings.ensure_directories()
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)

    def _blocked_llm(_settings: Settings) -> None:
        """
        Always raises a RuntimeError indicating the LLM model is unavailable.

        Raises:
            RuntimeError: with message "model unavailable".
        """
        raise RuntimeError("model unavailable")

    monkeypatch.setattr("agentic_trader.cli.ensure_llm_ready", _blocked_llm)

    result = CliRunner().invoke(app, ["backtest", "--symbol", "AAPL"])

    assert result.exit_code != 0
    assert "model unavailable" in str(result.exception)


def test_dashboard_snapshot_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """
    Validates that the `dashboard-snapshot` CLI JSON aggregates persisted run artifacts, service state, LLM health, logs, portfolio, UI sections, and replay snapshot.

    Asserts that the payload includes:
    - doctor health indicating the LLM provider is reachable and runtime mode is `"operation"`.
    - status reflecting runtime mode `"operation"` and `current_symbol == "AAPL"`.
    - supervisor and broker summaries (launch count and backend).
    - recent log entries including an `"agent_regime_started"` event.
    - agent activity showing `current_stage == "regime"` with status `"running"`.
    - portfolio availability (`available is True`).
    - presence of UI sections: `memoryExplorer`, `retrievalInspection`, and `recentRuns` with the first recent run symbol `"AAPL"`.
    - trade and market context with `tradeContext.record.symbol == "AAPL"`.
    - replay availability and that the replay snapshot's `mtf_alignment == "bullish"`.
    """
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
    assert payload["doctor"]["runtime_mode"] == "operation"
    assert payload["status"]["runtime_mode"] == "operation"
    assert payload["status"]["state"]["current_symbol"] == "AAPL"
    assert payload["supervisor"]["state"]["launch_count"] == 0
    assert payload["broker"]["backend"] == "paper"
    assert payload["broker"]["external_paper"] is False
    assert "healthcheck" in payload["broker"]
    assert payload["providerDiagnostics"]["market_data"]["selected_provider"] == "yahoo_market"
    assert isinstance(payload["providerDiagnostics"]["warnings"], list)
    assert payload["v1Readiness"]["paper_operations"]["allowed"] is False
    assert payload["v1Readiness"]["alpaca_paper"]["ready"] is False
    assert payload["research"]["status"] == "disabled"
    assert payload["logs"][0]["event_type"] == "agent_regime_started"
    assert payload["agentActivity"]["current_stage"] == "regime"
    assert payload["agentActivity"]["current_stage_status"] == "running"
    assert payload["portfolio"]["available"] is True
    assert "memoryExplorer" in payload
    assert "retrievalInspection" in payload
    assert "recentRuns" in payload
    assert payload["recentRuns"]["runs"][0]["symbol"] == "AAPL"
    assert "tradeContext" in payload
    assert "marketContext" in payload
    assert payload["tradeContext"]["record"]["symbol"] == "AAPL"
    assert payload["replay"]["available"] is True
    assert payload["replay"]["replay"]["snapshot"]["mtf_alignment"] == "bullish"


def test_evidence_bundle_json_creates_read_only_artifacts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(
        runtime_dir=tmp_path / "runtime",
        database_path=tmp_path / "runtime" / "agentic_trader.duckdb",
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

    artifacts_root = tmp_path / "artifacts"
    result = CliRunner().invoke(
        app,
        [
            "evidence-bundle",
            "--output-dir",
            str(artifacts_root),
            "--label",
            "evidence-test",
            "--no-latest-smoke",
            "--json",
        ],
    )

    assert result.exit_code == 0
    manifest = json.loads(result.stdout)
    bundle_dir = Path(manifest["bundle_dir"])
    assert bundle_dir == artifacts_root / "evidence-test"
    files = manifest["files"]
    for key in (
        "dashboard",
        "status",
        "broker",
        "provider_diagnostics",
        "v1_readiness",
        "supervisor",
        "logs",
        "runtime_mode_operation",
        "research",
        "hardware_profile",
        "manifest",
    ):
        assert Path(files[key]).exists()

    dashboard = json.loads(Path(files["dashboard"]).read_text(encoding="utf-8"))
    assert "providerDiagnostics" in dashboard
    assert "v1Readiness" in dashboard
    broker = json.loads(Path(files["broker"]).read_text(encoding="utf-8"))
    assert broker["backend"] == "paper"


def test_hardware_profile_json_reports_recommendations(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        model_name="qwen3:8b",
        max_output_tokens=4096,
    )
    settings.ensure_directories()
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)
    monkeypatch.setattr("agentic_trader.cli.os.cpu_count", lambda: 8)
    monkeypatch.setattr("agentic_trader.cli._total_memory_bytes", lambda: 32 * 1024**3)
    monkeypatch.setattr(
        "agentic_trader.cli._accelerator_payload",
        lambda: {"type": "test", "detail": "deterministic"},
    )

    result = CliRunner().invoke(app, ["hardware-profile", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["hardware"]["cpu_count"] == 8
    assert payload["hardware"]["memory_gb"] == 32.0
    assert payload["hardware"]["accelerator"]["type"] == "test"
    assert payload["configured_runtime"]["estimated_model_size_b"] == 8.0
    assert payload["recommendations"]["safe_parallel_agents"] == 2
    assert payload["recommendations"]["profile"] == "standard-local"


def test_instruct_json_reports_instruction_and_applied_preferences(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)
    monkeypatch.setattr("agentic_trader.cli.ensure_llm_ready", lambda _settings: None)
    monkeypatch.setattr(
        "agentic_trader.cli.interpret_operator_instruction",
        lambda **_kwargs: OperatorInstruction(
            summary="Move to a more conservative profile.",
            should_update_preferences=True,
            preference_update=PreferenceUpdate(
                risk_profile="conservative",
                behavior_preset="capital_preservation",
            ),
            requires_confirmation=False,
            rationale="Structured test instruction.",
        ),
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "instruct",
            "--message",
            "be conservative",
            "--apply",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["instruction"]["summary"] == "Move to a more conservative profile."
    assert payload["instruction"]["should_update_preferences"] is True
    assert payload["applied"] is True
    assert payload["updated_preferences"]["risk_profile"] == "conservative"
    assert payload["updated_preferences"]["behavior_preset"] == "capital_preservation"


def test_memory_explorer_and_retrieval_inspection_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """
    Validates JSON availability semantics for `memory-explorer` and `retrieval-inspection` CLI commands when no persisted run exists.

    Sets up temporary settings and an empty TradingDatabase, then invokes the CLI:
    - `memory-explorer --json` must exit successfully with `"available": false`.
    - `retrieval-inspection --json` must exit successfully with `"available": true` and an empty `stages` list.
    """
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
    """
    Verifies the CLI JSON output of the `trade-context` command reflects a persisted run's execution and fundamental assessment.

    Persists a run for symbol "NVDA", invokes `trade-context --json`, and asserts the payload is available and contains:
    - the persisted record's symbol and execution rationale,
    - fundamental assessment with `overall_bias == "neutral"` and an `evidence_vs_inference` field,
    - execution fields `execution_backend`, `execution_adapter`, and `execution_outcome_status` set to `"paper"`, `"paper"`, and `"filled"` respectively.
    """
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
    assert payload["record"]["fundamental_assessment"]["overall_bias"] == "neutral"
    assert "evidence_vs_inference" in payload["record"]["fundamental_assessment"]
    assert payload["record"]["execution_backend"] == "paper"
    assert payload["record"]["execution_adapter"] == "paper"
    assert payload["record"]["execution_outcome_status"] == "filled"


def test_trade_context_human_output_shows_execution_outcome(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)

    persist_run(settings=settings, artifacts=_artifacts("NVDA"))

    runner = CliRunner()
    result = runner.invoke(app, ["trade-context"])
    assert result.exit_code == 0
    assert "Execution Backend" in result.stdout
    assert "Execution Adapter" in result.stdout
    assert "Execution Outcome" in result.stdout
    assert "Rejection Reason" in result.stdout
    assert "paper" in result.stdout
    assert "filled" in result.stdout


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

    human_result = runner.invoke(app, ["supervisor-status"])
    assert human_result.exit_code == 0
    assert "line-2" in human_result.stdout


def test_broker_status_json_reports_execution_guardrails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="live",
        live_execution_enabled=False,
        execution_kill_switch_active=False,
    )
    settings.ensure_directories()
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)

    runner = CliRunner()
    result = runner.invoke(app, ["broker-status", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["backend"] == "live"
    assert payload["state"] == "blocked"
    assert payload["live_requested"] is True
    assert payload["live_ready"] is False


def test_research_status_json_reports_sidecar_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        research_mode="training",
        research_sidecar_enabled=True,
        research_symbols="AAPL,MSFT",
    )
    settings.ensure_directories()
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)

    runner = CliRunner()
    result = runner.invoke(app, ["research-status", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["mode"] == "training"
    assert payload["enabled"] is True
    assert payload["status"] == "idle"
    assert payload["watched_symbols"] == ["AAPL", "MSFT"]
    assert payload["provider_health"][0]["provider_id"] == "sec_edgar_research"
    assert payload["latestSnapshot"]["available"] is False
    assert settings.database_path.exists() is False


def test_research_refresh_json_persists_snapshot(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        research_mode="training",
        research_sidecar_enabled=True,
        research_symbols="AAPL",
    )
    settings.ensure_directories()
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)

    runner = CliRunner()
    result = runner.invoke(app, ["research-refresh", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["persisted"] is True
    assert payload["state"]["status"] == "completed"
    assert payload["record"]["state"]["watched_symbols"] == ["AAPL"]
    assert research_latest_snapshot_path(settings).exists()
    assert settings.database_path.exists() is False

    status_result = runner.invoke(app, ["research-status", "--json"])
    assert status_result.exit_code == 0
    status_payload = json.loads(status_result.stdout)
    assert status_payload["latestSnapshot"]["available"] is True
    assert (
        status_payload["latestSnapshot"]["record"]["snapshot_id"]
        == payload["record"]["snapshot_id"]
    )
    assert settings.database_path.exists() is False


def test_research_flow_setup_json_reports_optional_boundary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)

    runner = CliRunner()
    result = runner.invoke(app, ["research-flow-setup", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["core_dependency"] is False
    assert payload["flow_dir"].endswith("sidecars/research_flow")
    assert "environment_exists" in payload
    assert payload["python_version"] == "3.13"
    assert "pnpm run setup:research-flow" in payload["recommended_commands"]
    assert any("optional" in note.lower() for note in payload["notes"])


def test_research_crewai_setup_alias_still_reports_optional_boundary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)

    runner = CliRunner()
    result = runner.invoke(app, ["research-crewai-setup", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["flow_dir"].endswith("sidecars/research_flow")


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
    assert snapshot_payload["research"]["mode"] == "off"
    assert snapshot_payload["research"]["enabled"] is False
    assert (
        snapshot_payload["chatHistory"]["entries"][0]["persona"] == "operator_liaison"
    )


def test_market_cache_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """
    Verify that the `market-cache` CLI command reports available market snapshot files and their filenames.

    Creates a single snapshot CSV in the configured market_data_cache_dir, invokes `market-cache --json`, and asserts the JSON `count` is 1 and the first entry's `filename` matches the created file.
    """
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


def test_provider_diagnostics_json_reports_source_ladder(
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
    result = runner.invoke(app, ["provider-diagnostics", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["market_data"]["selected_provider"] == "yahoo_market"
    assert payload["market_data"]["selected_role"] == "fallback"
    assert payload["configured_keys"]["alpaca"] is False
    assert any(
        provider["provider_id"] == "sec_edgar_fundamentals"
        for provider in payload["providers"]
    )
    assert payload["warnings"]


def test_v1_readiness_json_reports_paper_and_alpaca_sections(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="paper",
        live_execution_enabled=False,
    )
    settings.ensure_directories()
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)

    runner = CliRunner()
    result = runner.invoke(app, ["v1-readiness", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["paper_operations"]["allowed"] is False
    assert payload["alpaca_paper"]["ready"] is False
    assert payload["broker"]["backend"] == "paper"
    assert any(
        check["name"] == "llm_provider_ready" and check["passed"] is False
        for check in payload["paper_operations"]["checks"]
    )
