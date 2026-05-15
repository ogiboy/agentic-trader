from typing import cast

import pytest

from agentic_trader.researchd.cycle_plan import research_cycle_plan_payload


def test_research_cycle_plan_preserves_manual_approval_boundary() -> None:
    payload = research_cycle_plan_payload(symbols=["aapl", " msft "], cadence_seconds=30)

    assert payload["watchlist"] == ["AAPL", "MSFT"]
    assert payload["cadence_seconds"] == 60
    safety_policy = cast(dict[str, object], payload["safety_policy"])
    phases = cast(list[dict[str, object]], payload["phases"])
    forbidden = cast(tuple[str, ...], phases[3]["forbidden"])
    assert safety_policy["manual_approval_required"] is True
    assert safety_policy["sidecar_broker_access"] is False
    assert phases[0]["name"] == "PRE-FLIGHT"
    assert "proposal_approve" in forbidden


def test_research_cycle_plan_rejects_empty_watchlist() -> None:
    with pytest.raises(ValueError, match="at least one non-empty symbol"):
        research_cycle_plan_payload(symbols=[" "], cadence_seconds=900)
