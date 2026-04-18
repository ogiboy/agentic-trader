import pytest

from agentic_trader.config import Settings
from agentic_trader.features import (
    build_decision_feature_bundle,
    get_market_features,
    resolve_symbol_identity,
)
from agentic_trader.features.macro import classify_news_signal
from agentic_trader.schemas import (
    InvestmentPreferences,
    MarketContextHorizon,
    MarketContextPack,
    MarketSnapshot,
    NewsSignal,
)


def _snapshot() -> MarketSnapshot:
    context_pack = MarketContextPack(
        symbol="AAPL",
        interval="1d",
        lookback="180d",
        interval_semantics="business-day approximation",
        window_start="2025-01-01",
        window_end="2025-06-30",
        bars_analyzed=120,
        higher_timeframe="1wk",
        higher_timeframe_used=True,
        horizons=[
            MarketContextHorizon(
                horizon_bars=5,
                available_bars=5,
                return_pct=0.03,
                max_drawdown_pct=-0.02,
                trend_vote="bullish",
                support=98.0,
                resistance=106.0,
            ),
            MarketContextHorizon(
                horizon_bars=20,
                available_bars=20,
                return_pct=0.09,
                max_drawdown_pct=-0.05,
                trend_vote="bullish",
                support=92.0,
                resistance=110.0,
            ),
        ],
        summary="AAPL context summary",
    )
    return MarketSnapshot(
        symbol="AAPL",
        interval="1d",
        as_of="2025-06-30",
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
        context_pack=context_pack,
    )


def test_symbol_identity_uses_market_suffix_and_preferences() -> None:
    tr_identity = resolve_symbol_identity("akbnk.is")
    assert tr_identity.exchange == "BIST"
    assert tr_identity.currency == "TRY"
    assert tr_identity.region == "TR"

    preferences = InvestmentPreferences(
        regions=["EU"],
        exchanges=["XETRA"],
        currencies=["EUR"],
    )
    eu_identity = resolve_symbol_identity("SAP", preferences)
    assert eu_identity.exchange == "XETRA"
    assert eu_identity.currency == "EUR"
    assert eu_identity.region == "EU"


def test_market_features_summarize_context_pack() -> None:
    features = get_market_features(_snapshot())

    assert features.returns_by_window["5b"] == pytest.approx(0.03)
    assert features.returns_by_window["20b"] == pytest.approx(0.09)
    assert features.max_drawdown_pct == pytest.approx(-0.05)
    assert features.support == pytest.approx(92.0)
    assert features.resistance == pytest.approx(110.0)
    assert features.trend_classification == "bullish"


def test_decision_feature_bundle_keeps_provider_keys_out_of_payload() -> None:
    settings = Settings(
        finnhub_api_key="secret-finnhub",
        polygon_api_key="secret-polygon",
        massive_api_key="secret-massive",
    )
    bundle = build_decision_feature_bundle(
        _snapshot(),
        settings=settings,
        news_items=[
            NewsSignal(
                symbol="AAPL",
                title="AAPL reports better iPhone demand",
                publisher="ExampleWire",
            )
        ],
    )
    payload = bundle.model_dump_json()

    assert bundle.fundamental.data_sources == [
        "finnhub_configured",
        "polygon_configured",
        "massive_configured",
        "sec_filings_future_source",
    ]
    assert "secret" not in payload
    assert bundle.macro.news_signals[0].category == "company_specific"


def test_news_classification_detects_macro_context() -> None:
    identity = resolve_symbol_identity("AAPL")
    signal = classify_news_signal(
        NewsSignal(
            symbol="AAPL",
            title="Fed rate outlook pressures technology sector",
            publisher="MacroWire",
        ),
        symbol_identity=identity,
    )

    assert signal.category == "macro_level"
    assert signal.relevance_score >= 0.6
