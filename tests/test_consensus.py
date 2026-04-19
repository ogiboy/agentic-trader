from agentic_trader.agents.consensus import assess_specialist_consensus
from agentic_trader.schemas import (
    FundamentalAssessment,
    MacroAssessment,
    RegimeAssessment,
    ResearchCoordinatorBrief,
    RiskPlan,
    StrategyPlan,
)


def test_assess_specialist_consensus_detects_alignment() -> None:
    consensus = assess_specialist_consensus(
        ResearchCoordinatorBrief(
            market_focus="trend_following",
            priority_signals=["trend_alignment"],
            caution_flags=[],
            summary="Aligned focus",
        ),
        RegimeAssessment(
            regime="trend_up",
            direction_bias="long",
            confidence=0.72,
            reasoning="Trend up",
        ),
        StrategyPlan(
            strategy_family="trend_following",
            action="buy",
            timeframe="swing",
            entry_logic="Buy above EMA20",
            invalidation_logic="Exit below EMA20",
            confidence=0.75,
        ),
        RiskPlan(
            position_size_pct=0.08,
            stop_loss=95.0,
            take_profit=110.0,
            risk_reward_ratio=2.0,
            max_holding_bars=20,
            notes="Healthy risk plan",
        ),
    )

    assert consensus.alignment_level == "aligned"
    assert "regime" in consensus.supporting_roles
    assert consensus.dissenting_roles == []


def test_assess_specialist_consensus_detects_conflict() -> None:
    consensus = assess_specialist_consensus(
        ResearchCoordinatorBrief(
            market_focus="capital_preservation",
            priority_signals=[],
            caution_flags=["defensive"],
            summary="Defensive focus",
        ),
        RegimeAssessment(
            regime="trend_down",
            direction_bias="short",
            confidence=0.68,
            reasoning="Trend down",
        ),
        StrategyPlan(
            strategy_family="trend_following",
            action="buy",
            timeframe="swing",
            entry_logic="Buy reversal",
            invalidation_logic="Exit on weakness",
            confidence=0.7,
        ),
        RiskPlan(
            position_size_pct=0.01,
            stop_loss=95.0,
            take_profit=103.0,
            risk_reward_ratio=1.1,
            max_holding_bars=10,
            notes="Tight risk plan",
        ),
    )

    assert consensus.alignment_level == "conflicted"
    assert "coordinator" in consensus.dissenting_roles
    assert "regime" in consensus.dissenting_roles


def test_consensus_does_not_count_unavailable_finance_fallbacks_as_support() -> None:
    consensus = assess_specialist_consensus(
        ResearchCoordinatorBrief(
            market_focus="trend_following",
            priority_signals=["trend_alignment"],
            caution_flags=[],
            summary="Aligned focus",
        ),
        RegimeAssessment(
            regime="trend_up",
            direction_bias="long",
            confidence=0.72,
            reasoning="Trend up",
        ),
        StrategyPlan(
            strategy_family="trend_following",
            action="buy",
            timeframe="swing",
            entry_logic="Buy above EMA20",
            invalidation_logic="Exit below EMA20",
            confidence=0.75,
        ),
        RiskPlan(
            position_size_pct=0.08,
            stop_loss=95.0,
            take_profit=110.0,
            risk_reward_ratio=2.0,
            max_holding_bars=20,
            notes="Healthy risk plan",
        ),
        fundamental=FundamentalAssessment(
            source="fallback",
            fallback_reason="Structured fundamental provider data is unavailable.",
        ),
        macro=MacroAssessment(
            source="fallback",
            fallback_reason="Structured macro/news provider data is unavailable.",
        ),
    )

    assert consensus.alignment_level == "aligned"
    assert "fundamental" not in consensus.supporting_roles
    assert "macro" not in consensus.supporting_roles
    assert any("Fundamental evidence was fallback-generated" in reason for reason in consensus.reasons)
    assert any("Macro/news evidence was fallback-generated" in reason for reason in consensus.reasons)
