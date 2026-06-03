from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from agentic_trader.schema_models.market import (
    FundamentalFeatureSet,
    MacroContext,
    SymbolIdentity,
    TechnicalFeatureSet,
)
from agentic_trader.schema_models.types import (
    DataProviderKind,
    DataSourceRole,
    DisclosureKind,
    FreshnessStatus,
    NewsClassification,
)


class ProviderMetadata(BaseModel):
    provider_id: str
    name: str
    provider_type: DataProviderKind
    role: DataSourceRole
    priority: int = 100
    enabled: bool = True
    requires_network: bool = False
    notes: list[str] = Field(default_factory=list[str])


class DataSourceAttribution(BaseModel):
    source_name: str
    provider_type: DataProviderKind
    source_role: DataSourceRole
    fetched_at: str | None = None
    freshness: FreshnessStatus = "unknown"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    completeness: float = Field(default=0.0, ge=0.0, le=1.0)
    notes: list[str] = Field(default_factory=list[str])


class MarketDataSnapshot(BaseModel):
    symbol_identity: SymbolIdentity
    interval: str
    lookback: str | None = None
    rows: int = 0
    columns: list[str] = Field(default_factory=list[str])
    window_start: str | None = None
    window_end: str | None = None
    last_close: float | None = None
    attribution: DataSourceAttribution
    missing_fields: list[str] = Field(default_factory=list[str])
    summary: str = ""


class FundamentalSnapshot(BaseModel):
    symbol_identity: SymbolIdentity
    revenue_growth: float | None = None
    profitability_stability: float | None = Field(default=None, ge=0.0, le=1.0)
    cash_flow_alignment: float | None = Field(default=None, ge=0.0, le=1.0)
    debt_risk: float | None = Field(default=None, ge=0.0, le=1.0)
    fx_exposure: str = "unknown"
    reinvestment_potential: float | None = Field(default=None, ge=0.0, le=1.0)
    attribution: DataSourceAttribution
    missing_fields: list[str] = Field(default_factory=list[str])
    summary: str = ""


class EvidenceInferenceBreakdown(BaseModel):
    evidence: list[str] = Field(default_factory=list[str])
    inference: list[str] = Field(default_factory=list[str])
    uncertainty: list[str] = Field(default_factory=list[str])


class NewsEvent(BaseModel):
    symbol: str
    title: str
    category: NewsClassification
    source: str
    published_at: str | None = None
    summary: str = ""
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    url: str | None = None
    attribution: DataSourceAttribution
    observed_at: str | None = None
    last_verified_at: str | None = None
    stale_after: str | None = None
    evidence_vs_inference: EvidenceInferenceBreakdown = Field(
        default_factory=EvidenceInferenceBreakdown
    )
    missing_fields: list[str] = Field(default_factory=list[str])


class DisclosureEvent(BaseModel):
    symbol: str
    region: str
    disclosure_type: DisclosureKind = "other"
    title: str
    published_at: str | None = None
    summary: str = ""
    url: str | None = None
    attribution: DataSourceAttribution
    observed_at: str | None = None
    last_verified_at: str | None = None
    stale_after: str | None = None
    evidence_vs_inference: EvidenceInferenceBreakdown = Field(
        default_factory=EvidenceInferenceBreakdown
    )
    missing_fields: list[str] = Field(default_factory=list[str])


class MacroSnapshot(BaseModel):
    region: str
    currency: str
    rates_bias: Literal["tailwind", "neutral", "headwind", "unknown"] = "unknown"
    inflation_bias: Literal["tailwind", "neutral", "headwind", "unknown"] = "unknown"
    fx_risk: Literal["low", "medium", "high", "unknown"] = "unknown"
    sector_risk_score: float | None = Field(default=None, ge=0.0, le=1.0)
    political_risk_score: float | None = Field(default=None, ge=0.0, le=1.0)
    attribution: DataSourceAttribution
    missing_fields: list[str] = Field(default_factory=list[str])
    summary: str = ""


class CanonicalAnalysisSnapshot(BaseModel):
    symbol_identity: SymbolIdentity
    generated_at: str
    market: MarketDataSnapshot
    fundamental: FundamentalSnapshot
    news_events: list[NewsEvent] = Field(default_factory=list[NewsEvent])
    disclosures: list[DisclosureEvent] = Field(default_factory=list[DisclosureEvent])
    macro: MacroSnapshot
    source_attributions: list[DataSourceAttribution] = Field(
        default_factory=list[DataSourceAttribution]
    )
    missing_sections: list[str] = Field(default_factory=list[str])
    completeness_score: float = Field(default=0.0, ge=0.0, le=1.0)
    summary: str = ""


class DecisionFeatureBundle(BaseModel):
    symbol_identity: SymbolIdentity
    technical: TechnicalFeatureSet
    fundamental: FundamentalFeatureSet
    macro: MacroContext
