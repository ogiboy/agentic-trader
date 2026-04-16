import hashlib
import re
from math import sqrt

from agentic_trader.schemas import MarketSnapshot, RunArtifacts

VECTOR_DIMENSIONS = 64
EMBEDDING_PROVIDER = "local_hashing"
EMBEDDING_MODEL_NAME = "agentic-hash-v1"
EMBEDDING_MODEL_VERSION = "1"
_TOKEN_RE = re.compile(r"[a-z0-9_.:-]+")


def _normalize(values: list[float]) -> list[float]:
    norm = sqrt(sum(value * value for value in values))
    if norm <= 0:
        return values
    return [round(value / norm, 6) for value in values]


def embed_text(text: str, *, dimensions: int = VECTOR_DIMENSIONS) -> list[float]:
    """
    Create a deterministic fixed-size embedding vector for the given text using a local hashing scheme.
    
    The function converts the input text to tokens, derives a consistent numeric contribution from each token, accumulates those contributions into a vector of length `dimensions`, and returns the vector normalized to unit length (unless the vector norm is zero). Empty or token-less input yields a zero vector of the requested dimensionality.
    
    Parameters:
        text (str): Input text to embed.
        dimensions (int): Length of the output embedding vector.
    
    Returns:
        list[float]: A normalized embedding vector of length `dimensions`. If the input contains no tokens, returns a zero vector of the same length.
    """
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


def embedding_metadata() -> dict[str, str | int]:
    """
    Describe the local embedding provider, model, version, and vector dimensions.
    
    Returns:
        metadata (dict[str, str | int]): Mapping with keys "provider", "model_name", "model_version", and "dimensions".
    """
    return {
        "provider": EMBEDDING_PROVIDER,
        "model_name": EMBEDDING_MODEL_NAME,
        "model_version": EMBEDDING_MODEL_VERSION,
        "dimensions": VECTOR_DIMENSIONS,
    }


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """
    Compute the cosine similarity between two equal-length vectors.
    
    Returns:
        float: Cosine similarity clamped to the range [0.0, 1.0]. Returns 0.0 if either vector is empty or if their lengths differ.
    """
    if not left or not right or len(left) != len(right):
        return 0.0
    return max(0.0, min(1.0, sum(a * b for a, b in zip(left, right))))


def snapshot_memory_text(snapshot: MarketSnapshot) -> str:
    """
    Builds a single-line, space-separated textual representation of a market snapshot.
    
    Parameters:
        snapshot (MarketSnapshot): Snapshot to serialize into a compact text form.
    
    Returns:
        str: Space-separated string containing snapshot fields in order:
            symbol, interval, `mtf:<mtf_alignment>`, `htf:<higher_timeframe>`,
            `rsi:<rsi_14>` (two decimals), `return5:<return_5>` (four decimals),
            `return20:<return_20>` (four decimals), and `volatility:<volatility_20>` (four decimals).
            If `snapshot.context_pack` is present, the string is extended with:
            `context:<summary>`, `context_flags:<comma-separated data_quality_flags or 'none'>`,
            `context_anomalies:<comma-separated anomaly_flags or 'none'>`, and one token per
            horizon formatted as `horizon<horizon_bars>:<trend_vote>:return=<return_pct>`.
    """
    parts = [
        snapshot.symbol,
        snapshot.interval,
        f"mtf:{snapshot.mtf_alignment}",
        f"htf:{snapshot.higher_timeframe}",
        f"rsi:{snapshot.rsi_14:.2f}",
        f"return5:{snapshot.return_5:.4f}",
        f"return20:{snapshot.return_20:.4f}",
        f"volatility:{snapshot.volatility_20:.4f}",
    ]
    if snapshot.context_pack is not None:
        parts.extend(
            [
                f"context:{snapshot.context_pack.summary}",
                "context_flags:"
                f"{','.join(snapshot.context_pack.data_quality_flags) or 'none'}",
                "context_anomalies:"
                f"{','.join(snapshot.context_pack.anomaly_flags) or 'none'}",
            ]
        )
        parts.extend(
            f"horizon{item.horizon_bars}:{item.trend_vote}:return={item.return_pct}"
            for item in snapshot.context_pack.horizons
        )
    return " ".join(parts)


def build_memory_document(artifacts: RunArtifacts) -> str:
    """
    Constructs a single textual memory document representing a run's artifacts.
    
    Parameters:
        artifacts (RunArtifacts): Collected run artifacts including snapshot, regime, strategy, manager, and review data.
    
    Returns:
        memory_document (str): A single string combining the snapshot text and key artifact fields: `regime`, `direction`, `strategy`, `action`, `manager`, `review` summary, and `warnings` (comma-separated or `'none'` when empty). Fields are separated by " | ".
    """
    snapshot = artifacts.snapshot
    parts = [
        snapshot_memory_text(snapshot),
        f"regime:{artifacts.regime.regime}",
        f"direction:{artifacts.regime.direction_bias}",
        f"strategy:{artifacts.strategy.strategy_family}",
        f"action:{artifacts.strategy.action}",
        f"fundamental:{artifacts.fundamental.overall_signal}",
        f"macro:{artifacts.macro.macro_signal}",
        f"manager:{artifacts.manager.action_bias}",
        f"review:{artifacts.review.summary}",
        f"warnings:{','.join(artifacts.review.warnings) or 'none'}",
    ]
    if artifacts.decision_features is not None:
        parts.extend(
            [
                f"symbol_identity:{artifacts.decision_features.symbol_identity.region}:{artifacts.decision_features.symbol_identity.exchange}:{artifacts.decision_features.symbol_identity.currency}",
                f"technical_trend:{artifacts.decision_features.technical.trend_classification}",
                f"fundamental_flags:{','.join(artifacts.decision_features.fundamental.quality_flags) or 'none'}",
                f"macro_news_count:{len(artifacts.decision_features.macro.news_signals)}",
            ]
        )
    return " | ".join(parts)


def embed_artifacts(artifacts: RunArtifacts) -> list[float]:
    return embed_text(build_memory_document(artifacts))


def embed_snapshot(snapshot: MarketSnapshot) -> list[float]:
    return embed_text(snapshot_memory_text(snapshot))
