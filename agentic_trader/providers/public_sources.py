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


FUNDAMENTAL_FIELDS = (
    "revenue_growth",
    "profitability_stability",
    "cash_flow_alignment",
    "debt_risk",
    "reinvestment_potential",
)


class SecEdgarFundamentalProvider:
    """SEC EDGAR scaffold for future US fundamental ingestion."""

    def __init__(self, settings: Settings) -> None:
        """
        Initialize the provider with runtime settings.
        
        Parameters:
            settings (Settings): Configuration and credentials used by the provider; stored on `self._settings`.
        """
        self._settings = settings

    def metadata(self) -> ProviderMetadata:
        """
        Provider metadata for the SEC EDGAR fundamentals scaffold.
        
        Returns:
            ProviderMetadata: Metadata with provider_id "sec_edgar_fundamentals", name "SEC EDGAR Fundamentals",
            provider_type "fundamental", role "primary", priority 10, enabled True, requires_network False,
            and notes ["sec_10k_10q_8k_source", "ingestion_pending"].
        """
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
        """
        Return a scaffolded FundamentalSnapshot indicating ingestion is pending for the given symbol.
        
        Parameters:
            symbol (SymbolIdentity): The symbol identity for which the snapshot is produced.
        
        Returns:
            FundamentalSnapshot: Snapshot with `fx_exposure` set to `"unknown"`, `missing_fields` containing the canonical FUNDAMENTAL_FIELDS, and `attribution` marked as missing with `fetched_at` set to the current UTC ISO timestamp. The attribution `notes` always include `"sec_10k_10q_8k_source"` and `"ingestion_pending"`; if `symbol.region` is not `"US"` an additional note `unsupported_region={region}` is appended.
        """
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
        """
        Initialize the provider with runtime settings.
        
        Parameters:
            settings (Settings): Configuration and credentials used by the provider; stored on `self._settings`.
        """
        self._settings = settings

    def metadata(self) -> ProviderMetadata:
        """
        Provide metadata describing the Finnhub fundamentals provider configuration.
        
        Returns:
            ProviderMetadata: Metadata with provider_id "finnhub_fundamentals", name "Finnhub Fundamentals",
            provider_type "fundamental", role "fallback", priority 40, boolean `enabled` and `requires_network`
            determined by whether an API key is configured, and `notes` that indicate optional free enrichment,
            the API key status, and that ingestion is pending.
        """
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
        """
        Return a placeholder FundamentalSnapshot for the given symbol indicating Finnhub enrichment is pending.
        
        Parameters:
            symbol (SymbolIdentity): The identity of the security to describe.
        
        Returns:
            FundamentalSnapshot: Snapshot with:
                - symbol_identity set to `symbol`
                - `fx_exposure` set to `"unknown"`
                - `attribution` identifying `source_name="finnhub"`, `provider_type="fundamental"`, `source_role="missing"`, `freshness="missing"`, `fetched_at` set to the current UTC timestamp, and `notes` containing `"optional_free_enrichment"`, either `"api_key_configured"` or `"api_key_missing"` depending on configuration, and `"ingestion_pending"`
                - `missing_fields` equal to `FUNDAMENTAL_FIELDS`
                - `summary` stating that structured fundamental ingestion is not implemented yet
        """
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
        """
        Initialize the provider with runtime settings.
        
        Parameters:
            settings (Settings): Configuration and credentials used by the provider; stored on `self._settings`.
        """
        self._settings = settings

    def metadata(self) -> ProviderMetadata:
        """
        Provider metadata for the Financial Modeling Prep fundamentals adapter.
        
        Returns:
            ProviderMetadata: Metadata describing the provider (provider_id "fmp_fundamentals", name "Financial Modeling Prep Fundamentals", provider_type "fundamental", role "fallback", priority 50). The `enabled` and `requires_network` flags reflect whether an API key is configured. `notes` contains "optional_free_enrichment", either "api_key_configured" or "api_key_missing" depending on configuration, and "ingestion_pending".
        """
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
        """
        Produce a FundamentalSnapshot that marks Financial Modeling Prep enrichment as pending for the given symbol.
        
        Parameters:
            symbol (SymbolIdentity): The symbol identity for which the snapshot is produced.
        
        Returns:
            FundamentalSnapshot: Snapshot with `fx_exposure` set to `"unknown"`, `missing_fields` populated from `FUNDAMENTAL_FIELDS`, and `attribution` notes indicating optional enrichment, API key status, and that ingestion is pending.
        """
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
        """
        Initialize the provider with runtime settings.
        
        Parameters:
            settings (Settings): Configuration and credentials used by the provider; stored on `self._settings`.
        """
        self._settings = settings

    def metadata(self) -> ProviderMetadata:
        """
        Provider metadata for the KAP (Turkey public disclosure) scaffold.
        
        Returns:
            ProviderMetadata: Metadata for the KAP disclosures provider with
            provider_id="kap_disclosures", name="KAP Disclosures", provider_type="disclosure",
            role="primary", priority=10, enabled=True, requires_network=False, and notes
            ["turkey_public_disclosure_platform", "ingestion_pending"].
        """
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
        """
        Return disclosure events for the given symbol (currently unimplemented and always returns an empty list).
        
        This provider scaffold does not perform any ingestion yet; the function accepts a symbol and a limit but ignores them and yields no disclosure events.
        
        Parameters:
            symbol (SymbolIdentity): Identifier for the security whose disclosures would be requested.
            limit (int): Maximum number of disclosure events to return (currently ignored).
        
        Returns:
            list[DisclosureEvent]: An empty list (no disclosure events).
        """
        _ = (symbol, limit, self._settings)
        return []
