from __future__ import annotations

from pydantic import BaseModel, Field

from agentic_trader.schema_models.types import (
    AgentProfile,
    AgentTone,
    BehaviorPreset,
    InterventionStyle,
    RiskProfile,
    StrictnessPreset,
    TradeStyle,
)


class LLMHealthStatus(BaseModel):
    provider: str
    base_url: str
    model_name: str
    service_reachable: bool
    model_available: bool
    generation_available: bool | None = None
    generation_message: str | None = None
    message: str


class InvestmentPreferences(BaseModel):
    regions: list[str] = Field(default_factory=lambda: ["US"])
    exchanges: list[str] = Field(default_factory=lambda: ["NASDAQ", "NYSE"])
    currencies: list[str] = Field(default_factory=lambda: ["USD"])
    sectors: list[str] = Field(default_factory=list[str])
    risk_profile: RiskProfile = "balanced"
    trade_style: TradeStyle = "swing"
    behavior_preset: BehaviorPreset = "balanced_core"
    agent_profile: AgentProfile = "explanatory"
    agent_tone: AgentTone = "supportive"
    strictness_preset: StrictnessPreset = "standard"
    intervention_style: InterventionStyle = "balanced"
    notes: str = ""
