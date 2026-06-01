"""Providers for the optional research sidecar.

Providers expose source readiness and missing-data truth. Real network-backed
providers must stay opt-in, source-attributed, and free of fabricated events.
"""

from agentic_trader.config import Settings
from agentic_trader.researchd.camofox_provider import CamofoxBrowserResearchProvider
from agentic_trader.researchd.firecrawl_provider import FirecrawlNewsResearchProvider
from agentic_trader.researchd.provider_core import (
    CamofoxServiceStatusBuilder,
    CommandRunner,
    FirecrawlSdkSearcher,
    HealthFetcher,
    JsonFetcher,
    ResearchEvidenceProvider,
    ResearchProviderOutput,
    ScaffoldResearchProvider,
    missing_attribution,
    provider_health_from_output,
    source_attributions_from_output,
)
from agentic_trader.researchd.sec_edgar_provider import SecEdgarSubmissionsProvider


def default_research_providers(settings: Settings) -> list[ResearchEvidenceProvider]:
    """Build the local-first ordered ladder of research sidecar providers."""
    social_configured = bool(settings.research_symbols)
    return [
        SecEdgarSubmissionsProvider(settings=settings),
        ScaffoldResearchProvider(
            provider_id="kap_research",
            name="KAP Research",
            provider_type="disclosure",
            role="primary",
            priority=20,
            notes=["turkey_public_disclosure_platform"],
        ),
        ScaffoldResearchProvider(
            provider_id="macro_research",
            name="Macro Research",
            provider_type="macro",
            role="primary",
            priority=30,
            notes=["fred_cbtr_evds_gdelt_future_sources"],
        ),
        FirecrawlNewsResearchProvider(settings=settings),
        CamofoxBrowserResearchProvider(settings=settings),
        ScaffoldResearchProvider(
            provider_id="news_event_research",
            name="News And Event Research",
            provider_type="news",
            role="fallback",
            priority=40,
            notes=["news_event_timeline_source"],
        ),
        ScaffoldResearchProvider(
            provider_id="social_watchlist_research",
            name="Social Watchlist Research",
            provider_type="social",
            role="fallback",
            priority=50,
            enabled=social_configured,
            requires_network=social_configured,
            notes=[
                "watchlist_only",
                "configured" if social_configured else "watchlist_missing",
            ],
        ),
    ]


__all__ = [
    "CamofoxBrowserResearchProvider",
    "CamofoxServiceStatusBuilder",
    "CommandRunner",
    "FirecrawlNewsResearchProvider",
    "FirecrawlSdkSearcher",
    "HealthFetcher",
    "JsonFetcher",
    "ResearchEvidenceProvider",
    "ResearchProviderOutput",
    "ScaffoldResearchProvider",
    "SecEdgarSubmissionsProvider",
    "default_research_providers",
    "missing_attribution",
    "provider_health_from_output",
    "source_attributions_from_output",
]
