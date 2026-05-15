from agentic_trader.execution.intent import ExecutionIntent, _utc_now


def test_intent_creation_with_timestamp():
    """Test creating ExecutionIntent with timestamp only (triggers line 64)."""
    timestamp = _utc_now()
    intent = ExecutionIntent(
        symbol="AAPL",
        side="buy",
        reference_price=100.0,
        confidence=0.8,
        thesis="Test thesis",
        approved=True,
        timestamp=timestamp,
        quantity=10.0,
        # No created_at - should sync to created_at
    )
    assert intent.timestamp == timestamp
    assert intent.created_at == timestamp


def test_intent_creation_with_created_at():
    """Test creating ExecutionIntent with created_at only (triggers line 62)."""
    created_at = _utc_now()
    intent = ExecutionIntent(
        symbol="AAPL",
        side="buy",
        reference_price=100.0,
        confidence=0.8,
        thesis="Test thesis",
        approved=True,
        created_at=created_at,
        quantity=10.0,
        # No timestamp - should sync to timestamp
    )
    assert intent.created_at == created_at
    assert intent.timestamp == created_at


def test_intent_creation_with_both_timestamps_matching():
    """Test creating ExecutionIntent with both timestamps matching."""
    now = _utc_now()
    intent = ExecutionIntent(
        symbol="AAPL",
        side="buy",
        reference_price=100.0,
        confidence=0.8,
        thesis="Test thesis",
        approved=True,
        timestamp=now,
        created_at=now,
        quantity=10.0,
    )
    assert intent.timestamp == now
    assert intent.created_at == now


def test_intent_creation_with_conflicting_timestamps():
    """Test that conflicting timestamps raise ValueError (line 68)."""
    import pytest
    from datetime import datetime, timezone

    timestamp = datetime.now(timezone.utc).isoformat()
    created_at = datetime.now(timezone.utc).isoformat()

    with pytest.raises(ValueError, match="must match"):
        ExecutionIntent(
            symbol="AAPL",
            side="buy",
            reference_price=100.0,
            confidence=0.8,
            thesis="Test thesis",
            approved=True,
            timestamp=timestamp,
            created_at=created_at,
        )


def test_intent_default_timestamps():
    """Test that timestamps are auto-generated when not provided."""
    intent = ExecutionIntent(
        symbol="AAPL",
        side="buy",
        reference_price=100.0,
        confidence=0.8,
        thesis="Test thesis",
        approved=True,
        quantity=10.0,
    )
    assert intent.timestamp is not None
    assert intent.created_at is not None
    assert intent.timestamp == intent.created_at


def test_intent_requires_quantity_or_notional_when_approved():
    """Test that approved intents require quantity or notional (line 77)."""
    import pytest

    with pytest.raises(ValueError, match="require quantity or notional"):
        ExecutionIntent(
            symbol="AAPL",
            side="buy",
            reference_price=100.0,
            confidence=0.8,
            thesis="Test thesis",
            approved=True,
            # Missing quantity and notional
        )


def test_intent_with_quantity_when_approved():
    """Test that approved intent with quantity is valid."""
    intent = ExecutionIntent(
        symbol="AAPL",
        side="buy",
        reference_price=100.0,
        confidence=0.8,
        thesis="Test thesis",
        approved=True,
        quantity=10.0,
    )
    assert intent.quantity == 10.0
    assert intent.approved is True


def test_intent_with_notional_when_approved():
    """Test that approved intent with notional is valid."""
    intent = ExecutionIntent(
        symbol="AAPL",
        side="buy",
        reference_price=100.0,
        confidence=0.8,
        thesis="Test thesis",
        approved=True,
        notional=1000.0,
    )
    assert intent.notional == 1000.0
    assert intent.approved is True


def test_intent_auto_assigns_created_at():
    """Test that created_at is auto-assigned from timestamp (line 74)."""
    intent = ExecutionIntent(
        symbol="AAPL",
        side="buy",
        reference_price=100.0,
        confidence=0.8,
        thesis="Test thesis",
        approved=True,
        timestamp=_utc_now(),
        quantity=10.0,
    )
    assert intent.created_at == intent.timestamp


def test_intent_holds_not_requires_size():
    """Test that hold intent doesn't require quantity or notional."""
    intent = ExecutionIntent(
        symbol="AAPL",
        side="hold",
        reference_price=100.0,
        confidence=0.8,
        thesis="Hold thesis",
        approved=False,
    )
    assert intent.side == "hold"
    assert intent.quantity is None
    assert intent.notional is None
