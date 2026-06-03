"""Provider collection and fallback selection helpers."""

from __future__ import annotations

from agentic_trader.providers.base import source_attribution, utc_now_iso
from agentic_trader.providers.interfaces import (
    DisclosureProvider,
    FundamentalDataProvider,
    MacroDataProvider,
    NewsProvider,
)
from agentic_trader.schemas import (
    DataSourceAttribution,
    DisclosureEvent,
    FundamentalSnapshot,
    MacroSnapshot,
    NewsEvent,
    SymbolIdentity,
)
from agentic_trader.security import safe_exception_note


def first_fundamental_snapshot(
    providers: list[FundamentalDataProvider], symbol: SymbolIdentity
) -> tuple[FundamentalSnapshot, list[str], list[DataSourceAttribution]]:
    errors: list[str] = []
    missing_snapshots: list[FundamentalSnapshot] = []
    for provider in providers:
        try:
            snapshot = provider.get_fundamental_data(symbol)
        except Exception as exc:
            errors.append(safe_exception_note(provider.metadata().provider_id, exc))
            continue
        if snapshot.attribution.source_role != "missing":
            return snapshot, errors, [item.attribution for item in missing_snapshots]
        missing_snapshots.append(snapshot)
    if missing_snapshots:
        if len(missing_snapshots) == len(providers):
            return (
                _missing_fundamental_snapshot(symbol, errors=errors),
                errors,
                [item.attribution for item in missing_snapshots],
            )
        return (
            missing_snapshots[0],
            errors,
            [item.attribution for item in missing_snapshots[1:]],
        )
    return _missing_fundamental_snapshot(symbol, errors=errors), errors, []


def first_macro_snapshot(
    providers: list[MacroDataProvider], symbol: SymbolIdentity
) -> tuple[MacroSnapshot, list[str]]:
    errors: list[str] = []
    for provider in providers:
        try:
            return provider.get_macro_context(symbol), errors
        except Exception as exc:
            errors.append(safe_exception_note(provider.metadata().provider_id, exc))
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


def collect_disclosures(
    providers: list[DisclosureProvider], symbol: SymbolIdentity, *, limit: int
) -> tuple[list[DisclosureEvent], list[str], list[DataSourceAttribution]]:
    disclosures: list[DisclosureEvent] = []
    errors: list[str] = []
    empty_attributions: list[DataSourceAttribution] = []
    for provider in providers:
        try:
            provider_metadata = provider.metadata()
        except Exception as exc:
            provider_name = type(provider).__name__
            errors.append(safe_exception_note(f"{provider_name}: metadata failed", exc))
            continue
        try:
            provider_disclosures = provider.get_disclosures(symbol, limit=limit)
        except Exception as exc:
            errors.append(safe_exception_note(provider_metadata.provider_id, exc))
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


def collect_provider_news(
    providers: list[NewsProvider], symbol: SymbolIdentity, *, limit: int
) -> tuple[list[NewsEvent], list[str], list[DataSourceAttribution]]:
    events: list[NewsEvent] = []
    errors: list[str] = []
    empty_attributions: list[DataSourceAttribution] = []
    for provider in providers:
        try:
            provider_metadata = provider.metadata()
        except Exception as exc:
            provider_name = type(provider).__name__
            errors.append(safe_exception_note(f"{provider_name}: metadata failed", exc))
            continue
        try:
            provider_events = provider.get_news(symbol, limit=limit)
        except Exception as exc:
            errors.append(safe_exception_note(provider_metadata.provider_id, exc))
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


def _missing_fundamental_snapshot(
    symbol: SymbolIdentity, *, errors: list[str]
) -> FundamentalSnapshot:
    return FundamentalSnapshot(
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
    )
