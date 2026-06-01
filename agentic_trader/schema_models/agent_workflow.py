from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from agentic_trader.schema_models.types import (
    AgentProfile,
    AgentTone,
    BehaviorPreset,
    CoordinatorFocus,
    ExecutionSide,
    InterventionStyle,
    RiskProfile,
    RuntimeMode,
    StrictnessPreset,
    TradeStyle,
)


class ResearchCoordinatorBrief(BaseModel):
    market_focus: CoordinatorFocus
    priority_signals: list[str] = Field(default_factory=list[str])
    caution_flags: list[str] = Field(default_factory=list[str])
    summary: str
    source: Literal["llm", "fallback"] = "llm"
    fallback_reason: str | None = None


class ManagerConflict(BaseModel):
    conflict_type: Literal["focus", "action", "approval", "confidence", "size"]
    severity: Literal["low", "medium", "high"] = "medium"
    summary: str
    specialist_view: str
    manager_resolution: str


class ManagerDecision(BaseModel):
    approved: bool
    action_bias: ExecutionSide
    confidence_cap: float = Field(ge=0.0, le=1.0)
    size_multiplier: float = Field(gt=0.0, le=1.0)
    rationale: str
    escalation_flags: list[str] = Field(default_factory=list[str])
    override_applied: bool = False
    conflicts: list["ManagerConflict"] = Field(default_factory=list["ManagerConflict"])
    resolution_notes: list[str] = Field(default_factory=list[str])
    source: Literal["llm", "fallback"] = "llm"
    fallback_reason: str | None = None


class SpecialistConsensus(BaseModel):
    alignment_level: Literal["aligned", "mixed", "conflicted"] = "mixed"
    summary: str = ""
    supporting_roles: list[str] = Field(default_factory=list[str])
    dissenting_roles: list[str] = Field(default_factory=list[str])
    reasons: list[str] = Field(default_factory=list[str])


class ReviewNote(BaseModel):
    summary: str
    strengths: list[str] = Field(default_factory=list[str])
    warnings: list[str] = Field(default_factory=list[str])
    next_checks: list[str] = Field(default_factory=list[str])


class PreferenceUpdate(BaseModel):
    regions: list[str] | None = None
    exchanges: list[str] | None = None
    currencies: list[str] | None = None
    sectors: list[str] | None = None
    risk_profile: RiskProfile | None = None
    trade_style: TradeStyle | None = None
    behavior_preset: BehaviorPreset | None = None
    agent_profile: AgentProfile | None = None
    agent_tone: AgentTone | None = None
    strictness_preset: StrictnessPreset | None = None
    intervention_style: InterventionStyle | None = None
    notes: str | None = None


class OperatorInstruction(BaseModel):
    summary: str
    should_update_preferences: bool = False
    preference_update: PreferenceUpdate = Field(default_factory=PreferenceUpdate)
    requires_confirmation: bool = True
    rationale: str


class RuntimeModeTransitionCheck(BaseModel):
    name: str
    passed: bool
    details: str
    blocking: bool = True


class RuntimeModeTransitionPlan(BaseModel):
    current_mode: RuntimeMode
    target_mode: RuntimeMode
    allowed: bool
    checks: list[RuntimeModeTransitionCheck] = Field(
        default_factory=list[RuntimeModeTransitionCheck]
    )
    summary: str
