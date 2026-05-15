from datetime import UTC, datetime
from math import fabs
from typing import Literal

from agentic_trader.memory.embeddings import cosine_similarity, embed_snapshot
from agentic_trader.schemas import (
    FreshnessStatus,
    HistoricalMemoryMatch,
    MarketSnapshot,
    MemoryRetrievalExplanation,
    RunRecord,
)
from agentic_trader.storage.db import TradingDatabase


def _bounded_similarity(left: float, right: float, *, scale: float) -> float:
    if scale <= 0:
        return 1.0 if left == right else 0.0
    return max(0.0, 1.0 - (fabs(left - right) / scale))


def _trend_signature(snapshot: MarketSnapshot) -> int:
    if snapshot.last_close > snapshot.ema_20 > snapshot.ema_50:
        return 1
    if snapshot.last_close < snapshot.ema_20 < snapshot.ema_50:
        return -1
    return 0


def _snapshot_similarity(current: MarketSnapshot, historical: MarketSnapshot) -> float:
    components = [
        _bounded_similarity(current.rsi_14, historical.rsi_14, scale=50.0),
        _bounded_similarity(current.return_5, historical.return_5, scale=0.2),
        _bounded_similarity(current.return_20, historical.return_20, scale=0.4),
        _bounded_similarity(current.volatility_20, historical.volatility_20, scale=0.2),
        _bounded_similarity(
            current.volume_ratio_20, historical.volume_ratio_20, scale=1.5
        ),
        _bounded_similarity(
            current.atr_14 / max(current.last_close, 1e-9),
            historical.atr_14 / max(historical.last_close, 1e-9),
            scale=0.1,
        ),
    ]
    trend_bonus = (
        0.1 if _trend_signature(current) == _trend_signature(historical) else 0.0
    )
    return min(1.0, (sum(components) / len(components)) + trend_bonus)


def _memory_freshness(as_of: str | None) -> FreshnessStatus:
    if not as_of:
        return "unknown"
    try:
        observed = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
    except ValueError:
        return "unknown"
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=UTC)
    age_days = (datetime.now(UTC) - observed).days
    return "fresh" if age_days <= 365 else "stale"


def _trend_alignment(current: MarketSnapshot, historical: MarketSnapshot) -> str:
    current_signature = _trend_signature(current)
    historical_signature = _trend_signature(historical)
    if current_signature == historical_signature:
        return "same_trend_signature"
    return "different_trend_signature"


def _strategy_alignment(
    *,
    requested_strategy: str | None,
    candidate_strategy: str,
) -> str:
    if requested_strategy is None:
        return "current_strategy_unknown"
    if requested_strategy == candidate_strategy:
        return "same_strategy_family"
    return "different_strategy_family"


def _diversity_bucket(candidate: RunRecord) -> str:
    outcome = "approved" if candidate.approved else "not_approved"
    return (
        f"symbol={candidate.symbol}|"
        f"regime={candidate.artifacts.regime.regime}|"
        f"strategy={candidate.artifacts.strategy.strategy_family}|"
        f"outcome={outcome}"
    )


def _retrieval_explanation(
    *,
    current: MarketSnapshot,
    candidate: RunRecord,
    similarity: float,
    heuristic_similarity: float,
    vector_similarity: float | None,
    requested_strategy: str | None,
    embedding_present: bool,
) -> MemoryRetrievalExplanation:
    historical = candidate.artifacts.snapshot
    as_of = historical.as_of
    score_components = {
        "final": round(similarity, 4),
        "heuristic": round(heuristic_similarity, 4),
    }
    notes = [
        "embedding_present" if embedding_present else "embedding_missing",
        "as_of_from_market_snapshot" if as_of else "as_of_missing_legacy_snapshot",
    ]
    eligibility_reason = "hybrid_similarity_to_current_snapshot"
    if vector_similarity is None:
        eligibility_reason = "heuristic_similarity_to_current_snapshot"
    else:
        score_components["vector"] = round(vector_similarity, 4)
        score_components["heuristic_weight"] = 0.45
        score_components["vector_weight"] = 0.55
    return MemoryRetrievalExplanation(
        eligibility_reason=eligibility_reason,
        score_components=score_components,
        as_of=as_of,
        freshness=_memory_freshness(as_of),
        outcome_tag="approved_trade" if candidate.approved else "not_approved",
        regime_alignment=_trend_alignment(current, historical),
        strategy_alignment=_strategy_alignment(
            requested_strategy=requested_strategy,
            candidate_strategy=candidate.artifacts.strategy.strategy_family,
        ),
        diversity_bucket=_diversity_bucket(candidate),
        notes=notes,
    )


def retrieve_similar_memories(
    db: TradingDatabase,
    snapshot: MarketSnapshot,
    *,
    limit: int = 5,
    candidate_limit: int = 200,
    strategy_family: str | None = None,
) -> list[HistoricalMemoryMatch]:
    candidates: list[RunRecord] = db.list_run_records(limit=candidate_limit)
    vector_rows = {
        run_id: embedding
        for run_id, _created_at, _symbol, embedding, _document in db.list_memory_vectors(
            limit=candidate_limit
        )
    }
    current_embedding = embed_snapshot(snapshot)
    ranked: list[HistoricalMemoryMatch] = []
    for candidate in candidates:
        historical = candidate.artifacts.snapshot
        heuristic_similarity = _snapshot_similarity(snapshot, historical)
        vector_similarity = None
        retrieval_source: Literal["heuristic", "vector", "hybrid"] = "heuristic"
        similarity = heuristic_similarity
        embedding = vector_rows.get(candidate.run_id)
        embedding_present = embedding is not None
        if embedding is not None:
            vector_similarity = cosine_similarity(current_embedding, embedding)
            similarity = (heuristic_similarity * 0.45) + (vector_similarity * 0.55)
            retrieval_source = "hybrid"
        ranked.append(
            HistoricalMemoryMatch(
                run_id=candidate.run_id,
                created_at=candidate.created_at,
                symbol=candidate.symbol,
                similarity_score=round(similarity, 4),
                heuristic_score=round(heuristic_similarity, 4),
                vector_score=(
                    round(vector_similarity, 4)
                    if vector_similarity is not None
                    else None
                ),
                retrieval_source=retrieval_source,
                regime=candidate.artifacts.regime.regime,
                strategy_family=candidate.artifacts.strategy.strategy_family,
                manager_bias=candidate.artifacts.manager.action_bias,
                approved=candidate.approved,
                summary=candidate.artifacts.review.summary,
                explanation=_retrieval_explanation(
                    current=snapshot,
                    candidate=candidate,
                    similarity=similarity,
                    heuristic_similarity=heuristic_similarity,
                    vector_similarity=vector_similarity,
                    requested_strategy=strategy_family,
                    embedding_present=embedding_present,
                ),
            )
        )
    ranked.sort(key=lambda item: item.similarity_score, reverse=True)
    return ranked[:limit]
