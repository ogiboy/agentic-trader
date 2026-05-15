from agentic_trader.finance.ideas import IdeaCandidate, rank_candidates, score_candidate


def test_momentum_preset_prefers_high_relative_volume_trend() -> None:
    strong = IdeaCandidate(
        symbol="AAPL",
        price=190,
        volume=5_000_000,
        change_pct=6.2,
        relative_volume=3.4,
        rsi=63,
        ema_9=184,
        spread_pct=0.04,
    )
    weak = IdeaCandidate(
        symbol="MSFT",
        price=410,
        volume=800_000,
        change_pct=0.4,
        relative_volume=0.8,
        rsi=49,
        ema_9=412,
        spread_pct=0.05,
    )

    ranked = rank_candidates([weak, strong], preset="momentum", limit=2)

    assert ranked[0].symbol == "AAPL"
    assert ranked[0].signal == "buy"
    assert ranked[0].score > ranked[1].score
    assert "price_above_ema9" in ranked[0].reasons


def test_gap_down_preset_surfaces_short_bias_and_risk_warnings() -> None:
    candidate = IdeaCandidate(
        symbol="TSLA",
        price=185,
        volume=70_000,
        change_pct=-8.1,
        relative_volume=2.2,
        gap_pct=-11.5,
        rsi=31,
        sma_20=205,
        spread_pct=1.4,
    )

    score = score_candidate(candidate, "gap-down")

    assert score.signal == "sell"
    assert score.score >= 40
    assert "low_volume" in score.warnings
    assert "wide_spread" in score.warnings


def test_mean_reversion_preset_keeps_weak_candidate_as_watch() -> None:
    candidate = IdeaCandidate(
        symbol="SPY",
        price=520,
        volume=60_000_000,
        change_pct=-0.3,
        relative_volume=0.7,
        rsi=52,
        sma_20=519,
        sma_50=512,
    )

    score = score_candidate(candidate, "mean-reversion")

    assert score.signal == "watch"
    assert score.score < 35


def test_rank_candidates_respects_zero_limit_and_rejects_negative_limit() -> None:
    candidate = IdeaCandidate(
        symbol="AAPL",
        price=190,
        volume=5_000_000,
        change_pct=6.2,
        relative_volume=3.4,
        rsi=63,
        ema_9=184,
    )

    assert rank_candidates([candidate], preset="momentum", limit=0) == []

    try:
        rank_candidates([candidate], preset="momentum", limit=-1)
    except ValueError as exc:
        assert "greater than or equal to zero" in str(exc)
    else:
        raise AssertionError("negative limits should be rejected")


def test_idea_score_reasons_and_warnings_are_immutable_tuples() -> None:
    score = score_candidate(
        IdeaCandidate(
            symbol="TSLA",
            price=185,
            volume=70_000,
            change_pct=-8.1,
            relative_volume=2.2,
            gap_pct=-11.5,
            rsi=31,
            sma_20=205,
            spread_pct=1.4,
        ),
        "gap-down",
    )

    assert isinstance(score.reasons, tuple)
    assert isinstance(score.warnings, tuple)


def test_directional_presets_do_not_reward_opposite_gap_or_momentum() -> None:
    bearish_momentum = score_candidate(
        IdeaCandidate(
            symbol="AAPL",
            price=190,
            volume=5_000_000,
            change_pct=-8.0,
            relative_volume=3.4,
            rsi=63,
            ema_9=184,
        ),
        "momentum",
    )
    negative_gap_up = score_candidate(
        IdeaCandidate(
            symbol="AAPL",
            price=190,
            volume=5_000_000,
            change_pct=1.0,
            relative_volume=0.0,
            gap_pct=-12.0,
        ),
        "gap-up",
    )
    positive_gap_down = score_candidate(
        IdeaCandidate(
            symbol="AAPL",
            price=190,
            volume=5_000_000,
            change_pct=-1.0,
            relative_volume=0.0,
            gap_pct=12.0,
        ),
        "gap-down",
    )

    assert bearish_momentum.signal == "watch"
    assert negative_gap_up.score < 40
    assert positive_gap_down.score < 40


def test_zero_float_indicators_are_not_treated_as_missing() -> None:
    momentum = score_candidate(
        IdeaCandidate(
            symbol="ZERO",
            price=1,
            volume=500_000,
            change_pct=1,
            relative_volume=1,
            ema_9=0.0,
        ),
        "momentum",
    )
    breakout = score_candidate(
        IdeaCandidate(
            symbol="ZERO",
            price=1,
            volume=500_000,
            change_pct=1,
            relative_volume=1,
            vwap=0.0,
            ema_9=0.5,
            sma_20=0.0,
        ),
        "breakout",
    )
    mean_reversion = score_candidate(
        IdeaCandidate(
            symbol="ZERO",
            price=-1,
            volume=500_000,
            change_pct=-1,
            relative_volume=1,
            sma_20=0.0,
        ),
        "mean-reversion",
    )

    assert "price_above_ema9" in momentum.reasons
    assert "above_vwap" in breakout.reasons
    assert "price_ema9_sma20_alignment" in breakout.reasons
    assert "below_sma20" in mean_reversion.reasons
    assert "invalid_price" in mean_reversion.warnings
