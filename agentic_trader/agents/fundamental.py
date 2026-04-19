from collections.abc import Sequence
from typing import Literal, cast

from agentic_trader.agents.constants import LLM_FALLBACK_REASON
from agentic_trader.agents.context import render_agent_context
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import (
    AgentContext,
    AnalysisSignal,
    EvidenceInferenceBreakdown,
    FundamentalFeatureSet,
    FundamentalAssessment,
    MacroContext,
    MarketSnapshot,
)


FxRisk = Literal["low", "medium", "high", "unknown"]
FUNDAMENTAL_PROVIDER_UNAVAILABLE_REASON = (
    "Structured fundamental provider data is unavailable."
)


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


def _score_quality(value: float | None, *, low_is_bad: bool = True) -> AnalysisSignal:
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


def _growth_quality(value: float | None) -> AnalysisSignal:
    if value is None:
        return "neutral"
    if value >= 0.1:
        return "supportive"
    if value <= -0.05:
        return "cautious"
    return "neutral"


def _fx_risk(features: FundamentalFeatureSet, macro: MacroContext | None) -> FxRisk:
    if macro is not None and macro.fx_risk != "unknown":
        return macro.fx_risk
    normalized_fx_exposure = features.fx_exposure.lower()
    if normalized_fx_exposure in {"low", "medium", "high"}:
        return cast(FxRisk, normalized_fx_exposure)
    return "unknown"


def _macro_fit(macro: MacroContext | None) -> AnalysisSignal:
    if macro is None:
        return "neutral"
    if macro.fx_risk == "high" or macro.rates_bias == "headwind":
        return "cautious"
    if macro.fx_risk == "low" and macro.rates_bias in {"tailwind", "neutral"}:
        return "supportive"
    return "neutral"


def _business_quality(
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


def _forward_outlook(
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


def _overall_bias(
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


def _validate_llm_evidence_contract(
    assessment: FundamentalAssessment,
) -> FundamentalAssessment:
    if assessment.source != "llm":
        return assessment
    evidence = assessment.evidence_vs_inference
    if not (evidence.evidence or evidence.inference or evidence.uncertainty):
        raise ValueError(
            "LLM fundamental assessment must include evidence, inference, or uncertainty."
        )
    if assessment.overall_bias != "neutral" and not evidence.evidence:
        raise ValueError(
            "Non-neutral LLM fundamental assessment requires direct evidence."
        )
    return assessment


def _metric_evidence(features: FundamentalFeatureSet) -> list[str]:
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


def _fallback_fundamental(
    context: AgentContext | None,
    *,
    fallback_reason: str = LLM_FALLBACK_REASON,
) -> FundamentalAssessment:
    risk_flags: list[str] = ["fundamental_evidence_neutral"]
    summary = "No structured fundamental provider data is available yet."
    strengths: list[str] = []
    evidence: list[str] = []
    inference: list[str] = []
    uncertainty: list[str] = ["Provider-backed fundamental evidence is unavailable."]
    growth_quality: AnalysisSignal = "neutral"
    profitability_quality: AnalysisSignal = "neutral"
    cash_flow_quality: AnalysisSignal = "neutral"
    balance_sheet_quality: AnalysisSignal = "neutral"
    fx_risk: FxRisk = "unknown"
    business_quality: AnalysisSignal = "neutral"
    macro_fit: AnalysisSignal = "neutral"
    forward_outlook: AnalysisSignal = "neutral"
    if context is not None and context.decision_features is not None:
        features = context.decision_features.fundamental
        macro = context.decision_features.macro
        risk_flags.extend(features.quality_flags)
        summary = features.summary or summary
        evidence.extend(_metric_evidence(features))
        if features.quality_flags:
            uncertainty.extend(features.quality_flags)
        growth_quality = _growth_quality(features.revenue_growth)
        profitability_quality = _score_quality(features.profitability_stability)
        cash_flow_quality = _score_quality(features.cash_flow_alignment)
        balance_sheet_quality = _score_quality(features.debt_risk, low_is_bad=False)
        reinvestment_quality = _score_quality(features.reinvestment_potential)
        fx_risk = _fx_risk(features, macro)
        macro_fit = _macro_fit(macro)
        business_quality = _business_quality(
            profitability_quality,
            cash_flow_quality,
            reinvestment_quality,
        )
        forward_outlook = _forward_outlook(
            growth_quality,
            business_quality,
            macro_fit,
        )
        if balance_sheet_quality in {"cautious", "avoid"}:
            risk_flags.append("high_debt_risk")
        if fx_risk in {"medium", "high"}:
            risk_flags.append(f"{fx_risk}_fx_risk")
        if growth_quality == "supportive":
            strengths.append("growth_evidence_supportive")
        if profitability_quality == "supportive":
            strengths.append("profitability_evidence_supportive")
        if cash_flow_quality == "supportive":
            strengths.append("cash_flow_evidence_supportive")
        inference.append(
            "Fallback assessment used only structured feature metrics and source quality flags."
        )
    provider_gap = any(
        flag
        in {
            "fundamental_provider_missing",
            "fundamental_fetch_not_implemented",
            "fundamental_provider_not_configured",
        }
        for flag in risk_flags
    )
    signals: list[AnalysisSignal] = [
        growth_quality,
        profitability_quality,
        cash_flow_quality,
        balance_sheet_quality,
        business_quality,
        macro_fit,
        forward_outlook,
    ]
    overall_bias = _overall_bias(signals, has_provider_gap=provider_gap)
    red_flags = _dedupe(risk_flags)
    return FundamentalAssessment(
        growth_quality=growth_quality,
        profitability_quality=profitability_quality,
        cash_flow_quality=cash_flow_quality,
        balance_sheet_quality=balance_sheet_quality,
        fx_risk=fx_risk,
        business_quality=business_quality,
        macro_fit=macro_fit,
        forward_outlook=forward_outlook,
        red_flags=red_flags,
        strengths=_dedupe(strengths),
        evidence_vs_inference=EvidenceInferenceBreakdown(
            evidence=_dedupe(evidence),
            inference=_dedupe(inference),
            uncertainty=_dedupe(uncertainty),
        ),
        overall_bias=overall_bias,
        revenue_growth_quality=growth_quality,
        debt_quality=balance_sheet_quality,
        fx_exposure_risk=fx_risk,
        reinvestment_quality=_score_quality(
            context.decision_features.fundamental.reinvestment_potential
            if context is not None and context.decision_features is not None
            else None
        ),
        overall_signal=overall_bias,
        confidence=0.0 if provider_gap else 0.35,
        summary=summary,
        risk_flags=red_flags,
        source="fallback",
        fallback_reason=fallback_reason,
    )


def _has_structured_fundamental_evidence(context: AgentContext | None) -> bool:
    """Return whether the context contains real provider-backed fundamentals."""
    if context is None or context.decision_features is None:
        return False
    flags = set(context.decision_features.fundamental.quality_flags)
    missing_flags = {
        "fundamental_provider_missing",
        "fundamental_fetch_not_implemented",
        "fundamental_provider_not_configured",
    }
    return not bool(flags.intersection(missing_flags))


def assess_fundamentals(
    llm: LocalLLM,
    snapshot: MarketSnapshot,
    *,
    allow_fallback: bool,
    context: AgentContext | None = None,
) -> FundamentalAssessment:
    """Ask the routed fundamental analyst for a structured quality assessment."""
    system_prompt = (
        "You are the fundamental analyst for a paper trading system. "
        "Use only the structured feature bundle and explicit tool outputs. "
        "Do not invent financial statements, filings, transcripts, or news. "
        "Separate direct evidence, inference, and uncertainty. "
        "When data is incomplete, stay neutral or cautious instead of filling gaps."
    )
    if not _has_structured_fundamental_evidence(context):
        return _fallback_fundamental(
            context,
            fallback_reason=FUNDAMENTAL_PROVIDER_UNAVAILABLE_REASON,
        )
    routed_llm = llm.for_role("fundamental")
    user_prompt = (
        render_agent_context(
            context,
            task=(
                "Assess growth, profitability, cash flow, balance sheet quality, "
                "FX risk, business quality, macro fit, and forward outlook. "
                "Return red flags, strengths, evidence_vs_inference, and overall_bias. "
                "Use no fake knowledge and mark uncertainty explicitly."
            ),
        )
        if context is not None
        else f"Symbol: {snapshot.symbol}\nSnapshot:\n{snapshot.model_dump_json(indent=2)}"
    )
    try:
        assessment = routed_llm.complete_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=FundamentalAssessment,
        )
        return _validate_llm_evidence_contract(assessment)
    except Exception:
        if not allow_fallback:
            raise
        return _fallback_fundamental(context)
