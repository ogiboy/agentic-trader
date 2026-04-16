"""Local-first placeholder providers for fundamentals, disclosures, and macro."""

from agentic_trader.config import Settings
from agentic_trader.providers.base import metadata, source_attribution, utc_now_iso
from agentic_trader.schemas import (
    DisclosureEvent,
    FundamentalSnapshot,
    MacroSnapshot,
    ProviderMetadata,
    SymbolIdentity,
)


def _configured_vendor_notes(settings: Settings) -> list[str]:
    notes: list[str] = []
    if settings.finnhub_api_key:
        notes.append("finnhub_configured")
    if settings.polygon_api_key:
        notes.append("polygon_configured")
    if settings.massive_api_key:
        notes.append("massive_configured")
    return notes


class LocalFundamentalProvider:
    """Safe fundamental scaffold that records provider readiness, not secrets."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def metadata(self) -> ProviderMetadata:
        return metadata(
            provider_id="local_fundamental_scaffold",
            name="Local Fundamental Scaffold",
            provider_type="fundamental",
            role="missing",
            enabled=True,
            notes=["structured_contract_only", *_configured_vendor_notes(self._settings)],
        )

    def get_fundamental_data(self, symbol: SymbolIdentity) -> FundamentalSnapshot:
        notes = _configured_vendor_notes(self._settings)
        if symbol.region == "TR":
            notes.extend(["kap_primary_future_source", "turkey_financials_pending"])
        else:
            notes.extend(["sec_edgar_primary_future_source", "company_facts_pending"])
        return FundamentalSnapshot(
            symbol_identity=symbol,
            fx_exposure="unknown",
            attribution=source_attribution(
                source_name="local_fundamental_scaffold",
                provider_type="fundamental",
                source_role="missing",
                fetched_at=utc_now_iso(),
                freshness="missing",
                confidence=0.0,
                completeness=0.0,
                notes=notes,
            ),
            missing_fields=[
                "revenue_growth",
                "profitability_stability",
                "cash_flow_alignment",
                "debt_risk",
                "reinvestment_potential",
            ],
            summary=(
                "Fundamental provider contract is active, but structured "
                "fundamental ingestion is not implemented yet."
            ),
        )


class LocalDisclosureProvider:
    """Disclosure scaffold for SEC EDGAR and KAP without live ingestion yet."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def metadata(self) -> ProviderMetadata:
        return metadata(
            provider_id="local_disclosure_scaffold",
            name="Local Disclosure Scaffold",
            provider_type="disclosure",
            role="missing",
            enabled=True,
            notes=["sec_edgar_future_source", "kap_future_source"],
        )

    def get_disclosures(
        self, symbol: SymbolIdentity, *, limit: int
    ) -> list[DisclosureEvent]:
        _ = (symbol, limit, self._settings)
        return []


class LocalMacroProvider:
    """Local macro scaffold that keeps missing macro data explicit."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def metadata(self) -> ProviderMetadata:
        notes = ["structured_contract_only", *_configured_vendor_notes(self._settings)]
        if self._settings.news_mode != "off":
            notes.append(f"news_{self._settings.news_mode}_configured")
        return metadata(
            provider_id="local_macro_scaffold",
            name="Local Macro Scaffold",
            provider_type="macro",
            role="missing",
            enabled=True,
            notes=notes,
        )

    def get_macro_context(self, symbol: SymbolIdentity) -> MacroSnapshot:
        notes = _configured_vendor_notes(self._settings)
        if symbol.region == "TR":
            notes.extend(["cbrt_future_source", "turkey_inflation_fx_pending"])
            fx_risk = "medium" if symbol.currency == "TRY" else "high"
        else:
            notes.extend(["macro_indicators_future_source", "rates_inflation_pending"])
            fx_risk = "unknown"
        return MacroSnapshot(
            region=symbol.region,
            currency=symbol.currency,
            fx_risk=fx_risk,
            attribution=source_attribution(
                source_name="local_macro_scaffold",
                provider_type="macro",
                source_role="missing",
                fetched_at=utc_now_iso(),
                freshness="missing",
                confidence=0.0,
                completeness=0.0,
                notes=notes,
            ),
            missing_fields=[
                "rates_bias",
                "inflation_bias",
                "sector_risk_score",
                "political_risk_score",
            ],
            summary=(
                "Macro provider contract is active, but structured macro "
                "indicator ingestion is not implemented yet."
            ),
        )
