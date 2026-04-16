from datetime import UTC, datetime

from agentic_trader.config import Settings
from agentic_trader.schemas import FundamentalFeatureSet, SymbolIdentity


def _configured_fundamental_sources(settings: Settings) -> list[str]:
    sources: list[str] = []
    if settings.finnhub_api_key:
        sources.append("finnhub_configured")
    if settings.polygon_api_key:
        sources.append("polygon_configured")
    if settings.massive_api_key:
        sources.append("massive_configured")
    return sources


def get_fundamental_features(
    symbol_identity: SymbolIdentity,
    *,
    settings: Settings,
) -> FundamentalFeatureSet:
    """
    Build the local-first fundamental feature contract without fetching live fundamentals yet.

    The provider configuration is recorded only as source availability metadata. API
    keys are never copied into the feature payload or QA artifacts.
    """
    sources = _configured_fundamental_sources(settings)
    quality_flags = ["fundamental_fetch_not_implemented"]
    if not sources:
        quality_flags.append("fundamental_provider_not_configured")
    if symbol_identity.region == "TR":
        sources.append("kap_future_source")
        quality_flags.append("kap_ingestion_pending")
    else:
        sources.append("sec_filings_future_source")
        quality_flags.append("sec_ingestion_pending")

    return FundamentalFeatureSet(
        symbol=symbol_identity.symbol,
        as_of=datetime.now(UTC).isoformat(),
        fx_exposure="unknown",
        data_sources=sources,
        quality_flags=quality_flags,
        summary=(
            "Fundamental feature contract is available, but live fundamentals are "
            "not ingested yet. Treat this as neutral evidence until structured "
            "provider fetchers are implemented."
        ),
    )
