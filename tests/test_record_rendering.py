from __future__ import annotations

import pytest
from rich.console import Console

from agentic_trader.cli_modules import record_rendering
from agentic_trader.schemas import (
    DailyRiskReport,
    InvestmentPreferences,
    MarketSnapshot,
    TradeContextRecord,
    TradeJournalEntry,
)


def _capture_record_rendering(monkeypatch: pytest.MonkeyPatch) -> Console:
    console = Console(record=True, width=160)
    monkeypatch.setattr(record_rendering, "console", console)
    return console


def test_record_rendering_prints_preferences_journal_and_risk_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = _capture_record_rendering(monkeypatch)

    record_rendering.render_preferences(
        InvestmentPreferences(
            regions=["US", "TR"],
            exchanges=["NASDAQ"],
            sectors=["technology"],
            notes="operator notes",
        )
    )
    record_rendering.render_trade_journal(
        [
            TradeJournalEntry(
                trade_id="trade-1",
                opened_at="2026-06-02T12:00:00Z",
                symbol="AAPL",
                entry_order_id="entry-1",
                planned_side="buy",
                approved=True,
                journal_status="open",
                entry_price=190.125,
                stop_loss=185,
                take_profit=205,
                position_size_pct=0.05,
                confidence=0.7,
                coordinator_focus="trend_following",
                strategy_family="trend",
                manager_bias="buy",
                review_summary="risk checked",
                notes="journal notes",
            )
        ]
    )
    record_rendering.render_risk_report(
        DailyRiskReport(
            report_date="2026-06-02",
            generated_at="2026-06-02T12:00:00Z",
            cash=1000,
            market_value=2000,
            equity=3000,
            realized_pnl=12.5,
            unrealized_pnl=-2.5,
            open_positions=1,
            fills_today=2,
            marks_recorded=1,
            daily_realized_pnl=12.5,
            gross_exposure_pct=0.2,
            largest_position_pct=0.2,
            drawdown_from_peak_pct=0.05,
            warnings=["exposure elevated"],
        )
    )
    output = console.export_text()

    assert "operator notes" in output
    assert "AAPL" in output
    assert "190.1250" in output
    assert "2026-06-02" in output
    assert "exposure elevated" in output


def test_record_rendering_handles_empty_and_unavailable_states(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = _capture_record_rendering(monkeypatch)

    record_rendering.render_trade_journal([])
    unavailable = record_rendering.render_unavailable_run_record(
        {"available": False, "error": "db locked"},
        None,
        unavailable_message="Run unavailable: {error}",
        empty_message="No runs.",
        empty_title="Run Review",
    )
    empty = record_rendering.render_unavailable_run_record(
        {"available": True, "error": None},
        None,
        unavailable_message="Run unavailable: {error}",
        empty_message="No runs.",
        empty_title="Run Review",
    )
    output = console.export_text()

    assert unavailable is True
    assert empty is True
    assert "db locked" in output
    assert "No runs." in output


def test_record_rendering_prints_trade_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console = _capture_record_rendering(monkeypatch)
    record = TradeContextRecord(
        trade_id="trade-1",
        created_at="2026-06-02T12:00:00Z",
        run_id="run-1",
        symbol="AAPL",
        market_snapshot=MarketSnapshot(
            symbol="AAPL",
            interval="1d",
            last_close=190,
            ema_20=188,
            ema_50=180,
            atr_14=3,
            rsi_14=55,
            volatility_20=0.2,
            return_5=0.01,
            return_20=0.04,
            volume_ratio_20=1.2,
            bars_analyzed=120,
        ),
        routed_models={"manager": "gpt-test"},
        retrieved_memory_summary={"manager": ["similar setup"]},
        tool_outputs={"risk": ["risk report"]},
        shared_memory_summary={"macro": ["macro note"]},
        manager_rationale="manager approved",
        execution_rationale="paper execution",
        execution_backend="paper",
        execution_adapter="paper",
        execution_outcome_status="accepted",
        review_summary="review passed",
        review_warnings=["watch drawdown"],
    )

    record_rendering.render_trade_context(
        record,
        canonical_analysis_lines=lambda _snapshot: ["canonical context"],
    )
    assert record_rendering.render_unavailable_trade_context(
        {"available": True, "record": record.model_dump(mode="json")},
        record,
    ) is False
    output = console.export_text()

    assert "trade-1" in output
    assert "gpt-test" in output
    assert "manager approved" in output
    assert "watch drawdown" in output
    assert "canonical context" in output
