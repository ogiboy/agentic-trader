from agentic_trader.agents.constants import LLM_FALLBACK_REASON
from agentic_trader.agents.context import render_agent_context
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import AgentContext, MacroAssessment, MarketSnapshot


def _fallback_macro(context: AgentContext | None) -> MacroAssessment:
    risk_flags: list[str] = ["macro_evidence_neutral"]
    summary = "No structured macro provider data is available yet."
    fx_risk = "unknown"
    if context is not None and context.decision_features is not None:
        macro = context.decision_features.macro
        fx_risk = macro.fx_risk
        summary = macro.summary or summary
        if not macro.news_signals:
            risk_flags.append("no_structured_news_signals")
        if macro.region == "TR":
            risk_flags.append("turkey_macro_ingestion_pending")
    return MacroAssessment(
        fx_risk=fx_risk,
        summary=summary,
        risk_flags=risk_flags,
        source="fallback",
        fallback_reason=LLM_FALLBACK_REASON,
    )


def assess_macro_context(
    llm: LocalLLM,
    snapshot: MarketSnapshot,
    *,
    allow_fallback: bool,
    context: AgentContext | None = None,
) -> MacroAssessment:
    """Ask the routed macro/news analyst for a structured risk assessment."""
    system_prompt = (
        "You are the macro and news analyst for a paper trading system. "
        "Use only structured macro context and classified news signals. "
        "Do not invent political, economic, or company-specific facts."
    )
    routed_llm = llm.for_role("macro")
    user_prompt = (
        render_agent_context(
            context,
            task=(
                "Assess macro signal, sector risk, news risk, FX risk, and "
                "risk flags from the structured context. Return only the schema."
            ),
        )
        if context is not None
        else f"Symbol: {snapshot.symbol}\nSnapshot:\n{snapshot.model_dump_json(indent=2)}"
    )
    try:
        return routed_llm.complete_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=MacroAssessment,
        )
    except Exception:
        if not allow_fallback:
            raise
        return _fallback_macro(context)
