from dataclasses import dataclass
from typing import Literal

IdeaPresetName = Literal[
    "momentum",
    "gap-up",
    "gap-down",
    "mean-reversion",
    "breakout",
    "volatile",
]
IdeaSignal = Literal["buy", "sell", "watch"]


@dataclass(frozen=True)
class IdeaCandidate:
    symbol: str
    price: float
    volume: float
    change_pct: float
    relative_volume: float = 0.0
    gap_pct: float = 0.0
    range_pct: float = 0.0
    rsi: float | None = None
    ema_9: float | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    vwap: float | None = None
    spread_pct: float = 0.0


@dataclass(frozen=True)
class IdeaScore:
    symbol: str
    preset: IdeaPresetName
    score: float
    signal: IdeaSignal
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]


PRESET_DESCRIPTIONS: dict[IdeaPresetName, str] = {
    "momentum": "High momentum with strong volume and trend confirmation.",
    "gap-up": "Large positive gap with enough volume and RSI headroom.",
    "gap-down": "Large negative gap for reversal watch or short bias.",
    "mean-reversion": "Oversold candidate below moving averages.",
    "breakout": "Price reclaiming VWAP or short moving averages with volume.",
    "volatile": "High intraday range and volume for watchlist triage.",
}


def score_candidate(candidate: IdeaCandidate, preset: IdeaPresetName) -> IdeaScore:
    warnings = _candidate_warnings(candidate)
    if preset == "momentum":
        score, reasons = _score_momentum(candidate)
        signal = "buy" if score >= 40 else "watch"
    elif preset == "gap-up":
        score, reasons = _score_gap_up(candidate)
        signal = "buy" if score >= 40 else "watch"
    elif preset == "gap-down":
        score, reasons = _score_gap_down(candidate)
        signal = "sell" if score >= 40 else "watch"
    elif preset == "mean-reversion":
        score, reasons = _score_mean_reversion(candidate)
        signal = "buy" if score >= 35 else "watch"
    elif preset == "breakout":
        score, reasons = _score_breakout(candidate)
        signal = "buy" if score >= 45 else "watch"
    else:
        score, reasons = _score_volatile(candidate)
        signal = "watch"
    return IdeaScore(
        symbol=candidate.symbol.upper(),
        preset=preset,
        score=round(min(score, 100.0), 2),
        signal=signal,
        reasons=tuple(reasons),
        warnings=tuple(warnings),
    )


def rank_candidates(
    candidates: list[IdeaCandidate], *, preset: IdeaPresetName, limit: int = 10
) -> list[IdeaScore]:
    if limit < 0:
        raise ValueError("limit must be greater than or equal to zero")
    ranked = sorted(
        (score_candidate(candidate, preset) for candidate in candidates),
        key=lambda item: item.score,
        reverse=True,
    )
    return ranked[:limit]


def _candidate_warnings(candidate: IdeaCandidate) -> list[str]:
    warnings: list[str] = []
    if candidate.price <= 0:
        warnings.append("invalid_price")
    if candidate.volume < 100_000:
        warnings.append("low_volume")
    if candidate.spread_pct > 1.0:
        warnings.append("wide_spread")
    return warnings


def _score_momentum(candidate: IdeaCandidate) -> tuple[float, list[str]]:
    score = min(max(candidate.change_pct, 0.0), 15) * 2
    reasons = [f"change={candidate.change_pct:.2f}%"]
    score += min(candidate.relative_volume, 5) * 5
    reasons.append(f"relative_volume={candidate.relative_volume:.2f}")
    if candidate.rsi is not None and 50 < candidate.rsi < 80:
        score += (candidate.rsi - 50) * 0.5
        reasons.append(f"rsi_headroom={candidate.rsi:.1f}")
    if candidate.ema_9 is not None and candidate.price > candidate.ema_9:
        score += 10
        reasons.append("price_above_ema9")
    return score, reasons


def _score_gap_up(candidate: IdeaCandidate) -> tuple[float, list[str]]:
    positive_gap = max(candidate.gap_pct, 0.0)
    score = min(positive_gap, 20) * 2
    reasons = [f"gap={candidate.gap_pct:.2f}%"] if positive_gap else []
    score += min(candidate.relative_volume, 6) * 5
    score += min(abs(candidate.change_pct), 10) * 2
    if candidate.rsi is not None and candidate.rsi < 70:
        score += 10
        reasons.append("rsi_not_overextended")
    return score, reasons


def _score_gap_down(candidate: IdeaCandidate) -> tuple[float, list[str]]:
    negative_gap = abs(candidate.gap_pct) if candidate.gap_pct < 0 else 0.0
    score = min(negative_gap, 20) * 2
    reasons = [f"gap={candidate.gap_pct:.2f}%"] if negative_gap else []
    if candidate.rsi is not None and candidate.rsi < 40:
        score += (40 - candidate.rsi) * 0.75
        reasons.append(f"oversold_rsi={candidate.rsi:.1f}")
    if candidate.sma_20 is not None and candidate.price < candidate.sma_20:
        distance = _distance_below_pct(candidate.price, candidate.sma_20)
        score += min(distance, 10) * 2
        reasons.append("below_sma20")
    score += min(candidate.relative_volume, 4) * 2.5
    return score, reasons


def _score_mean_reversion(candidate: IdeaCandidate) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    if candidate.rsi is not None and candidate.rsi < 40:
        score += (40 - candidate.rsi) * (1.0 if candidate.rsi < 30 else 0.5)
        reasons.append(f"oversold_rsi={candidate.rsi:.1f}")
    for label, average in (("sma20", candidate.sma_20), ("sma50", candidate.sma_50)):
        if average is not None and candidate.price < average:
            distance = _distance_below_pct(candidate.price, average)
            score += min(distance, 10) * 2.5
            reasons.append(f"below_{label}")
    score += min(candidate.relative_volume, 4) * 5
    return score, reasons


def _score_breakout(candidate: IdeaCandidate) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    if candidate.vwap is not None and candidate.price > candidate.vwap:
        score += 15
        reasons.append("above_vwap")
    if candidate.ema_9 is not None and candidate.sma_20 is not None:
        if candidate.price > candidate.ema_9 > candidate.sma_20:
            score += 30
            reasons.append("price_ema9_sma20_alignment")
        elif candidate.price > candidate.ema_9:
            score += 15
            reasons.append("above_ema9")
    score += min(candidate.relative_volume, 6) * 5
    score += min(abs(candidate.change_pct), 5) * 3
    return score, reasons


def _score_volatile(candidate: IdeaCandidate) -> tuple[float, list[str]]:
    score = min(candidate.range_pct, 20) * 2
    reasons = [f"range={candidate.range_pct:.2f}%"]
    score += min(candidate.relative_volume, 5) * 5
    score += min(abs(candidate.change_pct), 10) * 2.5
    if candidate.rsi is not None and (candidate.rsi > 70 or candidate.rsi < 30):
        score += 10
        reasons.append(f"rsi_extreme={candidate.rsi:.1f}")
    return score, reasons


def _distance_below_pct(price: float, average: float) -> float:
    if average == 0:
        return 0.0
    return ((average - price) / average) * 100
