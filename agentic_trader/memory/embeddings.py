import hashlib
import re
from math import sqrt

from agentic_trader.schemas import MarketSnapshot, RunArtifacts

VECTOR_DIMENSIONS = 64
_TOKEN_RE = re.compile(r"[a-z0-9_.:-]+")


def _normalize(values: list[float]) -> list[float]:
    norm = sqrt(sum(value * value for value in values))
    if norm <= 0:
        return values
    return [round(value / norm, 6) for value in values]


def embed_text(text: str, *, dimensions: int = VECTOR_DIMENSIONS) -> list[float]:
    vector = [0.0] * dimensions
    tokens = _TOKEN_RE.findall(text.lower())
    if not tokens:
        return vector
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        weight = 1.0 + (min(len(token), 16) / 16.0)
        vector[index] += sign * weight
    return _normalize(vector)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return max(0.0, min(1.0, sum(a * b for a, b in zip(left, right))))


def snapshot_memory_text(snapshot: MarketSnapshot) -> str:
    return " ".join(
        [
            snapshot.symbol,
            snapshot.interval,
            f"mtf:{snapshot.mtf_alignment}",
            f"htf:{snapshot.higher_timeframe}",
            f"rsi:{snapshot.rsi_14:.2f}",
            f"return5:{snapshot.return_5:.4f}",
            f"return20:{snapshot.return_20:.4f}",
            f"volatility:{snapshot.volatility_20:.4f}",
        ]
    )


def build_memory_document(artifacts: RunArtifacts) -> str:
    snapshot = artifacts.snapshot
    return " | ".join(
        [
            snapshot_memory_text(snapshot),
            f"regime:{artifacts.regime.regime}",
            f"direction:{artifacts.regime.direction_bias}",
            f"strategy:{artifacts.strategy.strategy_family}",
            f"action:{artifacts.strategy.action}",
            f"manager:{artifacts.manager.action_bias}",
            f"review:{artifacts.review.summary}",
            f"warnings:{','.join(artifacts.review.warnings) or 'none'}",
        ]
    )


def embed_artifacts(artifacts: RunArtifacts) -> list[float]:
    return embed_text(build_memory_document(artifacts))


def embed_snapshot(snapshot: MarketSnapshot) -> list[float]:
    return embed_text(snapshot_memory_text(snapshot))
