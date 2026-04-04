from pathlib import Path

from agentic_trader.config import Settings
from agentic_trader.engine.paper_broker import PaperBroker
from agentic_trader.engine.position_manager import evaluate_position_exit
from agentic_trader.schemas import ExecutionDecision, MarketSnapshot
from agentic_trader.storage.db import TradingDatabase


def test_paper_broker_updates_account_and_positions(tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        default_cash=10_000.0,
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    broker = PaperBroker(db, settings)

    order_id = broker.submit(
        ExecutionDecision(
            approved=True,
            side="buy",
            symbol="TEST",
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=110.0,
            position_size_pct=0.1,
            confidence=0.9,
            rationale="Test buy",
        )
    )

    assert order_id.startswith("paper-")

    snapshot = db.get_account_snapshot()
    position = db.get_position("TEST")
    assert position is not None
    assert position.quantity > 0
    assert snapshot.cash < 10_000.0
    assert snapshot.open_positions == 1


def test_paper_broker_avoids_same_direction_pyramiding(tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        default_cash=10_000.0,
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    broker = PaperBroker(db, settings)

    decision = ExecutionDecision(
        approved=True,
        side="buy",
        symbol="TEST",
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        position_size_pct=0.1,
        confidence=0.9,
        rationale="Test buy",
    )
    broker.submit(decision)
    first_position = db.get_position("TEST")
    broker.submit(decision)
    second_position = db.get_position("TEST")

    assert first_position is not None
    assert second_position is not None
    assert second_position.quantity == first_position.quantity


def test_position_manager_triggers_take_profit_exit(tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        default_cash=10_000.0,
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    broker = PaperBroker(db, settings)
    broker.submit(
        ExecutionDecision(
            approved=True,
            side="buy",
            symbol="TEST",
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=110.0,
            position_size_pct=0.1,
            confidence=0.9,
            rationale="Test buy",
        )
    )
    db.save_position_plan(
        symbol="TEST",
        side="buy",
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        max_holding_bars=20,
        holding_bars=2,
        invalidation_logic="Exit on weakness.",
    )

    position = db.get_position("TEST")
    plan = db.get_position_plan("TEST")
    assert position is not None
    assert plan is not None

    decision = evaluate_position_exit(
        MarketSnapshot(
            symbol="TEST",
            interval="1d",
            last_close=111.0,
            ema_20=105.0,
            ema_50=101.0,
            atr_14=2.0,
            rsi_14=60.0,
            volatility_20=0.1,
            return_5=0.03,
            return_20=0.08,
            volume_ratio_20=1.1,
            bars_analyzed=120,
        ),
        position,
        plan,
    )

    assert decision.should_exit is True
    assert decision.reason == "take_profit"


def test_paper_broker_respects_max_open_positions(tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        default_cash=10_000.0,
        max_open_positions=1,
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    broker = PaperBroker(db, settings)

    first = ExecutionDecision(
        approved=True,
        side="buy",
        symbol="AAA",
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        position_size_pct=0.1,
        confidence=0.9,
        rationale="First entry",
    )
    second = first.model_copy(update={"symbol": "BBB"})

    broker.submit(first)
    broker.submit(second)

    assert db.get_position("AAA") is not None
    assert db.get_position("BBB") is None
    assert db.get_account_snapshot().open_positions == 1


def test_paper_broker_respects_gross_exposure_cap(tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        default_cash=10_000.0,
        max_gross_exposure_pct=0.15,
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    broker = PaperBroker(db, settings)

    first = ExecutionDecision(
        approved=True,
        side="buy",
        symbol="AAA",
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        position_size_pct=0.1,
        confidence=0.9,
        rationale="First entry",
    )
    second = first.model_copy(update={"symbol": "BBB"})

    broker.submit(first)
    broker.submit(second)

    assert db.get_position("AAA") is not None
    assert db.get_position("BBB") is None


def test_paper_broker_respects_cash_for_new_long_positions(tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        default_cash=1_000.0,
        max_gross_exposure_pct=2.0,
        max_open_positions=5,
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    broker = PaperBroker(db, settings)

    order_id = broker.submit(
        ExecutionDecision(
            approved=True,
            side="buy",
            symbol="AAA",
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=110.0,
            position_size_pct=1.2,
            confidence=0.9,
            rationale="Too large for cash",
        )
    )

    assert order_id.startswith("paper-")
    assert db.get_position("AAA") is None
    assert db.get_account_snapshot().cash == 1_000.0
