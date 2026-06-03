from agentic_trader.agents.context import render_agent_context
from agentic_trader.agents.fundamental_fallback import (
    FUNDAMENTAL_PROVIDER_UNAVAILABLE_REASON,
)
from agentic_trader.agents.fundamental_fallback import (
    PROVIDER_GAP_FLAGS as PROVIDER_GAP_FLAGS,
)
from agentic_trader.agents.fundamental_fallback import FxRisk as FxRisk
from agentic_trader.agents.fundamental_fallback import (
    business_quality as _business_quality,
)
from agentic_trader.agents.fundamental_fallback import dedupe as _dedupe
from agentic_trader.agents.fundamental_fallback import (
    fallback_fundamental as _fallback_fundamental,
)
from agentic_trader.agents.fundamental_fallback import (
    forward_outlook as _forward_outlook,
)
from agentic_trader.agents.fundamental_fallback import fx_risk as _fx_risk
from agentic_trader.agents.fundamental_fallback import growth_quality as _growth_quality
from agentic_trader.agents.fundamental_fallback import (
    has_structured_fundamental_evidence as _has_structured_fundamental_evidence,
)
from agentic_trader.agents.fundamental_fallback import macro_fit as _macro_fit
from agentic_trader.agents.fundamental_fallback import (
    metric_evidence as _metric_evidence,
)
from agentic_trader.agents.fundamental_fallback import overall_bias as _overall_bias
from agentic_trader.agents.fundamental_fallback import score_quality as _score_quality
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import AgentContext, FundamentalAssessment, MarketSnapshot


def _validate_llm_evidence_contract(
    assessment: FundamentalAssessment,
) -> None:
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


def assess_fundamentals(
    llm: LocalLLM,
    snapshot: MarketSnapshot,
    *,
    allow_fallback: bool,
    context: AgentContext | None = None,
) -> FundamentalAssessment:
    """
    Build a structured FundamentalAssessment through the role-routed LLM.

    Missing provider-backed evidence returns a deterministic fallback before
    touching the model. LLM failures fall back only when `allow_fallback` is set.
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


dedupe = _dedupe
score_quality = _score_quality
growth_quality = _growth_quality
fx_risk = _fx_risk
macro_fit = _macro_fit
business_quality = _business_quality
forward_outlook = _forward_outlook
overall_bias = _overall_bias
validate_llm_evidence_contract = _validate_llm_evidence_contract
metric_evidence = _metric_evidence
fallback_fundamental = _fallback_fundamental
has_structured_fundamental_evidence = _has_structured_fundamental_evidence
