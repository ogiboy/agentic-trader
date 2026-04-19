"""Public-source provider scaffolds for canonical financial context.

These adapters intentionally do not fetch live remote data yet. They make the
V1 source ladder explicit while returning missing-field snapshots instead of
fabricating fundamentals or disclosures.
"""

from agentic_trader.config import Settings
from agentic_trader.providers.base import metadata, source_attribution, utc_now_iso
from agentic_trader.schemas import (
    DisclosureEvent,
    FundamentalSnapshot,
    ProviderMetadata,
    SymbolIdentity,
)


FUNDAMENTAL_FIELDS = [
    "revenue_growth",
    "profitability_stability",
    "cash_flow_alignment",
    "debt_risk",
    "reinvestment_potential",
]


class SecEdgarFundamentalProvider:
    """SEC EDGAR scaffold for future US fundamental ingestion."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def metadata(self) -> ProviderMetadata:
        return metadata(
            provider_id="sec_edgar_fundamentals",
            name="SEC EDGAR Fundamentals",
            provider_type="fundamental",
            role="primary",
            priority=10,
            enabled=True,
            requires_network=False,
            notes=["sec_10k_10q_8k_source", "ingestion_pending"],
        )

    def get_fundamental_data(self, symbol: SymbolIdentity) -> FundamentalSnapshot:
        notes = ["sec_10k_10q_8k_source", "ingestion_pending"]
        if symbol.region != "US":
            notes.append(f"unsupported_region={symbol.region}")
        return FundamentalSnapshot(
            symbol_identity=symbol,
            fx_exposure="unknown",
            attribution=source_attribution(
                source_name="sec_edgar",
                provider_type="fundamental",
                source_role="missing",
                fetched_at=utc_now_iso(),
                freshness="missing",
                notes=notes,
            ),
            missing_fields=list(FUNDAMENTAL_FIELDS),
            summary=(
                "SEC EDGAR fundamental source is defined, but 10-K/10-Q/8-K "
                "ingestion is not implemented yet."
            ),
        )


class FinnhubFundamentalProvider:
    """Finnhub scaffold for optional free-friendly enrichment."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def metadata(self) -> ProviderMetadata:
        configured = bool(self._settings.finnhub_api_key)
        return metadata(
            provider_id="finnhub_fundamentals",
            name="Finnhub Fundamentals",
            provider_type="fundamental",
            role="fallback",
            priority=40,
            enabled=configured,
            requires_network=configured,
            notes=[
                "optional_free_enrichment",
                "api_key_configured" if configured else "api_key_missing",
                "ingestion_pending",
            ],
        )

    def get_fundamental_data(self, symbol: SymbolIdentity) -> FundamentalSnapshot:
        configured = bool(self._settings.finnhub_api_key)
        return FundamentalSnapshot(
            symbol_identity=symbol,
            fx_exposure="unknown",
            attribution=source_attribution(
                source_name="finnhub",
                provider_type="fundamental",
                source_role="missing",
                fetched_at=utc_now_iso(),
                freshness="missing",
                notes=[
                    "optional_free_enrichment",
                    "api_key_configured" if configured else "api_key_missing",
                    "ingestion_pending",
                ],
            ),
            missing_fields=list(FUNDAMENTAL_FIELDS),
            summary=(
                "Finnhub enrichment is configured as an optional source, but "
                "structured fundamental ingestion is not implemented yet."
            ),
        )


class FmpFundamentalProvider:
    """Financial Modeling Prep scaffold for optional free-friendly enrichment."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def metadata(self) -> ProviderMetadata:
        configured = bool(self._settings.fmp_api_key)
        return metadata(
            provider_id="fmp_fundamentals",
            name="Financial Modeling Prep Fundamentals",
            provider_type="fundamental",
            role="fallback",
            priority=50,
            enabled=configured,
            requires_network=configured,
            notes=[
                "optional_free_enrichment",
                "api_key_configured" if configured else "api_key_missing",
                "ingestion_pending",
            ],
        )

    def get_fundamental_data(self, symbol: SymbolIdentity) -> FundamentalSnapshot:
        configured = bool(self._settings.fmp_api_key)
        return FundamentalSnapshot(
            symbol_identity=symbol,
            fx_exposure="unknown",
            attribution=source_attribution(
                source_name="fmp",
                provider_type="fundamental",
                source_role="missing",
                fetched_at=utc_now_iso(),
                freshness="missing",
                notes=[
                    "optional_free_enrichment",
                    "api_key_configured" if configured else "api_key_missing",
                    "ingestion_pending",
                ],
            ),
            missing_fields=list(FUNDAMENTAL_FIELDS),
            summary=(
                "Financial Modeling Prep enrichment is configured as an optional "
                "source, but structured fundamental ingestion is not implemented yet."
            ),
        )


class KapDisclosureProvider:
    """KAP scaffold for future Turkey public disclosure ingestion."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def metadata(self) -> ProviderMetadata:
        return metadata(
            provider_id="kap_disclosures",
            name="KAP Disclosures",
            provider_type="disclosure",
            role="primary",
            priority=10,
            enabled=True,
            requires_network=False,
            notes=["turkey_public_disclosure_platform", "ingestion_pending"],
        )

    def get_disclosures(
        self, symbol: SymbolIdentity, *, limit: int
    ) -> list[DisclosureEvent]:
        _ = (symbol, limit, self._settings)
        return []
