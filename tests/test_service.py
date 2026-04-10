from pathlib import Path
from typing import Any
import duckdb
import pytest

from agentic_trader.cli import app
from agentic_trader.config import Settings
from agentic_trader.schemas import (
    ExecutionDecision,
    LLMHealthStatus,
    ManagerDecision,
    MarketSnapshot,
    RegimeAssessment,
    ResearchCoordinatorBrief,
    RiskPlan,
    ReviewNote,
    RunArtifacts,
    StrategyPlan,
)
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.workflows.service import (
    restart_background_service,
    run_service,
    start_background_service,
)
from typer.testing import CliRunner


def _artifacts(symbol: str) -> RunArtifacts:
    return RunArtifacts(
        snapshot=MarketSnapshot(
            symbol=symbol,
            interval="1d",
            last_close=100.0,
            ema_20=101.0,
            ema_50=99.0,
            atr_14=2.0,
            rsi_14=55.0,
            volatility_20=0.12,
            return_5=0.02,
            return_20=0.08,
            volume_ratio_20=1.1,
            bars_analyzed=120,
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
            confidence=0.7,
            reasoning="Test regime",
        ),
        strategy=StrategyPlan(
            strategy_family="trend_following",
            action="buy",
            timeframe="swing",
            entry_logic="Test entry",
            invalidation_logic="Test invalidation",
            confidence=0.7,
        ),
        risk=RiskPlan(
            position_size_pct=0.05,
            stop_loss=95.0,
            take_profit=110.0,
            risk_reward_ratio=2.0,
            max_holding_bars=20,
            notes="Test risk",
        ),
        manager=ManagerDecision(
            approved=True,
            action_bias="buy",
            confidence_cap=0.7,
            size_multiplier=1.0,
            rationale="Manager approved",
        ),
        execution=ExecutionDecision(
            approved=True,
            side="buy",
            symbol=symbol,
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=110.0,
            position_size_pct=0.05,
            confidence=0.7,
            rationale="Test execution",
        ),
        review=ReviewNote(
            summary="Review summary",
            strengths=["x"],
            warnings=[],
            next_checks=["y"],
        ),
    )


def test_service_state_migration_allows_legacy_duckdb_file(tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    conn = duckdb.connect(str(settings.database_path))
    conn.execute(
        """
        create table service_state (
            service_name varchar primary key,
            state varchar not null,
            updated_at varchar not null,
            started_at varchar,
            last_heartbeat_at varchar,
            continuous boolean not null,
            poll_seconds integer,
            cycle_count integer not null,
            current_symbol varchar,
            last_error varchar,
            message varchar not null
        )
        """
    )
    conn.execute(
        """
        insert into service_state (
            service_name, state, updated_at, continuous, poll_seconds,
            cycle_count, message
        )
        values ('orchestrator', 'running', '2026-04-11T00:00:00+00:00',
                true, 300, 3, 'Legacy state.')
        """
    )
    conn.close()

    db = TradingDatabase(settings)
    state = db.get_service_state()
    db.close()

    assert state is not None
    assert state.symbols == []
    assert state.stop_requested is False
    assert state.background_mode is False
    assert state.launch_count == 0
    assert state.restart_count == 0


def test_run_service_records_runtime_state_and_events(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()

    monkeypatch.setattr(
        "agentic_trader.workflows.service.ensure_llm_ready",
        lambda current_settings: LLMHealthStatus(
            provider="ollama",
            base_url=current_settings.base_url,
            model_name=current_settings.model_name,
            service_reachable=True,
            model_available=True,
            message="ok",
        ),
    )
    monkeypatch.setattr(
        "agentic_trader.workflows.service.run_once",
        lambda **kwargs: _artifacts(kwargs["symbol"]),
    )
    monkeypatch.setattr(
        "agentic_trader.workflows.service.persist_run",
        lambda **kwargs: "paper-test-order",
    )

    results = run_service(
        settings=settings,
        symbols=["AAPL", "MSFT"],
        interval="1d",
        lookback="180d",
        poll_seconds=1,
        continuous=False,
        max_cycles=None,
    )

    assert len(results) == 2

    db = TradingDatabase(settings)
    state = db.get_service_state()
    events = db.list_service_events(limit=10)

    assert state is not None
    assert state.state == "completed"
    assert state.cycle_count == 1
    assert state.symbols == ["AAPL", "MSFT"]
    assert state.interval == "1d"
    assert state.lookback == "180d"
    assert state.current_symbol is None
    assert {event.event_type for event in events} >= {
        "service_started",
        "cycle_started",
        "symbol_completed",
        "service_completed",
    }


def test_run_service_records_agent_stage_events(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()

    monkeypatch.setattr(
        "agentic_trader.workflows.service.ensure_llm_ready",
        lambda current_settings: LLMHealthStatus(
            provider="ollama",
            base_url=current_settings.base_url,
            model_name=current_settings.model_name,
            service_reachable=True,
            model_available=True,
            message="ok",
        ),
    )

    def _run_once_with_progress(**kwargs: Any) -> RunArtifacts:
        progress = kwargs["progress_callback"]
        progress("coordinator", "started", "Coordinator started.")
        progress("coordinator", "completed", "Coordinator finished.")
        progress("manager", "started", "Manager started.")
        progress("manager", "completed", "Manager finished.")
        return _artifacts(kwargs["symbol"])

    monkeypatch.setattr(
        "agentic_trader.workflows.service.run_once", _run_once_with_progress
    )
    monkeypatch.setattr(
        "agentic_trader.workflows.service.persist_run",
        lambda **kwargs: "paper-test-order",
    )

    run_service(
        settings=settings,
        symbols=["AAPL"],
        interval="1d",
        lookback="180d",
        poll_seconds=1,
        continuous=False,
        max_cycles=None,
    )

    db = TradingDatabase(settings)
    events = db.list_service_events(limit=10)
    event_types = {event.event_type for event in events}
    assert "agent_coordinator_started" in event_types
    assert "agent_coordinator_completed" in event_types
    assert "agent_manager_started" in event_types
    assert "agent_manager_completed" in event_types


def test_run_service_respects_stop_request(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)

    monkeypatch.setattr(
        "agentic_trader.workflows.service.ensure_llm_ready",
        lambda current_settings: LLMHealthStatus(
            provider="ollama",
            base_url=current_settings.base_url,
            model_name=current_settings.model_name,
            service_reachable=True,
            model_available=True,
            message="ok",
        ),
    )

    def _run_once_with_stop(**kwargs: Any) -> RunArtifacts:
        db.request_stop_service()
        return _artifacts(kwargs["symbol"])

    monkeypatch.setattr(
        "agentic_trader.workflows.service.run_once", _run_once_with_stop
    )
    monkeypatch.setattr(
        "agentic_trader.workflows.service.persist_run",
        lambda **kwargs: "paper-test-order",
    )

    results = run_service(
        settings=settings,
        symbols=["AAPL", "MSFT"],
        interval="1d",
        lookback="180d",
        poll_seconds=1,
        continuous=True,
        max_cycles=None,
    )

    state = db.get_service_state()
    assert len(results) == 1
    assert state is not None
    assert state.state == "stopped"
    assert state.stop_requested is True


def test_start_background_service_records_spawn(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()

    class _FakeProcess:
        pid = 4242

    def _fake_popen(*args: Any, **kwargs: Any) -> _FakeProcess:
        return _FakeProcess()

    monkeypatch.setattr(
        "agentic_trader.workflows.service.subprocess.Popen", _fake_popen
    )

    pid = start_background_service(
        settings=settings,
        symbols=["AAPL", "MSFT"],
        interval="1d",
        lookback="180d",
        poll_seconds=300,
        continuous=True,
        max_cycles=None,
        workdir=tmp_path,
    )

    db = TradingDatabase(settings)
    state = db.get_service_state()
    assert pid == 4242
    assert state is not None
    assert state.pid == 4242
    assert state.state == "starting"
    assert state.background_mode is True
    assert state.launch_count == 1
    assert state.restart_count == 0
    assert state.symbols == ["AAPL", "MSFT"]
    assert state.interval == "1d"
    assert state.lookback == "180d"


def test_start_background_service_recovers_stale_pid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
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
        cycle_count=4,
        current_symbol="AAPL",
        message="Processing AAPL",
        pid=99999,
    )

    class _FakeProcess:
        pid = 4343

    def _fake_popen_stale(*args: Any, **kwargs: Any) -> _FakeProcess:
        return _FakeProcess()

    monkeypatch.setattr(
        "agentic_trader.workflows.service.is_process_alive", lambda pid: False
    )
    monkeypatch.setattr(
        "agentic_trader.workflows.service.subprocess.Popen",
        _fake_popen_stale,
    )

    pid = start_background_service(
        settings=settings,
        symbols=["AAPL"],
        interval="1d",
        lookback="180d",
        poll_seconds=300,
        continuous=True,
        max_cycles=None,
        workdir=tmp_path,
    )

    updated = db.get_service_state()
    events = db.list_service_events(limit=5)
    assert pid == 4343
    assert updated is not None
    assert updated.pid == 4343
    assert updated.state == "starting"
    assert updated.symbols == ["AAPL"]
    assert any(event.event_type == "stale_service_recovered" for event in events)


def test_restart_background_service_uses_last_recorded_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
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
        cycle_count=4,
        symbols=["AAPL", "MSFT"],
        interval="1d",
        lookback="180d",
        max_cycles=None,
        current_symbol="AAPL",
        message="Processing AAPL",
        pid=99999,
    )

    monkeypatch.setattr("agentic_trader.workflows.service.is_process_alive", lambda pid: False)
    monkeypatch.setattr(
        "agentic_trader.workflows.service.start_background_service",
        lambda **kwargs: 5151,
    )

    pid = restart_background_service(settings=settings, grace_seconds=0.0, workdir=tmp_path)

    assert pid == 5151


def test_stop_service_command_marks_stop_requested(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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
        cycle_count=3,
        current_symbol="AAPL",
        message="Running",
        pid=4242,
        stop_requested=False,
    )

    runner = CliRunner()
    monkeypatch.setattr("agentic_trader.cli.is_process_alive", lambda pid: True)
    result = runner.invoke(
        app,
        ["stop-service"],
        env={
            "AGENTIC_TRADER_RUNTIME_DIR": str(tmp_path),
            "AGENTIC_TRADER_DATABASE_PATH": str(tmp_path / "agentic_trader.duckdb"),
        },
    )

    updated = db.get_service_state()
    assert result.exit_code == 0
    assert updated is not None
    assert updated.stop_requested is True
    assert updated.state == "stopping"


def test_run_service_records_last_terminal_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    monkeypatch.setattr(
        "agentic_trader.workflows.service.ensure_llm_ready",
        lambda current_settings: LLMHealthStatus(
            provider="ollama",
            base_url=current_settings.base_url,
            model_name=current_settings.model_name,
            service_reachable=True,
            model_available=True,
            message="ok",
        ),
    )
    monkeypatch.setattr(
        "agentic_trader.workflows.service.run_once",
        lambda **kwargs: _artifacts(kwargs["symbol"]),
    )
    monkeypatch.setattr(
        "agentic_trader.workflows.service.persist_run",
        lambda **kwargs: "paper-test-order",
    )

    run_service(
        settings=settings,
        symbols=["AAPL"],
        interval="1d",
        lookback="180d",
        poll_seconds=1,
        continuous=False,
        max_cycles=None,
    )

    db = TradingDatabase(settings)
    state = db.get_service_state()
    assert state is not None
    assert state.last_terminal_state == "completed"
    assert state.last_terminal_at is not None


def test_restart_service_command_restarts_with_saved_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
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
        cycle_count=3,
        symbols=["AAPL"],
        interval="1d",
        lookback="180d",
        max_cycles=None,
        current_symbol="AAPL",
        message="Running",
        pid=4242,
        stop_requested=False,
    )

    runner = CliRunner()
    monkeypatch.setattr(
        "agentic_trader.cli.restart_background_service",
        lambda **kwargs: 9090,
    )
    result = runner.invoke(
        app,
        ["restart-service"],
        env={
            "AGENTIC_TRADER_RUNTIME_DIR": str(tmp_path),
            "AGENTIC_TRADER_DATABASE_PATH": str(tmp_path / "agentic_trader.duckdb"),
        },
    )

    assert result.exit_code == 0
    assert "9090" in result.stdout
