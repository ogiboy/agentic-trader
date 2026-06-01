from typing import cast

from agentic_trader.finance.ideas import IdeaCandidate, score_candidate
from agentic_trader.finance.strategy_catalog import (
    STRATEGY_PROFILES,
    finance_reconciliation_contract_payload,
    get_strategy_profile,
    list_strategy_profiles,
    score_strategy_context,
    strategy_catalog_payload,
    strategy_profile_for_preset,
    strategy_profile_payload,
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


def test_strategy_profile_payload_returns_dict_with_all_fields() -> None:
    profile = strategy_profile_for_preset("momentum")

    payload = strategy_profile_payload(profile)

    assert payload["name"] == "momentum-volume"
    assert payload["family"] == "momentum"
    assert payload["status"] == "implemented"
    assert isinstance(payload["summary"], str) and payload["summary"]
    assert isinstance(payload["evidence_requirements"], tuple)
    assert isinstance(payload["risk_controls"], tuple)
    assert isinstance(payload["validation_checks"], tuple)
    assert isinstance(payload["idea_presets"], tuple)
    assert isinstance(payload["required_inputs"], tuple)
    assert "proposal_policy" in payload
    assert "v1_path" in payload


def test_strategy_profile_payload_is_json_safe() -> None:
    import json

    profile = strategy_profile_for_preset("momentum")
    payload = strategy_profile_payload(profile)

    # Should be encodable to JSON (lists/strings only, no custom objects)
    # asdict() converts tuples to tuples which are JSON-serializable via list
    dumped = json.dumps(
        {
            key: list(cast(tuple[object, ...], value))
            if isinstance(value, tuple)
            else value
            for key, value in payload.items()
        }
    )
    assert "momentum-volume" in dumped


def test_strategy_profile_payload_contains_evidence_requirements() -> None:
    profile = strategy_profile_for_preset("momentum")

    payload = strategy_profile_payload(profile)

    evidence = payload["evidence_requirements"]
    assert isinstance(evidence, tuple)
    assert "fresh_news_or_disclosure_catalyst" in evidence


def test_strategy_profile_payload_works_for_all_profiles() -> None:
    for profile in STRATEGY_PROFILES:
        payload = strategy_profile_payload(profile)
        assert isinstance(payload["name"], str)
        assert isinstance(payload["family"], str)
        assert isinstance(payload["status"], str)


def test_strategy_profile_payload_round_trips_through_get_strategy_profile() -> None:
    profile = get_strategy_profile("momentum-volume")

    payload = strategy_profile_payload(profile)

    assert payload["name"] == profile.name
    assert payload["family"] == profile.family
    assert payload["status"] == profile.status
    assert payload["v1_path"] == profile.v1_path


def test_strategy_profile_payload_rejects_non_dataclass() -> None:
    import pytest

    with pytest.raises(TypeError, match="expected dataclass instance"):
        strategy_profile_payload({"name": "fake"})  # type: ignore[arg-type]


def test_finance_reconciliation_contract_keeps_missing_evidence_explicit() -> None:
    payload = finance_reconciliation_contract_payload()
    ledger_categories = cast(list[dict[str, object]], payload["ledger_categories"])
    categories = {str(category["name"]) for category in ledger_categories}

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
