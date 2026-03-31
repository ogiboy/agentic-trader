from pathlib import Path

from agentic_trader.config import Settings
from agentic_trader.engine.paper_broker import PaperBroker
from agentic_trader.schemas import ExecutionDecision
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
