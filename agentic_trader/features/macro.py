from datetime import UTC, datetime

from agentic_trader.config import Settings
from agentic_trader.schemas import (
    MacroContext,
    NewsClassification,
    NewsSignal,
    StructuredNewsSignal,
    SymbolIdentity,
)

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
    if settings.polygon_api_key:
        sources.append("polygon_configured")
    if settings.massive_api_key:
        sources.append("massive_configured")
    if region == "TR":
        sources.extend(["kap_future_source", "cbrt_future_source"])
    else:
        sources.extend(["sec_future_source", "macro_indicators_future_source"])
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


def get_macro_context(
    symbol_identity: SymbolIdentity,
    *,
    settings: Settings,
    news_items: list[NewsSignal] | None = None,
) -> MacroContext:
    """Build structured macro/news context from local settings and optional headlines."""
    news_signals = [
        classify_news_signal(item, symbol_identity=symbol_identity)
        for item in (news_items or [])
    ]
    sources = _configured_macro_sources(settings, symbol_identity.region)
    if not news_signals and settings.news_mode == "off":
        sources.append("news_disabled")

    fx_risk = "medium" if symbol_identity.currency not in {"USD", "TRY"} else "unknown"
    if symbol_identity.region == "TR":
        fx_risk = "high" if symbol_identity.currency != "TRY" else "medium"

    return MacroContext(
        symbol=symbol_identity.symbol,
        as_of=datetime.now(UTC).isoformat(),
        region=symbol_identity.region,
        currency=symbol_identity.currency,
        fx_risk=fx_risk,
        news_signals=news_signals,
        data_sources=sources,
        summary=(
            "Macro/news context is structured and ready for provider enrichment. "
            f"{len(news_signals)} headline(s) were classified for this cycle."
        ),
    )
