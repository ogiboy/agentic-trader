from pathlib import Path

import pytest

from agentic_trader.config import Settings
from agentic_trader.engine.broker import (
    PaperBrokerAdapter,
    SimulatedRealBrokerAdapter,
    get_broker_adapter,
)
from agentic_trader.execution.intent import ExecutionIntent, build_execution_intent
from agentic_trader.schemas import (
    ExecutionDecision,
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
from agentic_trader.workflows.run_once import persist_run


def _settings(tmp_path: Path) -> Settings:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        default_cash=10_000.0,
    )
    settings.ensure_directories()
    return settings


def _decision() -> ExecutionDecision:
    return ExecutionDecision(
        approved=True,
        side="buy",
        symbol="AAPL",
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        position_size_pct=0.1,
        confidence=0.74,
        rationale="Execution guard approved the trade.",
    )


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
        execution=_decision().model_copy(update={"symbol": symbol}),
        review=ReviewNote(
            summary="Review captured the approved long setup.",
            strengths=["Aligned trend"],
            warnings=[],
            next_checks=["Watch invalidation logic"],
        ),
    )


def test_execution_intent_creation_and_validation(tmp_path: Path) -> None:
    settings = _settings(tmp_path)

    intent = build_execution_intent(
        decision=_decision(),
        settings=settings,
        run_id="run-test",
        reasoning_id="manager",
        trace_link="run:run-test/trace",
        invalidation_condition="Exit on close below EMA20.",
        reference_equity=10_000.0,
    )

    assert intent.symbol == "AAPL"
    assert intent.notional == pytest.approx(1_000.0)
    assert intent.source_run_id == "run-test"
    assert intent.invalidation_condition == "Exit on close below EMA20."
    assert intent.backend_metadata["position_size_pct"] == pytest.approx(0.1)
    assert intent.timestamp == intent.created_at

    legacy_timestamp = "2026-01-01T00:00:00+00:00"
    legacy_intent = ExecutionIntent(
        symbol="AAPL",
        side="hold",
        reference_price=100.0,
        confidence=0.2,
        thesis="Legacy payload.",
        approved=False,
        created_at=legacy_timestamp,
    )
    assert legacy_intent.timestamp == legacy_timestamp
    assert legacy_intent.created_at == legacy_timestamp

    with pytest.raises(ValueError, match="timestamp and created_at"):
        ExecutionIntent(
            symbol="AAPL",
            side="hold",
            reference_price=100.0,
            confidence=0.2,
            thesis="Conflicting audit timestamps.",
            approved=False,
            timestamp="2026-01-01T00:00:00+00:00",
            created_at="2026-01-01T00:01:00+00:00",
        )

    with pytest.raises(ValueError, match="quantity or notional"):
        ExecutionIntent(
            symbol="AAPL",
            side="buy",
            reference_price=100.0,
            confidence=0.8,
            thesis="Missing size.",
            approved=True,
        )


def test_paper_adapter_places_order_and_reports_health(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    db = TradingDatabase(settings)
    adapter = get_broker_adapter(db=db, settings=settings)
    assert isinstance(adapter, PaperBrokerAdapter)

    intent = build_execution_intent(
        decision=_decision(),
        settings=settings,
        reference_equity=adapter.get_account_state().equity,
        adapter_name=adapter.backend_name,
    )
    outcome = adapter.place_order(intent)

    assert outcome.status == "filled"
    assert outcome.order_id is not None
    assert outcome.order_id.startswith("paper-")
    assert adapter.get_positions()[0].symbol == "AAPL"
    assert adapter.get_open_orders() == []
    assert adapter.cancel_order(outcome.order_id) is False
    assert adapter.healthcheck().ok is True
    db.close()


def test_simulated_real_adapter_is_non_live_and_records_metadata(tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        default_cash=10_000.0,
        execution_backend="simulated_real",
        simulated_partial_fill_probability=1.0,
        simulated_partial_fill_min_ratio=0.5,
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    adapter = get_broker_adapter(db=db, settings=settings)
    assert isinstance(adapter, SimulatedRealBrokerAdapter)

    intent = build_execution_intent(
        decision=_decision(),
        settings=settings,
        reference_equity=adapter.get_account_state().equity,
        adapter_name=adapter.backend_name,
    ).model_copy(update={"intent_id": "intent-simulated-test"})
    outcome = adapter.place_order(intent)

    assert outcome.execution_backend == "simulated_real"
    assert outcome.adapter_name == "simulated_real"
    assert outcome.status in {"filled", "partially_filled"}
    assert outcome.simulated_metadata["non_live"] is True
    fill_ratio = outcome.simulated_metadata["fill_ratio"]
    assert isinstance(fill_ratio, int | float)
    assert float(fill_ratio) <= 1.0
    assert adapter.healthcheck().simulated is True
    assert adapter.healthcheck().live is False
    db.close()


def test_live_backend_remains_blocked_without_enablement(tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        default_cash=10_000.0,
        execution_backend="live",
        live_execution_enabled=False,
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)

    with pytest.raises(RuntimeError, match="live execution is disabled"):
        get_broker_adapter(db=db, settings=settings)
    db.close()


def test_persist_run_records_execution_context(tmp_path: Path) -> None:
    settings = _settings(tmp_path)

    order_id = persist_run(settings=settings, artifacts=_artifacts())

    db = TradingDatabase(settings)
    execution_record = db.latest_execution_record()
    trade_context = db.latest_trade_context()

    assert order_id.startswith("paper-")
    assert execution_record is not None
    assert execution_record["order_id"] == order_id
    assert execution_record["execution_backend"] == "paper"
    assert execution_record["status"] == "filled"
    assert (
        execution_record["intent"]["timestamp"]
        == execution_record["intent"]["created_at"]
    )
    assert execution_record["outcome"]["status"] == "filled"
    assert trade_context is not None
    assert trade_context.execution_backend == "paper"
    assert trade_context.execution_outcome_status == "filled"
    assert trade_context.execution_intent is not None
    assert trade_context.execution_intent["source_run_id"] == execution_record["run_id"]
    db.close()


def test_persist_run_records_rejected_execution_metadata(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    rejection_reason = "Execution guard rejected the trade."
    artifacts = _artifacts().model_copy(
        update={
            "execution": _decision().model_copy(
                update={
                    "approved": False,
                    "confidence": 0.2,
                    "rationale": rejection_reason,
                }
            )
        }
    )

    persist_run(settings=settings, artifacts=artifacts)

    db = TradingDatabase(settings)
    execution_record = db.latest_execution_record()
    trade_context = db.latest_trade_context()

    assert execution_record is not None
    assert execution_record["execution_backend"] == "paper"
    assert execution_record["status"] == "rejected"
    assert execution_record["rejection_reason"] == rejection_reason
    assert execution_record["outcome"]["rejection_reason"] == rejection_reason
    assert trade_context is not None
    assert trade_context.execution_outcome_status == "rejected"
    assert trade_context.execution_rejection_reason == rejection_reason
    db.close()
