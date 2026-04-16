"""Yahoo-backed fallback providers kept behind the canonical provider boundary."""

from agentic_trader.config import Settings
from agentic_trader.market.data import fetch_ohlcv
from agentic_trader.market.news import fetch_news_brief
from agentic_trader.providers.base import (
    market_snapshot_from_frame,
    metadata,
    source_attribution,
    utc_now_iso,
)
from agentic_trader.providers.interfaces import MarketDataResult
from agentic_trader.schemas import NewsEvent, ProviderMetadata, SymbolIdentity


class YahooMarketDataProvider:
    """Fallback market-data provider that wraps the existing yfinance path."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def metadata(self) -> ProviderMetadata:
        return metadata(
            provider_id="yahoo_market",
            name="Yahoo Finance Market Data",
            provider_type="market",
            role="fallback",
            priority=80,
            enabled=True,
            requires_network=self._settings.market_data_mode != "prefer_cache",
            notes=[f"market_data_mode={self._settings.market_data_mode}"],
        )

    def get_market_data(
        self, symbol: SymbolIdentity, *, interval: str, lookback: str
    ) -> MarketDataResult:
        frame = fetch_ohlcv(
            symbol.symbol,
            interval=interval,
            lookback=lookback,
            settings=self._settings,
        )
        snapshot = market_snapshot_from_frame(
            frame,
            symbol=symbol,
            interval=interval,
            lookback=lookback,
            attribution=source_attribution(
                source_name="yahoo_finance",
                provider_type="market",
                source_role="fallback",
                fetched_at=utc_now_iso(),
                freshness="unknown",
                confidence=0.65,
                completeness=1.0 if not frame.empty else 0.0,
                notes=[f"market_data_mode={self._settings.market_data_mode}"],
            ),
        )
        return MarketDataResult(frame=frame, snapshot=snapshot)


class YahooNewsProvider:
    """Optional yfinance headline provider normalized into canonical news events."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def metadata(self) -> ProviderMetadata:
        return metadata(
            provider_id="yahoo_news",
            name="Yahoo Finance News",
            provider_type="news",
            role="fallback",
            priority=80,
            enabled=self._settings.news_mode == "yfinance",
            requires_network=True,
            notes=[f"news_mode={self._settings.news_mode}"],
        )

    def get_news(self, symbol: SymbolIdentity, *, limit: int) -> list[NewsEvent]:
        if self._settings.news_mode != "yfinance":
            return []
        events: list[NewsEvent] = []
        for item in fetch_news_brief(symbol.symbol, self._settings)[:limit]:
            events.append(
                NewsEvent(
                    symbol=symbol.symbol,
                    title=item.title,
                    category="sector_level",
                    source=item.publisher,
                    published_at=item.published_at,
                    summary=item.title[:240],
                    relevance_score=0.45,
                    url=item.link,
                    attribution=source_attribution(
                        source_name="yahoo_finance_news",
                        provider_type="news",
                        source_role="fallback",
                        fetched_at=utc_now_iso(),
                        freshness="unknown",
                        confidence=0.45,
                        completeness=0.5,
                        notes=["raw_headline_normalized"],
                    ),
                )
            )
        return events
