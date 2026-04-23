from typing import Any

import pytest
from pydantic import ValidationError

from agentic_trader.schemas import FundamentalAssessment


@pytest.mark.parametrize(
    ("kwargs", "expected_field", "expected_value"),
    [
        (
            {"growth_quality": "supportive"},
            "revenue_growth_quality",
            "supportive",
        ),
        (
            {"revenue_growth_quality": "cautious"},
            "growth_quality",
            "cautious",
        ),
        (
            {"red_flags": ["high_debt_risk"]},
            "risk_flags",
            ["high_debt_risk"],
        ),
        (
            {"risk_flags": ["fundamental_provider_missing"]},
            "red_flags",
            ["fundamental_provider_missing"],
        ),
    ],
)
def test_fundamental_assessment_syncs_legacy_fields(
    kwargs: dict[str, Any], expected_field: str, expected_value: object
) -> None:
    assessment = FundamentalAssessment(**kwargs)

    assert getattr(assessment, expected_field) == expected_value


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "growth_quality": "supportive",
            "revenue_growth_quality": "cautious",
        },
        {
            "balance_sheet_quality": "supportive",
            "debt_quality": "avoid",
        },
        {
            "fx_risk": "low",
            "fx_exposure_risk": "high",
        },
        {
            "overall_bias": "supportive",
            "overall_signal": "neutral",
        },
        {
            "red_flags": ["a"],
            "risk_flags": ["b"],
        },
    ],
)
def test_fundamental_assessment_rejects_conflicting_legacy_fields(
    kwargs: dict[str, Any],
) -> None:
    with pytest.raises(ValidationError, match="Conflicting fundamental assessment fields"):
        FundamentalAssessment(**kwargs)
