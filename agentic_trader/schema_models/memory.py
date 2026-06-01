from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from agentic_trader.schema_models.types import FreshnessStatus

class ConfidenceCalibration(BaseModel):
    sample_size: int = 0
    closed_trades: int = 0
    win_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    average_pnl: float = 0.0
    confidence_multiplier: float = Field(default=1.0, gt=0.0, le=1.0)
    notes: list[str] = Field(default_factory=list[str])

class SharedMemoryEntry(BaseModel):
    role: str
    summary: str
    payload_json: str

class MemoryRetrievalExplanation(BaseModel):
    eligibility_reason: str = "candidate_run_record"
    score_components: dict[str, float] = Field(default_factory=dict[str, float])
    as_of: str | None = None
    freshness: FreshnessStatus = "unknown"
    outcome_tag: str = "unknown"
    regime_alignment: str = "unknown"
    strategy_alignment: str = "unknown"
    diversity_bucket: str = "unknown"
    notes: list[str] = Field(default_factory=list[str])

class HistoricalMemoryMatch(BaseModel):
    run_id: str
    created_at: str
    symbol: str
    similarity_score: float = Field(ge=0.0)
    heuristic_score: float | None = None
    vector_score: float | None = None
    retrieval_source: Literal["heuristic", "vector", "hybrid"] = "heuristic"
    regime: str
    strategy_family: str
    manager_bias: str
    approved: bool
    summary: str
    explanation: "MemoryRetrievalExplanation" = Field(
        default_factory=lambda: MemoryRetrievalExplanation()
    )
