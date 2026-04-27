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
PROVIDER_GAP_FLAGS = {
    "fundamental_provider_missing",
    "fundamental_fetch_not_implemented",
    "fundamental_provider_not_configured",
}


def _dedupe(items: list[str]) -> list[str]:
    """
    Return a list of unique, truthy strings from the input while preserving their first-seen order.

    Parameters:
        items (list[str]): Sequence of strings that may contain duplicates or falsy/empty values.

    Returns:
        list[str]: Deduplicated list containing the first occurrence of each truthy string from `items`, in original order.
    """
    return list(dict.fromkeys(item for item in items if item))


def _score_quality(value: float | None, *, low_is_bad: bool = True) -> AnalysisSignal:
    """
    Map a numeric score to an analysis signal representing quality.

    When `low_is_bad` is True, higher numeric values indicate better quality; when False, lower values indicate better quality and very high values may indicate `"avoid"`.

    Parameters:
        low_is_bad (bool): If True, treat lower scores as worse; if False, treat higher scores as worse.

    Returns:
        AnalysisSignal: One of `"supportive"`, `"cautious"`, `"neutral"`, or `"avoid"`. Returns `"neutral"` if `value` is `None`.
    """
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
    """
    Classify a growth rate into an analysis quality signal.

    Parameters:
        value (float | None): Growth rate as a decimal (e.g., 0.05 for 5%), or `None` if unavailable.

    Returns:
        str: `'supportive'` if value is greater than or equal to 0.1, `'cautious'` if value is less than or equal to -0.05, `'neutral'` otherwise.
    """
    if value is None:
        return "neutral"
    if value >= 0.1:
        return "supportive"
    if value <= -0.05:
        return "cautious"
    return "neutral"


def _fx_risk(features: FundamentalFeatureSet, macro: MacroContext | None) -> FxRisk:
    """
    Determine the FX risk label for an instrument using macro context when available, otherwise deriving it from feature-provided exposure.

    Parameters:
        features (FundamentalFeatureSet): Structured fundamental features; `features.fx_exposure` may contain a textual exposure label.
        macro (MacroContext | None): Optional macro context whose `fx_risk` overrides feature-derived exposure when it is not `"unknown"`.

    Returns:
        FxRisk: One of `"low"`, `"medium"`, `"high"`, or `"unknown"`. If `macro.fx_risk` is set (not `"unknown"`), that value is returned. If `features.fx_exposure` is empty or not one of `"low"`, `"medium"`, or `"high"`, returns `"unknown"`.
    """
    if macro is not None and macro.fx_risk != "unknown":
        return macro.fx_risk
    if not features.fx_exposure:
        return "unknown"
    normalized_fx_exposure = features.fx_exposure.lower()
    if normalized_fx_exposure in {"low", "medium", "high"}:
        return cast(FxRisk, normalized_fx_exposure)
    return "unknown"


def _macro_fit(macro: MacroContext | None) -> AnalysisSignal:
    """
    Determine how macroeconomic conditions influence the assessment's macro fit signal.

    Parameters:
        macro (MacroContext | None): Macro context containing `fx_risk` and `rates_bias`; pass `None` when macro data is unavailable.

    Returns:
        AnalysisSignal: `"supportive"` if macro conditions are favorable, `"cautious"` if they are adverse, `"neutral"` otherwise.
    """
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
    """
    Determine the aggregate business-quality signal from profitability, cash-flow, and reinvestment signals.

    Parameters:
        profitability_quality (AnalysisSignal): Quality signal for profitability.
        cash_flow_quality (AnalysisSignal): Quality signal for cash flow alignment.
        reinvestment_quality (AnalysisSignal): Quality signal for reinvestment potential.

    Returns:
        AnalysisSignal: One of `"avoid"`, `"cautious"`, `"supportive"`, or `"neutral"`.
        - `"avoid"` if any input is `"avoid"`.
        - `"cautious"` if no inputs are `"avoid"` and any input is `"cautious"`.
        - `"supportive"` if profitability and cash flow are both in `{"supportive", "neutral"}` and at least one of profitability, cash flow, or reinvestment is `"supportive"`.
        - `"neutral"` otherwise.
    """
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
    """
    Determine the forward outlook signal from growth, business quality, and macro fit.

    Returns:
        AnalysisSignal: `"avoid"` if any input is `"avoid"`, `"cautious"` if any input is `"cautious"` (and none are `"avoid"`), `"supportive"` if both `growth_quality` and `business_quality` are `"supportive"`, and `"neutral"` otherwise.
    """
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
    """
    Compute an aggregated overall bias from multiple analysis signals and a provider-gap indicator.

    Evaluates precedence: any `"avoid"` yields `"avoid"`, else any `"cautious"` yields `"cautious"`. If neither is present and `has_provider_gap` is True, returns `"neutral"`. If at least four signals are `"supportive"`, returns `"supportive"`. Otherwise returns `"neutral"`.

    Parameters:
        signals (Sequence[AnalysisSignal]): Sequence of individual analysis signals to aggregate.
        has_provider_gap (bool): When True and no `"avoid"`/`"cautious"` signals are present, forces a `"neutral"` bias to reflect missing provider-backed evidence.

    Returns:
        AnalysisSignal: One of `"avoid"`, `"cautious"`, `"supportive"`, or `"neutral"` representing the aggregated bias.
    """
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
) -> None:
    """
    Validate that an LLM-produced FundamentalAssessment satisfies minimum evidence requirements.

    If the assessment's source is "llm", requires that at least one of `evidence`, `inference`, or `uncertainty` is present in `assessment.evidence_vs_inference`. Additionally, if `assessment.overall_bias` is not "neutral", requires non-empty direct `evidence`.

    Parameters:
        assessment (FundamentalAssessment): The assessment to validate.

    Raises:
        ValueError: If `assessment.source == "llm"` but no evidence/inference/uncertainty are provided, or if the assessment has a non-neutral overall_bias without direct evidence.
    """
    if assessment.source != "llm":
        return
    evidence = assessment.evidence_vs_inference
    if not (evidence.evidence or evidence.inference or evidence.uncertainty):
        raise ValueError(
            "LLM fundamental assessment must include evidence, inference, or uncertainty."
        )
    if assessment.overall_bias != "neutral" and not evidence.evidence:
        raise ValueError(
            "Non-neutral LLM fundamental assessment requires direct evidence."
        )


def _metric_evidence(features: FundamentalFeatureSet) -> list[str]:
    """
    Builds a list of evidence strings from the provided fundamental feature set.

    Parameters:
        features (FundamentalFeatureSet): Feature bundle containing metric fields, optional data_sources, and an optional summary.

    Returns:
        list[str]: Evidence entries in this order:
            - `label=value` for each non-None metric among `revenue_growth`, `profitability_stability`,
              `cash_flow_alignment`, `debt_risk`, and `reinvestment_potential` (in that order).
            - `sources=...` containing comma-joined `data_sources` if present.
            - The `summary` string if present.
    """
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


def _fallback_risk_flags(
    features: FundamentalFeatureSet,
    balance_sheet_quality: AnalysisSignal,
    fx_risk: FxRisk,
) -> list[str]:
    """
    Builds a list of fallback risk-flag identifiers based on feature quality flags, balance-sheet quality, and FX risk.

    Parameters:
        features (FundamentalFeatureSet): Source of base `quality_flags` to include.
        balance_sheet_quality (AnalysisSignal): If `"cautious"` or `"avoid"`, adds `"high_debt_risk"`.
        fx_risk (FxRisk): If `"medium"` or `"high"`, adds `"{fx_risk}_fx_risk"` (e.g., `"high_fx_risk"`).

    Returns:
        list[str]: Deduplicated-semantics list of risk flag strings starting with `"fundamental_evidence_neutral"` followed by `features.quality_flags` and any added debt or FX risk flags.
    """
    risk_flags = ["fundamental_evidence_neutral", *features.quality_flags]
    if balance_sheet_quality in {"cautious", "avoid"}:
        risk_flags.append("high_debt_risk")
    if fx_risk in {"medium", "high"}:
        risk_flags.append(f"{fx_risk}_fx_risk")
    return risk_flags


def _fallback_strengths(
    growth_quality: AnalysisSignal,
    profitability_quality: AnalysisSignal,
    cash_flow_quality: AnalysisSignal,
) -> list[str]:
    """
    Produce strength labels corresponding to quality signals that are "supportive".

    Parameters:
        growth_quality (AnalysisSignal): Quality signal for revenue/growth.
        profitability_quality (AnalysisSignal): Quality signal for profitability.
        cash_flow_quality (AnalysisSignal): Quality signal for cash flow.

    Returns:
        list[str]: A list containing any of "growth_evidence_supportive",
        "profitability_evidence_supportive", and "cash_flow_evidence_supportive"
        for each input whose quality equals "supportive".
    """
    quality_labels = [
        (growth_quality, "growth_evidence_supportive"),
        (profitability_quality, "profitability_evidence_supportive"),
        (cash_flow_quality, "cash_flow_evidence_supportive"),
    ]
    return [label for quality, label in quality_labels if quality == "supportive"]


def _has_provider_gap(context: AgentContext | None, risk_flags: Sequence[str]) -> bool:
    """
    Determine whether structured fundamental data from providers is missing or flagged as unavailable.

    Parameters:
        context (AgentContext | None): Agent context that may contain `decision_features`; treat `None` as missing.
        risk_flags (Sequence[str]): Sequence of risk/quality flags to check for provider-gap indicators.

    Returns:
        True if `context` is missing or lacks `decision_features`, or if any flag in `risk_flags` appears in `PROVIDER_GAP_FLAGS`; `false` otherwise.
    """
    if context is None or context.decision_features is None:
        return True
    return any(flag in PROVIDER_GAP_FLAGS for flag in risk_flags)


def _fallback_fundamental(
    context: AgentContext | None,
    *,
    fallback_reason: str = LLM_FALLBACK_REASON,
) -> FundamentalAssessment:
    """
    Build a fallback FundamentalAssessment when structured provider-backed fundamentals are unavailable.

    If `context.decision_features` is present, derives quality signals, evidence, risk flags, strengths, FX risk, macro fit, business quality, and forward outlook from those structured features. If structured features are missing, returns a neutral minimal assessment indicating provider-backed data is unavailable. The returned assessment has `source="fallback"`, records `fallback_reason`, and sets `confidence` to 0.0 when a provider-gap flag is present or 0.35 otherwise.

    Parameters:
        context (AgentContext | None): Optional agent context whose `decision_features` (if present) are used to populate fallback signals and evidence.
        fallback_reason (str): Human-readable reason stored on the returned assessment explaining why the fallback was used.

    Returns:
        FundamentalAssessment: A complete fallback assessment populated from available structured features or neutral defaults, including `evidence_vs_inference`, `red_flags`/`risk_flags`, `strengths`, individual quality and risk fields, `overall_bias`/`overall_signal`, `confidence`, `source`, and `fallback_reason`.
    """
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
    reinvestment_quality: AnalysisSignal = "neutral"
    if context is not None and context.decision_features is not None:
        features = context.decision_features.fundamental
        macro = context.decision_features.macro
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
        risk_flags = _fallback_risk_flags(features, balance_sheet_quality, fx_risk)
        strengths.extend(
            _fallback_strengths(
                growth_quality,
                profitability_quality,
                cash_flow_quality,
            )
        )
        inference.append(
            "Fallback assessment used only structured feature metrics and source quality flags."
        )
    provider_gap = _has_provider_gap(context, risk_flags)
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
        reinvestment_quality=reinvestment_quality,
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
    """
    Builds a structured FundamentalAssessment for a market snapshot using the role-routed fundamental LLM or a computed fallback.

    If structured provider evidence is missing a deterministic fallback assessment is returned. If the LLM call or validation fails, a fallback is returned only when allow_fallback is True; otherwise the original exception is propagated.

    Parameters:
        llm (LocalLLM): Role-routed local LLM client used to generate the assessment.
        snapshot (MarketSnapshot): Market snapshot used when no AgentContext is provided.
        allow_fallback (bool): If True, return a computed fallback assessment on LLM or validation errors.
        context (AgentContext | None): Optional agent context containing structured decision_features to ground the assessment.

    Returns:
        FundamentalAssessment: The assembled assessment; `source` is `"llm"` when produced by the model or `"fallback"` when a computed fallback is used.

    Raises:
        Exception: Propagates any exception raised during LLM invocation or validation when allow_fallback is False.
    """
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
        _validate_llm_evidence_contract(assessment)
        return assessment
    except Exception:
        if not allow_fallback:
            raise
        return _fallback_fundamental(context)
