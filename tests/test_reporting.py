from pathlib import Path

import pytest

from agentic_trader.config import Settings
from agentic_trader.engine.paper_broker import PaperBroker
from agentic_trader.schemas import (
    ExecutionDecision,
    ManagerDecision,
    MarketSnapshot,
    PositionExitDecision,
    RegimeAssessment,
    ResearchCoordinatorBrief,
    RiskPlan,
    ReviewNote,
    RunArtifacts,
    StrategyPlan,
)
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.workflows.run_once import persist_run


def _artifacts(symbol: str = "AAPL") -> RunArtifacts:
    return RunArtifacts(
        snapshot=MarketSnapshot(
            symbol=symbol,
            interval="1d",
            last_close=100.0,
            ema_20=102.0,
            ema_50=98.0,
            atr_14=2.0,
            rsi_14=58.0,
            volatility_20=0.12,
            return_5=0.03,
            return_20=0.09,
            volume_ratio_20=1.1,
            bars_analyzed=160,
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
            confidence=0.75,
            reasoning="Trend is aligned.",
        ),
        strategy=StrategyPlan(
            strategy_family="trend_following",
            action="buy",
            timeframe="swing",
            entry_logic="Buy while price stays above moving averages.",
            invalidation_logic="Exit on close below EMA20.",
            confidence=0.74,
        ),
        risk=RiskPlan(
            position_size_pct=0.1,
            stop_loss=95.0,
            take_profit=110.0,
            risk_reward_ratio=2.0,
            max_holding_bars=20,
            notes="Risk plan",
        ),
        manager=ManagerDecision(
            approved=True,
            action_bias="buy",
            confidence_cap=0.74,
            size_multiplier=1.0,
            rationale="Manager approved the trend setup.",
        ),
        execution=ExecutionDecision(
            approved=True,
            side="buy",
            symbol=symbol,
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=110.0,
            position_size_pct=0.1,
            confidence=0.74,
            rationale="Execution approved.",
        ),
        review=ReviewNote(
            summary="Review captured the approved long setup.",
            strengths=["Aligned trend"],
            warnings=[],
            next_checks=["Watch invalidation logic"],
        ),
    )


def test_persist_run_creates_trade_journal_and_account_mark(tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        default_cash=10_000.0,
    )
    settings.ensure_directories()

    order_id = persist_run(settings=settings, artifacts=_artifacts())

    db = TradingDatabase(settings)
    journal = db.list_trade_journal(limit=5)
    trade_context = db.latest_trade_context()
    marks = db.list_account_marks(limit=5)

    assert order_id.startswith("paper-")
    assert len(journal) == 1
    assert journal[0].entry_order_id == order_id
    assert journal[0].journal_status == "open"
    assert journal[0].symbol == "AAPL"
    assert trade_context is not None
    assert trade_context.symbol == "AAPL"
    assert trade_context.manager_rationale == "Manager approved the trend setup."
    assert len(marks) >= 1
    assert marks[0].source == "run_persisted"


def test_close_position_updates_trade_journal_and_risk_report(tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        default_cash=10_000.0,
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    broker = PaperBroker(db, settings)

    persist_run(settings=settings, artifacts=_artifacts("MSFT"))
    order_id = broker.close_position(
        PositionExitDecision(
            should_exit=True,
            side="sell",
            symbol="MSFT",
            reason="take_profit",
            rationale="Target reached.",
            exit_price=110.0,
        )
    )

    journal = db.list_trade_journal(limit=5)
    report = db.build_daily_risk_report()

    assert order_id.startswith("paper-")
    assert len(journal) == 1
    assert journal[0].journal_status == "closed"
    assert journal[0].exit_reason == "take_profit"
    assert journal[0].realized_pnl is not None
    assert report.fills_today >= 2
    assert report.marks_recorded >= 2


def test_risk_report_uses_portfolio_limit_thresholds(tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        default_cash=10_000.0,
        max_open_positions=2,
        max_gross_exposure_pct=0.2,
    )
    settings.ensure_directories()

    persist_run(settings=settings, artifacts=_artifacts("AAPL"))
    db = TradingDatabase(settings)
    db.settings.max_open_positions = 1
    db.settings.max_gross_exposure_pct = 0.05
    report = db.build_daily_risk_report()

    assert "Open position count is elevated." in report.warnings
    assert "Gross exposure is above 5% of equity." in report.warnings
    assert report.portfolio_hhi == pytest.approx(1.0)
    assert report.top_position_symbols == ["AAPL"]
    assert any(
        warning.startswith("Portfolio concentration HHI is elevated")
        for warning in report.warnings
    )
