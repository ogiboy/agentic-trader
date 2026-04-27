from math import fabs
from typing import Literal

from agentic_trader.memory.embeddings import cosine_similarity, embed_snapshot
from agentic_trader.schemas import HistoricalMemoryMatch, MarketSnapshot, RunRecord
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


def retrieve_similar_memories(
    db: TradingDatabase,
    snapshot: MarketSnapshot,
    *,
    limit: int = 5,
    candidate_limit: int = 200,
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
            )
        )
    ranked.sort(key=lambda item: item.similarity_score, reverse=True)
    return ranked[:limit]
