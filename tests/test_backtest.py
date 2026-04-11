from pathlib import Path
import pytest

import pandas as pd

from agentic_trader.backtest.walk_forward import (
    run_memory_ablation_backtest,
    run_backtest_comparison,
    run_deterministic_baseline_backtest,
    run_walk_forward_backtest,
)
from agentic_trader.config import Settings
from agentic_trader.schemas import (
    BacktestReport,
    ExecutionDecision,
    ManagerDecision,
    MarketSnapshot,
    RegimeAssessment,
    ResearchCoordinatorBrief,
    RiskPlan,
    ReviewNote,
    RunArtifacts,
    StrategyPlan,
)


def _frame() -> pd.DataFrame:
    closes = [100.0 + (index * 0.5) for index in range(100)]
    return pd.DataFrame(
        {
            "open": closes,
            "high": [value + 0.5 for value in closes],
            "low": [value - 0.5 for value in closes],
            "close": closes,
            "volume": [1_000_000 + (index * 1_000) for index in range(100)],
        },
        index=pd.date_range("2024-01-01", periods=100, freq="D"),
    )


def test_walk_forward_backtest_closes_trade_and_reports_metrics(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        default_cash=10_000.0,
    )
    settings.ensure_directories()

    state = {"entered": False}

    def _fake_run_from_snapshot(
        *,
        settings: Settings,
        snapshot: MarketSnapshot,
        allow_fallback: bool,
        memory_enabled: bool,
    ) -> RunArtifacts:
        if not state["entered"]:
            state["entered"] = True
            strategy = StrategyPlan(
                strategy_family="trend_following",
                action="buy",
                timeframe="swing",
                entry_logic="Enter with the uptrend.",
                invalidation_logic="Exit below EMA20.",
                confidence=0.75,
            )
            risk = RiskPlan(
                position_size_pct=0.1,
                stop_loss=snapshot.last_close - 2.0,
                take_profit=snapshot.last_close + 1.0,
                risk_reward_ratio=2.0,
                max_holding_bars=10,
                notes="Backtest risk plan.",
            )
            execution = ExecutionDecision(
                approved=True,
                side="buy",
                symbol=snapshot.symbol,
                entry_price=snapshot.last_close,
                stop_loss=risk.stop_loss,
                take_profit=risk.take_profit,
                position_size_pct=risk.position_size_pct,
                confidence=0.75,
                rationale="Enter test trade.",
            )
        else:
            strategy = StrategyPlan(
                strategy_family="no_trade",
                action="hold",
                timeframe="swing",
                entry_logic="No new entries.",
                invalidation_logic="No position.",
                confidence=0.7,
            )
            risk = RiskPlan(
                position_size_pct=0.01,
                stop_loss=max(snapshot.last_close - 1.0, 0.01),
                take_profit=snapshot.last_close + 1.0,
                risk_reward_ratio=1.0,
                max_holding_bars=5,
                notes="Idle risk plan.",
            )
            execution = ExecutionDecision(
                approved=False,
                side="hold",
                symbol=snapshot.symbol,
                entry_price=snapshot.last_close,
                stop_loss=risk.stop_loss,
                take_profit=risk.take_profit,
                position_size_pct=risk.position_size_pct,
                confidence=0.7,
                rationale="No new trade.",
            )

        return RunArtifacts(
            snapshot=snapshot,
            coordinator=ResearchCoordinatorBrief(
                market_focus="trend_following",
                priority_signals=["trend_alignment"],
                caution_flags=[],
                summary="Coordinator summary.",
            ),
            regime=RegimeAssessment(
                regime="trend_up",
                direction_bias="long",
                confidence=0.8,
                reasoning="Trend is up.",
            ),
            strategy=strategy,
            risk=risk,
            manager=ManagerDecision(
                approved=True,
                action_bias="buy" if execution.side == "buy" else "hold",
                confidence_cap=0.8,
                size_multiplier=1.0,
                rationale="Manager decision.",
            ),
            execution=execution,
            review=ReviewNote(
                summary="Review summary.",
                strengths=["Structured test"],
                warnings=[],
                next_checks=["Observe exit"],
            ),
        )

    monkeypatch.setattr(
        "agentic_trader.backtest.walk_forward.run_from_snapshot",
        _fake_run_from_snapshot,
    )

    report = run_walk_forward_backtest(
        settings=settings,
        symbol="AAPL",
        interval="1d",
        lookback="2y",
        warmup_bars=60,
        allow_fallback=False,
        frame=_frame(),
    )

    assert report.total_trades == 1
    assert report.closed_trades == 1
    assert report.win_rate == pytest.approx(1.0)
    assert report.ending_equity > report.starting_equity
    assert report.trades[0].exit_reason in {"take_profit", "end_of_data"}


def test_deterministic_baseline_backtest_returns_metrics(tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        default_cash=10_000.0,
    )
    settings.ensure_directories()

    report = run_deterministic_baseline_backtest(
        settings=settings,
        symbol="AAPL",
        interval="1d",
        lookback="2y",
        warmup_bars=60,
        frame=_frame(),
    )

    assert report.total_cycles == 40
    assert report.ending_equity > 0


def test_backtest_comparison_reports_deltas(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        default_cash=10_000.0,
    )
    settings.ensure_directories()

    monkeypatch.setattr(
        "agentic_trader.backtest.walk_forward.run_walk_forward_backtest",
        lambda **kwargs: BacktestReport(
            symbol="AAPL",
            interval="1d",
            lookback="2y",
            warmup_bars=60,
            total_cycles=40,
            total_trades=4,
            closed_trades=4,
            win_rate=0.75,
            expectancy=120.0,
            total_return_pct=0.12,
            max_drawdown_pct=0.04,
            exposure_pct=0.55,
            fallback_cycles=0,
            starting_equity=10_000.0,
            ending_equity=11_200.0,
            trades=[],
        ),
    )
    monkeypatch.setattr(
        "agentic_trader.backtest.walk_forward.run_deterministic_baseline_backtest",
        lambda **kwargs: BacktestReport(
            symbol="AAPL",
            interval="1d",
            lookback="2y",
            warmup_bars=60,
            total_cycles=40,
            total_trades=3,
            closed_trades=3,
            win_rate=0.66,
            expectancy=80.0,
            total_return_pct=0.08,
            max_drawdown_pct=0.03,
            exposure_pct=0.48,
            fallback_cycles=0,
            starting_equity=10_000.0,
            ending_equity=10_800.0,
            trades=[],
        ),
    )

    comparison = run_backtest_comparison(
        settings=settings,
        symbol="AAPL",
        interval="1d",
        lookback="2y",
        warmup_bars=60,
        allow_fallback=False,
        frame=_frame(),
    )

    assert comparison.ending_equity_delta == pytest.approx(400.0)
    assert comparison.total_return_delta_pct == pytest.approx(0.04)


def test_memory_ablation_backtest_reports_deltas(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        default_cash=10_000.0,
    )
    settings.ensure_directories()

    calls: list[bool] = []

    def _fake_run_walk_forward_backtest(**kwargs) -> BacktestReport:
        memory_enabled = bool(kwargs["memory_enabled"])
        calls.append(memory_enabled)
        if memory_enabled:
            return BacktestReport(
                symbol="AAPL",
                interval="1d",
                lookback="2y",
                warmup_bars=60,
                total_cycles=40,
                total_trades=4,
                closed_trades=4,
                win_rate=0.75,
                expectancy=120.0,
                total_return_pct=0.12,
                max_drawdown_pct=0.04,
                exposure_pct=0.55,
                fallback_cycles=0,
                starting_equity=10_000.0,
                ending_equity=11_200.0,
                trades=[],
            )
        return BacktestReport(
            symbol="AAPL",
            interval="1d",
            lookback="2y",
            warmup_bars=60,
            total_cycles=40,
            total_trades=3,
            closed_trades=3,
            win_rate=0.66,
            expectancy=80.0,
            total_return_pct=0.08,
            max_drawdown_pct=0.03,
            exposure_pct=0.48,
            fallback_cycles=0,
            starting_equity=10_000.0,
            ending_equity=10_800.0,
            trades=[],
        )

    monkeypatch.setattr(
        "agentic_trader.backtest.walk_forward.run_walk_forward_backtest",
        _fake_run_walk_forward_backtest,
    )

    ablation = run_memory_ablation_backtest(
        settings=settings,
        symbol="AAPL",
        interval="1d",
        lookback="2y",
        warmup_bars=60,
        allow_fallback=False,
        frame=_frame(),
    )

    assert calls == [True, False]
    assert ablation.ending_equity_delta == pytest.approx(400.0)
    assert ablation.total_return_delta_pct == pytest.approx(0.04)
