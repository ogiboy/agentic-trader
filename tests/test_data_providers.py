from pathlib import Path

from agentic_trader.config import Settings
from agentic_trader.features import build_decision_feature_bundle
from agentic_trader.providers import (
    ProviderSet,
    build_canonical_analysis_snapshot,
    default_provider_set,
)
from agentic_trader.providers.aggregation import (
    _collect_disclosures,
    _collect_provider_news,
    _first_fundamental_snapshot,
)
from agentic_trader.providers.base import metadata, source_attribution, utc_now_iso
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
        source.source_name == "sec_edgar" for source in snapshot.source_attributions
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

    assert bundle.fundamental.data_sources == ["fundamental_provider_unavailable"]
    assert any(
        source.source_name == "sec_edgar" for source in canonical.source_attributions
    )
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


def test_sec_edgar_fundamental_provider_normalizes_companyfacts() -> None:
    settings = Settings(
        news_mode="off",
        research_sec_edgar_enabled=True,
        research_sec_edgar_user_agent="Agentic Trader test contact@example.com",
        request_timeout_seconds=999,
    )
    calls: list[str] = []

    def fake_fetcher(url, headers, timeout_seconds):
        calls.append(url)
        assert headers["User-Agent"] == "Agentic Trader test contact@example.com"
        assert headers["Accept"] == "application/json"
        assert timeout_seconds == 30.0
        if url == "https://www.sec.gov/files/company_tickers.json":
            return {
                "0": {
                    "cik_str": 320193,
                    "ticker": "AAPL",
                    "title": "Apple Inc.",
                }
            }
        if url == "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json":
            return _sec_companyfacts_payload()
        raise AssertionError(f"unexpected SEC URL: {url}")

    provider = SecEdgarFundamentalProvider(settings, fetcher=fake_fetcher)
    snapshot = provider.get_fundamental_data(SymbolIdentity(symbol="AAPL"))

    assert calls == [
        "https://www.sec.gov/files/company_tickers.json",
        "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json",
    ]
    assert snapshot.attribution.source_role == "primary"
    assert snapshot.attribution.freshness == "fresh"
    assert snapshot.attribution.completeness == 1.0
    assert "sec_companyfacts_api" in snapshot.attribution.notes
    assert "raw_filing_text_not_downloaded" in snapshot.attribution.notes
    assert snapshot.missing_fields == []
    assert snapshot.revenue_growth is not None
    assert 0.19 < snapshot.revenue_growth < 0.21
    assert snapshot.profitability_stability == 0.25
    assert snapshot.cash_flow_alignment == 1.0
    assert snapshot.debt_risk == 0.3
    assert snapshot.reinvestment_potential == 0.2
    assert "Apple Inc." in snapshot.summary


def test_sec_edgar_fundamental_provider_requires_opt_in_before_network() -> None:
    provider = SecEdgarFundamentalProvider(
        Settings(news_mode="off", research_sec_edgar_enabled=False),
        fetcher=_rejecting_sec_fetcher,
    )

    snapshot = provider.get_fundamental_data(SymbolIdentity(symbol="AAPL"))

    assert snapshot.attribution.source_role == "missing"
    assert "provider_disabled" in snapshot.attribution.notes


def test_sec_edgar_fundamental_provider_requires_user_agent_before_network() -> None:
    provider = SecEdgarFundamentalProvider(
        Settings(
            news_mode="off",
            research_sec_edgar_enabled=True,
            research_sec_edgar_user_agent="",
        ),
        fetcher=_rejecting_sec_fetcher,
    )

    snapshot = provider.get_fundamental_data(SymbolIdentity(symbol="AAPL"))

    assert snapshot.attribution.source_role == "missing"
    assert "sec_user_agent_missing" in snapshot.attribution.notes


def test_sec_edgar_fundamental_provider_skips_non_us_symbols_before_network() -> None:
    provider = SecEdgarFundamentalProvider(
        Settings(
            news_mode="off",
            research_sec_edgar_enabled=True,
            research_sec_edgar_user_agent="Agentic Trader test contact@example.com",
        ),
        fetcher=_rejecting_sec_fetcher,
    )

    snapshot = provider.get_fundamental_data(
        SymbolIdentity(symbol="AKBNK.IS", region="TR", currency="TRY")
    )

    assert snapshot.attribution.source_role == "missing"
    assert "unsupported_region=TR" in snapshot.attribution.notes


def test_sec_edgar_companyfacts_growth_ignores_non_research_forms() -> None:
    settings = Settings(
        news_mode="off",
        research_sec_edgar_enabled=True,
        research_sec_edgar_user_agent="Agentic Trader test contact@example.com",
    )

    def fake_fetcher(url, headers, timeout_seconds):
        _ = (headers, timeout_seconds)
        if url == "https://www.sec.gov/files/company_tickers.json":
            return {
                "0": {
                    "cik_str": 320193,
                    "ticker": "AAPL",
                    "title": "Apple Inc.",
                }
            }
        if url == "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json":
            return _sec_companyfacts_payload(
                extra_revenue_facts=[
                    {
                        "val": 999.0,
                        "end": "2025-01-31",
                        "filed": "2025-02-01",
                        "form": "10-Q",
                        "fp": "Q1",
                        "frame": "CY2025Q1",
                    },
                    {
                        "val": 888.0,
                        "end": "2025-02-28",
                        "filed": "2025-03-01",
                        "form": "8-K",
                    }
                ]
            )
        raise AssertionError(f"unexpected SEC URL: {url}")

    provider = SecEdgarFundamentalProvider(settings, fetcher=fake_fetcher)
    snapshot = provider.get_fundamental_data(SymbolIdentity(symbol="AAPL"))

    assert snapshot.revenue_growth is not None
    assert 0.19 < snapshot.revenue_growth < 0.21


def test_canonical_snapshot_selects_sec_companyfacts_fundamentals() -> None:
    settings = Settings(
        news_mode="off",
        research_sec_edgar_enabled=True,
        research_sec_edgar_user_agent="Agentic Trader test contact@example.com",
    )
    provider = SecEdgarFundamentalProvider(
        settings,
        fetcher=_sec_success_fetcher(_sec_companyfacts_payload()),
    )

    canonical = build_canonical_analysis_snapshot(
        _snapshot(),
        settings=settings,
        providers=ProviderSet(fundamental=[provider]),
    )

    assert canonical.fundamental.attribution.source_name == "sec_edgar"
    assert canonical.fundamental.attribution.source_role == "primary"
    assert "fundamentals" not in canonical.missing_sections
    assert any(
        source.source_name == "sec_edgar" for source in canonical.source_attributions
    )


def test_canonical_snapshot_marks_partial_sec_companyfacts_missing_sections() -> None:
    settings = Settings(
        news_mode="off",
        research_sec_edgar_enabled=True,
        research_sec_edgar_user_agent="Agentic Trader test contact@example.com",
    )
    provider = SecEdgarFundamentalProvider(
        settings,
        fetcher=_sec_success_fetcher(_sec_companyfacts_payload(include_cash=False)),
    )

    canonical = build_canonical_analysis_snapshot(
        _snapshot(),
        settings=settings,
        providers=ProviderSet(fundamental=[provider]),
    )

    assert canonical.fundamental.attribution.source_name == "sec_edgar"
    assert canonical.fundamental.attribution.source_role == "primary"
    assert "fundamentals" in canonical.missing_sections
    assert "company_fact:cash" in canonical.fundamental.missing_fields
    assert "reinvestment_potential" in canonical.fundamental.missing_fields


def test_sec_edgar_fundamental_provider_redacts_fetch_errors() -> None:
    settings = Settings(
        news_mode="off",
        research_sec_edgar_enabled=True,
        research_sec_edgar_user_agent="Agentic Trader test contact@example.com",
    )

    def fake_fetcher(url, headers, timeout_seconds):
        _ = (url, headers, timeout_seconds)
        raise ValueError("api_key=secret-sec")

    provider = SecEdgarFundamentalProvider(settings, fetcher=fake_fetcher)
    snapshot = provider.get_fundamental_data(SymbolIdentity(symbol="AAPL"))

    payload = snapshot.model_dump_json()
    assert snapshot.attribution.source_role == "missing"
    assert "secret-sec" not in payload
    assert "<redacted>" in payload


def _rejecting_sec_fetcher(url, headers, timeout_seconds):
    _ = (url, headers, timeout_seconds)
    raise AssertionError("SEC fetcher should not be called")


def _sec_success_fetcher(payload: dict[str, object]):
    def fake_fetcher(url, headers, timeout_seconds):
        _ = (headers, timeout_seconds)
        if url == "https://www.sec.gov/files/company_tickers.json":
            return {
                "0": {
                    "cik_str": 320193,
                    "ticker": "AAPL",
                    "title": "Apple Inc.",
                }
            }
        if url == "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json":
            return payload
        raise AssertionError(f"unexpected SEC URL: {url}")

    return fake_fetcher


def _sec_companyfacts_payload(
    *,
    include_cash: bool = True,
    extra_revenue_facts: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    def fact(value: float, filed: str) -> dict[str, object]:
        return {
            "val": value,
            "end": filed.removesuffix("-01") + "-28",
            "filed": filed,
            "form": "10-K",
            "fy": int(filed[:4]),
            "fp": "FY",
        }

    revenue_facts = [
        fact(100.0, "2023-11-01"),
        fact(120.0, "2024-11-01"),
        *(extra_revenue_facts or []),
    ]
    us_gaap: dict[str, object] = {
        "RevenueFromContractWithCustomerExcludingAssessedTax": {
            "units": {"USD": revenue_facts}
        },
        "NetIncomeLoss": {"units": {"USD": [fact(30.0, "2024-11-01")]}},
        "Assets": {"units": {"USD": [fact(200.0, "2024-11-01")]}},
        "Liabilities": {"units": {"USD": [fact(60.0, "2024-11-01")]}},
        "NetCashProvidedByUsedInOperatingActivities": {
            "units": {"USD": [fact(35.0, "2024-11-01")]}
        },
    }
    if include_cash:
        us_gaap["CashAndCashEquivalentsAtCarryingValue"] = {
            "units": {"USD": [fact(40.0, "2024-11-01")]}
        }

    return {
        "entityName": "Apple Inc.",
        "facts": {
            "us-gaap": us_gaap,
        },
    }


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


def test_aggregation_redacts_provider_exception_secrets() -> None:
    class SecretFailingProvider(_FailingFundamentalProvider):
        def get_fundamental_data(self, symbol: SymbolIdentity) -> FundamentalSnapshot:
            _ = symbol
            raise RuntimeError("api_key=secret-fmp")

    canonical = build_canonical_analysis_snapshot(
        _snapshot(),
        settings=_settings(),
        providers=ProviderSet(fundamental=[SecretFailingProvider()]),
    )

    payload = canonical.model_dump_json()
    assert "secret-fmp" not in payload
    assert "<redacted>" in payload


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


class _MissingFundamentalProvider:
    def __init__(self, provider_id: str) -> None:
        self._provider_id = provider_id

    def metadata(self) -> ProviderMetadata:
        return metadata(
            provider_id=self._provider_id,
            name=self._provider_id,
            provider_type="fundamental",
            role="missing",
        )

    def get_fundamental_data(self, symbol: SymbolIdentity) -> FundamentalSnapshot:
        return FundamentalSnapshot(
            symbol_identity=symbol,
            attribution=source_attribution(
                source_name=self._provider_id,
                provider_type="fundamental",
                source_role="missing",
                fetched_at=utc_now_iso(),
                freshness="missing",
            ),
            missing_fields=["fundamental_snapshot"],
            summary=f"{self._provider_id} missing fundamentals.",
        )


class _MetadataFailingDisclosureProvider:
    def metadata(self) -> ProviderMetadata:
        raise RuntimeError("metadata offline")

    def get_disclosures(
        self, symbol: SymbolIdentity, *, limit: int
    ) -> list[DisclosureEvent]:
        _ = (symbol, limit)
        raise AssertionError("get_disclosures should not be called")


class _MetadataFailingNewsProvider:
    def metadata(self) -> ProviderMetadata:
        raise RuntimeError("metadata offline")

    def get_news(self, symbol: SymbolIdentity, *, limit: int) -> list[NewsEvent]:
        _ = (symbol, limit)
        raise AssertionError("get_news should not be called")


def test_all_missing_fundamental_providers_return_generic_missing_snapshot() -> None:
    symbol = SymbolIdentity(symbol="AAPL")

    snapshot, errors, extra_attributions = _first_fundamental_snapshot(
        [
            _MissingFundamentalProvider("provider_a"),
            _MissingFundamentalProvider("provider_b"),
        ],
        symbol,
    )

    assert snapshot.attribution.source_name == "fundamental_provider_unavailable"
    assert snapshot.summary == "No fundamental provider produced a snapshot."
    assert errors == []
    assert {item.source_name for item in extra_attributions} == {
        "provider_a",
        "provider_b",
    }


def test_collect_disclosures_records_metadata_failures_without_aborting() -> None:
    disclosures, errors, empty_attributions = _collect_disclosures(
        [_MetadataFailingDisclosureProvider(), LocalDisclosureProvider(_settings())],
        SymbolIdentity(symbol="AAPL"),
        limit=5,
    )

    assert disclosures == []
    assert any("metadata failed" in error for error in errors)
    assert empty_attributions


def test_collect_provider_news_records_metadata_failures_without_aborting() -> None:
    events, errors, empty_attributions = _collect_provider_news(
        [_MetadataFailingNewsProvider(), YahooNewsProvider(_settings())],
        SymbolIdentity(symbol="AAPL"),
        limit=5,
    )

    assert events == []
    assert any("metadata failed" in error for error in errors)
    assert empty_attributions
