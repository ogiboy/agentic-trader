from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from agentic_trader.schema_models.types import (
    MarketSessionState,
    MTFAlignment,
    NewsClassification,
    TrendVote,
)


class MarketSessionStatus(BaseModel):
    symbol: str
    venue: str
    asset_class: Literal["equity", "crypto"]
    timezone: str
    session_state: MarketSessionState
    tradable_now: bool
    note: str


class MarketContextHorizon(BaseModel):
    horizon_bars: int
    available_bars: int
    return_pct: float | None = None
    volatility_pct: float | None = None
    max_drawdown_pct: float | None = None
    trend_vote: TrendVote = "insufficient"
    support: float | None = None
    resistance: float | None = None
    range_position: float | None = Field(default=None, ge=0.0, le=1.0)
    atr_pct: float | None = None
    volume_ratio: float | None = None


class MarketContextPack(BaseModel):
    symbol: str
    interval: str
    lookback: str | None = None
    interval_semantics: str
    window_start: str | None = None
    window_end: str | None = None
    bars_required: int = 60
    bars_expected: int | None = None
    bars_analyzed: int
    coverage_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    higher_timeframe: str
    higher_timeframe_used: bool
    horizons: list[MarketContextHorizon] = Field(
        default_factory=list[MarketContextHorizon]
    )
    data_quality_flags: list[str] = Field(default_factory=list[str])
    anomaly_flags: list[str] = Field(default_factory=list[str])
    summary: str = ""


class MarketSnapshot(BaseModel):
    symbol: str
    interval: str
    as_of: str | None = None
    last_close: float
    ema_20: float
    ema_50: float
    atr_14: float
    rsi_14: float
    volatility_20: float
    return_5: float
    return_20: float
    volume_ratio_20: float
    higher_timeframe: str = "same_as_base"
    htf_last_close: float = 0.0
    htf_ema_20: float = 0.0
    htf_ema_50: float = 0.0
    htf_rsi_14: float = 50.0
    htf_return_5: float = 0.0
    mtf_alignment: MTFAlignment = "mixed"
    mtf_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    bars_analyzed: int
    context_pack: MarketContextPack | None = None


class SymbolIdentity(BaseModel):
    symbol: str
    exchange: str | None = None
    currency: str = "USD"
    region: str = "US"
    asset_class: Literal["equity", "crypto", "fx", "unknown"] = "equity"


class TechnicalFeatureSet(BaseModel):
    symbol: str
    interval: str
    as_of: str | None = None
    price_anchor: float | None = None
    returns_by_window: dict[str, float | None] = Field(
        default_factory=dict[str, float | None]
    )
    volatility_20: float | None = None
    max_drawdown_pct: float | None = None
    support: float | None = None
    resistance: float | None = None
    trend_classification: TrendVote = "insufficient"
    momentum_indicators: dict[str, float] = Field(default_factory=dict[str, float])
    context_summary: str = ""
    data_quality_flags: list[str] = Field(default_factory=list[str])


class FundamentalFeatureSet(BaseModel):
    symbol: str
    as_of: str | None = None
    revenue_growth: float | None = None
    profitability_stability: float | None = Field(default=None, ge=0.0, le=1.0)
    cash_flow_alignment: float | None = Field(default=None, ge=0.0, le=1.0)
    debt_risk: float | None = Field(default=None, ge=0.0, le=1.0)
    fx_exposure: str = "unknown"
    reinvestment_potential: float | None = Field(default=None, ge=0.0, le=1.0)
    data_sources: list[str] = Field(default_factory=list[str])
    quality_flags: list[str] = Field(default_factory=list[str])
    summary: str = ""


class StructuredNewsSignal(BaseModel):
    symbol: str | None = None
    title: str
    category: NewsClassification
    source: str
    published_at: str | None = None
    summary: str
    relevance_score: float = Field(ge=0.0, le=1.0)


class MacroContext(BaseModel):
    symbol: str
    as_of: str | None = None
    region: str = "US"
    currency: str = "USD"
    sector: str | None = None
    rates_bias: Literal["tailwind", "neutral", "headwind", "unknown"] = "unknown"
    inflation_bias: Literal["tailwind", "neutral", "headwind", "unknown"] = "unknown"
    fx_risk: Literal["low", "medium", "high", "unknown"] = "unknown"
    sector_risk_score: float | None = Field(default=None, ge=0.0, le=1.0)
    political_risk_score: float | None = Field(default=None, ge=0.0, le=1.0)
    news_signals: list[StructuredNewsSignal] = Field(
        default_factory=list[StructuredNewsSignal]
    )
    data_sources: list[str] = Field(default_factory=list[str])
    summary: str = ""
