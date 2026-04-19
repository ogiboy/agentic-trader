"""Canonical multi-source aggregation for agent and operator context."""

from dataclasses import dataclass, field

from agentic_trader.config import Settings
from agentic_trader.features.macro import classify_news_signal
from agentic_trader.features.symbols import resolve_symbol_identity
from agentic_trader.providers.base import (
    market_snapshot_from_runtime_snapshot,
    source_attribution,
    utc_now_iso,
)
from agentic_trader.providers.interfaces import (
    DisclosureProvider,
    FundamentalDataProvider,
    MacroDataProvider,
    MarketDataProvider,
    NewsProvider,
)
from agentic_trader.providers.local import (
    LocalDisclosureProvider,
    LocalFundamentalProvider,
    LocalMacroProvider,
)
from agentic_trader.providers.public_sources import (
    FinnhubFundamentalProvider,
    FmpFundamentalProvider,
    KapDisclosureProvider,
    SecEdgarFundamentalProvider,
)
from agentic_trader.providers.yahoo import YahooMarketDataProvider, YahooNewsProvider
from agentic_trader.schemas import (
    CanonicalAnalysisSnapshot,
    DataSourceAttribution,
    DisclosureEvent,
    FundamentalSnapshot,
    InvestmentPreferences,
    MacroSnapshot,
    MarketSnapshot,
    NewsEvent,
    NewsSignal,
    SymbolIdentity,
)


@dataclass
class ProviderSet:
    """Grouped provider adapters used by the canonical aggregation layer."""

    market: list[MarketDataProvider] = field(default_factory=list)
    fundamental: list[FundamentalDataProvider] = field(default_factory=list)
    news: list[NewsProvider] = field(default_factory=list)
    disclosures: list[DisclosureProvider] = field(default_factory=list)
    macro: list[MacroDataProvider] = field(default_factory=list)


def default_provider_set(settings: Settings) -> ProviderSet:
    """Create the default local-first provider set without mandatory cloud services."""
    return ProviderSet(
        market=[YahooMarketDataProvider(settings)],
        fundamental=[
            SecEdgarFundamentalProvider(settings),
            FinnhubFundamentalProvider(settings),
            FmpFundamentalProvider(settings),
            LocalFundamentalProvider(settings),
        ],
        news=[YahooNewsProvider(settings)],
        disclosures=[
            KapDisclosureProvider(settings),
            LocalDisclosureProvider(settings),
        ],
        macro=[LocalMacroProvider(settings)],
    )


def canonical_news_from_signals(
    news_items: list[NewsSignal],
    *,
    symbol_identity: SymbolIdentity,
    source_name: str = "runtime_news_tool",
) -> list[NewsEvent]:
    """Convert existing lightweight news signals into canonical news events."""
    events: list[NewsEvent] = []
    for item in news_items:
        signal = classify_news_signal(item, symbol_identity=symbol_identity)
        events.append(
            NewsEvent(
                symbol=signal.symbol or symbol_identity.symbol,
                title=signal.title,
                category=signal.category,
                source=signal.source,
                published_at=signal.published_at,
                summary=signal.summary,
                relevance_score=signal.relevance_score,
                url=item.link,
                attribution=source_attribution(
                    source_name=source_name,
                    provider_type="news",
                    source_role="fallback",
                    fetched_at=utc_now_iso(),
                    freshness="unknown",
                    confidence=signal.relevance_score,
                    completeness=0.7,
                    notes=["classified_headline"],
                ),
            )
        )
    return events


def _first_fundamental_snapshot(
    providers: list[FundamentalDataProvider], symbol: SymbolIdentity
) -> tuple[FundamentalSnapshot, list[str], list[DataSourceAttribution]]:
    errors: list[str] = []
    missing_snapshots: list[FundamentalSnapshot] = []
    for provider in providers:
        try:
            snapshot = provider.get_fundamental_data(symbol)
        except Exception as exc:
            errors.append(f"{provider.metadata().provider_id}: {exc}")
            continue
        if snapshot.attribution.source_role != "missing":
            return snapshot, errors, [
                item.attribution for item in missing_snapshots
            ]
        missing_snapshots.append(snapshot)
    if missing_snapshots:
        return (
            missing_snapshots[0],
            errors,
            [item.attribution for item in missing_snapshots[1:]],
        )
    return (
        FundamentalSnapshot(
            symbol_identity=symbol,
            attribution=source_attribution(
                source_name="fundamental_provider_unavailable",
                provider_type="fundamental",
                source_role="missing",
                fetched_at=utc_now_iso(),
                freshness="missing",
                notes=errors,
            ),
            missing_fields=["fundamental_snapshot"],
            summary="No fundamental provider produced a snapshot.",
        ),
        errors,
        [],
    )


def _first_macro_snapshot(
    providers: list[MacroDataProvider], symbol: SymbolIdentity
) -> tuple[MacroSnapshot, list[str]]:
    errors: list[str] = []
    for provider in providers:
        try:
            return provider.get_macro_context(symbol), errors
        except Exception as exc:
            errors.append(f"{provider.metadata().provider_id}: {exc}")
    return (
        MacroSnapshot(
            region=symbol.region,
            currency=symbol.currency,
            attribution=source_attribution(
                source_name="macro_provider_unavailable",
                provider_type="macro",
                source_role="missing",
                fetched_at=utc_now_iso(),
                freshness="missing",
                notes=errors,
            ),
            missing_fields=["macro_snapshot"],
            summary="No macro provider produced a snapshot.",
        ),
        errors,
    )


def _collect_disclosures(
    providers: list[DisclosureProvider], symbol: SymbolIdentity, *, limit: int
) -> tuple[list[DisclosureEvent], list[str], list[DataSourceAttribution]]:
    disclosures: list[DisclosureEvent] = []
    errors: list[str] = []
    empty_attributions: list[DataSourceAttribution] = []
    for provider in providers:
        provider_metadata = provider.metadata()
        try:
            provider_disclosures = provider.get_disclosures(symbol, limit=limit)
        except Exception as exc:
            errors.append(f"{provider_metadata.provider_id}: {exc}")
            continue
        disclosures.extend(provider_disclosures)
        if not provider_disclosures:
            empty_attributions.append(
                source_attribution(
                    source_name=provider_metadata.provider_id,
                    provider_type="disclosure",
                    source_role="missing",
                    fetched_at=utc_now_iso(),
                    freshness="missing",
                    notes=[
                        "no_disclosures_returned",
                        *provider_metadata.notes,
                    ],
                )
            )
    return disclosures[:limit], errors, empty_attributions


def _collect_provider_news(
    providers: list[NewsProvider], symbol: SymbolIdentity, *, limit: int
) -> tuple[list[NewsEvent], list[str], list[DataSourceAttribution]]:
    events: list[NewsEvent] = []
    errors: list[str] = []
    empty_attributions: list[DataSourceAttribution] = []
    for provider in providers:
        provider_metadata = provider.metadata()
        try:
            provider_events = provider.get_news(symbol, limit=limit)
        except Exception as exc:
            errors.append(f"{provider_metadata.provider_id}: {exc}")
            continue
        events.extend(provider_events)
        if not provider_events:
            empty_attributions.append(
                source_attribution(
                    source_name=provider_metadata.provider_id,
                    provider_type="news",
                    source_role="missing",
                    fetched_at=utc_now_iso(),
                    freshness="missing",
                    notes=[
                        "no_news_events_returned",
                        *provider_metadata.notes,
                    ],
                )
            )
    return events[:limit], errors, empty_attributions


def _attributions(
    *,
    market: DataSourceAttribution,
    fundamental: DataSourceAttribution,
    macro: DataSourceAttribution,
    news_events: list[NewsEvent],
    disclosures: list[DisclosureEvent],
    extra_attributions: list[DataSourceAttribution] | None = None,
) -> list[DataSourceAttribution]:
    return [
        market,
        fundamental,
        macro,
        *(event.attribution for event in news_events),
        *(event.attribution for event in disclosures),
        *(extra_attributions or []),
    ]


def _completeness_score(attributions: list[DataSourceAttribution]) -> float:
    if not attributions:
        return 0.0
    return round(
        sum(item.completeness for item in attributions) / len(attributions),
        4,
    )


def build_canonical_analysis_snapshot(
    snapshot: MarketSnapshot,
    *,
    settings: Settings,
    preferences: InvestmentPreferences | None = None,
    news_items: list[NewsSignal] | None = None,
    providers: ProviderSet | None = None,
    lookback: str | None = None,
) -> CanonicalAnalysisSnapshot:
    """Merge provider outputs into one canonical analysis snapshot."""
    provider_set = providers or default_provider_set(settings)
    symbol_identity = resolve_symbol_identity(snapshot.symbol, preferences)
    market = market_snapshot_from_runtime_snapshot(
        snapshot,
        symbol=symbol_identity,
        lookback=lookback
        or (snapshot.context_pack.lookback if snapshot.context_pack else None),
    )

    fundamental, fundamental_errors, extra_fundamental_attributions = (
        _first_fundamental_snapshot(
            provider_set.fundamental,
            symbol_identity,
        )
    )
    macro, macro_errors = _first_macro_snapshot(provider_set.macro, symbol_identity)

    if news_items is not None:
        news_events = canonical_news_from_signals(
            news_items,
            symbol_identity=symbol_identity,
        )
        news_errors: list[str] = []
        empty_news_attributions: list[DataSourceAttribution] = []
    else:
        news_events, news_errors, empty_news_attributions = _collect_provider_news(
            provider_set.news,
            symbol_identity,
            limit=settings.news_headline_limit,
        )
    disclosures, disclosure_errors, empty_disclosure_attributions = _collect_disclosures(
        provider_set.disclosures,
        symbol_identity,
        limit=5,
    )

    missing_sections: list[str] = []
    if market.missing_fields:
        missing_sections.append("market")
    if fundamental.missing_fields:
        missing_sections.append("fundamentals")
    if macro.missing_fields:
        missing_sections.append("macro")
    if not news_events:
        missing_sections.append("news")
    if not disclosures:
        missing_sections.append("disclosures")

    error_notes = [
        *fundamental_errors,
        *macro_errors,
        *news_errors,
        *disclosure_errors,
    ]
    attributions = _attributions(
        market=market.attribution,
        fundamental=fundamental.attribution,
        macro=macro.attribution,
        news_events=news_events,
        disclosures=disclosures,
        extra_attributions=[
            *extra_fundamental_attributions,
            *empty_news_attributions,
            *empty_disclosure_attributions,
        ],
    )
    if error_notes:
        attributions.append(
            source_attribution(
                source_name="provider_aggregation_errors",
                provider_type="macro",
                source_role="missing",
                fetched_at=utc_now_iso(),
                freshness="unknown",
                notes=error_notes,
            )
        )

    return CanonicalAnalysisSnapshot(
        symbol_identity=symbol_identity,
        generated_at=utc_now_iso(),
        market=market,
        fundamental=fundamental,
        news_events=news_events,
        disclosures=disclosures,
        macro=macro,
        source_attributions=attributions,
        missing_sections=missing_sections,
        completeness_score=_completeness_score(attributions),
        summary=(
            f"Canonical analysis snapshot for {symbol_identity.symbol}: "
            f"market rows={market.rows}, news={len(news_events)}, "
            f"disclosures={len(disclosures)}, missing={','.join(missing_sections) or 'none'}."
        ),
    )
