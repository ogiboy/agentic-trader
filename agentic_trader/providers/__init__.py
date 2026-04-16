"""Provider boundaries and canonical data aggregation for external market context."""

from agentic_trader.providers.aggregation import (
    ProviderSet,
    build_canonical_analysis_snapshot,
    canonical_news_from_signals,
    default_provider_set,
)
from agentic_trader.providers.interfaces import (
    DisclosureProvider,
    FundamentalDataProvider,
    MacroDataProvider,
    MarketDataProvider,
    MarketDataResult,
    NewsProvider,
)

__all__ = [
    "DisclosureProvider",
    "FundamentalDataProvider",
    "MacroDataProvider",
    "MarketDataProvider",
    "MarketDataResult",
    "NewsProvider",
    "ProviderSet",
    "build_canonical_analysis_snapshot",
    "canonical_news_from_signals",
    "default_provider_set",
]
