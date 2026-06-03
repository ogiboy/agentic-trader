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
from agentic_trader.providers.provider_collection import (
    collect_disclosures as _collect_disclosures_impl,
)
from agentic_trader.providers.provider_collection import (
    collect_provider_news as _collect_provider_news_impl,
)
from agentic_trader.providers.provider_collection import (
    first_fundamental_snapshot as _first_fundamental_snapshot_impl,
)
from agentic_trader.providers.provider_collection import (
    first_macro_snapshot as _first_macro_snapshot_impl,
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


def _market_provider_list() -> list[MarketDataProvider]:
    return []


def _fundamental_provider_list() -> list[FundamentalDataProvider]:
    return []


def _news_provider_list() -> list[NewsProvider]:
    return []


def _disclosure_provider_list() -> list[DisclosureProvider]:
    return []


def _macro_provider_list() -> list[MacroDataProvider]:
    return []


@dataclass
class ProviderSet:
    """Grouped provider adapters used by the canonical aggregation layer."""

    market: list[MarketDataProvider] = field(default_factory=_market_provider_list)
    fundamental: list[FundamentalDataProvider] = field(
        default_factory=_fundamental_provider_list
    )
    news: list[NewsProvider] = field(default_factory=_news_provider_list)
    disclosures: list[DisclosureProvider] = field(
        default_factory=_disclosure_provider_list
    )
    macro: list[MacroDataProvider] = field(default_factory=_macro_provider_list)


def default_provider_set(settings: Settings) -> ProviderSet:
    """
    Builds the default ProviderSet using a local-first ordering for adapters.

    Parameters:
        settings (Settings): Configuration passed to provider adapters.

    Returns:
        ProviderSet: A ProviderSet with default adapters:
          - market: YahooMarketDataProvider
          - fundamental: SecEdgar, Finnhub, Fmp, and Local fundamental providers
          - news: YahooNewsProvider
          - disclosures: KapDisclosureProvider and LocalDisclosureProvider
          - macro: LocalMacroProvider
    """
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


def first_fundamental_snapshot(
    providers: list[FundamentalDataProvider], symbol: SymbolIdentity
) -> tuple[FundamentalSnapshot, list[str], list[DataSourceAttribution]]:
    """Return the first usable fundamental snapshot through the public aggregation seam."""
    return _first_fundamental_snapshot_impl(providers, symbol)


def _first_macro_snapshot(
    providers: list[MacroDataProvider], symbol: SymbolIdentity
) -> tuple[MacroSnapshot, list[str]]:
    return _first_macro_snapshot_impl(providers, symbol)


def collect_disclosures(
    providers: list[DisclosureProvider], symbol: SymbolIdentity, *, limit: int
) -> tuple[list[DisclosureEvent], list[str], list[DataSourceAttribution]]:
    """Collect disclosures through the public aggregation seam."""
    return _collect_disclosures_impl(providers, symbol, limit=limit)


def collect_provider_news(
    providers: list[NewsProvider], symbol: SymbolIdentity, *, limit: int
) -> tuple[list[NewsEvent], list[str], list[DataSourceAttribution]]:
    """Collect provider news through the public aggregation seam."""
    return _collect_provider_news_impl(providers, symbol, limit=limit)


def _attributions(
    *,
    market: DataSourceAttribution,
    fundamental: DataSourceAttribution,
    macro: DataSourceAttribution,
    news_events: list[NewsEvent],
    disclosures: list[DisclosureEvent],
    extra_attributions: list[DataSourceAttribution] | None = None,
) -> list[DataSourceAttribution]:
    """
    Assemble canonical data source attributions from market, fundamental, macro, and event-level sources into a single ordered list.

    Parameters:
        market (DataSourceAttribution): Attribution for the market snapshot.
        fundamental (DataSourceAttribution): Attribution for the fundamental snapshot.
        macro (DataSourceAttribution): Attribution for the macro snapshot.
        news_events (list[NewsEvent]): News events whose `attribution` values will be included in order.
        disclosures (list[DisclosureEvent]): Disclosure events whose `attribution` values will be included in order.
        extra_attributions (list[DataSourceAttribution] | None): Additional attributions to append, if any.

    Returns:
        list[DataSourceAttribution]: Ordered list containing the market, fundamental, and macro attributions followed by attributions extracted from `news_events`, `disclosures`, and `extra_attributions`.
    """
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


@dataclass(frozen=True)
class _ProviderSnapshotBundle:
    fundamental: FundamentalSnapshot
    macro: MacroSnapshot
    errors: list[str]
    extra_fundamental_attributions: list[DataSourceAttribution]


@dataclass(frozen=True)
class _EventBundle:
    news_events: list[NewsEvent]
    disclosures: list[DisclosureEvent]
    errors: list[str]
    empty_news_attributions: list[DataSourceAttribution]
    empty_disclosure_attributions: list[DataSourceAttribution]


def build_canonical_analysis_snapshot(
    snapshot: MarketSnapshot,
    *,
    settings: Settings,
    preferences: InvestmentPreferences | None = None,
    news_items: list[NewsSignal] | None = None,
    providers: ProviderSet | None = None,
    lookback: str | None = None,
) -> CanonicalAnalysisSnapshot:
    """Build canonical market, fundamental, macro, news, and disclosure context."""
    provider_set = providers or default_provider_set(settings)
    symbol_identity = resolve_symbol_identity(snapshot.symbol, preferences)
    market = market_snapshot_from_runtime_snapshot(
        snapshot,
        symbol=symbol_identity,
        lookback=lookback
        or (snapshot.context_pack.lookback if snapshot.context_pack else None),
    )
    provider_snapshots = _provider_snapshots(provider_set, symbol_identity)
    events = _event_bundle(
        settings,
        provider_set=provider_set,
        symbol_identity=symbol_identity,
        news_items=news_items,
    )
    missing_sections = _missing_sections(
        market_missing=bool(market.missing_fields),
        fundamental_missing=bool(provider_snapshots.fundamental.missing_fields),
        macro_missing=bool(provider_snapshots.macro.missing_fields),
        news_missing=not events.news_events,
        disclosures_missing=not events.disclosures,
    )
    attributions = _canonical_attributions(
        market=market.attribution,
        fundamental=provider_snapshots.fundamental.attribution,
        macro=provider_snapshots.macro.attribution,
        news_events=events.news_events,
        disclosures=events.disclosures,
        extra_attributions=[
            *provider_snapshots.extra_fundamental_attributions,
            *events.empty_news_attributions,
            *events.empty_disclosure_attributions,
        ],
        error_notes=[*provider_snapshots.errors, *events.errors],
    )

    return CanonicalAnalysisSnapshot(
        symbol_identity=symbol_identity,
        generated_at=utc_now_iso(),
        market=market,
        fundamental=provider_snapshots.fundamental,
        news_events=events.news_events,
        disclosures=events.disclosures,
        macro=provider_snapshots.macro,
        source_attributions=attributions,
        missing_sections=missing_sections,
        completeness_score=_completeness_score(attributions),
        summary=_canonical_summary(
            symbol_identity=symbol_identity,
            market_rows=market.rows,
            news_count=len(events.news_events),
            disclosure_count=len(events.disclosures),
            missing_sections=missing_sections,
        ),
    )


def _provider_snapshots(
    provider_set: ProviderSet, symbol_identity: SymbolIdentity
) -> _ProviderSnapshotBundle:
    fundamental, fundamental_errors, extra_fundamental_attributions = (
        first_fundamental_snapshot(
            provider_set.fundamental,
            symbol_identity,
        )
    )
    macro, macro_errors = _first_macro_snapshot(provider_set.macro, symbol_identity)
    return _ProviderSnapshotBundle(
        fundamental=fundamental,
        macro=macro,
        errors=[*fundamental_errors, *macro_errors],
        extra_fundamental_attributions=extra_fundamental_attributions,
    )


def _event_bundle(
    settings: Settings,
    *,
    provider_set: ProviderSet,
    symbol_identity: SymbolIdentity,
    news_items: list[NewsSignal] | None,
) -> _EventBundle:
    if news_items is not None:
        news_events = canonical_news_from_signals(
            news_items,
            symbol_identity=symbol_identity,
        )
        news_errors: list[str] = []
        empty_news_attributions: list[DataSourceAttribution] = []
    else:
        news_events, news_errors, empty_news_attributions = collect_provider_news(
            provider_set.news,
            symbol_identity,
            limit=settings.news_headline_limit,
        )
    disclosures, disclosure_errors, empty_disclosure_attributions = collect_disclosures(
        provider_set.disclosures,
        symbol_identity,
        limit=5,
    )
    return _EventBundle(
        news_events=news_events,
        disclosures=disclosures,
        errors=[*news_errors, *disclosure_errors],
        empty_news_attributions=empty_news_attributions,
        empty_disclosure_attributions=empty_disclosure_attributions,
    )


def _missing_sections(
    *,
    market_missing: bool,
    fundamental_missing: bool,
    macro_missing: bool,
    news_missing: bool,
    disclosures_missing: bool,
) -> list[str]:
    sections: list[str] = []
    for name, missing in (
        ("market", market_missing),
        ("fundamentals", fundamental_missing),
        ("macro", macro_missing),
        ("news", news_missing),
        ("disclosures", disclosures_missing),
    ):
        if missing:
            sections.append(name)
    return sections


def _canonical_attributions(
    *,
    market: DataSourceAttribution,
    fundamental: DataSourceAttribution,
    macro: DataSourceAttribution,
    news_events: list[NewsEvent],
    disclosures: list[DisclosureEvent],
    extra_attributions: list[DataSourceAttribution],
    error_notes: list[str],
) -> list[DataSourceAttribution]:
    attributions = _attributions(
        market=market,
        fundamental=fundamental,
        macro=macro,
        news_events=news_events,
        disclosures=disclosures,
        extra_attributions=extra_attributions,
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
    return attributions


def _canonical_summary(
    *,
    symbol_identity: SymbolIdentity,
    market_rows: int,
    news_count: int,
    disclosure_count: int,
    missing_sections: list[str],
) -> str:
    return (
        f"Canonical analysis snapshot for {symbol_identity.symbol}: "
        f"market rows={market_rows}, news={news_count}, "
        f"disclosures={disclosure_count}, "
        f"missing={','.join(missing_sections) or 'none'}."
    )
