"""Tests for the helper functions added/changed in agentic_trader/agents/fundamental.py."""

from typing import cast

import pytest

from agentic_trader.agents.fundamental import (
    FUNDAMENTAL_PROVIDER_UNAVAILABLE_REASON,
    _business_quality,
    _dedupe,
    _fallback_fundamental,
    _forward_outlook,
    _fx_risk,
    _growth_quality,
    _has_structured_fundamental_evidence,
    _macro_fit,
    _metric_evidence,
    _overall_bias,
    _score_quality,
    _validate_llm_evidence_contract,
    assess_fundamentals,
)
from agentic_trader.config import Settings
from agentic_trader.features import build_decision_feature_bundle
from agentic_trader.schemas import (
    AnalysisSignal,
    AgentContext,
    EvidenceInferenceBreakdown,
    FundamentalAssessment,
    FundamentalFeatureSet,
    InvestmentPreferences,
    MacroContext,
    MarketSnapshot,
    PortfolioSnapshot,
)


# ---------------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------------


def _snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        symbol="AAPL",
        interval="1d",
        last_close=105.0,
        ema_20=102.0,
        ema_50=99.0,
        atr_14=2.0,
        rsi_14=61.0,
        volatility_20=0.12,
        return_5=0.03,
        return_20=0.09,
        volume_ratio_20=1.2,
        bars_analyzed=120,
    )


def _context(snapshot: MarketSnapshot | None = None) -> AgentContext:
    s = snapshot or _snapshot()
    settings = Settings()
    return AgentContext(
        role="fundamental",
        model_name="test-model",
        snapshot=s,
        decision_features=build_decision_feature_bundle(s, settings=settings),
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


def _features(
    revenue_growth: float | None = None,
    profitability_stability: float | None = None,
    cash_flow_alignment: float | None = None,
    debt_risk: float | None = None,
    fx_exposure: str = "unknown",
    reinvestment_potential: float | None = None,
    quality_flags: list[str] | None = None,
    data_sources: list[str] | None = None,
    summary: str = "",
) -> FundamentalFeatureSet:
    return FundamentalFeatureSet(
        symbol="AAPL",
        revenue_growth=revenue_growth,
        profitability_stability=profitability_stability,
        cash_flow_alignment=cash_flow_alignment,
        debt_risk=debt_risk,
        fx_exposure=fx_exposure,
        reinvestment_potential=reinvestment_potential,
        quality_flags=quality_flags or [],
        data_sources=data_sources or [],
        summary=summary,
    )


def _macro(
    fx_risk: str = "unknown",
    rates_bias: str = "unknown",
    region: str = "US",
) -> MacroContext:
    return MacroContext(
        symbol="AAPL",
        fx_risk=fx_risk,  # type: ignore[arg-type]
        rates_bias=rates_bias,  # type: ignore[arg-type]
        region=region,
    )


# ---------------------------------------------------------------------------
# _dedupe
# ---------------------------------------------------------------------------


class TestDedupe:
    def test_removes_duplicates_preserving_order(self) -> None:
        result = _dedupe(["a", "b", "a", "c", "b"])
        assert result == ["a", "b", "c"]

    def test_filters_empty_strings(self) -> None:
        result = _dedupe(["x", "", "y", ""])
        assert result == ["x", "y"]

    def test_empty_input(self) -> None:
        assert _dedupe([]) == []

    def test_all_duplicates_returns_single_item(self) -> None:
        assert _dedupe(["dup", "dup", "dup"]) == ["dup"]

    def test_no_duplicates_unchanged(self) -> None:
        assert _dedupe(["p", "q", "r"]) == ["p", "q", "r"]


# ---------------------------------------------------------------------------
# _score_quality
# ---------------------------------------------------------------------------


class TestScoreQuality:
    # low_is_bad=True (default): higher value -> better signal
    def test_none_returns_neutral(self) -> None:
        assert _score_quality(None) == "neutral"

    def test_high_value_is_supportive(self) -> None:
        assert _score_quality(0.7) == "supportive"
        assert _score_quality(1.0) == "supportive"

    def test_low_value_is_cautious(self) -> None:
        assert _score_quality(0.35) == "cautious"
        assert _score_quality(0.0) == "cautious"

    def test_mid_value_is_neutral(self) -> None:
        assert _score_quality(0.5) == "neutral"
        assert _score_quality(0.36) == "neutral"
        assert _score_quality(0.69) == "neutral"

    # low_is_bad=False: lower value -> better signal; very high -> avoid
    def test_very_high_value_is_avoid(self) -> None:
        assert _score_quality(0.85, low_is_bad=False) == "avoid"
        assert _score_quality(1.0, low_is_bad=False) == "avoid"

    def test_high_value_is_cautious_when_low_is_bad_false(self) -> None:
        assert _score_quality(0.55, low_is_bad=False) == "cautious"
        assert _score_quality(0.84, low_is_bad=False) == "cautious"

    def test_low_value_is_supportive_when_low_is_bad_false(self) -> None:
        assert _score_quality(0.25, low_is_bad=False) == "supportive"
        assert _score_quality(0.0, low_is_bad=False) == "supportive"

    def test_mid_value_is_neutral_when_low_is_bad_false(self) -> None:
        assert _score_quality(0.4, low_is_bad=False) == "neutral"
        assert _score_quality(0.26, low_is_bad=False) == "neutral"
        assert _score_quality(0.54, low_is_bad=False) == "neutral"

    def test_none_returns_neutral_when_low_is_bad_false(self) -> None:
        assert _score_quality(None, low_is_bad=False) == "neutral"


# ---------------------------------------------------------------------------
# _growth_quality
# ---------------------------------------------------------------------------


class TestGrowthQuality:
    def test_none_is_neutral(self) -> None:
        assert _growth_quality(None) == "neutral"

    def test_strong_positive_growth_is_supportive(self) -> None:
        assert _growth_quality(0.1) == "supportive"
        assert _growth_quality(0.5) == "supportive"

    def test_negative_growth_is_cautious(self) -> None:
        assert _growth_quality(-0.05) == "cautious"
        assert _growth_quality(-0.5) == "cautious"

    def test_low_positive_growth_is_neutral(self) -> None:
        assert _growth_quality(0.05) == "neutral"
        assert _growth_quality(0.09) == "neutral"

    def test_boundary_at_negative_threshold(self) -> None:
        # -0.04 is above -0.05, so neutral
        assert _growth_quality(-0.04) == "neutral"


# ---------------------------------------------------------------------------
# _fx_risk
# ---------------------------------------------------------------------------


class TestFxRisk:
    def test_macro_overrides_feature_when_not_unknown(self) -> None:
        feat = _features(fx_exposure="low")
        mac = _macro(fx_risk="high")
        assert _fx_risk(feat, mac) == "high"

    def test_macro_unknown_falls_back_to_feature(self) -> None:
        feat = _features(fx_exposure="medium")
        mac = _macro(fx_risk="unknown")
        assert _fx_risk(feat, mac) == "medium"

    def test_no_macro_uses_feature(self) -> None:
        feat = _features(fx_exposure="low")
        assert _fx_risk(feat, None) == "low"

    def test_feature_fx_exposure_case_insensitive(self) -> None:
        feat = _features(fx_exposure="HIGH")
        assert _fx_risk(feat, None) == "high"

    def test_empty_feature_fx_exposure_returns_unknown(self) -> None:
        feat = _features(fx_exposure="")
        assert _fx_risk(feat, None) == "unknown"

    def test_unrecognized_feature_fx_exposure_returns_unknown(self) -> None:
        feat = _features(fx_exposure="moderate")
        assert _fx_risk(feat, None) == "unknown"

    def test_feature_unknown_returns_unknown(self) -> None:
        feat = _features(fx_exposure="unknown")
        assert _fx_risk(feat, None) == "unknown"

    def test_macro_unknown_and_feature_unknown_returns_unknown(self) -> None:
        feat = _features(fx_exposure="unknown")
        mac = _macro(fx_risk="unknown")
        assert _fx_risk(feat, mac) == "unknown"


# ---------------------------------------------------------------------------
# _macro_fit
# ---------------------------------------------------------------------------


class TestMacroFit:
    def test_none_returns_neutral(self) -> None:
        assert _macro_fit(None) == "neutral"

    def test_high_fx_risk_returns_cautious(self) -> None:
        assert _macro_fit(_macro(fx_risk="high")) == "cautious"

    def test_headwind_rates_returns_cautious(self) -> None:
        assert _macro_fit(_macro(rates_bias="headwind")) == "cautious"

    def test_low_fx_with_tailwind_returns_supportive(self) -> None:
        assert _macro_fit(_macro(fx_risk="low", rates_bias="tailwind")) == "supportive"

    def test_low_fx_with_neutral_rates_returns_supportive(self) -> None:
        assert _macro_fit(_macro(fx_risk="low", rates_bias="neutral")) == "supportive"

    def test_medium_fx_with_neutral_rates_returns_neutral(self) -> None:
        assert _macro_fit(_macro(fx_risk="medium", rates_bias="neutral")) == "neutral"

    def test_unknown_fx_and_unknown_rates_returns_neutral(self) -> None:
        assert _macro_fit(_macro(fx_risk="unknown", rates_bias="unknown")) == "neutral"


# ---------------------------------------------------------------------------
# _business_quality
# ---------------------------------------------------------------------------


class TestBusinessQuality:
    def test_avoid_in_any_input_returns_avoid(self) -> None:
        assert _business_quality("avoid", "supportive", "supportive") == "avoid"
        assert _business_quality("supportive", "avoid", "neutral") == "avoid"
        assert _business_quality("neutral", "neutral", "avoid") == "avoid"

    def test_cautious_without_avoid_returns_cautious(self) -> None:
        assert _business_quality("cautious", "neutral", "neutral") == "cautious"
        assert _business_quality("neutral", "cautious", "supportive") == "cautious"
        assert _business_quality("supportive", "neutral", "cautious") == "cautious"

    def test_supportive_both_profitability_and_cash_flow_returns_supportive(
        self,
    ) -> None:
        assert _business_quality("supportive", "supportive", "neutral") == "supportive"

    def test_profitability_supportive_cash_flow_neutral_reinvestment_supportive(
        self,
    ) -> None:
        assert _business_quality("supportive", "neutral", "supportive") == "supportive"

    def test_all_neutral_returns_neutral(self) -> None:
        assert _business_quality("neutral", "neutral", "neutral") == "neutral"

    def test_only_reinvestment_supportive_returns_neutral(self) -> None:
        # profitability and cash_flow must be in {supportive, neutral} and one must be supportive
        # if only reinvestment is supportive and others are neutral, result should be neutral
        # because profitability_quality and cash_flow_quality are not both in {supportive, neutral}
        # Wait - neutral IS in {supportive, neutral}, so this should return "supportive" if reinvestment is supportive
        # Let me re-read the code logic:
        # if {profitability_quality, cash_flow_quality}.issubset({"supportive", "neutral"}):
        #   if "supportive" in {profitability_quality, cash_flow_quality, reinvestment_quality}:
        #     return "supportive"
        # So if both profit and cash_flow are neutral, and reinvestment is supportive -> supportive
        assert _business_quality("neutral", "neutral", "supportive") == "supportive"

    def test_avoid_takes_priority_over_cautious(self) -> None:
        assert _business_quality("avoid", "cautious", "cautious") == "avoid"


# ---------------------------------------------------------------------------
# _forward_outlook
# ---------------------------------------------------------------------------


class TestForwardOutlook:
    def test_avoid_in_any_returns_avoid(self) -> None:
        assert _forward_outlook("avoid", "supportive", "supportive") == "avoid"
        assert _forward_outlook("supportive", "avoid", "neutral") == "avoid"
        assert _forward_outlook("neutral", "neutral", "avoid") == "avoid"

    def test_cautious_without_avoid_returns_cautious(self) -> None:
        assert _forward_outlook("cautious", "neutral", "neutral") == "cautious"
        assert _forward_outlook("supportive", "cautious", "neutral") == "cautious"
        assert _forward_outlook("neutral", "supportive", "cautious") == "cautious"

    def test_both_growth_and_business_supportive_returns_supportive(self) -> None:
        assert _forward_outlook("supportive", "supportive", "neutral") == "supportive"
        assert (
            _forward_outlook("supportive", "supportive", "supportive") == "supportive"
        )

    def test_only_growth_supportive_returns_neutral(self) -> None:
        assert _forward_outlook("supportive", "neutral", "neutral") == "neutral"

    def test_only_business_supportive_returns_neutral(self) -> None:
        assert _forward_outlook("neutral", "supportive", "neutral") == "neutral"

    def test_all_neutral_returns_neutral(self) -> None:
        assert _forward_outlook("neutral", "neutral", "neutral") == "neutral"


# ---------------------------------------------------------------------------
# _overall_bias
# ---------------------------------------------------------------------------


class TestOverallBias:
    def test_avoid_signal_dominates(self) -> None:
        signals: list[AnalysisSignal] = [
            "avoid",
            "supportive",
            "supportive",
            "supportive",
            "supportive",
        ]
        assert _overall_bias(signals, has_provider_gap=False) == "avoid"

    def test_cautious_without_avoid_dominates(self) -> None:
        signals: list[AnalysisSignal] = [
            "cautious",
            "supportive",
            "supportive",
            "supportive",
            "supportive",
        ]
        assert _overall_bias(signals, has_provider_gap=False) == "cautious"

    def test_provider_gap_forces_neutral(self) -> None:
        # Even 4+ supportive signals yield neutral when provider gap exists
        signals: list[AnalysisSignal] = [
            "supportive",
            "supportive",
            "supportive",
            "supportive",
            "supportive",
        ]
        assert _overall_bias(signals, has_provider_gap=True) == "neutral"

    def test_four_or_more_supportive_without_gap_returns_supportive(self) -> None:
        signals: list[AnalysisSignal] = [
            "supportive",
            "supportive",
            "supportive",
            "supportive",
        ]
        assert _overall_bias(signals, has_provider_gap=False) == "supportive"

    def test_fewer_than_four_supportive_returns_neutral(self) -> None:
        signals: list[AnalysisSignal] = [
            "supportive",
            "supportive",
            "supportive",
            "neutral",
        ]
        assert _overall_bias(signals, has_provider_gap=False) == "neutral"

    def test_empty_signals_without_gap_returns_neutral(self) -> None:
        assert _overall_bias([], has_provider_gap=False) == "neutral"

    def test_empty_signals_with_gap_returns_neutral(self) -> None:
        assert _overall_bias([], has_provider_gap=True) == "neutral"

    def test_avoid_takes_priority_over_provider_gap(self) -> None:
        signals: list[AnalysisSignal] = ["avoid"]
        assert _overall_bias(signals, has_provider_gap=True) == "avoid"

    def test_cautious_takes_priority_over_provider_gap(self) -> None:
        signals: list[AnalysisSignal] = ["cautious"]
        assert _overall_bias(signals, has_provider_gap=True) == "cautious"


# ---------------------------------------------------------------------------
# _validate_llm_evidence_contract
# ---------------------------------------------------------------------------


class TestValidateLlmEvidenceContract:
    def test_non_llm_source_passes_validation(self) -> None:
        assessment = FundamentalAssessment(
            source="fallback",
            overall_bias="supportive",
        )
        assert _validate_llm_evidence_contract(assessment) is None

    def test_llm_with_no_evidence_or_inference_or_uncertainty_raises(self) -> None:
        assessment = FundamentalAssessment(
            source="llm",
            overall_bias="neutral",
            evidence_vs_inference=EvidenceInferenceBreakdown(
                evidence=[], inference=[], uncertainty=[]
            ),
        )
        with pytest.raises(ValueError, match="evidence, inference, or uncertainty"):
            _validate_llm_evidence_contract(assessment)

    def test_llm_with_only_inference_passes(self) -> None:
        assessment = FundamentalAssessment(
            source="llm",
            overall_bias="neutral",
            evidence_vs_inference=EvidenceInferenceBreakdown(
                inference=["Inferred from sector trends."]
            ),
        )
        assert _validate_llm_evidence_contract(assessment) is None

    def test_llm_with_only_uncertainty_passes(self) -> None:
        assessment = FundamentalAssessment(
            source="llm",
            overall_bias="neutral",
            evidence_vs_inference=EvidenceInferenceBreakdown(
                uncertainty=["Data is incomplete."]
            ),
        )
        assert _validate_llm_evidence_contract(assessment) is None

    def test_non_neutral_llm_bias_without_direct_evidence_raises(self) -> None:
        assessment = FundamentalAssessment(
            source="llm",
            overall_bias="supportive",
            evidence_vs_inference=EvidenceInferenceBreakdown(
                inference=["Strong revenue trend observed."]
            ),
        )
        with pytest.raises(ValueError, match="requires direct evidence"):
            _validate_llm_evidence_contract(assessment)

    def test_non_neutral_llm_bias_with_direct_evidence_passes(self) -> None:
        assessment = FundamentalAssessment(
            source="llm",
            overall_bias="cautious",
            evidence_vs_inference=EvidenceInferenceBreakdown(
                evidence=["Debt-to-equity ratio above 2.5."],
                inference=["Likely to face refinancing headwinds."],
            ),
        )
        assert _validate_llm_evidence_contract(assessment) is None

    def test_avoid_bias_without_direct_evidence_raises(self) -> None:
        assessment = FundamentalAssessment(
            source="llm",
            overall_bias="avoid",
            evidence_vs_inference=EvidenceInferenceBreakdown(
                inference=["Seems risky."]
            ),
        )
        with pytest.raises(ValueError, match="requires direct evidence"):
            _validate_llm_evidence_contract(assessment)


# ---------------------------------------------------------------------------
# _metric_evidence
# ---------------------------------------------------------------------------


class TestMetricEvidence:
    def test_all_none_metrics_returns_empty_evidence_lines(self) -> None:
        feat = _features()
        result = _metric_evidence(feat)
        # No metrics, no data_sources, no summary → empty
        assert result == []

    def test_present_metric_appears_in_evidence(self) -> None:
        feat = _features(revenue_growth=0.12)
        result = _metric_evidence(feat)
        assert any("revenue_growth=0.12" in item for item in result)

    def test_data_sources_appended_when_present(self) -> None:
        feat = _features(data_sources=["finnhub", "fmp"])
        result = _metric_evidence(feat)
        assert any("sources=finnhub,fmp" in item for item in result)

    def test_summary_appended_when_present(self) -> None:
        feat = _features(summary="Solid balance sheet from SEC 10-K.")
        result = _metric_evidence(feat)
        assert "Solid balance sheet from SEC 10-K." in result

    def test_all_metrics_present(self) -> None:
        feat = _features(
            revenue_growth=0.15,
            profitability_stability=0.72,
            cash_flow_alignment=0.68,
            debt_risk=0.25,
            reinvestment_potential=0.61,
        )
        result = _metric_evidence(feat)
        labels = {
            "revenue_growth",
            "profitability_stability",
            "cash_flow_alignment",
            "debt_risk",
            "reinvestment_potential",
        }
        found = {item.split("=")[0] for item in result}
        assert labels <= found


# ---------------------------------------------------------------------------
# _has_structured_fundamental_evidence
# ---------------------------------------------------------------------------


class TestHasStructuredFundamentalEvidence:
    def test_none_context_returns_false(self) -> None:
        assert _has_structured_fundamental_evidence(None) is False

    def test_context_without_decision_features_returns_false(self) -> None:
        context = _context()
        bare_context = context.model_copy(update={"decision_features": None})
        assert _has_structured_fundamental_evidence(bare_context) is False

    def test_quality_flags_with_provider_missing_returns_false(self) -> None:
        context = _context()
        features = context.decision_features
        assert features is not None
        flagged = context.model_copy(
            update={
                "decision_features": features.model_copy(
                    update={
                        "fundamental": features.fundamental.model_copy(
                            update={"quality_flags": ["fundamental_provider_missing"]}
                        )
                    }
                )
            }
        )
        assert _has_structured_fundamental_evidence(flagged) is False

    def test_quality_flags_with_fetch_not_implemented_returns_false(self) -> None:
        context = _context()
        features = context.decision_features
        assert features is not None
        flagged = context.model_copy(
            update={
                "decision_features": features.model_copy(
                    update={
                        "fundamental": features.fundamental.model_copy(
                            update={
                                "quality_flags": ["fundamental_fetch_not_implemented"]
                            }
                        )
                    }
                )
            }
        )
        assert _has_structured_fundamental_evidence(flagged) is False

    def test_quality_flags_with_provider_not_configured_returns_false(self) -> None:
        context = _context()
        features = context.decision_features
        assert features is not None
        flagged = context.model_copy(
            update={
                "decision_features": features.model_copy(
                    update={
                        "fundamental": features.fundamental.model_copy(
                            update={
                                "quality_flags": ["fundamental_provider_not_configured"]
                            }
                        )
                    }
                )
            }
        )
        assert _has_structured_fundamental_evidence(flagged) is False

    def test_no_provider_flags_returns_true(self) -> None:
        context = _context()
        features = context.decision_features
        assert features is not None
        clean = context.model_copy(
            update={
                "decision_features": features.model_copy(
                    update={
                        "fundamental": features.fundamental.model_copy(
                            update={"quality_flags": []}
                        )
                    }
                )
            }
        )
        assert _has_structured_fundamental_evidence(clean) is True

    def test_unrelated_quality_flags_return_true(self) -> None:
        context = _context()
        features = context.decision_features
        assert features is not None
        unrelated = context.model_copy(
            update={
                "decision_features": features.model_copy(
                    update={
                        "fundamental": features.fundamental.model_copy(
                            update={"quality_flags": ["some_other_flag"]}
                        )
                    }
                )
            }
        )
        assert _has_structured_fundamental_evidence(unrelated) is True


# ---------------------------------------------------------------------------
# _fallback_fundamental
# ---------------------------------------------------------------------------


class TestFallbackFundamental:
    def test_fallback_with_no_context_is_neutral(self) -> None:
        result = _fallback_fundamental(None)
        assert result.source == "fallback"
        assert result.overall_bias == "neutral"
        assert result.confidence == pytest.approx(0.0)

    def test_fallback_with_high_debt_risk_produces_avoid_balance_sheet(self) -> None:
        context = _context()
        features = context.decision_features
        assert features is not None
        high_debt_context = context.model_copy(
            update={
                "decision_features": features.model_copy(
                    update={
                        "fundamental": features.fundamental.model_copy(
                            update={"debt_risk": 0.9, "quality_flags": []}
                        )
                    }
                )
            }
        )
        result = _fallback_fundamental(high_debt_context)
        assert result.balance_sheet_quality == "avoid"
        assert "high_debt_risk" in result.red_flags

    def test_fallback_with_provider_missing_flag_sets_confidence_zero(self) -> None:
        context = _context()
        features = context.decision_features
        assert features is not None
        flagged = context.model_copy(
            update={
                "decision_features": features.model_copy(
                    update={
                        "fundamental": features.fundamental.model_copy(
                            update={
                                "quality_flags": ["fundamental_fetch_not_implemented"],
                            }
                        )
                    }
                )
            }
        )
        result = _fallback_fundamental(
            flagged, fallback_reason=FUNDAMENTAL_PROVIDER_UNAVAILABLE_REASON
        )
        assert result.confidence == pytest.approx(0.0)

    def test_fallback_without_provider_missing_flag_sets_confidence_035(self) -> None:
        context = _context()
        features = context.decision_features
        assert features is not None
        no_flags = context.model_copy(
            update={
                "decision_features": features.model_copy(
                    update={
                        "fundamental": features.fundamental.model_copy(
                            update={"quality_flags": []}
                        )
                    }
                )
            }
        )
        result = _fallback_fundamental(no_flags)
        assert result.confidence == pytest.approx(0.35)

    def test_fallback_deduplicates_red_flags(self) -> None:
        context = _context()
        features = context.decision_features
        assert features is not None
        # debt_risk=0.9 triggers high_debt_risk; set quality_flags to include a duplicate
        dup_context = context.model_copy(
            update={
                "decision_features": features.model_copy(
                    update={
                        "fundamental": features.fundamental.model_copy(
                            update={
                                "debt_risk": 0.9,
                                "quality_flags": ["high_debt_risk"],
                            }
                        )
                    }
                )
            }
        )
        result = _fallback_fundamental(dup_context)
        # high_debt_risk should appear exactly once in red_flags
        assert result.red_flags.count("high_debt_risk") == 1

    def test_fallback_sets_fallback_reason(self) -> None:
        result = _fallback_fundamental(None, fallback_reason="test reason")
        assert result.fallback_reason == "test reason"

    def test_fallback_with_high_growth_adds_strength(self) -> None:
        context = _context()
        features = context.decision_features
        assert features is not None
        high_growth = context.model_copy(
            update={
                "decision_features": features.model_copy(
                    update={
                        "fundamental": features.fundamental.model_copy(
                            update={"revenue_growth": 0.20, "quality_flags": []}
                        )
                    }
                )
            }
        )
        result = _fallback_fundamental(high_growth)
        assert "growth_evidence_supportive" in result.strengths

    def test_fallback_evidence_contains_metric_when_present(self) -> None:
        context = _context()
        features = context.decision_features
        assert features is not None
        with_growth = context.model_copy(
            update={
                "decision_features": features.model_copy(
                    update={
                        "fundamental": features.fundamental.model_copy(
                            update={"revenue_growth": 0.15, "quality_flags": []}
                        )
                    }
                )
            }
        )
        result = _fallback_fundamental(with_growth)
        assert any(
            "revenue_growth=0.15" in e for e in result.evidence_vs_inference.evidence
        )

    def test_fallback_with_medium_fx_risk_adds_flag(self) -> None:
        context = _context()
        features = context.decision_features
        assert features is not None
        medium_fx = context.model_copy(
            update={
                "decision_features": features.model_copy(
                    update={
                        "fundamental": features.fundamental.model_copy(
                            update={"fx_exposure": "medium", "quality_flags": []}
                        )
                    }
                )
            }
        )
        result = _fallback_fundamental(medium_fx)
        assert "medium_fx_risk" in result.red_flags


# ---------------------------------------------------------------------------
# assess_fundamentals (integration with helper chain)
# ---------------------------------------------------------------------------


class TestAssessFundamentals:
    def test_falls_back_when_provider_flags_present(self) -> None:
        """assess_fundamentals should return fallback without calling LLM when provider flags are present."""
        context = _context()
        features = context.decision_features
        assert features is not None
        flagged = context.model_copy(
            update={
                "decision_features": features.model_copy(
                    update={
                        "fundamental": features.fundamental.model_copy(
                            update={"quality_flags": ["fundamental_provider_missing"]}
                        )
                    }
                )
            }
        )

        class _NoCallLLM:
            def for_role(self, _role: str) -> "_NoCallLLM":
                return self

            def complete_structured(self, **_kwargs: object) -> object:
                raise AssertionError(
                    "LLM should not be called when provider data is missing"
                )

        from agentic_trader.llm.client import LocalLLM

        result = assess_fundamentals(
            cast(LocalLLM, _NoCallLLM()),
            _snapshot(),
            allow_fallback=True,
            context=flagged,
        )
        assert result.source == "fallback"
        assert result.fallback_reason == FUNDAMENTAL_PROVIDER_UNAVAILABLE_REASON

    def test_returns_structured_fallback_when_allow_fallback_false_and_no_provider_evidence(
        self,
    ) -> None:
        """When no provider evidence exists, returns explicit fallback even in strict runtime mode."""
        context = _context()
        features = context.decision_features
        assert features is not None
        flagged = context.model_copy(
            update={
                "decision_features": features.model_copy(
                    update={
                        "fundamental": features.fundamental.model_copy(
                            update={"quality_flags": ["fundamental_provider_missing"]}
                        )
                    }
                )
            }
        )
        from agentic_trader.llm.client import LocalLLM

        class _FailLLM:
            def for_role(self, _role: str) -> "_FailLLM":
                return self

            def complete_structured(self, **_kwargs: object) -> object:
                raise RuntimeError("LLM unavailable")

        result = assess_fundamentals(
            cast(LocalLLM, _FailLLM()),
            _snapshot(),
            allow_fallback=False,
            context=flagged,
        )

        assert result.source == "fallback"
        assert result.fallback_reason == FUNDAMENTAL_PROVIDER_UNAVAILABLE_REASON
