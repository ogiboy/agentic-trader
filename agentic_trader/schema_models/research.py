from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from agentic_trader.schema_models.providers import (
    DataSourceAttribution,
    EvidenceInferenceBreakdown,
)
from agentic_trader.schema_models.types import (
    DataProviderKind,
    DataSourceRole,
    FreshnessStatus,
    ResearchCycleControlAction,
    ResearchCycleControlStatus,
    ResearchEvidenceKind,
    ResearchMode,
    ResearchSignalDirection,
)

class ResearchTimedRecord(BaseModel):
    source_attributions: list[DataSourceAttribution] = Field(
        default_factory=list[DataSourceAttribution]
    )
    observed_at: str
    last_verified_at: str | None = None
    stale_after: str | None = None
    evidence_vs_inference: EvidenceInferenceBreakdown = Field(
        default_factory=EvidenceInferenceBreakdown
    )
    missing_fields: list[str] = Field(default_factory=list[str])

    def is_stale(self, reference_time: str | None = None) -> bool:
        if self.stale_after is None:
            return False
        stale_after = datetime.fromisoformat(self.stale_after.replace("Z", "+00:00"))
        reference = (
            datetime.fromisoformat(reference_time.replace("Z", "+00:00"))
            if reference_time
            else datetime.now(UTC)
        )
        return stale_after <= reference

class RawEvidenceRecord(ResearchTimedRecord):
    record_id: str
    source_kind: ResearchEvidenceKind
    source_name: str
    title: str
    symbol: str | None = None
    entity_name: str | None = None
    region: str | None = None
    url: str | None = None
    normalized_summary: str = ""
    source_payload_ref: str | None = None

class MacroEvent(ResearchTimedRecord):
    event_id: str
    region: str
    currency: str | None = None
    title: str
    summary: str = ""
    direction: ResearchSignalDirection = "unknown"
    affected_channels: list[str] = Field(default_factory=list[str])

class SocialSignal(ResearchTimedRecord):
    signal_id: str
    platform: str
    query: str
    symbol: str | None = None
    entity_name: str | None = None
    summary: str = ""
    direction: ResearchSignalDirection = "unknown"
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    source_count: int = Field(default=0, ge=0)

class ResearchFinding(ResearchTimedRecord):
    finding_id: str
    subject: str
    title: str
    thesis: str = ""
    verified_facts: list[str] = Field(default_factory=list[str])
    inferences: list[str] = Field(default_factory=list[str])
    unknowns: list[str] = Field(default_factory=list[str])
    contradictions: list[str] = Field(default_factory=list[str])
    market_channels: list[str] = Field(default_factory=list[str])
    horizon: str = "unknown"
    watch_next: list[str] = Field(default_factory=list[str])
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

class EntityDossier(ResearchTimedRecord):
    entity_id: str
    entity_name: str
    symbol: str | None = None
    region: str | None = None
    timeline: list[str] = Field(default_factory=list[str])
    current_thesis: str = ""
    key_findings: list[ResearchFinding] = Field(default_factory=list[ResearchFinding])
    contradiction_file: list[str] = Field(default_factory=list[str])
    source_diversity_score: float = Field(default=0.0, ge=0.0, le=1.0)

class WorldStateSnapshot(ResearchTimedRecord):
    snapshot_id: str
    mode: ResearchMode = "off"
    generated_at: str
    watched_symbols: list[str] = Field(default_factory=list[str])
    entity_dossiers: list[EntityDossier] = Field(default_factory=list[EntityDossier])
    macro_events: list[MacroEvent] = Field(default_factory=list[MacroEvent])
    social_signals: list[SocialSignal] = Field(default_factory=list[SocialSignal])
    findings: list[ResearchFinding] = Field(default_factory=list[ResearchFinding])
    summary: str = ""

class ResearchProviderHealth(BaseModel):
    provider_id: str
    name: str
    provider_type: DataProviderKind
    enabled: bool
    requires_network: bool = False
    source_role: DataSourceRole
    freshness: FreshnessStatus = "unknown"
    last_successful_update_at: str | None = None
    message: str = ""
    notes: list[str] = Field(default_factory=list[str])

class ResearchSidecarState(BaseModel):
    mode: ResearchMode = "off"
    enabled: bool = False
    backend: str = "noop"
    status: Literal["disabled", "idle", "running", "completed", "failed"] = "disabled"
    updated_at: str
    last_started_at: str | None = None
    last_successful_update_at: str | None = None
    last_error: str | None = None
    watched_symbols: list[str] = Field(default_factory=list[str])
    provider_health: list[ResearchProviderHealth] = Field(
        default_factory=list[ResearchProviderHealth]
    )
    source_health_summary: dict[str, int] = Field(default_factory=dict[str, int])

class ResearchCycleOperatorControl(BaseModel):
    status: ResearchCycleControlStatus = "running"
    requested_action: ResearchCycleControlAction = "idle"
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_by: str = "operator"
    reason: str | None = None
    trigger_now_requested: bool = False
    trigger_requested_at: str | None = None
    paused_at: str | None = None
    resumed_at: str | None = None

class ResearchDigestReplayRecord(BaseModel):
    artifact_id: str
    generated_at: str
    snapshot_id: str | None = None
    mode: ResearchMode
    backend: str = "noop"
    watched_symbols: list[str] = Field(default_factory=list[str])
    digest: dict[str, object] = Field(default_factory=dict[str, object])
    executions: list[dict[str, object]] = Field(default_factory=list[dict[str, object]])
    execution_policy: dict[str, bool] = Field(default_factory=dict[str, bool])
    operator_control: ResearchCycleOperatorControl
    replay_notes: list[str] = Field(default_factory=list[str])

class ResearchSnapshotRecord(BaseModel):
    snapshot_id: str
    created_at: str
    mode: ResearchMode
    backend: str = "noop"
    status: Literal["disabled", "idle", "running", "completed", "failed"] = "disabled"
    watched_symbols: list[str] = Field(default_factory=list[str])
    raw_evidence: list[RawEvidenceRecord] = Field(
        default_factory=list[RawEvidenceRecord]
    )
    world_state: WorldStateSnapshot | None = None
    state: ResearchSidecarState
    memory_update: dict[str, object] = Field(default_factory=dict[str, object])
