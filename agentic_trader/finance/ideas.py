from dataclasses import dataclass
from collections.abc import Callable
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


PresetScorer = Callable[[IdeaCandidate], tuple[float, list[str]]]


@dataclass(frozen=True)
class _PresetScoringRule:
    scorer: PresetScorer
    active_signal: IdeaSignal
    threshold: float | None


PRESET_DESCRIPTIONS: dict[IdeaPresetName, str] = {
    "momentum": "High momentum with strong volume and trend confirmation.",
    "gap-up": "Large positive gap with enough volume and RSI headroom.",
    "gap-down": "Large negative gap for reversal watch or short bias.",
    "mean-reversion": "Oversold candidate below moving averages.",
    "breakout": "Price reclaiming VWAP or short moving averages with volume.",
    "volatile": "High intraday range and volume for watchlist triage.",
}


def _signal_for_score(score: float, rule: _PresetScoringRule) -> IdeaSignal:
    if rule.threshold is None:
        return "watch"
    if score >= rule.threshold:
        return rule.active_signal
    return "watch"


def score_candidate(candidate: IdeaCandidate, preset: IdeaPresetName) -> IdeaScore:
    warnings = _candidate_warnings(candidate)
    rule = _SCORE_RULES[preset]
    score, reasons = rule.scorer(candidate)
    signal = _signal_for_score(score, rule)
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
    reasons = _gap_reasons(candidate, positive_gap)
    score += min(candidate.relative_volume, 6) * 5
    score += min(abs(candidate.change_pct), 10) * 2
    if candidate.rsi is not None and candidate.rsi < 70:
        score += 10
        reasons.append("rsi_not_overextended")
    return score, reasons


def _score_gap_down(candidate: IdeaCandidate) -> tuple[float, list[str]]:
    negative_gap = _negative_gap_pct(candidate)
    score = min(negative_gap, 20) * 2
    reasons = _gap_reasons(candidate, negative_gap)
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
        score += (40 - candidate.rsi) * _mean_reversion_rsi_multiplier(
            candidate.rsi
        )
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


_SCORE_RULES: dict[IdeaPresetName, _PresetScoringRule] = {
    "momentum": _PresetScoringRule(_score_momentum, "buy", 40),
    "gap-up": _PresetScoringRule(_score_gap_up, "buy", 40),
    "gap-down": _PresetScoringRule(_score_gap_down, "sell", 40),
    "mean-reversion": _PresetScoringRule(_score_mean_reversion, "buy", 35),
    "breakout": _PresetScoringRule(_score_breakout, "buy", 45),
    "volatile": _PresetScoringRule(_score_volatile, "watch", None),
}


def _gap_reasons(candidate: IdeaCandidate, gap_magnitude: float) -> list[str]:
    if gap_magnitude:
        return [f"gap={candidate.gap_pct:.2f}%"]
    return []


def _negative_gap_pct(candidate: IdeaCandidate) -> float:
    if candidate.gap_pct < 0:
        return abs(candidate.gap_pct)
    return 0.0


def _mean_reversion_rsi_multiplier(rsi: float) -> float:
    if rsi < 30:
        return 1.0
    return 0.5


def _distance_below_pct(price: float, average: float) -> float:
    if average == 0:
        return 0.0
    return ((average - price) / average) * 100
