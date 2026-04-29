"""Optional research sidecar orchestration boundary.

The sidecar is intentionally separate from the trading runtime. It can assemble
research evidence and world-state packets, but it does not call broker,
execution, run persistence, or strict trading-gate code.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from agentic_trader.config import Settings
from agentic_trader.researchd.providers import (
    ResearchEvidenceProvider,
    ResearchProviderOutput,
    default_research_providers,
    missing_attribution,
    provider_health_from_output,
)
from agentic_trader.schemas import (
    EntityDossier,
    MacroEvent,
    RawEvidenceRecord,
    ResearchFinding,
    ResearchProviderHealth,
    ResearchSidecarState,
    SocialSignal,
    WorldStateSnapshot,
)


def utc_now_iso() -> str:
    """Return an ISO timestamp in UTC for sidecar metadata."""
    return datetime.now(UTC).isoformat()


def parse_research_symbols(raw_symbols: str) -> list[str]:
    """Parse comma-separated watch symbols from settings."""
    return [
        symbol.strip().upper()
        for symbol in raw_symbols.split(",")
        if symbol.strip()
    ]


@dataclass(frozen=True)
class ResearchPipelineResult:
    """Result of one sidecar pipeline pass."""

    state: ResearchSidecarState
    world_state: WorldStateSnapshot | None = None
    raw_evidence: list[RawEvidenceRecord] = field(default_factory=list)
    macro_events: list[MacroEvent] = field(default_factory=list)
    social_signals: list[SocialSignal] = field(default_factory=list)
    findings: list[ResearchFinding] = field(default_factory=list)
    dossiers: list[EntityDossier] = field(default_factory=list)
    memory_update: dict[str, object] = field(default_factory=dict)


class ResearchSidecarBackend(Protocol):
    """Backend interface for optional future engines such as CrewAI."""

    name: str

    def run(
        self,
        *,
        settings: Settings,
        symbols: list[str],
        provider_outputs: list[ResearchProviderOutput],
    ) -> ResearchPipelineResult:
        """Run research synthesis for already-normalized provider output."""
        ...


class NoopResearchBackend:
    """Safe backend that records source state without synthesizing fake findings."""

    name = "noop"

    def run(
        self,
        *,
        settings: Settings,
        symbols: list[str],
        provider_outputs: list[ResearchProviderOutput],
    ) -> ResearchPipelineResult:
        now = utc_now_iso()
        raw_evidence: list[RawEvidenceRecord] = []
        macro_events: list[MacroEvent] = []
        social_signals: list[SocialSignal] = []
        health: list[ResearchProviderHealth] = []
        attributions = []

        for output in provider_outputs:
            raw_evidence.extend(output.raw_evidence)
            macro_events.extend(output.macro_events)
            social_signals.extend(output.social_signals)
            health.append(provider_health_from_output(output))
            attributions.append(missing_attribution(output.metadata))

        world_state = WorldStateSnapshot(
            snapshot_id=f"world-{uuid4()}",
            mode=settings.research_mode,
            generated_at=now,
            observed_at=now,
            source_attributions=attributions,
            watched_symbols=symbols,
            macro_events=macro_events,
            social_signals=social_signals,
            findings=[],
            summary=(
                "Research sidecar foundation ran with provider scaffolds only; "
                "no live evidence or synthesized findings were produced."
            ),
        )
        state = ResearchSidecarState(
            mode=settings.research_mode,
            enabled=settings.research_sidecar_enabled,
            backend=self.name,
            status="completed",
            updated_at=now,
            last_started_at=now,
            last_successful_update_at=now,
            watched_symbols=symbols,
            provider_health=health,
            source_health_summary=summarize_provider_health(health),
        )
        return ResearchPipelineResult(
            state=state,
            world_state=world_state,
            raw_evidence=raw_evidence,
            macro_events=macro_events,
            social_signals=social_signals,
            memory_update={
                "status": "not_written",
                "reason": "sidecar persistence is not enabled in this foundation slice",
                "raw_web_text_injected": False,
            },
        )


class CrewAiResearchBackend:
    """Placeholder boundary for a future optional CrewAI Flow/Crew backend."""

    name = "crewai"

    def run(
        self,
        *,
        settings: Settings,
        symbols: list[str],
        provider_outputs: list[ResearchProviderOutput],
    ) -> ResearchPipelineResult:
        _ = (settings, symbols, provider_outputs)
        now = utc_now_iso()
        state = ResearchSidecarState(
            mode=settings.research_mode,
            enabled=settings.research_sidecar_enabled,
            backend=self.name,
            status="failed",
            updated_at=now,
            last_started_at=now,
            last_error=(
                "CrewAI sidecar backend is reserved behind the adapter boundary "
                "and is not implemented in this foundation slice."
            ),
            watched_symbols=symbols,
            source_health_summary={},
        )
        return ResearchPipelineResult(state=state)


def summarize_provider_health(
    provider_health: list[ResearchProviderHealth],
) -> dict[str, int]:
    """Count provider health by freshness status for dashboard consumers."""
    summary = {"fresh": 0, "stale": 0, "unknown": 0, "missing": 0}
    for item in provider_health:
        summary[item.freshness] = summary.get(item.freshness, 0) + 1
    return summary


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
