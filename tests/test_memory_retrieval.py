from pathlib import Path

import duckdb

from agentic_trader.config import Settings
from agentic_trader.memory.retrieval import retrieve_similar_memories
from agentic_trader.schemas import (
    ExecutionDecision,
    ManagerDecision,
    MarketSnapshot,
    RegimeAssessment,
    RegimeName,
    ResearchCoordinatorBrief,
    RiskPlan,
    ReviewNote,
    RunArtifacts,
    StrategyPlan,
)
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.workflows.run_once import persist_run


def _artifacts(
    symbol: str, *, close: float, return_5: float, regime: RegimeName
) -> RunArtifacts:
    """
    Constructs a synthetic RunArtifacts object containing a market snapshot and associated coordinator, regime, strategy, risk, manager, execution, and review data for a given symbol.

    Parameters:
        symbol (str): Ticker symbol for the snapshot and execution decision.
        close (float): Last close price used to derive indicator values.
        return_5 (float): Five-period return used to populate snapshot return fields.
        regime (RegimeName): Regime label that determines directional fields (e.g., long/buy for "trend_up", short/sell otherwise).

    Returns:
        RunArtifacts: A fully populated RunArtifacts instance with deterministic indicator values derived from `close`, snapshot returns derived from `return_5`, and directional/action fields set according to `regime`.
    """
    return RunArtifacts(
        snapshot=MarketSnapshot(
            symbol=symbol,
            interval="1d",
            last_close=close,
            ema_20=close * 0.99,
            ema_50=close * 0.97,
            atr_14=2.0,
            rsi_14=60.0 if regime == "trend_up" else 40.0,
            volatility_20=0.1,
            return_5=return_5,
            return_20=return_5 * 2,
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
            regime=regime,
            direction_bias="long" if regime == "trend_up" else "short",
            confidence=0.7,
            reasoning="Stored memory regime",
        ),
        strategy=StrategyPlan(
            strategy_family="trend_following",
            action="buy" if regime == "trend_up" else "sell",
            timeframe="swing",
            entry_logic="Stored entry",
            invalidation_logic="Stored invalidation",
            confidence=0.7,
        ),
        risk=RiskPlan(
            position_size_pct=0.05,
            stop_loss=close - 5,
            take_profit=close + 10,
            risk_reward_ratio=2.0,
            max_holding_bars=20,
            notes="Stored risk",
        ),
        manager=ManagerDecision(
            approved=True,
            action_bias="buy" if regime == "trend_up" else "sell",
            confidence_cap=0.7,
            size_multiplier=1.0,
            rationale="Stored manager",
        ),
        execution=ExecutionDecision(
            approved=True,
            side="buy" if regime == "trend_up" else "sell",
            symbol=symbol,
            entry_price=close,
            stop_loss=close - 5,
            take_profit=close + 10,
            position_size_pct=0.05,
            confidence=0.7,
            rationale="Stored execution",
        ),
        review=ReviewNote(
            summary="Stored review",
            strengths=["stored"],
            warnings=[],
            next_checks=["check"],
        ),
    )


def test_retrieve_similar_memories_prefers_closest_snapshot(tmp_path: Path) -> None:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
    )
    settings.ensure_directories()

    persist_run(
        settings=settings,
        artifacts=_artifacts("AAPL", close=100.0, return_5=0.03, regime="trend_up"),
    )
    persist_run(
        settings=settings,
        artifacts=_artifacts("MSFT", close=150.0, return_5=-0.08, regime="trend_down"),
    )
    db = TradingDatabase(settings)

    matches = retrieve_similar_memories(
        db,
        MarketSnapshot(
            symbol="NVDA",
            interval="1d",
            last_close=101.0,
            ema_20=100.0,
            ema_50=98.0,
            atr_14=2.0,
            rsi_14=59.0,
            volatility_20=0.1,
            return_5=0.025,
            return_20=0.05,
            volume_ratio_20=1.12,
            bars_analyzed=160,
        ),
        limit=2,
    )

    assert len(matches) == 2
    vectors = db.list_memory_vectors(limit=5)
    assert len(vectors) == 2
    metadata = db.conn.execute(
        """
        select embedding_provider, embedding_model, embedding_version, embedding_dimensions
        from memory_vectors
        where run_id = ?
        """,
        [vectors[0][0]],
    ).fetchone()
    assert metadata is not None
    assert metadata[0] == "local_hashing"
    assert metadata[1] == "agentic-hash-v1"
    assert metadata[2] == "1"
    assert metadata[3] == 64
    assert matches[0].symbol == "AAPL"
    assert matches[0].retrieval_source == "hybrid"
    assert matches[0].vector_score is not None
    assert matches[0].heuristic_score is not None
    assert matches[0].similarity_score >= matches[1].similarity_score


def test_memory_vector_schema_migrates_legacy_rows(tmp_path: Path) -> None:
    database_path = tmp_path / "agentic_trader.duckdb"
    legacy = duckdb.connect(str(database_path))
    legacy.execute(
        """
        create table memory_vectors (
            run_id varchar primary key,
            created_at varchar not null,
            symbol varchar not null,
            embedding_json varchar not null,
            document_text varchar not null
        )
        """
    )
    legacy.execute(
        """
        insert into memory_vectors (
            run_id, created_at, symbol, embedding_json, document_text
        )
        values ('legacy-run', '2026-04-15T00:00:00+00:00', 'AAPL', '[0.0]', 'legacy')
        """
    )
    legacy.close()
    settings = Settings(runtime_dir=tmp_path, database_path=database_path)

    db = TradingDatabase(settings)
    row = db.conn.execute(
        """
        select embedding_provider, embedding_model, embedding_version, embedding_dimensions
        from memory_vectors
        where run_id = 'legacy-run'
        """
    ).fetchone()

    assert row is not None
    assert row[0] == "local_hashing"
    assert row[1] == "agentic-hash-v1"
    assert row[2] == "1"
    assert row[3] == 64
