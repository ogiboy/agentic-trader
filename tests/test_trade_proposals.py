import json
from typing import cast

import duckdb
import pytest

from agentic_trader.config import Settings
from agentic_trader.execution.intent import ExecutionIntent, ExecutionOutcome
from agentic_trader.finance.ideas import IdeaCandidate
from agentic_trader.finance.proposal_candidates import (
    ProposalCandidateDraft,
    create_proposal_candidate,
    promote_proposal_candidate,
)
from agentic_trader.finance.proposals import (
    TradeProposalDraft,
    approve_trade_proposal,
    create_trade_proposal,
    expire_trade_proposal,
    reconcile_trade_proposal,
    refresh_trade_proposal_order,
    reject_trade_proposal,
    repair_missing_position_plans,
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


def test_reject_trade_proposal_requires_review_note(tmp_path) -> None:
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

    with pytest.raises(ValueError, match="requires review_notes"):
        reject_trade_proposal(db=db, proposal_id=proposal.proposal_id, reason=" ")


def test_proposal_candidate_promotes_to_pending_proposal(tmp_path) -> None:
    """
    Verifies that a ProposalCandidate can be promoted into a pending TradeProposal and that duplicate promotions are blocked.
    
    Asserts the promoted candidate's status becomes "promoted" and links to a created trade proposal whose status is "pending", whose source is "proposal-candidate", and whose execution_order_id remains None. Also asserts the stored proposal's review_notes include the candidate ID, that re-promoting the same candidate raises a ValueError containing "already promoted", and that exactly one pending proposal exists after promotion.
    """
    settings = _settings(tmp_path)
    db = TradingDatabase(settings)
    candidate = create_proposal_candidate(
        db=db,
        draft=ProposalCandidateDraft(
            idea=IdeaCandidate(
                symbol="aapl",
                price=190,
                volume=5_000_000,
                change_pct=6.2,
                relative_volume=3.4,
                rsi=63,
                ema_9=184,
                spread_pct=0.05,
            ),
            preset="momentum",
            quantity=1,
            stop_loss=182,
            take_profit=205,
            invalidation_condition="Close below 9 EMA.",
            thesis="Momentum candidate with volume confirmation.",
            freshness="same_session_quote",
            materiality="high relative-volume scanner hit",
        ),
    )

    promoted, proposal = promote_proposal_candidate(
        db=db,
        candidate_id=candidate.candidate_id,
        review_notes="operator checked scanner evidence",
    )

    stored_candidate = db.get_proposal_candidate(candidate.candidate_id)
    stored_proposal = db.get_trade_proposal(proposal.proposal_id)
    assert promoted.status == "promoted"
    assert promoted.proposal_id == proposal.proposal_id
    assert stored_candidate is not None
    assert stored_candidate.status == "promoted"
    assert stored_proposal is not None
    assert stored_proposal.status == "pending"
    assert stored_proposal.source == "proposal-candidate"
    assert stored_proposal.execution_order_id is None
    assert candidate.candidate_id in stored_proposal.review_notes

    with pytest.raises(ValueError, match="already promoted"):
        promote_proposal_candidate(db=db, candidate_id=candidate.candidate_id)
    assert len(db.list_trade_proposals(status="pending")) == 1


def test_proposal_candidate_records_redacted_provider_context(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("AGENTIC_TRADER_TEST_API_KEY", "super-secret-token")
    settings = _settings(tmp_path)
    db = TradingDatabase(settings)

    candidate = create_proposal_candidate(
        db=db,
        settings=settings,
        draft=ProposalCandidateDraft(
            idea=IdeaCandidate(
                symbol="AAPL",
                price=190,
                volume=5_000_000,
                change_pct=6.2,
                relative_volume=3.4,
                rsi=63,
                ema_9=184,
                spread_pct=0.05,
            ),
            preset="momentum",
            quantity=1,
            stop_loss=182,
            take_profit=205,
            freshness="same_session_quote",
            evidence={
                "provider_error": (
                    "api_key=super-secret-token Bearer abcdef123456 "
                    "https://example.test/?token=super-secret-token"
                )
            },
        ),
    )

    stored = db.get_proposal_candidate(candidate.candidate_id)
    assert stored is not None
    context = stored.evidence["canonical_analysis"]
    assert isinstance(context, dict)
    assert context["available"] is True
    assert context["policy"] == {
        "enabled": True,
        "network_light_default": True,
        "fetch_provider_news": False,
        "broker_access": False,
        "proposal_approval": False,
    }
    assert "fundamentals" in context["missing_sections"]
    assert "news" in context["missing_sections"]
    assert "source_attributions" in context
    serialized = json.dumps(stored.evidence)
    assert "super-secret-token" not in serialized
    assert "abcdef123456" not in serialized
    assert "<redacted>" in serialized


def test_proposal_candidate_blocks_watch_or_low_liquidity_promotion(tmp_path) -> None:
    """
    Verifies that promotion of proposal candidates is blocked for watch-only symbols and for candidates with low liquidity.
    
    Creates a "volatile" candidate expected to be treated as watch-only and a "momentum" candidate with very low traded volume, then asserts that promoting each candidate raises a ValueError containing "watch-only" and "blocking scanner warnings" respectively.
    """
    settings = _settings(tmp_path)
    db = TradingDatabase(settings)
    watch = create_proposal_candidate(
        db=db,
        draft=ProposalCandidateDraft(
            idea=IdeaCandidate(
                symbol="MSFT",
                price=420,
                volume=4_000_000,
                change_pct=2.0,
                relative_volume=2.5,
                range_pct=8.0,
                spread_pct=0.05,
            ),
            preset="volatile",
            quantity=1,
        ),
    )
    illiquid = create_proposal_candidate(
        db=db,
        draft=ProposalCandidateDraft(
            idea=IdeaCandidate(
                symbol="NVDA",
                price=120,
                volume=20_000,
                change_pct=8.0,
                relative_volume=4.0,
                spread_pct=0.05,
            ),
            preset="momentum",
            quantity=1,
            stop_loss=115,
            take_profit=135,
        ),
    )

    with pytest.raises(ValueError, match="watch-only"):
        promote_proposal_candidate(db=db, candidate_id=watch.candidate_id)
    with pytest.raises(ValueError, match="blocking scanner warnings"):
        promote_proposal_candidate(db=db, candidate_id=illiquid.candidate_id)


def test_proposal_candidate_blocks_stale_evidence_and_bad_risk_geometry(
    tmp_path,
) -> None:
    settings = _settings(tmp_path)
    db = TradingDatabase(settings)
    stale = create_proposal_candidate(
        db=db,
        draft=ProposalCandidateDraft(
            idea=IdeaCandidate(
                symbol="AAPL",
                price=190,
                volume=5_000_000,
                change_pct=6.2,
                relative_volume=3.4,
                rsi=63,
                ema_9=184,
                spread_pct=0.05,
            ),
            preset="momentum",
            quantity=1,
            stop_loss=182,
            take_profit=205,
            freshness="stale_quote",
        ),
    )
    bad_risk = create_proposal_candidate(
        db=db,
        draft=ProposalCandidateDraft(
            idea=IdeaCandidate(
                symbol="MSFT",
                price=420,
                volume=5_000_000,
                change_pct=6.2,
                relative_volume=3.4,
                rsi=63,
                ema_9=410,
                spread_pct=0.05,
            ),
            preset="momentum",
            quantity=1,
            stop_loss=430,
            take_profit=450,
            freshness="same_session_quote",
        ),
    )

    with pytest.raises(ValueError, match="stale or missing freshness"):
        promote_proposal_candidate(db=db, candidate_id=stale.candidate_id)
    with pytest.raises(ValueError, match="stop_loss < reference_price"):
        promote_proposal_candidate(db=db, candidate_id=bad_risk.candidate_id)


def test_proposal_candidate_rejects_invalid_sizing_on_create(tmp_path) -> None:
    settings = _settings(tmp_path)
    db = TradingDatabase(settings)
    draft = ProposalCandidateDraft(
        idea=IdeaCandidate(
            symbol="AAPL",
            price=190,
            volume=5_000_000,
            change_pct=6.2,
            relative_volume=3.4,
            rsi=63,
            ema_9=184,
            spread_pct=0.05,
        ),
        preset="momentum",
        quantity=0,
        stop_loss=182,
        take_profit=205,
    )

    with pytest.raises(ValueError, match="quantity greater than zero"):
        create_proposal_candidate(db=db, draft=draft)


def test_proposal_candidate_requires_exactly_one_size_on_create(tmp_path) -> None:
    settings = _settings(tmp_path)
    db = TradingDatabase(settings)
    base_idea = IdeaCandidate(
        symbol="AAPL",
        price=190,
        volume=5_000_000,
        change_pct=6.2,
        relative_volume=3.4,
        rsi=63,
        ema_9=184,
        spread_pct=0.05,
    )

    with pytest.raises(ValueError, match="exactly one of quantity or notional"):
        create_proposal_candidate(
            db=db,
            draft=ProposalCandidateDraft(idea=base_idea, preset="momentum"),
        )

    with pytest.raises(ValueError, match="exactly one of quantity or notional"):
        create_proposal_candidate(
            db=db,
            draft=ProposalCandidateDraft(
                idea=base_idea,
                preset="momentum",
                quantity=1,
                notional=100,
            ),
        )


def test_proposal_candidate_preserves_reserved_evidence_keys(tmp_path) -> None:
    settings = _settings(tmp_path)
    db = TradingDatabase(settings)

    candidate = create_proposal_candidate(
        db=db,
        draft=ProposalCandidateDraft(
            idea=IdeaCandidate(
                symbol="AAPL",
                price=190,
                volume=5_000_000,
                change_pct=6.2,
                relative_volume=3.4,
                rsi=63,
                ema_9=184,
                spread_pct=0.05,
            ),
            preset="momentum",
            quantity=1,
            evidence={
                "blocking_warnings": ["fake_clear"],
                "authority": {"broker_access": True},
                "canonical_analysis": {"available": True},
                "operator_note": "keep this non-reserved note",
            },
        ),
    )

    assert candidate.evidence["blocking_warnings"] == []
    assert candidate.evidence["authority"] == {
        "broker_access": False,
        "proposal_approval": False,
        "manual_review_required": True,
    }
    canonical_analysis = cast(dict[str, object], candidate.evidence["canonical_analysis"])
    assert canonical_analysis["available"] is False
    assert candidate.evidence["operator_note"] == "keep this non-reserved note"


def test_trade_proposal_rejects_mixed_draft_and_fields(tmp_path) -> None:
    settings = _settings(tmp_path)
    db = TradingDatabase(settings)
    draft = TradeProposalDraft(
        symbol="AAPL",
        side="buy",
        quantity=1,
        reference_price=100,
        confidence=0.7,
        thesis="Draft and fields should not be mixed.",
    )

    with pytest.raises(ValueError, match="Pass either draft or proposal fields"):
        create_trade_proposal(db=db, draft=draft, symbol="MSFT")


def test_trade_proposal_expire_terminalizes_pending_proposal(tmp_path) -> None:
    settings = _settings(tmp_path)
    db = TradingDatabase(settings)
    proposal = create_trade_proposal(
        db=db,
        symbol="AAPL",
        side="buy",
        quantity=1,
        reference_price=100,
        confidence=0.7,
        thesis="Stale proposal should expire without broker access.",
    )

    expired = expire_trade_proposal(db=db, proposal_id=proposal.proposal_id)

    assert expired.status == "expired"
    with pytest.raises(ValueError, match="not pending"):
        approve_trade_proposal(
            db=db,
            settings=settings,
            proposal_id=proposal.proposal_id,
            review_notes="expired proposal audit",
        )


def test_trade_proposal_approval_requires_exit_risk_controls(tmp_path) -> None:
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

    with pytest.raises(ValueError, match="requires stop_loss and take_profit"):
        approve_trade_proposal(
            db=db,
            settings=settings,
            proposal_id=proposal.proposal_id,
            review_notes="risk control audit",
        )

    stored = db.get_trade_proposal(proposal.proposal_id)
    assert stored is not None
    assert stored.status == "pending"
    assert db.latest_execution_record() is None


def test_trade_proposal_approval_rejects_inconsistent_risk_controls(tmp_path) -> None:
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
        stop_loss=105,
        take_profit=110,
    )

    with pytest.raises(ValueError, match="stop_loss < reference_price"):
        approve_trade_proposal(
            db=db,
            settings=settings,
            proposal_id=proposal.proposal_id,
            review_notes="risk geometry audit",
        )


def test_trade_proposal_approval_requires_review_notes(tmp_path) -> None:
    """
    Verifies that approving a trade proposal requires non-empty review notes and leaves the proposal pending when approval fails.
    
    Creates a pending trade proposal with stop-loss and take-profit, attempts to approve it using whitespace-only `review_notes` (expecting a `ValueError` matching "approval requires review_notes"), and asserts the stored proposal remains in the "pending" state and that no execution record was created.
    """
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

    with pytest.raises(ValueError, match="approval requires review_notes"):
        approve_trade_proposal(
            db=db,
            settings=settings,
            proposal_id=proposal.proposal_id,
            review_notes=" ",
        )

    stored = db.get_trade_proposal(proposal.proposal_id)
    assert stored is not None
    assert stored.status == "pending"
    assert db.latest_execution_record() is None


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
    journal = db.list_trade_journal(limit=5)
    position_plan = db.get_position_plan("MSFT")
    assert approved.status == "executed"
    assert approved.execution_order_id == outcome.order_id
    assert outcome.status == "filled"
    assert len(journal) == 1
    assert journal[0].entry_order_id == outcome.order_id
    assert journal[0].journal_status == "open"
    assert journal[0].symbol == "MSFT"
    assert journal[0].strategy_family == "manual_proposal"
    assert proposal.proposal_id in journal[0].notes
    assert latest is not None
    assert latest["intent_id"] == approved.execution_intent_id
    assert position_plan is not None
    assert position_plan.entry_price == pytest.approx(100)
    assert position_plan.stop_loss == pytest.approx(95)
    assert position_plan.take_profit == pytest.approx(110)
    assert position_plan.holding_bars == 0
    intent = latest["intent"]
    assert isinstance(intent, dict)
    assert intent["approved"] is True
    assert intent["order_type"] == "market"
    assert intent["limit_price"] is None
    assert intent["backend_metadata"]["source"] == "proposal_queue"
    assert intent["backend_metadata"]["proposal_id"] == proposal.proposal_id

    with pytest.raises(ValueError, match="not pending"):
        reject_trade_proposal(db=db, proposal_id=proposal.proposal_id, reason="late")


def test_trade_proposal_limit_order_records_limit_intent(tmp_path) -> None:
    settings = _settings(tmp_path)
    db = TradingDatabase(settings)
    proposal = create_trade_proposal(
        db=db,
        symbol="MSFT",
        side="buy",
        order_type="limit",
        quantity=1,
        limit_price=99.5,
        reference_price=100,
        confidence=0.81,
        thesis="Manual paper desk limit approval candidate.",
        stop_loss=95,
        take_profit=110,
    )

    approved, outcome = approve_trade_proposal(
        db=db,
        settings=settings,
        proposal_id=proposal.proposal_id,
        review_notes="limit paper desk approval",
    )

    latest = db.latest_execution_record()
    assert approved.status == "executed"
    assert approved.limit_price == pytest.approx(99.5)
    assert outcome.status == "filled"
    assert latest is not None
    intent = latest["intent"]
    assert isinstance(intent, dict)
    assert intent["order_type"] == "limit"
    assert intent["limit_price"] == pytest.approx(99.5)


def test_trade_proposal_journal_keeps_accepted_broker_orders_open(tmp_path) -> None:
    settings = _settings(tmp_path)
    db = TradingDatabase(settings)
    proposal = create_trade_proposal(
        db=db,
        symbol="NVDA",
        side="buy",
        quantity=1,
        reference_price=900,
        confidence=0.78,
        thesis="External paper broker acknowledgement should stay operator-visible.",
        stop_loss=860,
        take_profit=980,
        source="manual",
    )
    outcome = ExecutionOutcome(
        intent_id="intent-accepted-1",
        order_id="alpaca-paper-accepted-1",
        status="accepted",
        adapter_name="alpaca_paper",
        execution_backend="alpaca_paper",
        message="Accepted by external paper broker.",
    )

    trade_id = db.create_trade_journal_from_proposal(proposal=proposal, outcome=outcome)

    journal = db.list_trade_journal(limit=5)
    assert trade_id is not None
    assert len(journal) == 1
    assert journal[0].entry_order_id == "alpaca-paper-accepted-1"
    assert journal[0].journal_status == "open"
    assert "outcome_status=accepted" in journal[0].notes


def test_trade_proposal_journal_upserts_by_entry_order_id(tmp_path) -> None:
    settings = _settings(tmp_path)
    db = TradingDatabase(settings)
    proposal = create_trade_proposal(
        db=db,
        symbol="NVDA",
        side="buy",
        quantity=1,
        reference_price=900,
        confidence=0.78,
        thesis="Initial thesis.",
        stop_loss=860,
        take_profit=980,
        source="manual",
    )
    outcome = ExecutionOutcome(
        intent_id="intent-accepted-1",
        order_id="alpaca-paper-accepted-1",
        status="accepted",
        adapter_name="alpaca_paper",
        execution_backend="alpaca_paper",
        message="Accepted by external paper broker.",
    )

    first_trade_id = db.create_trade_journal_from_proposal(
        proposal=proposal, outcome=outcome
    )
    filled_outcome = outcome.model_copy(
        update={
            "status": "filled",
            "filled_quantity": 1,
            "average_fill_price": 901,
            "message": "Filled by external paper broker.",
        }
    )
    second_trade_id = db.create_trade_journal_from_proposal(
        proposal=proposal, outcome=filled_outcome
    )

    journal = db.list_trade_journal(limit=5)
    assert second_trade_id == first_trade_id
    assert len(journal) == 1
    assert journal[0].entry_order_id == "alpaca-paper-accepted-1"
    assert journal[0].entry_price == pytest.approx(901)
    assert journal[0].journal_status == "open"
    assert "outcome_status=filled" in journal[0].notes


def test_trade_journal_migration_deduplicates_legacy_entry_order_rows(
    tmp_path,
) -> None:
    settings = _settings(tmp_path)
    db = TradingDatabase(settings)
    db.conn.execute("drop index if exists trade_journal_entry_order_id_idx")
    db.conn.executemany(
        """
        insert into trade_journal (
            trade_id, opened_at, closed_at, symbol, run_id, entry_order_id,
            exit_order_id, planned_side, approved, journal_status, entry_price,
            exit_price, stop_loss, take_profit, position_size_pct, confidence,
            coordinator_focus, strategy_family, manager_bias, review_summary,
            exit_reason, realized_pnl, notes
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                "trade-old",
                "2026-01-01T00:00:00+00:00",
                None,
                "NVDA",
                None,
                "order-duplicate",
                None,
                "buy",
                True,
                "open",
                900.0,
                None,
                860.0,
                980.0,
                0.0,
                0.7,
                "",
                "",
                "",
                "old",
                None,
                None,
                "old",
            ),
            (
                "trade-new",
                "2026-01-02T00:00:00+00:00",
                None,
                "NVDA",
                None,
                "order-duplicate",
                None,
                "buy",
                True,
                "open",
                901.0,
                None,
                860.0,
                980.0,
                0.0,
                0.8,
                "",
                "",
                "",
                "new",
                None,
                None,
                "new",
            ),
        ],
    )

    db._migrate_trade_journal_constraints()

    rows = db.conn.execute(
        "select trade_id from trade_journal where entry_order_id = ?",
        ["order-duplicate"],
    ).fetchall()
    assert rows == [("trade-new",)]


def test_trade_proposal_approval_keeps_accepted_order_in_flight(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """
    Verifies that approving a trade proposal against an external broker that acknowledges (but does not fill) the order leaves the proposal in an in-flight approved state and records an open journal entry.
    
    Creates a manual proposal, monkeypatches the broker adapter to return an `ExecutionOutcome` with status `"accepted"`, calls approval, and asserts that the execution outcome and stored proposal reflect the `"accepted"` status and that the trade journal contains a single open entry.
    """
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="alpaca_paper",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    proposal = create_trade_proposal(
        db=db,
        symbol="NVDA",
        side="buy",
        quantity=1,
        reference_price=900,
        confidence=0.78,
        thesis="External paper broker acknowledgement is not a fill.",
        stop_loss=860,
        take_profit=980,
        source="manual",
    )

    class AcceptedAdapter:
        def place_order(self, intent):
            """
            Create an ExecutionOutcome representing an accepted broker order for the given execution intent.
            
            Parameters:
                intent: The execution intent whose `intent_id` will be recorded on the outcome.
            
            Returns:
                ExecutionOutcome: An outcome with `intent_id` taken from `intent.intent_id`, `order_id` set to "alpaca-paper-accepted-approval", `status` set to "accepted", and both `adapter_name` and `execution_backend` set to "alpaca_paper".
            """
            return ExecutionOutcome(
                intent_id=intent.intent_id,
                order_id="alpaca-paper-accepted-approval",
                status="accepted",
                adapter_name="alpaca_paper",
                execution_backend="alpaca_paper",
            )

    monkeypatch.setattr(
        "agentic_trader.finance.proposals.get_broker_adapter",
        lambda *, db, settings: AcceptedAdapter(),
    )

    approved, outcome = approve_trade_proposal(
        db=db,
        settings=settings,
        proposal_id=proposal.proposal_id,
        review_notes="submit external paper order",
    )

    assert outcome.status == "accepted"
    assert approved.status == "approved"
    assert approved.execution_outcome_status == "accepted"
    journal = db.list_trade_journal(limit=5)
    assert len(journal) == 1
    assert journal[0].journal_status == "open"


def test_trade_proposal_refresh_updates_accepted_order_without_resubmit(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        execution_backend="alpaca_paper",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    proposal = create_trade_proposal(
        db=db,
        symbol="NVDA",
        side="buy",
        quantity=1,
        reference_price=900,
        confidence=0.78,
        thesis="External paper broker acknowledgement should be refreshable.",
        stop_loss=860,
        take_profit=980,
        source="manual",
    )
    intent = ExecutionIntent(
        intent_id="intent-refresh",
        symbol="NVDA",
        side="buy",
        quantity=1,
        reference_price=900,
        confidence=0.78,
        thesis="External paper broker acknowledgement should be refreshable.",
        approved=True,
        execution_backend="alpaca_paper",
        adapter_name="alpaca_paper",
        backend_metadata={"proposal_id": proposal.proposal_id},
    )
    accepted_outcome = ExecutionOutcome(
        intent_id=intent.intent_id,
        order_id="alpaca-paper-accepted-2",
        status="accepted",
        adapter_name="alpaca_paper",
        execution_backend="alpaca_paper",
    )
    executed = proposal.model_copy(
        update={
            "status": "approved",
            "updated_at": utc_now_iso(),
            "execution_intent_id": intent.intent_id,
            "execution_order_id": accepted_outcome.order_id,
            "execution_outcome_status": accepted_outcome.status,
        }
    )
    assert db.update_trade_proposal(executed, expected_status="pending")
    db.record_execution_outcome(run_id=None, intent=intent, outcome=accepted_outcome)
    db.create_trade_journal_from_proposal(proposal=executed, outcome=accepted_outcome)
    refresh_calls = 0

    class RefreshAdapter:
        def place_order(self, intent):
            """
            Fail fast if code attempts to submit a new broker order during an order-refresh operation.
            
            Parameters:
                intent: The execution intent that would have been sent to the broker (not used).
            
            Raises:
                AssertionError: Always raised with message "refresh must not submit a new broker order".
            """
            raise AssertionError("refresh must not submit a new broker order")

        def get_order_outcome(self, *, order_id, intent):
            """
            Fetch the execution outcome for a broker order and return an ExecutionOutcome representing a filled alpaca_paper order.
            
            Parameters:
                order_id (str): Broker order identifier to look up.
                intent (ExecutionIntent): Execution intent associated with the order; its `intent_id` will be copied into the outcome.
            
            Returns:
                ExecutionOutcome: Outcome with `intent_id` from `intent`, the supplied `order_id`, `status` set to `"filled"`, `adapter_name` and `execution_backend` set to `"alpaca_paper"`, `filled_quantity` of 1, and `average_fill_price` of 901.
            """
            nonlocal refresh_calls
            refresh_calls += 1
            assert order_id == "alpaca-paper-accepted-2"
            return ExecutionOutcome(
                intent_id=intent.intent_id,
                order_id=order_id,
                status="filled",
                adapter_name="alpaca_paper",
                execution_backend="alpaca_paper",
                filled_quantity=1,
                average_fill_price=901,
            )

    monkeypatch.setattr(
        "agentic_trader.finance.proposals.get_broker_order_reader",
        lambda *, db, settings: RefreshAdapter(),
    )

    refreshed, outcome = refresh_trade_proposal_order(
        db=db,
        settings=settings,
        proposal_id=proposal.proposal_id,
        review_notes="broker refresh",
    )

    latest = db.get_execution_record(intent.intent_id)
    journal = db.list_trade_journal(limit=5)
    position_plan = db.get_position_plan("NVDA")
    assert refresh_calls == 1
    assert refreshed.status == "executed"
    assert refreshed.execution_outcome_status == "filled"
    assert refreshed.execution_order_id == "alpaca-paper-accepted-2"
    assert outcome.status == "filled"
    assert latest is not None
    assert latest["status"] == "filled"
    assert len(journal) == 1
    assert journal[0].journal_status == "open"
    assert journal[0].entry_price == pytest.approx(901)
    assert "outcome_status=filled" in journal[0].notes
    assert position_plan is not None
    assert position_plan.entry_price == pytest.approx(901)


def test_repair_missing_position_plans_backfills_from_executed_proposal(
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
        stop_loss=95,
        take_profit=110,
        invalidation_condition="Exit if thesis breaks.",
    )
    approve_trade_proposal(
        db=db,
        settings=settings,
        proposal_id=proposal.proposal_id,
        review_notes="repair fixture approval",
    )
    db.delete_position_plan("MSFT")

    dry_run = repair_missing_position_plans(db=db)

    assert dry_run == [
        {
            "symbol": "MSFT",
            "status": "candidate",
            "reason": "dry-run candidate from executed proposal",
            "proposal_id": proposal.proposal_id,
            "side": "buy",
            "entry_price": 100.0,
            "stop_loss": 95.0,
            "take_profit": 110.0,
        }
    ]
    assert db.get_position_plan("MSFT") is None

    applied = repair_missing_position_plans(db=db, apply_repair=True)

    assert applied[0]["status"] == "created"
    plan = db.get_position_plan("MSFT")
    assert plan is not None
    assert plan.entry_price == pytest.approx(100)
    assert plan.stop_loss == pytest.approx(95)
    assert plan.take_profit == pytest.approx(110)
    assert plan.invalidation_logic == "Exit if thesis breaks."


def test_trade_proposal_approval_persists_in_flight_before_adapter_call(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """
    Verifies that approving a trade proposal persists an in-flight execution intent before calling the broker adapter and transitions the proposal to failed if the adapter raises.
    
    Asserts that after a broker adapter exception:
    - the stored proposal status is "failed" and has a non-null `execution_intent_id`;
    - the returned final proposal status is "failed";
    - the returned execution outcome has `status == "rejected"` and `rejection_reason == "adapter_exception"`;
    - the broker adapter was invoked exactly once;
    - subsequent attempts to approve the same proposal raise `ValueError` with "not pending".
    """
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
            review_notes="second approval attempt",
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
        stop_loss=95,
        take_profit=110,
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
            review_notes="atomic pending audit",
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
        stop_loss=95,
        take_profit=110,
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
            review_notes="atomic final audit",
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
        stop_loss=95,
        take_profit=110,
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
    journal = db.list_trade_journal(limit=5)
    position_plan = db.get_position_plan("MSFT")
    assert len(journal) == 1
    assert journal[0].entry_order_id == "paper-order-repair"
    assert journal[0].journal_status == "open"
    assert position_plan is not None
    assert position_plan.stop_loss == pytest.approx(95)
    assert position_plan.take_profit == pytest.approx(110)


def test_trade_proposal_reconcile_fails_closed_without_execution_record(
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
    approved = proposal.model_copy(
        update={
            "status": "approved",
            "updated_at": utc_now_iso(),
            "execution_intent_id": "intent-missing",
        }
    )
    assert db.update_trade_proposal(approved, expected_status="pending")

    with pytest.raises(ValueError, match="no recorded execution outcome"):
        reconcile_trade_proposal(
            db=db,
            proposal_id=proposal.proposal_id,
            review_notes="repair check",
        )


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


def test_trade_proposal_rejects_invalid_limit_contract(tmp_path) -> None:
    settings = _settings(tmp_path)
    db = TradingDatabase(settings)

    with pytest.raises(ValueError, match="Limit trade proposals require limit_price"):
        create_trade_proposal(
            db=db,
            symbol="AAPL",
            side="buy",
            order_type="limit",
            quantity=1,
            reference_price=100,
            confidence=0.7,
            thesis="Limit proposal without explicit price.",
        )

    with pytest.raises(ValueError, match="Limit trade proposals require quantity"):
        create_trade_proposal(
            db=db,
            symbol="AAPL",
            side="buy",
            order_type="limit",
            notional=100,
            limit_price=99.5,
            reference_price=100,
            confidence=0.7,
            thesis="Limit proposal sized by notional.",
        )

    with pytest.raises(ValueError, match="must not include limit_price"):
        create_trade_proposal(
            db=db,
            symbol="AAPL",
            side="buy",
            order_type="market",
            quantity=1,
            limit_price=99.5,
            reference_price=100,
            confidence=0.7,
            thesis="Market proposal with stray limit price.",
        )

    with pytest.raises(ValueError, match="order_type to be limit or market"):
        create_trade_proposal(
            db=db,
            symbol="AAPL",
            side="buy",
            order_type="stop",  # type: ignore[arg-type]
            quantity=1,
            reference_price=100,
            confidence=0.7,
            thesis="Unsupported order type should not enter the queue.",
        )

    with pytest.raises(ValueError, match="limit_price greater than zero"):
        create_trade_proposal(
            db=db,
            symbol="AAPL",
            side="buy",
            order_type="limit",
            quantity=1,
            limit_price=0,
            reference_price=100,
            confidence=0.7,
            thesis="Zero limit price should not enter the queue.",
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
        side="buy",
        order_type="limit",
        quantity=2,
        limit_price=124.25,
        reference_price=125,
        confidence=0.64,
        thesis="Risk desk limit candidate.",
        source="manual",
    )

    payload = json.loads(proposal.model_dump_json())
    hydrated = db.get_trade_proposal(payload["proposal_id"])

    assert hydrated is not None
    assert hydrated.quantity == pytest.approx(2)
    assert hydrated.side == "buy"
    assert hydrated.order_type == "limit"
    assert hydrated.limit_price == pytest.approx(124.25)


def test_trade_proposal_reads_legacy_database_without_table(tmp_path) -> None:
    settings = _settings(tmp_path)
    conn = duckdb.connect(str(settings.database_path))
    conn.execute("create table legacy_marker (id varchar)")
    conn.close()
    db = TradingDatabase(settings, read_only=True)

    assert db.list_trade_proposals() == []
    assert db.get_trade_proposal("proposal-missing") is None
