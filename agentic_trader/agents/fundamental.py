from agentic_trader.agents.constants import LLM_FALLBACK_REASON
from agentic_trader.agents.context import render_agent_context
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import (
    AgentContext,
    FundamentalAssessment,
    MarketSnapshot,
)


def _fallback_fundamental(context: AgentContext | None) -> FundamentalAssessment:
    risk_flags: list[str] = ["fundamental_evidence_neutral"]
    summary = "No structured fundamental provider data is available yet."
    if context is not None and context.decision_features is not None:
        features = context.decision_features.fundamental
        risk_flags.extend(features.quality_flags)
        summary = features.summary or summary
    return FundamentalAssessment(
        summary=summary,
        risk_flags=risk_flags,
        source="fallback",
        fallback_reason=LLM_FALLBACK_REASON,
    )


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
        "Do not invent financial statements, filings, transcripts, or news."
    )
    routed_llm = llm.for_role("fundamental")
    user_prompt = (
        render_agent_context(
            context,
            task=(
                "Assess revenue growth quality, profitability stability, cash-flow "
                "alignment, debt quality, FX exposure, reinvestment quality, and "
                "overall fundamental signal. Return only the structured schema."
            ),
        )
        if context is not None
        else f"Symbol: {snapshot.symbol}\nSnapshot:\n{snapshot.model_dump_json(indent=2)}"
    )
    try:
        return routed_llm.complete_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=FundamentalAssessment,
        )
    except Exception:
        if not allow_fallback:
            raise
        return _fallback_fundamental(context)
