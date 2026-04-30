"""Provider scaffolds for the optional research sidecar.

These providers expose source readiness and missing-data truth. They do not
fetch remote sources yet, and they never return fabricated research events.
"""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from agentic_trader.config import Settings
from agentic_trader.providers.base import metadata, source_attribution, utc_now_iso
from agentic_trader.schemas import (
    DataProviderKind,
    DataSourceRole,
    MacroEvent,
    ProviderMetadata,
    RawEvidenceRecord,
    ResearchProviderHealth,
    SocialSignal,
)


@dataclass(frozen=True)
class ResearchProviderOutput:
    """Normalized output shape returned by sidecar research providers."""

    metadata: ProviderMetadata
    raw_evidence: list[RawEvidenceRecord] = field(default_factory=list)
    macro_events: list[MacroEvent] = field(default_factory=list)
    social_signals: list[SocialSignal] = field(default_factory=list)
    missing_reasons: list[str] = field(default_factory=list)


@runtime_checkable
class ResearchEvidenceProvider(Protocol):
    """Provider contract for sidecar evidence collection."""

    def metadata(self) -> ProviderMetadata:
        """Return provider identity and operational metadata."""
        ...

    def collect(self, *, symbols: list[str], limit: int) -> ResearchProviderOutput:
        """Collect normalized research evidence or explicit missing-source state."""
        ...


class ScaffoldResearchProvider:
    """A provider placeholder that reports missing ingestion without fake data."""

    def __init__(
        self,
        *,
        provider_id: str,
        name: str,
        provider_type: DataProviderKind,
        role: DataSourceRole,
        priority: int,
        notes: list[str],
        enabled: bool = True,
        requires_network: bool = False,
    ) -> None:
        self._metadata = metadata(
            provider_id=provider_id,
            name=name,
            provider_type=provider_type,
            role=role,
            priority=priority,
            enabled=enabled,
            requires_network=requires_network,
            notes=[*notes, "ingestion_pending"],
        )

    def metadata(self) -> ProviderMetadata:
        return self._metadata

    def collect(self, *, symbols: list[str], limit: int) -> ResearchProviderOutput:
        _ = (symbols, limit)
        return ResearchProviderOutput(
            metadata=self._metadata,
            missing_reasons=["ingestion_pending"],
        )


def default_research_providers(settings: Settings) -> list[ResearchEvidenceProvider]:
    """Return the local-first research source ladder for the sidecar."""
    social_configured = bool(settings.research_symbols)
    return [
        ScaffoldResearchProvider(
            provider_id="sec_edgar_research",
            name="SEC EDGAR Research",
            provider_type="disclosure",
            role="primary",
            priority=10,
            notes=["sec_10k_10q_8k_source", "official_disclosure_source"],
        ),
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


def provider_health_from_output(output: ResearchProviderOutput) -> ResearchProviderHealth:
    """Convert provider output into an operator-safe health summary."""
    meta = output.metadata
    has_payload = bool(output.raw_evidence or output.macro_events or output.social_signals)
    freshness = "fresh" if has_payload else "missing"
    source_role = meta.role if has_payload else "missing"
    fetched_at = utc_now_iso() if has_payload else None
    notes = list(dict.fromkeys([*meta.notes, *output.missing_reasons]))
    return ResearchProviderHealth(
        provider_id=meta.provider_id,
        name=meta.name,
        provider_type=meta.provider_type,
        enabled=meta.enabled,
        requires_network=meta.requires_network,
        source_role=source_role,
        freshness=freshness,
        last_successful_update_at=fetched_at,
        message=(
            "Provider returned normalized research evidence."
            if has_payload
            else "Provider scaffold is visible, but ingestion is not implemented yet."
        ),
        notes=notes,
    )


def missing_attribution(provider: ProviderMetadata):
    """Build a missing-source attribution for future provider output objects."""
    return source_attribution(
        source_name=provider.provider_id,
        provider_type=provider.provider_type,
        source_role="missing",
        fetched_at=utc_now_iso(),
        freshness="missing",
        notes=[*provider.notes, "no_research_payload_returned"],
    )
