from __future__ import annotations

from uuid import uuid4

from agentic_trader.config import Settings
from agentic_trader.researchd.orchestrator_types import (
    ResearchPipelineResult,
    research_world_state_summary,
    summarize_provider_health,
)
from agentic_trader.researchd.providers import (
    ResearchProviderOutput,
    provider_health_from_output,
    source_attributions_from_output,
)
from agentic_trader.schemas import (
    DataSourceAttribution,
    MacroEvent,
    RawEvidenceRecord,
    ResearchProviderHealth,
    ResearchSidecarState,
    SocialSignal,
    WorldStateSnapshot,
)
from agentic_trader.time_utils import utc_now_iso


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
        attributions: list[DataSourceAttribution] = []

        for output in provider_outputs:
            raw_evidence.extend(output.raw_evidence)
            macro_events.extend(output.macro_events)
            social_signals.extend(output.social_signals)
            health.append(provider_health_from_output(output))
            attributions.extend(source_attributions_from_output(output))

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
            summary=research_world_state_summary(
                raw_evidence_count=len(raw_evidence),
                macro_event_count=len(macro_events),
                social_signal_count=len(social_signals),
                finding_count=0,
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
                "reason": "trade memory writes are intentionally disabled for research snapshots",
                "raw_web_text_injected": False,
            },
        )


__all__ = ("NoopResearchBackend",)
