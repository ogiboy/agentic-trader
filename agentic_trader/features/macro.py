from datetime import UTC, datetime
from typing import Literal

from agentic_trader.config import Settings
from agentic_trader.schemas import (
    MacroContext,
    MacroSnapshot,
    NewsEvent,
    NewsClassification,
    NewsSignal,
    StructuredNewsSignal,
    SymbolIdentity,
)

MacroBias = Literal["tailwind", "neutral", "headwind", "unknown"]
MacroFxRisk = Literal["low", "medium", "high", "unknown"]

MACRO_KEYWORDS = {
    "central bank",
    "cbrt",
    "cpi",
    "economy",
    "fed",
    "fx",
    "inflation",
    "interest rate",
    "macro",
    "policy",
    "rates",
    "tcmb",
}
SECTOR_KEYWORDS = {
    "bank",
    "energy",
    "industrial",
    "retail",
    "sector",
    "semiconductor",
    "technology",
    "utilities",
}


def _configured_macro_sources(settings: Settings, region: str) -> list[str]:
    sources: list[str] = []
    if settings.news_mode != "off":
        sources.append(f"news_{settings.news_mode}")
    if settings.finnhub_api_key:
        sources.append("finnhub_configured")
    if settings.fmp_api_key:
        sources.append("fmp_configured")
    if settings.polygon_api_key:
        sources.append("polygon_configured")
    if settings.massive_api_key:
        sources.append("massive_configured")
    if region == "TR":
        sources.extend(
            [
                "kap_future_source",
                "company_disclosures_future_source",
                "cbrt_future_source",
                "turkey_macro_data_future_source",
                "fx_rates_future_source",
            ]
        )
    else:
        sources.extend(
            [
                "sec_10k_10q_8k_future_source",
                "earnings_transcripts_future_source",
                "macro_indicators_future_source",
            ]
        )
    return sources


def classify_news_signal(
    item: NewsSignal,
    *,
    symbol_identity: SymbolIdentity,
) -> StructuredNewsSignal:
    """Classify a raw headline into company, sector, or macro context."""
    text = f"{item.title} {item.publisher}".lower()
    symbol_root = symbol_identity.symbol.split(".")[0].split("-")[0].lower()
    category: NewsClassification = "sector_level"
    relevance_score = 0.45

    if symbol_root and symbol_root in text:
        category = "company_specific"
        relevance_score = 0.8
    elif any(keyword in text for keyword in MACRO_KEYWORDS):
        category = "macro_level"
        relevance_score = 0.65
    elif any(keyword in text for keyword in SECTOR_KEYWORDS):
        category = "sector_level"
        relevance_score = 0.55

    return StructuredNewsSignal(
        symbol=item.symbol or symbol_identity.symbol,
        title=item.title,
        category=category,
        source=item.publisher,
        published_at=item.published_at,
        summary=item.title[:240],
        relevance_score=relevance_score,
    )


def _news_signals_from_events(
    news_events: list[NewsEvent],
) -> list[StructuredNewsSignal]:
    return [
        StructuredNewsSignal(
            symbol=event.symbol,
            title=event.title,
            category=event.category,
            source=event.source,
            published_at=event.published_at,
            summary=event.summary,
            relevance_score=event.relevance_score,
        )
        for event in news_events
    ]


def _build_news_signals(
    symbol_identity: SymbolIdentity,
    news_items: list[NewsSignal] | None,
    news_events: list[NewsEvent] | None,
) -> list[StructuredNewsSignal]:
    if news_events is not None:
        return _news_signals_from_events(news_events)
    return [
        classify_news_signal(item, symbol_identity=symbol_identity)
        for item in (news_items or [])
    ]


def _macro_sources(
    symbol_identity: SymbolIdentity,
    settings: Settings,
    news_signals: list[StructuredNewsSignal],
    macro_snapshot: MacroSnapshot | None,
) -> list[str]:
    if macro_snapshot is not None:
        sources = [
            macro_snapshot.attribution.source_name,
            *macro_snapshot.attribution.notes,
        ]
    else:
        sources = _configured_macro_sources(settings, symbol_identity.region)
    if not news_signals and settings.news_mode == "off":
        sources.append("news_disabled")
    return sources


def _default_fx_risk(symbol_identity: SymbolIdentity) -> MacroFxRisk:
    if symbol_identity.region == "TR":
        if symbol_identity.currency != "TRY":
            return "high"
        return "medium"
    if symbol_identity.currency not in {"USD", "TRY"}:
        return "medium"
    return "unknown"


def _macro_as_of(macro_snapshot: MacroSnapshot | None) -> str | None:
    if macro_snapshot is not None:
        return macro_snapshot.attribution.fetched_at
    return datetime.now(UTC).isoformat()


def _macro_region(
    symbol_identity: SymbolIdentity,
    macro_snapshot: MacroSnapshot | None,
) -> str:
    if macro_snapshot is not None:
        return macro_snapshot.region
    return symbol_identity.region


def _macro_currency(
    symbol_identity: SymbolIdentity,
    macro_snapshot: MacroSnapshot | None,
) -> str:
    if macro_snapshot is not None:
        return macro_snapshot.currency
    return symbol_identity.currency


def _macro_rates_bias(macro_snapshot: MacroSnapshot | None) -> MacroBias:
    if macro_snapshot is not None:
        return macro_snapshot.rates_bias
    return "unknown"


def _macro_inflation_bias(macro_snapshot: MacroSnapshot | None) -> MacroBias:
    if macro_snapshot is not None:
        return macro_snapshot.inflation_bias
    return "unknown"


def _macro_fx_risk(
    symbol_identity: SymbolIdentity,
    macro_snapshot: MacroSnapshot | None,
) -> MacroFxRisk:
    if macro_snapshot is not None:
        return macro_snapshot.fx_risk
    return _default_fx_risk(symbol_identity)


def _macro_sector_risk_score(macro_snapshot: MacroSnapshot | None) -> float | None:
    if macro_snapshot is not None:
        return macro_snapshot.sector_risk_score
    return None


def _macro_political_risk_score(macro_snapshot: MacroSnapshot | None) -> float | None:
    if macro_snapshot is not None:
        return macro_snapshot.political_risk_score
    return None


def _macro_summary(
    news_signals: list[StructuredNewsSignal],
    macro_snapshot: MacroSnapshot | None,
) -> str:
    if macro_snapshot is not None:
        return macro_snapshot.summary
    return (
        "Macro/news context is structured and ready for provider enrichment. "
        f"{len(news_signals)} headline(s) were classified for this cycle."
    )


def get_macro_context(
    symbol_identity: SymbolIdentity,
    *,
    settings: Settings,
    news_items: list[NewsSignal] | None = None,
    news_events: list[NewsEvent] | None = None,
    macro_snapshot: MacroSnapshot | None = None,
) -> MacroContext:
    """Build structured macro/news context from local settings and optional headlines."""
    news_signals = _build_news_signals(symbol_identity, news_items, news_events)
    sources = _macro_sources(symbol_identity, settings, news_signals, macro_snapshot)

    return MacroContext(
        symbol=symbol_identity.symbol,
        as_of=_macro_as_of(macro_snapshot),
        region=_macro_region(symbol_identity, macro_snapshot),
        currency=_macro_currency(symbol_identity, macro_snapshot),
        rates_bias=_macro_rates_bias(macro_snapshot),
        inflation_bias=_macro_inflation_bias(macro_snapshot),
        fx_risk=_macro_fx_risk(symbol_identity, macro_snapshot),
        sector_risk_score=_macro_sector_risk_score(macro_snapshot),
        political_risk_score=_macro_political_risk_score(macro_snapshot),
        news_signals=news_signals,
        data_sources=sources,
        summary=_macro_summary(news_signals, macro_snapshot),
    )
