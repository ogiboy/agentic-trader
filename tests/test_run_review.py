from pathlib import Path

from agentic_trader.cli import app
from agentic_trader.config import Settings
from agentic_trader.schemas import (
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
from agentic_trader.workflows.run_once import persist_run
from typer.testing import CliRunner


def _artifacts(symbol: str = "AAPL") -> RunArtifacts:
    return RunArtifacts(
        snapshot=MarketSnapshot(
            symbol=symbol,
            interval="1d",
            last_close=100.0,
            ema_20=101.0,
            ema_50=99.0,
            atr_14=2.0,
            rsi_14=55.0,
            volatility_20=0.12,
            return_5=0.02,
            return_20=0.08,
            volume_ratio_20=1.1,
            bars_analyzed=120,
        ),
        coordinator=ResearchCoordinatorBrief(
            market_focus="trend_following",
            priority_signals=["trend_alignment"],
            caution_flags=[],
            summary="Coordinator summary",
        ),
        regime=RegimeAssessment(
            regime="trend_up",
            direction_bias="long",
            confidence=0.7,
            reasoning="Test regime",
        ),
        strategy=StrategyPlan(
            strategy_family="trend_following",
            action="buy",
            timeframe="swing",
            entry_logic="Test entry",
            invalidation_logic="Test invalidation",
            confidence=0.7,
        ),
        risk=RiskPlan(
            position_size_pct=0.05,
            stop_loss=95.0,
            take_profit=110.0,
            risk_reward_ratio=2.0,
            max_holding_bars=20,
            notes="Test risk",
        ),
        manager=ManagerDecision(
            approved=True,
            action_bias="buy",
            confidence_cap=0.7,
            size_multiplier=1.0,
            rationale="Manager approved",
        ),
        execution=ExecutionDecision(
            approved=True,
            side="buy",
            symbol=symbol,
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=110.0,
            position_size_pct=0.05,
            confidence=0.7,
            rationale="Test execution",
        ),
        review=ReviewNote(
            summary="Review summary",
            strengths=["x"],
            warnings=[],
            next_checks=["y"],
        ),
    )


def test_review_run_and_export_report_commands(tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    persist_run(settings=settings, artifacts=_artifacts())

    runner = CliRunner()
    env = {
        "AGENTIC_TRADER_RUNTIME_DIR": str(tmp_path),
        "AGENTIC_TRADER_DATABASE_PATH": str(tmp_path / "agentic_trader.duckdb"),
    }

    review_result = runner.invoke(app, ["review-run"], env=env)
    export_path = tmp_path / "run-review.md"
    export_result = runner.invoke(app, ["export-report", "--output", str(export_path)], env=env)

    assert review_result.exit_code == 0
    assert "Run Review" in review_result.output
    assert export_result.exit_code == 0
    assert export_path.exists()
    assert "## Manager" in export_path.read_text(encoding="utf-8")
