from agentic_trader.agents.consensus import (
    _fallback_evidence_note,
    assess_specialist_consensus,
)
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
    assert any(
        "Fundamental evidence was fallback-generated" in reason
        for reason in consensus.reasons
    )
    assert any(
        "Macro/news evidence was fallback-generated" in reason
        for reason in consensus.reasons
    )


# ---------------------------------------------------------------------------
# _fallback_evidence_note
# ---------------------------------------------------------------------------


def test_fallback_evidence_note_includes_role_name() -> None:
    note = _fallback_evidence_note("Fundamental")
    assert "Fundamental" in note
    assert "fallback-generated" in note
    assert "not counted as support" in note


def test_fallback_evidence_note_for_macro() -> None:
    note = _fallback_evidence_note("Macro/news")
    assert "Macro/news" in note
    assert "not counted as support" in note


# ---------------------------------------------------------------------------
# hold action
# ---------------------------------------------------------------------------


def _aligned_inputs() -> tuple[
    ResearchCoordinatorBrief,
    RegimeAssessment,
    StrategyPlan,
    RiskPlan,
]:
    coordinator = ResearchCoordinatorBrief(
        market_focus="trend_following",
        priority_signals=["trend_alignment"],
        caution_flags=[],
        summary="Aligned focus",
    )
    regime = RegimeAssessment(
        regime="trend_up",
        direction_bias="long",
        confidence=0.72,
        reasoning="Trend up",
    )
    strategy = StrategyPlan(
        strategy_family="trend_following",
        action="buy",
        timeframe="swing",
        entry_logic="Buy above EMA20",
        invalidation_logic="Exit below EMA20",
        confidence=0.75,
    )
    risk = RiskPlan(
        position_size_pct=0.08,
        stop_loss=95.0,
        take_profit=110.0,
        risk_reward_ratio=2.0,
        max_holding_bars=20,
        notes="Healthy risk plan",
    )
    return coordinator, regime, strategy, risk


def test_hold_action_returns_conflicted_with_defensive_notes() -> None:
    coordinator, regime, _, risk = _aligned_inputs()
    hold_strategy = StrategyPlan(
        strategy_family="no_trade",
        action="hold",
        timeframe="flat",
        entry_logic="No valid setup.",
        invalidation_logic="Wait for confirmation.",
        confidence=0.35,
    )
    consensus = assess_specialist_consensus(coordinator, regime, hold_strategy, risk)

    assert consensus.alignment_level == "conflicted"
    assert "strategy" in consensus.supporting_roles
    assert "coordinator" in consensus.dissenting_roles
    assert "regime" in consensus.dissenting_roles
    assert any("defensive" in reason.lower() for reason in consensus.reasons)


# ---------------------------------------------------------------------------
# aligned summary text updated in PR
# ---------------------------------------------------------------------------


def test_aligned_consensus_uses_updated_summary_text() -> None:
    coordinator, regime, strategy, risk = _aligned_inputs()
    consensus = assess_specialist_consensus(coordinator, regime, strategy, risk)

    assert consensus.alignment_level == "aligned"
    assert (
        "Available specialists were aligned before manager synthesis."
        in consensus.summary
    )


def test_aligned_consensus_default_reasons_when_no_fallbacks() -> None:
    coordinator, regime, strategy, risk = _aligned_inputs()
    consensus = assess_specialist_consensus(coordinator, regime, strategy, risk)

    assert consensus.alignment_level == "aligned"
    assert any("No specialist disagreements" in r for r in consensus.reasons)


def test_aligned_consensus_preserves_fallback_notes_in_reasons() -> None:
    coordinator, regime, strategy, risk = _aligned_inputs()
    # Both fundamental and macro are fallback; core specialists are aligned
    consensus = assess_specialist_consensus(
        coordinator,
        regime,
        strategy,
        risk,
        fundamental=FundamentalAssessment(source="fallback"),
        macro=MacroAssessment(source="fallback"),
    )

    assert consensus.alignment_level == "aligned"
    # Fallback notes should appear in reasons instead of the default "No specialist disagreements" string
    assert any(
        "Fundamental evidence was fallback-generated" in r for r in consensus.reasons
    )
    assert any(
        "Macro/news evidence was fallback-generated" in r for r in consensus.reasons
    )


# ---------------------------------------------------------------------------
# fundamental overall_bias (was overall_signal in pre-PR code)
# ---------------------------------------------------------------------------


def test_fundamental_supportive_bias_is_counted_as_support() -> None:
    coordinator, regime, strategy, risk = _aligned_inputs()
    consensus = assess_specialist_consensus(
        coordinator,
        regime,
        strategy,
        risk,
        fundamental=FundamentalAssessment(
            source="llm",
            overall_bias="supportive",
        ),
    )

    assert "fundamental" in consensus.supporting_roles
    assert "fundamental" not in consensus.dissenting_roles


def test_fundamental_neutral_bias_is_counted_as_support() -> None:
    coordinator, regime, strategy, risk = _aligned_inputs()
    consensus = assess_specialist_consensus(
        coordinator,
        regime,
        strategy,
        risk,
        fundamental=FundamentalAssessment(
            source="llm",
            overall_bias="neutral",
        ),
    )

    assert "fundamental" in consensus.supporting_roles


def test_fundamental_cautious_bias_causes_dissent() -> None:
    coordinator, regime, strategy, risk = _aligned_inputs()
    consensus = assess_specialist_consensus(
        coordinator,
        regime,
        strategy,
        risk,
        fundamental=FundamentalAssessment(
            source="llm",
            overall_bias="cautious",
        ),
    )

    assert "fundamental" in consensus.dissenting_roles
    assert "fundamental" not in consensus.supporting_roles
    assert any(
        "Fundamental analyst returned cautious evidence." in r
        for r in consensus.reasons
    )


def test_fundamental_avoid_bias_causes_dissent() -> None:
    coordinator, regime, strategy, risk = _aligned_inputs()
    consensus = assess_specialist_consensus(
        coordinator,
        regime,
        strategy,
        risk,
        fundamental=FundamentalAssessment(
            source="llm",
            overall_bias="avoid",
        ),
    )

    assert "fundamental" in consensus.dissenting_roles
    assert any("avoid" in r for r in consensus.reasons)


# ---------------------------------------------------------------------------
# macro non-fallback paths
# ---------------------------------------------------------------------------


def test_macro_supportive_signal_is_counted_as_support() -> None:
    coordinator, regime, strategy, risk = _aligned_inputs()
    consensus = assess_specialist_consensus(
        coordinator,
        regime,
        strategy,
        risk,
        macro=MacroAssessment(source="llm", macro_signal="supportive"),
    )

    assert "macro" in consensus.supporting_roles
    assert "macro" not in consensus.dissenting_roles


def test_macro_neutral_signal_is_counted_as_support() -> None:
    coordinator, regime, strategy, risk = _aligned_inputs()
    consensus = assess_specialist_consensus(
        coordinator,
        regime,
        strategy,
        risk,
        macro=MacroAssessment(source="llm", macro_signal="neutral"),
    )

    assert "macro" in consensus.supporting_roles


def test_macro_cautious_signal_causes_dissent() -> None:
    coordinator, regime, strategy, risk = _aligned_inputs()
    consensus = assess_specialist_consensus(
        coordinator,
        regime,
        strategy,
        risk,
        macro=MacroAssessment(source="llm", macro_signal="cautious"),
    )

    assert "macro" in consensus.dissenting_roles
    assert any("cautious" in r for r in consensus.reasons)


# ---------------------------------------------------------------------------
# mixed consensus (exactly one dissenter)
# ---------------------------------------------------------------------------


def test_mixed_consensus_when_exactly_one_dissenter() -> None:
    # Make risk plan constrained to trigger one dissent (risk), but others aligned
    coordinator = ResearchCoordinatorBrief(
        market_focus="trend_following",
        priority_signals=["trend_alignment"],
        caution_flags=[],
        summary="Aligned focus",
    )
    regime = RegimeAssessment(
        regime="trend_up",
        direction_bias="long",
        confidence=0.72,
        reasoning="Trend up",
    )
    strategy = StrategyPlan(
        strategy_family="trend_following",
        action="buy",
        timeframe="swing",
        entry_logic="Buy above EMA20",
        invalidation_logic="Exit below EMA20",
        confidence=0.75,
    )
    # Low risk_reward_ratio to trigger one dissent on risk, but small enough position_size_pct
    constrained_risk = RiskPlan(
        position_size_pct=0.08,
        stop_loss=95.0,
        take_profit=105.0,
        risk_reward_ratio=1.0,  # < 1.5 threshold → risk dissents
        max_holding_bars=20,
        notes="Constrained risk plan",
    )
    consensus = assess_specialist_consensus(
        coordinator, regime, strategy, constrained_risk
    )

    assert consensus.alignment_level == "mixed"
    assert "risk" in consensus.dissenting_roles
    assert len(consensus.dissenting_roles) == 1
    assert any("risk_reward_ratio=1.00" in reason for reason in consensus.reasons)
