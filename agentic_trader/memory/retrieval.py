from math import fabs

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
    ranked: list[HistoricalMemoryMatch] = []
    for candidate in candidates:
        historical = candidate.artifacts.snapshot
        similarity = _snapshot_similarity(snapshot, historical)
        ranked.append(
            HistoricalMemoryMatch(
                run_id=candidate.run_id,
                created_at=candidate.created_at,
                symbol=candidate.symbol,
                similarity_score=round(similarity, 4),
                regime=candidate.artifacts.regime.regime,
                strategy_family=candidate.artifacts.strategy.strategy_family,
                manager_bias=candidate.artifacts.manager.action_bias,
                approved=candidate.approved,
                summary=candidate.artifacts.review.summary,
            )
        )
    ranked.sort(key=lambda item: item.similarity_score, reverse=True)
    return ranked[:limit]
