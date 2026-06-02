"""Shared research sidecar orchestration types."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from agentic_trader.config import Settings
from agentic_trader.researchd.providers import ResearchProviderOutput
from agentic_trader.schemas import (
    DataSourceAttribution,
    EntityDossier,
    MacroEvent,
    RawEvidenceRecord,
    ResearchFinding,
    ResearchProviderHealth,
    ResearchSidecarState,
    SocialSignal,
    WorldStateSnapshot,
)

ContractRunner = Callable[
    [list[str], str, Path, dict[str, str], float],
    subprocess.CompletedProcess[str],
]


def _empty_raw_evidence_records() -> list[RawEvidenceRecord]:
    return []


def _empty_macro_events() -> list[MacroEvent]:
    return []


def _empty_social_signals() -> list[SocialSignal]:
    return []


def _empty_research_findings() -> list[ResearchFinding]:
    return []


def _empty_entity_dossiers() -> list[EntityDossier]:
    return []


def _empty_memory_update() -> dict[str, object]:
    return {}


@dataclass(frozen=True)
class ResearchPipelineResult:
    """Result of one sidecar pipeline pass."""

    state: ResearchSidecarState
    world_state: WorldStateSnapshot | None = None
    raw_evidence: list[RawEvidenceRecord] = field(
        default_factory=_empty_raw_evidence_records
    )
    macro_events: list[MacroEvent] = field(default_factory=_empty_macro_events)
    social_signals: list[SocialSignal] = field(default_factory=_empty_social_signals)
    findings: list[ResearchFinding] = field(default_factory=_empty_research_findings)
    dossiers: list[EntityDossier] = field(default_factory=_empty_entity_dossiers)
    memory_update: dict[str, object] = field(default_factory=_empty_memory_update)


@dataclass(frozen=True)
class ContractPayloadItems:
    raw_evidence: list[RawEvidenceRecord]
    macro_events: list[MacroEvent]
    social_signals: list[SocialSignal]
    findings: list[ResearchFinding]
    dossiers: list[EntityDossier]
    attributions: list[DataSourceAttribution]


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


def summarize_provider_health(
    provider_health: list[ResearchProviderHealth],
) -> dict[str, int]:
    """Count provider health by freshness status for dashboard consumers."""

    summary = {"fresh": 0, "stale": 0, "unknown": 0, "missing": 0}
    for item in provider_health:
        summary[item.freshness] = summary.get(item.freshness, 0) + 1
    return summary


def research_world_state_summary(
    *,
    raw_evidence_count: int,
    macro_event_count: int,
    social_signal_count: int,
    finding_count: int,
) -> str:
    if any(
        count > 0
        for count in (
            raw_evidence_count,
            macro_event_count,
            social_signal_count,
            finding_count,
        )
    ):
        return (
            "Research sidecar assembled normalized evidence packets: "
            f"raw_evidence={raw_evidence_count}, macro_events={macro_event_count}, "
            f"social_signals={social_signal_count}, findings={finding_count}. "
            "Trade-memory writes remain disabled."
        )
    return (
        "Research sidecar foundation ran with provider scaffolds only; "
        "no live evidence or synthesized findings were produced."
    )
