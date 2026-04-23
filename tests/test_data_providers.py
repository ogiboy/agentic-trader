from pathlib import Path

from agentic_trader.config import Settings
from agentic_trader.features import build_decision_feature_bundle
from agentic_trader.providers import (
    ProviderSet,
    build_canonical_analysis_snapshot,
    default_provider_set,
)
from agentic_trader.providers.interfaces import (
    DisclosureProvider,
    FundamentalDataProvider,
    MacroDataProvider,
    MarketDataProvider,
    NewsProvider,
)
from agentic_trader.providers.local import (
    LocalDisclosureProvider,
    LocalFundamentalProvider,
    LocalMacroProvider,
)
from agentic_trader.providers.public_sources import (
    FinnhubFundamentalProvider,
    FmpFundamentalProvider,
    KapDisclosureProvider,
    SecEdgarFundamentalProvider,
)
from agentic_trader.providers.yahoo import YahooMarketDataProvider, YahooNewsProvider
from agentic_trader.schemas import (
    ExecutionDecision,
    DisclosureEvent,
    FundamentalSnapshot,
    InvestmentPreferences,
    MacroSnapshot,
    MarketContextPack,
    MarketSnapshot,
    NewsSignal,
    NewsEvent,
    ProviderMetadata,
    RegimeAssessment,
    ResearchCoordinatorBrief,
    ReviewNote,
    RiskPlan,
    RunArtifacts,
    StrategyPlan,
    ManagerDecision,
    SymbolIdentity,
)
from agentic_trader.storage.db import TradingDatabase


def _settings(tmp_path: Path | None = None) -> Settings:
    if tmp_path is None:
        return Settings(news_mode="off")
    return Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        market_data_cache_dir=tmp_path / "market_cache",
        news_mode="off",
    )


def _snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        symbol="AAPL",
        interval="1d",
        as_of="2026-01-30",
        last_close=105.0,
        ema_20=102.0,
        ema_50=99.0,
        atr_14=2.0,
        rsi_14=61.0,
        volatility_20=0.12,
        return_5=0.03,
        return_20=0.09,
        volume_ratio_20=1.2,
        mtf_alignment="bullish",
        mtf_confidence=0.72,
        bars_analyzed=120,
        context_pack=MarketContextPack(
            symbol="AAPL",
            interval="1d",
            lookback="180d",
            interval_semantics="business-day approximation",
            window_start="2025-08-01",
            window_end="2026-01-30",
            bars_analyzed=120,
            coverage_ratio=0.95,
            higher_timeframe="1wk",
            higher_timeframe_used=True,
            summary="AAPL context summary",
        ),
    )


def test_default_provider_adapters_conform_to_interfaces() -> None:
    """
    Verify default provider adapter classes implement their expected provider interfaces.
    
    Asserts that the default provider classes instantiate as the corresponding interface types:
    - YahooMarketDataProvider -> MarketDataProvider
    - LocalFundamentalProvider, SecEdgarFundamentalProvider, FinnhubFundamentalProvider, FmpFundamentalProvider -> FundamentalDataProvider
    - YahooNewsProvider -> NewsProvider
    - LocalDisclosureProvider, KapDisclosureProvider -> DisclosureProvider
    - LocalMacroProvider -> MacroDataProvider
    """
    settings = _settings()

    assert isinstance(YahooMarketDataProvider(settings), MarketDataProvider)
    assert isinstance(LocalFundamentalProvider(settings), FundamentalDataProvider)
    assert isinstance(SecEdgarFundamentalProvider(settings), FundamentalDataProvider)
    assert isinstance(FinnhubFundamentalProvider(settings), FundamentalDataProvider)
    assert isinstance(FmpFundamentalProvider(settings), FundamentalDataProvider)
    assert isinstance(YahooNewsProvider(settings), NewsProvider)
    assert isinstance(LocalDisclosureProvider(settings), DisclosureProvider)
    assert isinstance(KapDisclosureProvider(settings), DisclosureProvider)
    assert isinstance(LocalMacroProvider(settings), MacroDataProvider)


def test_canonical_snapshot_preserves_attribution_and_missing_sections() -> None:
    """
    Validate that building a canonical analysis snapshot preserves source attributions, records missing sections, and retains key snapshot metadata.
    
    Asserts that the canonical snapshot for the sample market:
    - has symbol "AAPL";
    - marks the market attribution `source_role` as "inferred";
    - contains 120 market rows;
    - classifies the first news event as "company_specific";
    - lists "fundamentals" and "disclosures" in `missing_sections`;
    - includes sources named "sec_edgar" and "kap_disclosures" in `source_attributions`.
    """
    snapshot = build_canonical_analysis_snapshot(
        _snapshot(),
        settings=_settings(),
        preferences=InvestmentPreferences(),
        news_items=[
            NewsSignal(
                symbol="AAPL",
                title="AAPL reports stronger services demand",
                publisher="ExampleWire",
            )
        ],
    )

    assert snapshot.symbol_identity.symbol == "AAPL"
    assert snapshot.market.attribution.source_role == "inferred"
    assert snapshot.market.rows == 120
    assert snapshot.news_events[0].category == "company_specific"
    assert "fundamentals" in snapshot.missing_sections
    assert "disclosures" in snapshot.missing_sections
    assert any(
        source.source_name == "sec_edgar"
        for source in snapshot.source_attributions
    )
    assert any(
        source.source_name == "kap_disclosures"
        for source in snapshot.source_attributions
    )


def test_decision_bundle_consumes_canonical_snapshot() -> None:
    settings = _settings()
    canonical = build_canonical_analysis_snapshot(
        _snapshot(),
        settings=settings,
        news_items=[
            NewsSignal(
                symbol="AAPL",
                title="Fed rates pressure technology stocks",
                publisher="MacroWire",
            )
        ],
    )
    bundle = build_decision_feature_bundle(
        _snapshot(),
        settings=settings,
        canonical_snapshot=canonical,
    )

    assert "sec_edgar" in bundle.fundamental.data_sources
    assert bundle.macro.news_signals[0].category == "macro_level"
    assert bundle.macro.data_sources[0] == "local_macro_scaffold"


def test_default_provider_ladder_names_public_sources() -> None:
    default_set = default_provider_set(_settings())

    assert [item.metadata().provider_id for item in default_set.market] == [
        "yahoo_market"
    ]
    assert [item.metadata().provider_id for item in default_set.fundamental] == [
        "sec_edgar_fundamentals",
        "finnhub_fundamentals",
        "fmp_fundamentals",
        "local_fundamental_scaffold",
    ]
    assert [item.metadata().provider_id for item in default_set.disclosures] == [
        "kap_disclosures",
        "local_disclosure_scaffold",
    ]


def test_empty_provider_outputs_are_visible_in_canonical_attribution() -> None:
    canonical = build_canonical_analysis_snapshot(
        _snapshot(),
        settings=_settings(),
        news_items=None,
    )

    source_names = {source.source_name for source in canonical.source_attributions}

    assert "news" in canonical.missing_sections
    assert "disclosures" in canonical.missing_sections
    assert "yahoo_news" in source_names
    assert "kap_disclosures" in source_names


class _FailingFundamentalProvider:
    def metadata(self) -> ProviderMetadata:
        """
        Metadata describing this fundamental data provider.
        
        @returns ProviderMetadata: The provider's identifier, display name, and capabilities (e.g., supported symbols, data types, and rate/limit hints).
        """
        return LocalFundamentalProvider(_settings()).metadata()

    def get_fundamental_data(self, symbol: SymbolIdentity) -> FundamentalSnapshot:
        _ = symbol
        raise RuntimeError("fundamental down")


class _FailingMacroProvider:
    def metadata(self) -> ProviderMetadata:
        return LocalMacroProvider(_settings()).metadata()

    def get_macro_context(self, symbol: SymbolIdentity) -> MacroSnapshot:
        _ = symbol
        raise RuntimeError("macro down")


class _FailingNewsProvider:
    def metadata(self) -> ProviderMetadata:
        return YahooNewsProvider(_settings()).metadata()

    def get_news(self, symbol: SymbolIdentity, *, limit: int) -> list[NewsEvent]:
        _ = symbol
        raise RuntimeError(f"news down {limit}")


class _FailingDisclosureProvider:
    def metadata(self) -> ProviderMetadata:
        return LocalDisclosureProvider(_settings()).metadata()

    def get_disclosures(
        self, symbol: SymbolIdentity, *, limit: int
    ) -> list[DisclosureEvent]:
        _ = symbol
        raise RuntimeError(f"disclosures down {limit}")


def test_aggregation_marks_provider_failures_without_fabricating_data() -> None:
    canonical = build_canonical_analysis_snapshot(
        _snapshot(),
        settings=_settings(),
        providers=ProviderSet(
            fundamental=[_FailingFundamentalProvider()],
            macro=[_FailingMacroProvider()],
            news=[_FailingNewsProvider()],
            disclosures=[_FailingDisclosureProvider()],
        ),
    )

    assert canonical.fundamental.attribution.source_role == "missing"
    assert canonical.macro.attribution.source_role == "missing"
    assert "fundamentals" in canonical.missing_sections
    assert "macro" in canonical.missing_sections
    assert any(
        source.source_name == "provider_aggregation_errors"
        for source in canonical.source_attributions
    )


def _artifacts(canonical_snapshot) -> RunArtifacts:
    return RunArtifacts(
        snapshot=_snapshot(),
        canonical_snapshot=canonical_snapshot,
        coordinator=ResearchCoordinatorBrief(
            market_focus="trend_following",
            summary="Coordinator summary.",
        ),
        regime=RegimeAssessment(
            regime="trend_up",
            direction_bias="long",
            confidence=0.8,
            reasoning="Trend up.",
        ),
        strategy=StrategyPlan(
            strategy_family="trend_following",
            action="buy",
            timeframe="1d",
            entry_logic="Breakout continuation.",
            invalidation_logic="Close below support.",
            confidence=0.7,
        ),
        risk=RiskPlan(
            position_size_pct=0.05,
            stop_loss=99.0,
            take_profit=115.0,
            risk_reward_ratio=2.0,
            max_holding_bars=10,
            notes="Risk plan.",
        ),
        manager=ManagerDecision(
            approved=True,
            action_bias="buy",
            confidence_cap=0.7,
            size_multiplier=1.0,
            rationale="Manager rationale.",
        ),
        execution=ExecutionDecision(
            approved=True,
            side="buy",
            symbol="AAPL",
            entry_price=105.0,
            stop_loss=99.0,
            take_profit=115.0,
            position_size_pct=0.05,
            confidence=0.7,
            rationale="Execution rationale.",
        ),
        review=ReviewNote(summary="Review summary."),
    )


def test_trade_context_persists_canonical_snapshot(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.ensure_directories()
    canonical = build_canonical_analysis_snapshot(
        _snapshot(),
        settings=settings,
        news_items=[],
    )
    db = TradingDatabase(settings)
    try:
        db.persist_trade_context(
            trade_id="trade-test",
            run_id="run-test",
            artifacts=_artifacts(canonical),
        )
        record = db.latest_trade_context()
    finally:
        db.close()

    assert record is not None
    assert record.canonical_snapshot is not None
    assert record.canonical_snapshot.symbol_identity.symbol == "AAPL"
