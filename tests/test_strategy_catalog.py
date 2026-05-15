from typing import cast

from agentic_trader.finance.ideas import IdeaCandidate, score_candidate
from agentic_trader.finance.strategy_catalog import (
    finance_reconciliation_contract_payload,
    get_strategy_profile,
    list_strategy_profiles,
    score_strategy_context,
    strategy_catalog_payload,
    strategy_profile_for_preset,
)


def test_strategy_catalog_maps_scanner_presets_to_runtime_profiles() -> None:
    profile = strategy_profile_for_preset("momentum")

    assert profile.name == "momentum-volume"
    assert profile.status == "implemented"
    assert "fresh_news_or_disclosure_catalyst" in profile.evidence_requirements


def test_strategy_catalog_filters_by_status_and_preset() -> None:
    implemented = list_strategy_profiles(status="implemented")
    breakout = strategy_catalog_payload(preset="breakout")
    profiles = cast(list[dict[str, object]], breakout["profiles"])

    assert implemented
    assert all(profile.status == "implemented" for profile in implemented)
    assert [item["name"] for item in profiles] == ["vwap-breakout"]


def test_strategy_profile_unknown_name_lists_known_profiles() -> None:
    try:
        get_strategy_profile("does-not-exist")
    except ValueError as exc:
        assert "momentum-volume" in str(exc)
    else:
        raise AssertionError("unknown profile should raise")


def test_score_strategy_context_requires_evidence_before_proposals() -> None:
    score = score_candidate(
        IdeaCandidate(
            symbol="NVDA",
            price=100,
            volume=5_000_000,
            change_pct=6.2,
            relative_volume=3.4,
            rsi=61,
            ema_9=96,
        ),
        "momentum",
    )

    context = score_strategy_context(score)
    strategy_profile = cast(dict[str, object], context["strategy_profile"])
    readiness = cast(dict[str, object], context["proposal_readiness"])
    missing_evidence = cast(list[str], readiness["missing_evidence"])

    assert strategy_profile["name"] == "momentum-volume"
    assert readiness["state"] == "needs_evidence"
    assert readiness["manual_approval_required"] is True
    assert "fresh_news_or_disclosure_catalyst" in missing_evidence


def test_finance_reconciliation_contract_keeps_missing_evidence_explicit() -> None:
    payload = finance_reconciliation_contract_payload()
    ledger_categories = cast(list[dict[str, object]], payload["ledger_categories"])
    categories = {str(item["name"]): item for item in ledger_categories}
    audit_policy = cast(dict[str, object], payload["audit_policy"])

    assert "trades" in categories
    assert "corporate_actions" in categories
    v1_policy = cast(dict[str, object], payload["v1_policy"])
    assert v1_policy["mode"] == "paper"
    assert (
        v1_policy["missing_evidence_policy"]
        == "missing evidence must stay explicit and never be treated as zero"
    )
    assert "corporate_actions" in cast(list[str], v1_policy["known_missing_categories"])
    assert audit_policy["distinguish_zero_from_missing"] is True
