from pathlib import Path

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
from agentic_trader.workflows.service import run_service, start_background_service
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


def test_run_service_records_runtime_state_and_events(monkeypatch, tmp_path: Path) -> None:
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
    assert state.current_symbol is None
    assert {event.event_type for event in events} >= {
        "service_started",
        "cycle_started",
        "symbol_completed",
        "service_completed",
    }


def test_run_service_respects_stop_request(monkeypatch, tmp_path: Path) -> None:
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

    def _run_once_with_stop(**kwargs):
        db.request_stop_service()
        return _artifacts(kwargs["symbol"])

    monkeypatch.setattr("agentic_trader.workflows.service.run_once", _run_once_with_stop)
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


def test_start_background_service_records_spawn(monkeypatch, tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()

    class _FakeProcess:
        pid = 4242

    def _fake_popen(*args, **kwargs):
        return _FakeProcess()

    monkeypatch.setattr("agentic_trader.workflows.service.subprocess.Popen", _fake_popen)

    pid = start_background_service(
        settings=settings,
        symbols=["AAPL", "MSFT"],
        interval="1d",
        lookback="180d",
        poll_seconds=300,
        max_cycles=None,
        workdir=tmp_path,
    )

    db = TradingDatabase(settings)
    state = db.get_service_state()
    assert pid == 4242
    assert state is not None
    assert state.pid == 4242
    assert state.state == "starting"


def test_stop_service_command_marks_stop_requested(tmp_path: Path) -> None:
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
