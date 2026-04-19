from agentic_trader.agents.constants import LLM_FALLBACK_REASON
from agentic_trader.agents.context import render_agent_context
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import AgentContext, MacroAssessment, MarketSnapshot


MACRO_PROVIDER_UNAVAILABLE_REASON = "Structured macro/news provider data is unavailable."


def _fallback_macro(
    context: AgentContext | None,
    *,
    fallback_reason: str = LLM_FALLBACK_REASON,
) -> MacroAssessment:
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
        fallback_reason=fallback_reason,
    )


def _has_structured_macro_evidence(context: AgentContext | None) -> bool:
    """Return whether the context has provider-backed macro or news evidence."""
    if context is None or context.decision_features is None:
        return False
    macro = context.decision_features.macro
    has_news = bool(macro.news_signals)
    non_evidence_sources = {
        "local_macro_scaffold",
        "finnhub_configured",
        "fmp_configured",
        "polygon_configured",
        "massive_configured",
        "news_disabled",
        "news_yfinance",
        "sec_future_source",
        "sec_10k_10q_8k_future_source",
        "earnings_transcripts_future_source",
        "macro_indicators_future_source",
        "kap_future_source",
        "company_disclosures_future_source",
        "cbrt_future_source",
        "turkey_macro_data_future_source",
        "fx_rates_future_source",
        "rates_inflation_pending",
        "turkey_inflation_fx_pending",
    }
    has_provider = any(
        source not in non_evidence_sources for source in macro.data_sources
    )
    has_scores = macro.sector_risk_score is not None or macro.political_risk_score is not None
    return has_news or has_provider or has_scores


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
    if not _has_structured_macro_evidence(context):
        return _fallback_macro(
            context,
            fallback_reason=MACRO_PROVIDER_UNAVAILABLE_REASON,
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
