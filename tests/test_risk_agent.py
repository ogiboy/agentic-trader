from typing import Any, cast

import pytest

from agentic_trader.agents.risk import build_risk_plan
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import MarketSnapshot, RegimeAssessment, RiskPlan, StrategyPlan


class _RiskLLM:
    def __init__(self, risk: RiskPlan):
        self.risk = risk

    def for_role(self, _role: str) -> "_RiskLLM":
        return self

    def complete_structured(self, **_kwargs: Any) -> RiskPlan:
        return self.risk


def _snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        symbol="AAPL",
        interval="1d",
        last_close=100.0,
        ema_20=101.0,
        ema_50=99.0,
        atr_14=2.5,
        rsi_14=52.0,
        volatility_20=0.06,
        return_5=0.01,
        return_20=0.02,
        volume_ratio_20=0.8,
        bars_analyzed=120,
    )


def test_risk_agent_normalizes_no_trade_reference_levels() -> None:
    strategy = StrategyPlan(
        strategy_family="no_trade",
        action="hold",
        timeframe="flat",
        entry_logic="No valid entry.",
        invalidation_logic="Wait for clearer evidence.",
        confidence=0.35,
    )
    raw_risk = RiskPlan(
        position_size_pct=0.2,
        stop_loss=1e-6,
        take_profit=1e-6,
        risk_reward_ratio=1e-6,
        max_holding_bars=100,
        notes="No-trade risk plan.",
    )

    finalized = build_risk_plan(
        cast(LocalLLM, _RiskLLM(raw_risk)),
        _snapshot(),
        RegimeAssessment(
            regime="no_trade",
            direction_bias="flat",
            confidence=0.35,
            reasoning="No clear edge.",
        ),
        strategy,
        allow_fallback=False,
    )

    assert finalized.position_size_pct == pytest.approx(0.01)
    assert finalized.stop_loss == pytest.approx(97.5)
    assert finalized.take_profit == pytest.approx(102.5)
    assert finalized.risk_reward_ratio == pytest.approx(1.0)
    assert finalized.max_holding_bars == 5
