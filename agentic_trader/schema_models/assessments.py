from __future__ import annotations

from typing import Literal, cast

from pydantic import BaseModel, Field, model_validator

from agentic_trader.schema_models.market import MarketSessionStatus, MarketSnapshot
from agentic_trader.schema_models.memory import (
    ConfidenceCalibration,
    HistoricalMemoryMatch,
    SharedMemoryEntry,
)
from agentic_trader.schema_models.preferences import InvestmentPreferences
from agentic_trader.schema_models.providers import (
    CanonicalAnalysisSnapshot,
    DecisionFeatureBundle,
    EvidenceInferenceBreakdown,
)
from agentic_trader.schema_models.runtime import ServiceStateSnapshot
from agentic_trader.schema_models.trading import PortfolioSnapshot
from agentic_trader.schema_models.types import AgentRole, AnalysisSignal


class FundamentalAssessment(BaseModel):
    growth_quality: AnalysisSignal = "neutral"
    profitability_quality: AnalysisSignal = "neutral"
    cash_flow_quality: AnalysisSignal = "neutral"
    balance_sheet_quality: AnalysisSignal = "neutral"
    fx_risk: Literal["low", "medium", "high", "unknown"] = "unknown"
    business_quality: AnalysisSignal = "neutral"
    macro_fit: AnalysisSignal = "neutral"
    forward_outlook: AnalysisSignal = "neutral"
    red_flags: list[str] = Field(default_factory=list[str])
    strengths: list[str] = Field(default_factory=list[str])
    evidence_vs_inference: EvidenceInferenceBreakdown = Field(
        default_factory=EvidenceInferenceBreakdown
    )
    overall_bias: AnalysisSignal = "neutral"
    revenue_growth_quality: AnalysisSignal = "neutral"
    debt_quality: AnalysisSignal = "neutral"
    fx_exposure_risk: Literal["low", "medium", "high", "unknown"] = "unknown"
    reinvestment_quality: AnalysisSignal = "neutral"
    overall_signal: AnalysisSignal = "neutral"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    summary: str = "Fundamental evidence is not available yet."
    risk_flags: list[str] = Field(default_factory=list[str])
    source: Literal["llm", "fallback"] = "fallback"
    fallback_reason: str | None = None

    @model_validator(mode="after")
    def sync_legacy_fields(self) -> "FundamentalAssessment":
        """
        Synchronize legacy and current field names so both representations remain consistent after model initialization.

        Copies values between legacy and new field pairs when only one of each pair was provided, ensuring fields such as `growth_quality`/`revenue_growth_quality`, `balance_sheet_quality`/`debt_quality`, `fx_risk`/`fx_exposure_risk`, `overall_bias`/`overall_signal`, and `red_flags`/`risk_flags` are aligned.

        Returns:
                self (FundamentalAssessment): The model instance with synchronized fields.
        """
        fields = set(self.model_fields_set)

        def _sync_pair(current: str, legacy: str) -> None:
            current_present = current in fields
            legacy_present = legacy in fields
            current_value = getattr(self, current)
            legacy_value = getattr(self, legacy)

            def _copy_mutable(value: object) -> object:
                return (
                    list(cast(list[object], value))
                    if isinstance(value, list)
                    else value
                )

            if current_present and legacy_present and current_value != legacy_value:
                raise ValueError(
                    f"Conflicting fundamental assessment fields: {current} != {legacy}."
                )
            if not current_present and legacy_present:
                setattr(self, current, _copy_mutable(legacy_value))
            elif not legacy_present and current_present:
                setattr(self, legacy, _copy_mutable(current_value))

        _sync_pair("growth_quality", "revenue_growth_quality")
        _sync_pair("balance_sheet_quality", "debt_quality")
        _sync_pair("fx_risk", "fx_exposure_risk")
        _sync_pair("overall_bias", "overall_signal")
        _sync_pair("red_flags", "risk_flags")
        return self


class MacroAssessment(BaseModel):
    macro_signal: AnalysisSignal = "neutral"
    sector_risk: Literal["low", "medium", "high", "unknown"] = "unknown"
    news_risk: Literal["low", "medium", "high", "unknown"] = "unknown"
    fx_risk: Literal["low", "medium", "high", "unknown"] = "unknown"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    summary: str = "Macro and news evidence is not available yet."
    risk_flags: list[str] = Field(default_factory=list[str])
    source: Literal["llm", "fallback"] = "fallback"
    fallback_reason: str | None = None


class AgentContext(BaseModel):
    role: AgentRole
    model_name: str
    snapshot: MarketSnapshot
    canonical_snapshot: CanonicalAnalysisSnapshot | None = None
    decision_features: DecisionFeatureBundle | None = None
    preferences: InvestmentPreferences
    portfolio: PortfolioSnapshot
    market_session: MarketSessionStatus | None = None
    service_state: "ServiceStateSnapshot | None" = None
    recent_runs: list[str] = Field(default_factory=list[str])
    memory_notes: list[str] = Field(default_factory=list[str])
    retrieved_memories: list[str] = Field(default_factory=list[str])
    retrieval_explanations: list["HistoricalMemoryMatch"] = Field(
        default_factory=list["HistoricalMemoryMatch"]
    )
    calibration: "ConfidenceCalibration | None" = None
    shared_memory_bus: list["SharedMemoryEntry"] = Field(
        default_factory=list["SharedMemoryEntry"]
    )
    tool_outputs: list[str] = Field(default_factory=list[str])
    upstream_context: dict[str, str] = Field(default_factory=dict[str, str])
