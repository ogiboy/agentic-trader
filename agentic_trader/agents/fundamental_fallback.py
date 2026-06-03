from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, cast

from agentic_trader.agents.constants import LLM_FALLBACK_REASON
from agentic_trader.schemas import (
    AgentContext,
    AnalysisSignal,
    EvidenceInferenceBreakdown,
    FundamentalAssessment,
    FundamentalFeatureSet,
    MacroContext,
)

FxRisk = Literal["low", "medium", "high", "unknown"]
FUNDAMENTAL_PROVIDER_UNAVAILABLE_REASON = (
    "Structured fundamental provider data is unavailable."
)
PROVIDER_GAP_FLAGS = {
    "fundamental_provider_missing",
    "fundamental_fetch_not_implemented",
    "fundamental_provider_not_configured",
}


@dataclass
class FallbackFundamentalState:
    risk_flags: list[str]
    summary: str
    strengths: list[str]
    evidence: list[str]
    inference: list[str]
    uncertainty: list[str]
    growth_quality: AnalysisSignal = "neutral"
    profitability_quality: AnalysisSignal = "neutral"
    cash_flow_quality: AnalysisSignal = "neutral"
    balance_sheet_quality: AnalysisSignal = "neutral"
    fx_risk: FxRisk = "unknown"
    business_quality: AnalysisSignal = "neutral"
    macro_fit: AnalysisSignal = "neutral"
    forward_outlook: AnalysisSignal = "neutral"
    reinvestment_quality: AnalysisSignal = "neutral"


def dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


def score_quality(value: float | None, *, low_is_bad: bool = True) -> AnalysisSignal:
    if value is None:
        return "neutral"
    if low_is_bad:
        if value >= 0.7:
            return "supportive"
        if value <= 0.35:
            return "cautious"
        return "neutral"
    if value >= 0.85:
        return "avoid"
    if value >= 0.55:
        return "cautious"
    if value <= 0.25:
        return "supportive"
    return "neutral"


def growth_quality(value: float | None) -> AnalysisSignal:
    if value is None:
        return "neutral"
    if value >= 0.1:
        return "supportive"
    if value <= -0.05:
        return "cautious"
    return "neutral"


def fx_risk(features: FundamentalFeatureSet, macro: MacroContext | None) -> FxRisk:
    if macro is not None and macro.fx_risk != "unknown":
        return macro.fx_risk
    if not features.fx_exposure:
        return "unknown"
    normalized_fx_exposure = features.fx_exposure.lower()
    if normalized_fx_exposure in {"low", "medium", "high"}:
        return cast(FxRisk, normalized_fx_exposure)
    return "unknown"


def macro_fit(macro: MacroContext | None) -> AnalysisSignal:
    if macro is None:
        return "neutral"
    if macro.fx_risk == "high" or macro.rates_bias == "headwind":
        return "cautious"
    if macro.fx_risk == "low" and macro.rates_bias in {"tailwind", "neutral"}:
        return "supportive"
    return "neutral"


def business_quality(
    profitability_quality: AnalysisSignal,
    cash_flow_quality: AnalysisSignal,
    reinvestment_quality: AnalysisSignal,
) -> AnalysisSignal:
    if "avoid" in {
        profitability_quality,
        cash_flow_quality,
        reinvestment_quality,
    }:
        return "avoid"
    if "cautious" in {
        profitability_quality,
        cash_flow_quality,
        reinvestment_quality,
    }:
        return "cautious"
    if {profitability_quality, cash_flow_quality}.issubset({"supportive", "neutral"}):
        if "supportive" in {
            profitability_quality,
            cash_flow_quality,
            reinvestment_quality,
        }:
            return "supportive"
    return "neutral"


def forward_outlook(
    growth_quality: AnalysisSignal,
    business_quality: AnalysisSignal,
    macro_fit: AnalysisSignal,
) -> AnalysisSignal:
    if "avoid" in {growth_quality, business_quality, macro_fit}:
        return "avoid"
    if "cautious" in {growth_quality, business_quality, macro_fit}:
        return "cautious"
    if growth_quality == "supportive" and business_quality == "supportive":
        return "supportive"
    return "neutral"


def overall_bias(
    signals: Sequence[AnalysisSignal],
    *,
    has_provider_gap: bool,
) -> AnalysisSignal:
    if "avoid" in signals:
        return "avoid"
    if "cautious" in signals:
        return "cautious"
    if has_provider_gap:
        return "neutral"
    if signals.count("supportive") >= 4:
        return "supportive"
    return "neutral"


def metric_evidence(features: FundamentalFeatureSet) -> list[str]:
    evidence: list[str] = []
    metric_map = {
        "revenue_growth": features.revenue_growth,
        "profitability_stability": features.profitability_stability,
        "cash_flow_alignment": features.cash_flow_alignment,
        "debt_risk": features.debt_risk,
        "reinvestment_potential": features.reinvestment_potential,
    }
    for label, value in metric_map.items():
        if value is not None:
            evidence.append(f"{label}={value}")
    if features.data_sources:
        evidence.append(f"sources={','.join(features.data_sources)}")
    if features.summary:
        evidence.append(features.summary)
    return evidence


def fallback_risk_flags(
    features: FundamentalFeatureSet,
    balance_sheet_quality: AnalysisSignal,
    fx_risk: FxRisk,
) -> list[str]:
    risk_flags = ["fundamental_evidence_neutral", *features.quality_flags]
    if balance_sheet_quality in {"cautious", "avoid"}:
        risk_flags.append("high_debt_risk")
    if fx_risk in {"medium", "high"}:
        risk_flags.append(f"{fx_risk}_fx_risk")
    return risk_flags


def fallback_strengths(
    growth_quality: AnalysisSignal,
    profitability_quality: AnalysisSignal,
    cash_flow_quality: AnalysisSignal,
) -> list[str]:
    quality_labels = [
        (growth_quality, "growth_evidence_supportive"),
        (profitability_quality, "profitability_evidence_supportive"),
        (cash_flow_quality, "cash_flow_evidence_supportive"),
    ]
    return [label for quality, label in quality_labels if quality == "supportive"]


def has_provider_gap(context: AgentContext | None, risk_flags: Sequence[str]) -> bool:
    if context is None or context.decision_features is None:
        return True
    return any(flag in PROVIDER_GAP_FLAGS for flag in risk_flags)


def fallback_fundamental(
    context: AgentContext | None,
    *,
    fallback_reason: str = LLM_FALLBACK_REASON,
) -> FundamentalAssessment:
    state = default_fallback_fundamental_state()
    if context is not None and context.decision_features is not None:
        apply_fundamental_features(state, context)
    provider_gap = has_provider_gap(context, state.risk_flags)
    signals: list[AnalysisSignal] = [
        state.growth_quality,
        state.profitability_quality,
        state.cash_flow_quality,
        state.balance_sheet_quality,
        state.business_quality,
        state.macro_fit,
        state.forward_outlook,
    ]
    bias = overall_bias(signals, has_provider_gap=provider_gap)
    red_flags = dedupe(state.risk_flags)
    return FundamentalAssessment(
        growth_quality=state.growth_quality,
        profitability_quality=state.profitability_quality,
        cash_flow_quality=state.cash_flow_quality,
        balance_sheet_quality=state.balance_sheet_quality,
        fx_risk=state.fx_risk,
        business_quality=state.business_quality,
        macro_fit=state.macro_fit,
        forward_outlook=state.forward_outlook,
        red_flags=red_flags,
        strengths=dedupe(state.strengths),
        evidence_vs_inference=EvidenceInferenceBreakdown(
            evidence=dedupe(state.evidence),
            inference=dedupe(state.inference),
            uncertainty=dedupe(state.uncertainty),
        ),
        overall_bias=bias,
        revenue_growth_quality=state.growth_quality,
        debt_quality=state.balance_sheet_quality,
        fx_exposure_risk=state.fx_risk,
        reinvestment_quality=state.reinvestment_quality,
        overall_signal=bias,
        confidence=0.0 if provider_gap else 0.35,
        summary=state.summary,
        risk_flags=red_flags,
        source="fallback",
        fallback_reason=fallback_reason,
    )


def default_fallback_fundamental_state() -> FallbackFundamentalState:
    return FallbackFundamentalState(
        risk_flags=["fundamental_evidence_neutral"],
        summary="No structured fundamental provider data is available yet.",
        strengths=[],
        evidence=[],
        inference=[],
        uncertainty=["Provider-backed fundamental evidence is unavailable."],
    )


def apply_fundamental_features(
    state: FallbackFundamentalState, context: AgentContext
) -> None:
    if context.decision_features is None:
        return
    features = context.decision_features.fundamental
    macro = context.decision_features.macro
    state.summary = features.summary or state.summary
    state.evidence.extend(metric_evidence(features))
    if features.quality_flags:
        state.uncertainty.extend(features.quality_flags)
    state.growth_quality = growth_quality(features.revenue_growth)
    state.profitability_quality = score_quality(features.profitability_stability)
    state.cash_flow_quality = score_quality(features.cash_flow_alignment)
    state.balance_sheet_quality = score_quality(features.debt_risk, low_is_bad=False)
    state.reinvestment_quality = score_quality(features.reinvestment_potential)
    state.fx_risk = fx_risk(features, macro)
    state.macro_fit = macro_fit(macro)
    state.business_quality = business_quality(
        state.profitability_quality,
        state.cash_flow_quality,
        state.reinvestment_quality,
    )
    state.forward_outlook = forward_outlook(
        state.growth_quality,
        state.business_quality,
        state.macro_fit,
    )
    state.risk_flags = fallback_risk_flags(
        features,
        state.balance_sheet_quality,
        state.fx_risk,
    )
    state.strengths.extend(
        fallback_strengths(
            state.growth_quality,
            state.profitability_quality,
            state.cash_flow_quality,
        )
    )
    state.inference.append(
        "Fallback assessment used only structured feature metrics and source quality flags."
    )


def has_structured_fundamental_evidence(context: AgentContext | None) -> bool:
    if context is None or context.decision_features is None:
        return False
    flags = set(context.decision_features.fundamental.quality_flags)
    return not bool(flags.intersection(PROVIDER_GAP_FLAGS))
