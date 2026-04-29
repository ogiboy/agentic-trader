"""Read-only status helpers for the optional research sidecar."""

from agentic_trader.config import Settings
from agentic_trader.researchd.orchestrator import (
    ResearchSidecar,
    parse_research_symbols,
    summarize_provider_health,
    utc_now_iso,
)
from agentic_trader.researchd.providers import (
    ResearchEvidenceProvider,
    default_research_providers,
)
from agentic_trader.schemas import ResearchProviderHealth, ResearchSidecarState


def _provider_status(provider: ResearchEvidenceProvider) -> ResearchProviderHealth:
    meta = provider.metadata()
    return ResearchProviderHealth(
        provider_id=meta.provider_id,
        name=meta.name,
        provider_type=meta.provider_type,
        enabled=meta.enabled,
        requires_network=meta.requires_network,
        source_role="missing",
        freshness="missing" if meta.enabled else "unknown",
        message=(
            "Provider scaffold is visible; no sidecar ingestion has run."
            if meta.enabled
            else "Provider is disabled by configuration."
        ),
        notes=list(meta.notes),
    )


def build_research_sidecar_state(
    settings: Settings,
    *,
    probe: bool = False,
    providers: list[ResearchEvidenceProvider] | None = None,
) -> ResearchSidecarState:
    """Build an operator-safe sidecar status snapshot.

    By default this is read-only and does not call provider collection. Passing
    `probe=True` runs one isolated foundation pass, which still cannot submit
    orders or mutate trading policy.
    """
    provider_set = providers or default_research_providers(settings)
    if probe:
        return ResearchSidecar(settings, providers=provider_set).collect_once().state

    now = utc_now_iso()
    provider_health = [_provider_status(provider) for provider in provider_set]
    enabled = settings.research_sidecar_enabled and settings.research_mode != "off"
    return ResearchSidecarState(
        mode=settings.research_mode,
        enabled=enabled,
        backend=settings.research_sidecar_backend,
        status="idle" if enabled else "disabled",
        updated_at=now,
        watched_symbols=parse_research_symbols(settings.research_symbols),
        provider_health=provider_health,
        source_health_summary=summarize_provider_health(provider_health),
    )
