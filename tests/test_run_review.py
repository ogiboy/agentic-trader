import json
import subprocess
from pathlib import Path

from agentic_trader.cli import app
from agentic_trader.config import Settings
from agentic_trader.providers import build_canonical_analysis_snapshot
from agentic_trader.schemas import (
    AgentStageTrace,
    CanonicalAnalysisSnapshot,
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


def _artifacts(
    symbol: str = "AAPL",
    canonical_snapshot: CanonicalAnalysisSnapshot | None = None,
) -> RunArtifacts:
    """
    Create a RunArtifacts test fixture populated with a MarketSnapshot and related analysis/decision objects.

    Parameters:
        symbol (str): Ticker symbol to use in the snapshot (default "AAPL").
        canonical_snapshot (CanonicalAnalysisSnapshot | None): Optional canonical analysis snapshot to attach to the returned RunArtifacts.

    Returns:
        RunArtifacts: A RunArtifacts instance with a MarketSnapshot (hardcoded indicators and bars_analyzed=120), coordinator, regime, strategy, risk, manager, execution, review, and a single agent trace. The provided canonical_snapshot is stored on the returned object when supplied.
    """
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
        canonical_snapshot=canonical_snapshot,
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
        agent_traces=[
            AgentStageTrace(
                role="coordinator",
                model_name="qwen3:8b",
                context_json='{"role":"coordinator"}',
                output_json='{"summary":"Coordinator summary"}',
                used_fallback=False,
            )
        ],
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
    trace_result = runner.invoke(app, ["trace-run"], env=env)
    export_path = tmp_path / "run-review.md"
    export_result = runner.invoke(
        app, ["export-report", "--output", str(export_path)], env=env
    )

    assert review_result.exit_code == 0
    assert trace_result.exit_code == 0
    assert "Run Review" in review_result.output
    assert "Fundamental" in review_result.output
    assert "Agent Trace" in trace_result.output
    assert export_result.exit_code == 0
    assert export_path.exists()
    assert "## Fundamental" in export_path.read_text(encoding="utf-8")
    assert "## Manager" in export_path.read_text(encoding="utf-8")
    assert "## Manager Conflicts" in export_path.read_text(encoding="utf-8")


def test_trade_context_surfaces_canonical_analysis(tmp_path: Path) -> None:
    """
    Verifies that the `trade-context` CLI command displays the canonical analysis and its expected subsections.

    Asserts that invoking `trade-context` with a persisted run containing a canonical analysis snapshot exits successfully and that the output contains the "Canonical Analysis" header, "Missing Sections", and the specific subsection keys: "fundamentals", "sec_edgar", and "local_macro_scaffold".

    Parameters:
        tmp_path (Path): Temporary directory provided by pytest used as the runtime directory and database location for the test.
    """
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        news_mode="off",
    )
    settings.ensure_directories()
    base_artifacts = _artifacts()
    canonical = build_canonical_analysis_snapshot(
        base_artifacts.snapshot,
        settings=settings,
        news_items=[],
    )
    persist_run(settings=settings, artifacts=_artifacts(canonical_snapshot=canonical))

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["trade-context"],
        env={
            "AGENTIC_TRADER_RUNTIME_DIR": str(tmp_path),
            "AGENTIC_TRADER_DATABASE_PATH": str(tmp_path / "agentic_trader.duckdb"),
            "AGENTIC_TRADER_NEWS_MODE": "off",
        },
    )

    assert result.exit_code == 0
    assert "Canonical Analysis" in result.output
    assert "Missing Sections" in result.output
    assert "fundamentals" in result.output
    assert "sec_edgar" in result.output
    assert "local_macro_scaffold" in result.output


def test_ink_review_surfaces_fundamental_truth() -> None:
    script = """
import { getFundamentalAssessmentLines } from './tui/review-lines.mjs';
const lines = getFundamentalAssessmentLines({
  overall_bias: 'supportive',
  risk_flags: ['high_debt_risk'],
  evidence_vs_inference: {
    evidence: ['revenue_growth=0.12'],
    inference: ['growth is broad-based'],
    uncertainty: ['provider lag possible'],
  },
});
console.log(JSON.stringify(lines));
"""
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=Path.cwd(),
        check=True,
        capture_output=True,
        text=True,
    )
    lines = json.loads(proc.stdout)

    assert lines == [
        "Fundamental Bias: supportive",
        "Fundamental Red Flags: high_debt_risk",
        "Fundamental Evidence: revenue_growth=0.12",
        "Fundamental Inference: growth is broad-based",
        "Fundamental Uncertainty: provider lag possible",
    ]


def test_ink_review_reads_canonical_analysis_snapshot() -> None:
    script = """
import { getCanonicalAnalysisLines } from './tui/review-lines.mjs';
const lines = getCanonicalAnalysisLines({
  snapshot: {
    summary: 'Canonical summary',
    completeness_score: 0.75,
    missing_sections: ['fundamentals'],
    market: { attribution: { source_name: 'polygon' } },
    fundamental: { attribution: { source_name: 'sec_edgar' } },
    macro: { attribution: { source_name: 'local_macro_scaffold' } },
    news_events: [{}, {}],
    disclosures: [{}],
    source_attributions: [
      { provider_type: 'market', source_name: 'polygon', source_role: 'primary', freshness: 'fresh' },
      { provider_type: 'fundamental', source_name: 'sec_edgar', source_role: 'missing', freshness: 'missing' },
    ],
  },
});
console.log(JSON.stringify(lines));
"""
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=Path.cwd(),
        check=True,
        capture_output=True,
        text=True,
    )
    lines = json.loads(proc.stdout)

    assert "Summary: Canonical summary" in lines
    assert "Completeness: 0.75" in lines
    assert "Missing: fundamentals" in lines
    assert "Fundamental Source: sec_edgar" in lines
    assert "Macro Source: local_macro_scaffold" in lines
    assert "Missing Sources: fundamental:sec_edgar" in lines
    assert "Sources Shown: 2/2" in lines
