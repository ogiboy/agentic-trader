"""Optional research sidecar orchestration boundary.

The sidecar is intentionally separate from the trading runtime. It can assemble
research evidence and world-state packets, but it does not call broker,
execution, run persistence, or strict trading-gate code.
"""

from __future__ import annotations

from agentic_trader.config import Settings
from agentic_trader.researchd.orchestrator_backends import (
    CrewAiResearchBackend,
    NoopResearchBackend,
)
from agentic_trader.researchd.orchestrator_types import (
    ContractRunner,
    ResearchPipelineResult,
    ResearchSidecarBackend,
    summarize_provider_health,
)
from agentic_trader.researchd.providers import (
    ResearchEvidenceProvider,
    default_research_providers,
)
from agentic_trader.schemas import ResearchSidecarState
from agentic_trader.time_utils import utc_now_iso


def parse_research_symbols(raw_symbols: str) -> list[str]:
    """Parse a comma-separated string into normalized symbols."""

    return [
        symbol.strip().upper() for symbol in raw_symbols.split(",") if symbol.strip()
    ]


class ResearchSidecar:
    """Small sidecar runner with isolated provider and backend seams."""

    def __init__(
        self,
        settings: Settings,
        *,
        providers: list[ResearchEvidenceProvider] | None = None,
        backend: ResearchSidecarBackend | None = None,
    ) -> None:
        self.settings = settings
        if providers is None and settings.research_camofox_enabled:
            from agentic_trader.system.runtime_tools import (
                ensure_camofox_service_if_configured,
            )

            ensure_camofox_service_if_configured(settings)
        self.providers = providers or default_research_providers(settings)
        self.backend = backend or self._backend_from_settings(settings)

    def _backend_from_settings(self, settings: Settings) -> ResearchSidecarBackend:
        if settings.research_sidecar_backend == "crewai":
            return CrewAiResearchBackend()
        return NoopResearchBackend()

    def collect_once(self) -> ResearchPipelineResult:
        """Run one sidecar collection pass if the sidecar is enabled."""

        symbols = parse_research_symbols(self.settings.research_symbols)
        if (
            not self.settings.research_sidecar_enabled
            or self.settings.research_mode == "off"
        ):
            now = utc_now_iso()
            state = ResearchSidecarState(
                mode=self.settings.research_mode,
                enabled=False,
                backend=self.settings.research_sidecar_backend,
                status="disabled",
                updated_at=now,
                watched_symbols=symbols,
                provider_health=[],
                source_health_summary={},
            )
            return ResearchPipelineResult(state=state)

        provider_outputs = [
            provider.collect(
                symbols=symbols,
                limit=self.settings.research_max_events_per_source,
            )
            for provider in self.providers
        ]
        return self.backend.run(
            settings=self.settings,
            symbols=symbols,
            provider_outputs=provider_outputs,
        )


__all__ = [
    "ContractRunner",
    "CrewAiResearchBackend",
    "NoopResearchBackend",
    "ResearchPipelineResult",
    "ResearchSidecar",
    "ResearchSidecarBackend",
    "parse_research_symbols",
    "summarize_provider_health",
    "utc_now_iso",
]
