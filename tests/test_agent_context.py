from pathlib import Path

import pandas as pd

from agentic_trader.agents.context import (
    _render_decision_feature_summary,
    build_agent_context,
    render_agent_context,
)
from agentic_trader.config import Settings
from agentic_trader.features import build_decision_feature_bundle
from agentic_trader.llm.client import LocalLLM
from agentic_trader.market.features import build_snapshot
from agentic_trader.schemas import (
    AgentContext,
    ExecutionDecision,
    InvestmentPreferences,
    ManagerDecision,
    MarketContextHorizon,
    MarketContextPack,
    MarketSnapshot,
    PortfolioSnapshot,
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
    decision_features = decision_features.model_copy(
        update={
            "fundamental": decision_features.fundamental.model_copy(
                update={
                    "revenue_growth": 0.12,
                    "profitability_stability": 0.74,
                    "cash_flow_alignment": 0.68,
                    "debt_risk": 0.22,
                    "reinvestment_potential": 0.61,
                    "data_sources": ["provider_fixture"],
                }
            )
        }
    )
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
    assert "revenue_growth=0.12" in rendered
    assert "profitability_stability=0.74" in rendered
    assert "cash_flow_alignment=0.68" in rendered
    assert "debt_risk=0.22" in rendered
    assert "reinvestment_potential=0.61" in rendered
    assert "sources=provider_fixture" in rendered
    assert "Market Context Pack:" not in rendered
    assert "Market Snapshot:" not in rendered


def test_render_decision_feature_summary_returns_placeholder_when_no_features(
    tmp_path: Path,
) -> None:
    snapshot = _artifacts().snapshot
    context = AgentContext(
        role="coordinator",
        model_name="test-model",
        snapshot=snapshot,
        decision_features=None,
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

    result = _render_decision_feature_summary(context)

    assert result == "No decision feature bundle is attached."


def test_render_decision_feature_summary_includes_fundamental_metrics_and_source_sections(
    tmp_path: Path,
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    snapshot = _artifacts().snapshot
    decision_features = build_decision_feature_bundle(snapshot, settings=settings)
    decision_features = decision_features.model_copy(
        update={
            "fundamental": decision_features.fundamental.model_copy(
                update={
                    "revenue_growth": 0.18,
                    "profitability_stability": 0.80,
                    "cash_flow_alignment": 0.72,
                    "debt_risk": 0.15,
                    "reinvestment_potential": 0.65,
                    "fx_exposure": "low",
                    "data_sources": ["sec_edgar", "finnhub"],
                    "quality_flags": ["partial_lookback_coverage"],
                    "as_of": "2025-06-30",
                }
            )
        }
    )
    context = AgentContext(
        role="fundamental",
        model_name="test-model",
        snapshot=snapshot,
        decision_features=decision_features,
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

    result = _render_decision_feature_summary(context)

    assert "Fundamental metrics:" in result
    assert "revenue_growth=0.18" in result
    assert "profitability_stability=0.8" in result
    assert "cash_flow_alignment=0.72" in result
    assert "debt_risk=0.15" in result
    assert "reinvestment_potential=0.65" in result
    assert "Fundamental source:" in result
    assert "fx_exposure=low" in result
    assert "sources=sec_edgar,finnhub" in result
    assert "flags=partial_lookback_coverage" in result
    assert "as_of=2025-06-30" in result


def test_render_agent_context_includes_market_snapshot_when_no_decision_features(
    tmp_path: Path,
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    snapshot = _artifacts().snapshot

    context = build_agent_context(
        role="coordinator",
        settings=settings,
        db=db,
        snapshot=snapshot,
        decision_features=None,
        memory_enabled=False,
    )

    rendered = render_agent_context(context, task="Assess context.")

    assert "Market Snapshot:" in rendered
    assert "Feature Input:" not in rendered


def test_render_agent_context_fallback_no_context_pack_message(
    tmp_path: Path,
) -> None:
    """When no decision features and no context_pack, render fallback message for context pack."""
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()
    db = TradingDatabase(settings)
    # Snapshot with no context_pack (default is None)
    snapshot = MarketSnapshot(
        symbol="AAPL",
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
    )
    assert snapshot.context_pack is None

    context = build_agent_context(
        role="coordinator",
        settings=settings,
        db=db,
        snapshot=snapshot,
        decision_features=None,
        memory_enabled=False,
    )

    rendered = render_agent_context(context, task="Check context.")

    assert "No persisted market context pack is attached." in rendered
    assert "Market Context Pack:" in rendered


def test_render_decision_feature_summary_includes_price_anchor_and_quality_flags(
    tmp_path: Path,
) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    snapshot = MarketSnapshot(
        symbol="TSLA",
        interval="1d",
        last_close=210.0,
        ema_20=205.0,
        ema_50=195.0,
        atr_14=5.0,
        rsi_14=65.0,
        volatility_20=0.18,
        return_5=0.05,
        return_20=0.12,
        volume_ratio_20=1.3,
        bars_analyzed=90,
        context_pack=MarketContextPack(
            symbol="TSLA",
            interval="1d",
            lookback="90d",
            interval_semantics="business-day approximation",
            window_start="2025-01-01",
            window_end="2025-06-30",
            bars_analyzed=90,
            higher_timeframe="same_as_base",
            higher_timeframe_used=False,
            horizons=[],
            data_quality_flags=["partial_lookback_coverage"],
            summary="TSLA context",
        ),
    )
    decision_features = build_decision_feature_bundle(snapshot, settings=settings)
    context = AgentContext(
        role="coordinator",
        model_name="test-model",
        snapshot=snapshot,
        decision_features=decision_features,
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

    result = _render_decision_feature_summary(context)

    # price_anchor should appear in Technical section
    assert "price_anchor=" in result
    # quality_flags should appear in Technical section
    assert "quality_flags=" in result
