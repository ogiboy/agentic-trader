"""Optional public fundamental-provider scaffolds."""

from agentic_trader.config import Settings
from agentic_trader.providers.base import metadata, source_attribution, utc_now_iso
from agentic_trader.providers.sec_companyfacts import FUNDAMENTAL_FIELDS
from agentic_trader.schemas import FundamentalSnapshot, ProviderMetadata, SymbolIdentity

OPTIONAL_ENRICHMENT_NOTES = ("optional_free_enrichment", "ingestion_pending")


class FinnhubFundamentalProvider:
    """Finnhub scaffold for optional free-friendly enrichment."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def metadata(self) -> ProviderMetadata:
        """Provide metadata describing the Finnhub fundamentals configuration."""
        configured = bool(self._settings.finnhub_api_key)
        return metadata(
            provider_id="finnhub_fundamentals",
            name="Finnhub Fundamentals",
            provider_type="fundamental",
            role="fallback",
            priority=40,
            enabled=configured,
            requires_network=configured,
            notes=_optional_notes(configured),
        )

    def get_fundamental_data(self, symbol: SymbolIdentity) -> FundamentalSnapshot:
        """Return a pending-ingestion snapshot for Finnhub fundamentals."""
        return _pending_optional_snapshot(
            symbol,
            configured=bool(self._settings.finnhub_api_key),
            source_name="finnhub",
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
        """Provide metadata for the Financial Modeling Prep adapter."""
        configured = bool(self._settings.fmp_api_key)
        return metadata(
            provider_id="fmp_fundamentals",
            name="Financial Modeling Prep Fundamentals",
            provider_type="fundamental",
            role="fallback",
            priority=50,
            enabled=configured,
            requires_network=configured,
            notes=_optional_notes(configured),
        )

    def get_fundamental_data(self, symbol: SymbolIdentity) -> FundamentalSnapshot:
        """Return a pending-ingestion snapshot for FMP fundamentals."""
        return _pending_optional_snapshot(
            symbol,
            configured=bool(self._settings.fmp_api_key),
            source_name="fmp",
            summary=(
                "Financial Modeling Prep enrichment is configured as an optional "
                "source, but structured fundamental ingestion is not implemented yet."
            ),
        )


def _optional_notes(configured: bool) -> list[str]:
    return [
        OPTIONAL_ENRICHMENT_NOTES[0],
        "api_key_configured" if configured else "api_key_missing",
        OPTIONAL_ENRICHMENT_NOTES[1],
    ]


def _pending_optional_snapshot(
    symbol: SymbolIdentity,
    *,
    configured: bool,
    source_name: str,
    summary: str,
) -> FundamentalSnapshot:
    return FundamentalSnapshot(
        symbol_identity=symbol,
        fx_exposure="unknown",
        attribution=source_attribution(
            source_name=source_name,
            provider_type="fundamental",
            source_role="missing",
            fetched_at=utc_now_iso(),
            freshness="missing",
            notes=_optional_notes(configured),
        ),
        missing_fields=list(FUNDAMENTAL_FIELDS),
        summary=summary,
    )
