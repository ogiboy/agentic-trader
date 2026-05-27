from importlib import import_module
from typing import cast

from agentic_trader.config import Settings
from agentic_trader.schemas import NewsSignal


def _news_items(symbol: str) -> list[object]:
    yfinance_module = import_module("yfinance")
    ticker_factory = getattr(yfinance_module, "Ticker")
    raw_items = getattr(ticker_factory(symbol), "news", []) or []
    return cast(list[object], raw_items) if isinstance(raw_items, list) else []


def fetch_news_brief(symbol: str, settings: Settings) -> list[NewsSignal]:
    if settings.news_mode == "off":
        return []

    try:
        raw_items = _news_items(symbol)
    except Exception:
        return []

    news: list[NewsSignal] = []
    for item in raw_items[: settings.news_headline_limit]:
        if not isinstance(item, dict):
            continue
        payload = cast(dict[str, object], item)
        provider_publish_time = payload.get("providerPublishTime")
        link = payload.get("link")
        news.append(
            NewsSignal(
                symbol=symbol,
                title=str(payload.get("title", "Untitled headline")),
                publisher=str(payload.get("publisher", "Unknown publisher")),
                published_at=(
                    str(provider_publish_time)
                    if provider_publish_time is not None
                    else None
                ),
                link=str(link) if link else None,
            )
        )
    return news
