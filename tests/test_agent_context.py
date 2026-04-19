from pathlib import Path

import pandas as pd

from agentic_trader.agents.context import build_agent_context, render_agent_context
from agentic_trader.config import Settings
from agentic_trader.features import build_decision_feature_bundle
from agentic_trader.llm.client import LocalLLM
from agentic_trader.market.features import build_snapshot
from agentic_trader.schemas import (
    ExecutionDecision,
    ManagerDecision,
    MarketContextHorizon,
    MarketContextPack,
    MarketSnapshot,
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
    """
    Create a RunArtifacts object populated with fixed example market, research, strategy, risk, manager, execution, and review data.
    
    Parameters:
        symbol (str): Ticker symbol to use in the generated MarketSnapshot and ExecutionDecision (default "AAPL").
    
    Returns:
        RunArtifacts: A deterministic set of example artifacts including:
            - snapshot: MarketSnapshot with price, indicators, returns, volume ratio, and bars_analyzed
            - coordinator: ResearchCoordinatorBrief with market focus, priority signals, and summary
            - regime: RegimeAssessment with regime, direction bias, confidence, and reasoning
            - strategy: StrategyPlan describing strategy family, action, timeframe, entry/invalidation logic, and confidence
            - risk: RiskPlan with position sizing, stop/take-profit, reward ratio, holding limit, and notes
            - manager: ManagerDecision with approval, bias, confidence cap, size multiplier, and rationale
            - execution: ExecutionDecision with approval, side, symbol, prices, sizing, confidence, and rationale
            - review: ReviewNote summarizing strengths, warnings, and next checks
    """
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


def test_settings_and_llm_route_models_by_role() -> None:
    settings = Settings(
        model_name="qwen3:8b",
        risk_model_name="qwen3:14b",
        explainer_model_name="llama3.1:8b",
    )
    llm = LocalLLM(settings)

    assert settings.model_for_role("strategy") == "qwen3:8b"
    assert settings.model_for_role("risk") == "qwen3:14b"
    assert llm.for_role("explainer").model_name == "llama3.1:8b"


def test_build_agent_context_includes_runs_memory_and_upstream(tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    persist_run(settings=settings, artifacts=_artifacts())
    db = TradingDatabase(settings)

    context = build_agent_context(
        role="manager",
        settings=settings,
        db=db,
        snapshot=_artifacts().snapshot,
        tool_outputs=["news_tool: no event risk detected"],
        upstream_context={"coordinator": _artifacts().coordinator},
    )

    assert context.model_name == "qwen3:8b"
    assert context.recent_runs
    assert context.memory_notes
    assert context.calibration is not None
    assert context.market_session is not None
    assert context.market_session.symbol == "AAPL"
    assert context.tool_outputs[0].startswith("market_session:")
    assert context.tool_outputs[1] == "news_tool: disabled"
    assert context.tool_outputs[2:] == ["news_tool: no event risk detected"]
    assert "coordinator" in context.upstream_context


def test_build_agent_context_can_disable_memory_injection(tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    persist_run(settings=settings, artifacts=_artifacts())
    db = TradingDatabase(settings)

    context = build_agent_context(
        role="strategy",
        settings=settings,
        db=db,
        snapshot=_artifacts().snapshot,
        memory_enabled=False,
    )

    assert context.recent_runs
    assert context.memory_notes == []
    assert context.retrieved_memories == []


def test_render_agent_context_surfaces_market_context_pack(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        {
            "open": [100 + i for i in range(90)],
            "high": [101 + i for i in range(90)],
            "low": [99 + i for i in range(90)],
            "close": [100 + i for i in range(90)],
            "volume": [1_000 + (i * 10) for i in range(90)],
        }
    )
    snapshot = build_snapshot(frame, symbol="AAPL", interval="1d", lookback="90d")
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    context = build_agent_context(
        role="coordinator",
        settings=settings,
        db=db,
        snapshot=snapshot,
        memory_enabled=False,
    )

    rendered = render_agent_context(context, task="Assess context.")

    assert "Market Context Pack:" in rendered
    assert '"lookback": "90d"' in rendered
    assert "No persisted market context pack" not in rendered


def test_render_agent_context_prefers_structured_features_when_available(
    tmp_path: Path,
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    snapshot = _artifacts().snapshot.model_copy(
        update={
            "context_pack": MarketContextPack(
                symbol="AAPL",
                interval="1d",
                lookback="180d",
                interval_semantics="business-day approximation",
                window_start="2025-01-01",
                window_end="2025-06-30",
                bars_analyzed=120,
                higher_timeframe="same_as_base",
                higher_timeframe_used=False,
                horizons=[
                    MarketContextHorizon(
                        horizon_bars=20,
                        available_bars=20,
                        return_pct=0.09,
                        trend_vote="bullish",
                    )
                ],
                data_quality_flags=[
                    "partial_lookback_coverage",
                    "higher_timeframe_fallback",
                ],
                summary="AAPL partial context",
            )
        }
    )
    decision_features = build_decision_feature_bundle(snapshot, settings=settings)
    context = build_agent_context(
        role="coordinator",
        settings=settings,
        db=db,
        snapshot=snapshot,
        decision_features=decision_features,
        memory_enabled=False,
    )

    rendered = render_agent_context(context, task="Assess context.")

    assert "Feature Input:" in rendered
    assert "price_anchor=100.0" in rendered
    assert "quality_flags=partial_lookback_coverage,higher_timeframe_fallback" in rendered
    assert "Market Context Pack:" not in rendered
    assert "Market Snapshot:" not in rendered
