from typing import Any, cast

import pytest

from agentic_trader.agents.fundamental import assess_fundamentals
from agentic_trader.agents.macro import assess_macro_context
from agentic_trader.config import Settings
from agentic_trader.features import build_decision_feature_bundle
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import (
    AgentContext,
    EvidenceInferenceBreakdown,
    FundamentalAssessment,
    InvestmentPreferences,
    MarketSnapshot,
    PortfolioSnapshot,
)


class _FailingLLM:
    def for_role(self, _role: str) -> "_FailingLLM":
        return self

    def complete_structured(self, **_kwargs: Any) -> object:
        raise RuntimeError("LLM unavailable in test")


class _StaticLLM:
    def __init__(self, assessment: FundamentalAssessment) -> None:
        self._assessment = assessment

    def for_role(self, _role: str) -> "_StaticLLM":
        return self

    def complete_structured(self, **_kwargs: Any) -> FundamentalAssessment:
        return self._assessment


def _snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        symbol="AAPL",
        interval="1d",
        as_of="2025-06-30",
        last_close=105.0,
        ema_20=102.0,
        ema_50=99.0,
        atr_14=2.0,
        rsi_14=61.0,
        volatility_20=0.12,
        return_5=0.03,
        return_20=0.09,
        volume_ratio_20=1.2,
        mtf_alignment="bullish",
        mtf_confidence=0.72,
        bars_analyzed=120,
    )


def _context(snapshot: MarketSnapshot) -> AgentContext:
    settings = Settings()
    return AgentContext(
        role="fundamental",
        model_name="test-model",
        snapshot=snapshot,
        decision_features=build_decision_feature_bundle(snapshot, settings=settings),
        preferences=InvestmentPreferences(),
        portfolio=PortfolioSnapshot(
            cash=100_000.0,
            market_value=0.0,
            equity=100_000.0,
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            open_positions=0,
        ),
    )


def test_fundamental_agent_falls_back_to_structured_neutral_assessment() -> None:
    context = _context(_snapshot())
    assessment = assess_fundamentals(
        cast(LocalLLM, _FailingLLM()),
        context.snapshot,
        allow_fallback=True,
        context=context,
    )

    assert assessment.source == "fallback"
    assert assessment.overall_bias == "neutral"
    assert assessment.overall_signal == "neutral"
    assert assessment.growth_quality == "neutral"
    assert assessment.balance_sheet_quality == "neutral"
    assert assessment.business_quality == "neutral"
    assert assessment.forward_outlook == "neutral"
    assert "fundamental_fetch_not_implemented" in assessment.risk_flags
    assert "fundamental_fetch_not_implemented" in assessment.red_flags
    assert assessment.evidence_vs_inference.uncertainty
    assert assessment.fallback_reason == "Structured fundamental provider data is unavailable."


def test_fundamental_assessment_schema_exposes_evidence_contract() -> None:
    properties = FundamentalAssessment.model_json_schema()["properties"]

    for field in [
        "growth_quality",
        "profitability_quality",
        "cash_flow_quality",
        "balance_sheet_quality",
        "fx_risk",
        "business_quality",
        "macro_fit",
        "forward_outlook",
        "red_flags",
        "strengths",
        "evidence_vs_inference",
        "overall_bias",
    ]:
        assert field in properties


def test_fundamental_agent_is_conservative_with_debt_risk() -> None:
    context = _context(_snapshot())
    features = context.decision_features
    assert features is not None
    cautious_features = features.model_copy(
        update={
            "fundamental": features.fundamental.model_copy(
                update={
                    "debt_risk": 0.92,
                    "quality_flags": [],
                    "summary": "Provider supplied partial balance sheet metrics.",
                }
            )
        }
    )
    cautious_context = context.model_copy(update={"decision_features": cautious_features})

    assessment = assess_fundamentals(
        cast(LocalLLM, _FailingLLM()),
        cautious_context.snapshot,
        allow_fallback=True,
        context=cautious_context,
    )

    assert assessment.balance_sheet_quality == "avoid"
    assert assessment.overall_bias == "avoid"
    assert "high_debt_risk" in assessment.red_flags
    assert assessment.evidence_vs_inference.evidence


def test_fundamental_agent_handles_missing_fx_exposure() -> None:
    context = _context(_snapshot())
    features = context.decision_features
    assert features is not None
    missing_fx_context = context.model_copy(
        update={
            "decision_features": features.model_copy(
                update={
                    "fundamental": features.fundamental.model_copy(
                        update={"fx_exposure": None}
                    )
                }
            )
        }
    )

    assessment = assess_fundamentals(
        cast(LocalLLM, _FailingLLM()),
        missing_fx_context.snapshot,
        allow_fallback=True,
        context=missing_fx_context,
    )

    assert assessment.fx_risk == "unknown"


def test_fundamental_agent_rejects_unsupported_llm_bias() -> None:
    context = _context(_snapshot())
    features = context.decision_features
    assert features is not None
    provider_context = context.model_copy(
        update={
            "decision_features": features.model_copy(
                update={
                    "fundamental": features.fundamental.model_copy(
                        update={"quality_flags": [], "data_sources": ["provider_fixture"]}
                    )
                }
            )
        }
    )
    unsupported = FundamentalAssessment(
        source="llm",
        overall_bias="supportive",
        evidence_vs_inference=EvidenceInferenceBreakdown(
            inference=["Analyst inferred quality without a cited metric."]
        ),
        summary="Looks strong without cited evidence.",
    )

    with pytest.raises(ValueError, match="requires direct evidence"):
        assess_fundamentals(
            cast(LocalLLM, _StaticLLM(unsupported)),
            provider_context.snapshot,
            allow_fallback=False,
            context=provider_context,
        )


def test_macro_agent_falls_back_to_structured_neutral_assessment() -> None:
    context = _context(_snapshot())
    assessment = assess_macro_context(
        cast(LocalLLM, _FailingLLM()),
        context.snapshot,
        allow_fallback=True,
        context=context,
    )

    assert assessment.source == "fallback"
    assert assessment.macro_signal == "neutral"
    assert "no_structured_news_signals" in assessment.risk_flags
    assert assessment.fallback_reason == "Structured macro/news provider data is unavailable."
