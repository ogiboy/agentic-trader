from typing import Any, cast

from agentic_trader.agents.fundamental import assess_fundamentals
from agentic_trader.agents.macro import assess_macro_context
from agentic_trader.config import Settings
from agentic_trader.features import build_decision_feature_bundle
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import (
    AgentContext,
    InvestmentPreferences,
    MarketSnapshot,
    PortfolioSnapshot,
)


class _FailingLLM:
    def for_role(self, _role: str) -> "_FailingLLM":
        return self

    def complete_structured(self, **_kwargs: Any) -> object:
        raise RuntimeError("LLM unavailable in test")


def _snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        symbol="AAPL",
        interval="1d",
        as_of="2025-06-30",
        last_close=105.0,
        ema_20=102.0,
        ema_50=99.0,
        atr_14=2.0,
        rsi_14=61.0,
        volatility_20=0.12,
        return_5=0.03,
        return_20=0.09,
        volume_ratio_20=1.2,
        mtf_alignment="bullish",
        mtf_confidence=0.72,
        bars_analyzed=120,
    )


def _context(snapshot: MarketSnapshot) -> AgentContext:
    settings = Settings()
    return AgentContext(
        role="fundamental",
        model_name="test-model",
        snapshot=snapshot,
        decision_features=build_decision_feature_bundle(snapshot, settings=settings),
        preferences=InvestmentPreferences(),
        portfolio=PortfolioSnapshot(
            cash=100_000.0,
            market_value=0.0,
            equity=100_000.0,
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            open_positions=0,
        ),
    )


def test_fundamental_agent_falls_back_to_structured_neutral_assessment() -> None:
    context = _context(_snapshot())
    assessment = assess_fundamentals(
        cast(LocalLLM, _FailingLLM()),
        context.snapshot,
        allow_fallback=True,
        context=context,
    )

    assert assessment.source == "fallback"
    assert assessment.overall_signal == "neutral"
    assert "fundamental_fetch_not_implemented" in assessment.risk_flags
    assert assessment.fallback_reason == "Structured fundamental provider data is unavailable."


def test_macro_agent_falls_back_to_structured_neutral_assessment() -> None:
    context = _context(_snapshot())
    assessment = assess_macro_context(
        cast(LocalLLM, _FailingLLM()),
        context.snapshot,
        allow_fallback=True,
        context=context,
    )

    assert assessment.source == "fallback"
    assert assessment.macro_signal == "neutral"
    assert "no_structured_news_signals" in assessment.risk_flags
    assert assessment.fallback_reason == "Structured macro/news provider data is unavailable."
