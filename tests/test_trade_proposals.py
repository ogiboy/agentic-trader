import json

import duckdb
import pytest

from agentic_trader.config import Settings
from agentic_trader.execution.intent import ExecutionIntent, ExecutionOutcome
from agentic_trader.finance.proposals import (
    approve_trade_proposal,
    create_trade_proposal,
    reconcile_trade_proposal,
    reject_trade_proposal,
    utc_now_iso,
)
from agentic_trader.storage.db import TradingDatabase


def _settings(tmp_path, **overrides) -> Settings:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="paper",
        **overrides,
    )
    settings.ensure_directories()
    return settings


def test_trade_proposal_create_list_and_reject(tmp_path) -> None:
    settings = _settings(tmp_path)
    db = TradingDatabase(settings)

    proposal = create_trade_proposal(
        db=db,
        symbol="aapl",
        side="buy",
        quantity=2,
        reference_price=100,
        confidence=0.72,
        thesis="Momentum scanner with confirmed news context.",
        source="scanner",
    )

    stored = db.get_trade_proposal(proposal.proposal_id)
    pending = db.list_trade_proposals(status="pending")
    assert stored is not None
    assert stored.symbol == "AAPL"
    assert stored.status == "pending"
    assert [item.proposal_id for item in pending] == [proposal.proposal_id]

    rejected = reject_trade_proposal(
        db=db, proposal_id=proposal.proposal_id, reason="spread too wide"
    )

    assert rejected.status == "rejected"
    assert rejected.rejection_reason == "spread too wide"
    stored_after_reject = db.get_trade_proposal(proposal.proposal_id)
    assert stored_after_reject is not None
    assert stored_after_reject.status == "rejected"


def test_trade_proposal_approval_records_execution_and_terminal_state(tmp_path) -> None:
    settings = _settings(tmp_path)
    db = TradingDatabase(settings)
    proposal = create_trade_proposal(
        db=db,
        symbol="MSFT",
        side="buy",
        quantity=1,
        reference_price=100,
        confidence=0.81,
        thesis="Manual paper desk approval candidate.",
        stop_loss=95,
        take_profit=110,
    )

    approved, outcome = approve_trade_proposal(
        db=db,
        settings=settings,
        proposal_id=proposal.proposal_id,
        review_notes="paper desk approval",
    )

    latest = db.latest_execution_record()
    assert approved.status == "executed"
    assert approved.execution_order_id == outcome.order_id
    assert outcome.status == "filled"
    assert latest is not None
    assert latest["intent_id"] == approved.execution_intent_id
    intent = latest["intent"]
    assert isinstance(intent, dict)
    assert intent["approved"] is True
    assert intent["backend_metadata"]["source"] == "proposal_queue"
    assert intent["backend_metadata"]["proposal_id"] == proposal.proposal_id

    with pytest.raises(ValueError, match="not pending"):
        reject_trade_proposal(db=db, proposal_id=proposal.proposal_id, reason="late")


def test_trade_proposal_approval_persists_in_flight_before_adapter_call(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    settings = _settings(tmp_path)
    db = TradingDatabase(settings)
    proposal = create_trade_proposal(
        db=db,
        symbol="MSFT",
        side="buy",
        quantity=1,
        reference_price=100,
        confidence=0.81,
        thesis="Manual paper desk approval candidate.",
    )
    place_order_attempts = 0

    class FailingAdapter:
        def place_order(self, intent):
            nonlocal place_order_attempts
            place_order_attempts += 1
            raise RuntimeError("adapter failure after approval persistence")

    monkeypatch.setattr(
        "agentic_trader.finance.proposals.get_broker_adapter",
        lambda *, db, settings: FailingAdapter(),
    )

    final, outcome = approve_trade_proposal(
        db=db,
        settings=settings,
        proposal_id=proposal.proposal_id,
        review_notes="paper desk approval",
    )

    stored = db.get_trade_proposal(proposal.proposal_id)
    assert stored is not None
    assert stored.status == "failed"
    assert stored.execution_intent_id is not None
    assert final.status == "failed"
    assert outcome.status == "rejected"
    assert outcome.rejection_reason == "adapter_exception"
    assert place_order_attempts == 1

    with pytest.raises(ValueError, match="not pending"):
        approve_trade_proposal(
            db=db,
            settings=settings,
            proposal_id=proposal.proposal_id,
        )
    assert place_order_attempts == 1


def test_trade_proposal_approval_requires_atomic_pending_transition(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    settings = _settings(tmp_path)
    db = TradingDatabase(settings)
    proposal = create_trade_proposal(
        db=db,
        symbol="MSFT",
        side="buy",
        quantity=1,
        reference_price=100,
        confidence=0.81,
        thesis="Manual paper desk approval candidate.",
    )
    original_update = db.update_trade_proposal
    place_order_attempts = 0

    def racing_update(record, *, expected_status=None):
        if record.status == "approved":
            return False
        return original_update(record, expected_status=expected_status)

    class Adapter:
        def place_order(self, intent):
            nonlocal place_order_attempts
            place_order_attempts += 1
            return intent

    monkeypatch.setattr(db, "update_trade_proposal", racing_update)
    monkeypatch.setattr(
        "agentic_trader.finance.proposals.get_broker_adapter",
        lambda *, db, settings: Adapter(),
    )

    with pytest.raises(ValueError, match="changed before approval"):
        approve_trade_proposal(
            db=db,
            settings=settings,
            proposal_id=proposal.proposal_id,
        )

    stored = db.get_trade_proposal(proposal.proposal_id)
    assert stored is not None
    assert stored.status == "pending"
    assert stored.execution_intent_id is None
    assert place_order_attempts == 0


def test_trade_proposal_approval_requires_atomic_final_transition(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    settings = _settings(tmp_path)
    db = TradingDatabase(settings)
    proposal = create_trade_proposal(
        db=db,
        symbol="MSFT",
        side="buy",
        quantity=1,
        reference_price=100,
        confidence=0.81,
        thesis="Manual paper desk approval candidate.",
    )
    original_update = db.update_trade_proposal

    def racing_update(record, *, expected_status=None):
        if record.status in {"executed", "failed"}:
            return False
        return original_update(record, expected_status=expected_status)

    monkeypatch.setattr(db, "update_trade_proposal", racing_update)

    with pytest.raises(ValueError, match="changed before broker outcome"):
        approve_trade_proposal(
            db=db,
            settings=settings,
            proposal_id=proposal.proposal_id,
        )

    stored = db.get_trade_proposal(proposal.proposal_id)
    assert stored is not None
    assert stored.status == "approved"
    assert stored.execution_intent_id is not None
    assert db.latest_execution_record() is not None


def test_trade_proposal_reconcile_repairs_in_flight_from_execution_record(
    tmp_path,
) -> None:
    settings = _settings(tmp_path)
    db = TradingDatabase(settings)
    proposal = create_trade_proposal(
        db=db,
        symbol="MSFT",
        side="buy",
        quantity=1,
        reference_price=100,
        confidence=0.81,
        thesis="Manual paper desk approval candidate.",
    )
    intent = ExecutionIntent(
        intent_id="intent-repair",
        symbol="MSFT",
        side="buy",
        quantity=1,
        reference_price=100,
        confidence=0.81,
        thesis="Manual paper desk approval candidate.",
        approved=True,
        execution_backend="paper",
        adapter_name="paper",
        backend_metadata={"proposal_id": proposal.proposal_id},
    )
    approved = proposal.model_copy(
        update={
            "status": "approved",
            "updated_at": utc_now_iso(),
            "execution_intent_id": intent.intent_id,
        }
    )
    assert db.update_trade_proposal(approved, expected_status="pending")
    outcome = ExecutionOutcome(
        intent_id=intent.intent_id,
        order_id="paper-order-repair",
        status="filled",
        adapter_name="paper",
        execution_backend="paper",
        filled_quantity=1,
        average_fill_price=100,
    )
    db.record_execution_outcome(run_id=None, intent=intent, outcome=outcome)

    repaired, record = reconcile_trade_proposal(
        db=db,
        proposal_id=proposal.proposal_id,
        review_notes="repair after interrupted final status write",
    )

    assert repaired.status == "executed"
    assert repaired.execution_order_id == "paper-order-repair"
    assert repaired.execution_outcome_status == "filled"
    assert "repair after interrupted" in repaired.review_notes
    assert record["intent_id"] == intent.intent_id


def test_trade_proposal_reconcile_fails_closed_without_execution_record(tmp_path) -> None:
    settings = _settings(tmp_path)
    db = TradingDatabase(settings)
    proposal = create_trade_proposal(
        db=db,
        symbol="MSFT",
        side="buy",
        quantity=1,
        reference_price=100,
        confidence=0.81,
        thesis="Manual paper desk approval candidate.",
    )
    approved = proposal.model_copy(
        update={
            "status": "approved",
            "updated_at": utc_now_iso(),
            "execution_intent_id": "intent-missing",
        }
    )
    assert db.update_trade_proposal(approved, expected_status="pending")

    with pytest.raises(ValueError, match="no recorded execution outcome"):
        reconcile_trade_proposal(db=db, proposal_id=proposal.proposal_id)


def test_trade_proposal_rejected_when_size_missing(tmp_path) -> None:
    settings = _settings(tmp_path)
    db = TradingDatabase(settings)

    with pytest.raises(ValueError, match="quantity or notional"):
        create_trade_proposal(
            db=db,
            symbol="AAPL",
            side="buy",
            reference_price=100,
            confidence=0.7,
            thesis="Missing size should not enter the review queue.",
        )


def test_trade_proposal_rejects_ambiguous_size(tmp_path) -> None:
    settings = _settings(tmp_path)
    db = TradingDatabase(settings)

    with pytest.raises(ValueError, match="exactly one of quantity or notional"):
        create_trade_proposal(
            db=db,
            symbol="AAPL",
            side="buy",
            quantity=1,
            notional=100,
            reference_price=100,
            confidence=0.7,
            thesis="Ambiguous sizing should not enter the queue.",
        )


def test_trade_proposal_rejects_non_positive_size(tmp_path) -> None:
    settings = _settings(tmp_path)
    db = TradingDatabase(settings)

    with pytest.raises(ValueError, match="quantity greater than zero"):
        create_trade_proposal(
            db=db,
            symbol="AAPL",
            side="buy",
            quantity=0,
            reference_price=100,
            confidence=0.7,
            thesis="Zero quantity should not enter the queue.",
        )

    with pytest.raises(ValueError, match="notional greater than zero"):
        create_trade_proposal(
            db=db,
            symbol="AAPL",
            side="buy",
            notional=-1,
            reference_price=100,
            confidence=0.7,
            thesis="Negative notional should not enter the queue.",
        )


def test_trade_proposal_rejects_invalid_price_and_confidence(tmp_path) -> None:
    settings = _settings(tmp_path)
    db = TradingDatabase(settings)

    with pytest.raises(ValueError, match="reference_price greater than zero"):
        create_trade_proposal(
            db=db,
            symbol="AAPL",
            side="buy",
            quantity=1,
            reference_price=0,
            confidence=0.7,
            thesis="Invalid reference price should be rejected.",
        )

    with pytest.raises(ValueError, match="confidence between 0 and 1"):
        create_trade_proposal(
            db=db,
            symbol="AAPL",
            side="buy",
            quantity=1,
            reference_price=100,
            confidence=1.7,
            thesis="Invalid confidence should be rejected.",
        )


def test_trade_proposal_row_survives_json_round_trip(tmp_path) -> None:
    settings = _settings(tmp_path)
    db = TradingDatabase(settings)
    proposal = create_trade_proposal(
        db=db,
        symbol="NVDA",
        side="sell",
        notional=250,
        reference_price=125,
        confidence=0.64,
        thesis="Risk desk hedge candidate.",
        source="manual",
    )

    payload = json.loads(proposal.model_dump_json())
    hydrated = db.get_trade_proposal(payload["proposal_id"])

    assert hydrated is not None
    assert hydrated.notional == pytest.approx(250)
    assert hydrated.side == "sell"


def test_trade_proposal_reads_legacy_database_without_table(tmp_path) -> None:
    settings = _settings(tmp_path)
    conn = duckdb.connect(str(settings.database_path))
    conn.execute("create table legacy_marker (id varchar)")
    conn.close()
    db = TradingDatabase(settings, read_only=True)

    assert db.list_trade_proposals() == []
    assert db.get_trade_proposal("proposal-missing") is None
