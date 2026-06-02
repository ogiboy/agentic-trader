from __future__ import annotations

from dataclasses import dataclass

from agentic_trader.schemas import (
    ExecutionDecision,
    ExecutionSide,
    ManagerDecision,
    MarketSnapshot,
    RegimeAssessment,
    ResearchCoordinatorBrief,
    ReviewNote,
    RiskPlan,
    RunArtifacts,
    StrategyPlan,
)


@dataclass(frozen=True)
class BaselineDecision:
    regime: RegimeAssessment
    strategy: StrategyPlan
    risk: RiskPlan
    execution: ExecutionDecision


def baseline_artifacts(snapshot: MarketSnapshot) -> RunArtifacts:
    baseline = baseline_decision(snapshot)
    manager = ManagerDecision(
        approved=baseline.execution.approved,
        action_bias=baseline.execution.side,
        confidence_cap=baseline.execution.confidence,
        size_multiplier=1.0,
        rationale="Deterministic baseline manager summary.",
    )
    review = ReviewNote(
        summary="Deterministic baseline review summary.",
        strengths=["Deterministic baseline produced a reproducible decision."],
        warnings=(
            [] if baseline.execution.approved else ["No baseline trade was approved."]
        ),
        next_checks=["Compare against the agent-driven replay."],
    )
    return RunArtifacts(
        snapshot=snapshot,
        coordinator=baseline_coordinator(baseline.execution),
        regime=baseline.regime,
        strategy=baseline.strategy,
        risk=baseline.risk,
        manager=manager,
        execution=baseline.execution,
        review=review,
    )


def baseline_decision(snapshot: MarketSnapshot) -> BaselineDecision:
    trend_up = (
        snapshot.last_close > snapshot.ema_20 > snapshot.ema_50
        and snapshot.rsi_14 >= 52
    )
    trend_down = (
        snapshot.last_close < snapshot.ema_20 < snapshot.ema_50
        and snapshot.rsi_14 <= 48
    )
    normalized_atr = max(snapshot.atr_14, snapshot.last_close * 0.01)
    if trend_up:
        return trend_up_baseline(snapshot, normalized_atr)
    if trend_down:
        return trend_down_baseline(snapshot, normalized_atr)
    return no_trade_baseline(snapshot, normalized_atr)


def trend_up_baseline(
    snapshot: MarketSnapshot, normalized_atr: float
) -> BaselineDecision:
    strategy = StrategyPlan(
        strategy_family="trend_following",
        action="buy",
        timeframe="swing",
        entry_logic="Baseline enters long when price is above EMA20 and EMA50 with supportive RSI.",
        invalidation_logic="Exit below EMA20 with weakening momentum.",
        confidence=0.68,
    )
    risk = RiskPlan(
        position_size_pct=0.08,
        stop_loss=round(snapshot.last_close - (1.5 * normalized_atr), 4),
        take_profit=round(snapshot.last_close + (3.0 * normalized_atr), 4),
        risk_reward_ratio=2.0,
        max_holding_bars=20,
        notes="Deterministic baseline risk plan for long trend setup.",
    )
    return BaselineDecision(
        regime=RegimeAssessment(
            regime="trend_up",
            direction_bias="long",
            confidence=0.68,
            reasoning="Deterministic baseline classified an uptrend.",
        ),
        strategy=strategy,
        risk=risk,
        execution=baseline_execution(
            snapshot=snapshot,
            risk=risk,
            approved=True,
            side="buy",
            confidence=0.68,
            rationale="Deterministic baseline approved long trend setup.",
        ),
    )


def trend_down_baseline(
    snapshot: MarketSnapshot, normalized_atr: float
) -> BaselineDecision:
    strategy = StrategyPlan(
        strategy_family="trend_following",
        action="sell",
        timeframe="swing",
        entry_logic="Baseline enters short when price is below EMA20 and EMA50 with weak RSI.",
        invalidation_logic="Exit above EMA20 with strengthening momentum.",
        confidence=0.68,
    )
    risk = RiskPlan(
        position_size_pct=0.08,
        stop_loss=round(snapshot.last_close + (1.5 * normalized_atr), 4),
        take_profit=round(snapshot.last_close - (3.0 * normalized_atr), 4),
        risk_reward_ratio=2.0,
        max_holding_bars=20,
        notes="Deterministic baseline risk plan for short trend setup.",
    )
    return BaselineDecision(
        regime=RegimeAssessment(
            regime="trend_down",
            direction_bias="short",
            confidence=0.68,
            reasoning="Deterministic baseline classified a downtrend.",
        ),
        strategy=strategy,
        risk=risk,
        execution=baseline_execution(
            snapshot=snapshot,
            risk=risk,
            approved=True,
            side="sell",
            confidence=0.68,
            rationale="Deterministic baseline approved short trend setup.",
        ),
    )


def no_trade_baseline(
    snapshot: MarketSnapshot, normalized_atr: float
) -> BaselineDecision:
    strategy = StrategyPlan(
        strategy_family="no_trade",
        action="hold",
        timeframe="flat",
        entry_logic="Baseline found no aligned setup.",
        invalidation_logic="Wait for trend alignment.",
        confidence=0.55,
    )
    risk = RiskPlan(
        position_size_pct=0.01,
        stop_loss=round(snapshot.last_close - normalized_atr, 4),
        take_profit=round(snapshot.last_close + normalized_atr, 4),
        risk_reward_ratio=1.0,
        max_holding_bars=5,
        notes="Deterministic baseline no-trade placeholder.",
    )
    return BaselineDecision(
        regime=RegimeAssessment(
            regime="range",
            direction_bias="flat",
            confidence=0.55,
            reasoning="Deterministic baseline found mixed conditions.",
        ),
        strategy=strategy,
        risk=risk,
        execution=baseline_execution(
            snapshot=snapshot,
            risk=risk,
            approved=False,
            side="hold",
            confidence=0.55,
            rationale="Deterministic baseline did not find a valid setup.",
        ),
    )


def baseline_execution(
    *,
    snapshot: MarketSnapshot,
    risk: RiskPlan,
    approved: bool,
    side: ExecutionSide,
    confidence: float,
    rationale: str,
) -> ExecutionDecision:
    return ExecutionDecision(
        approved=approved,
        side=side,
        symbol=snapshot.symbol,
        entry_price=snapshot.last_close,
        stop_loss=risk.stop_loss,
        take_profit=risk.take_profit,
        position_size_pct=risk.position_size_pct,
        confidence=confidence,
        rationale=rationale,
    )


def baseline_coordinator(execution: ExecutionDecision) -> ResearchCoordinatorBrief:
    trading = execution.side in {"buy", "sell"}
    return ResearchCoordinatorBrief(
        market_focus="trend_following" if trading else "no_trade",
        priority_signals=["trend_alignment"] if trading else ["wait_for_clarity"],
        caution_flags=[] if trading else ["mixed_signals"],
        summary="Deterministic baseline coordinator summary.",
    )
