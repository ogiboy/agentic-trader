from agentic_trader.config import Settings
from agentic_trader.schemas import NewsSignal

import yfinance as yf  # type: ignore[import-untyped]


def fetch_news_brief(symbol: str, settings: Settings) -> list[NewsSignal]:
    if settings.news_mode == "off":
        return []

    try:
        raw_items = getattr(yf.Ticker(symbol), "news", []) or []
    except Exception:
        return []

    news: list[NewsSignal] = []
    for item in raw_items[: settings.news_headline_limit]:
        if not isinstance(item, dict):
            continue
        news.append(
            NewsSignal(
                symbol=symbol,
                title=str(item.get("title", "Untitled headline")),
                publisher=str(item.get("publisher", "Unknown publisher")),
                published_at=(
                    str(item.get("providerPublishTime"))
                    if item.get("providerPublishTime") is not None
                    else None
                ),
                link=str(item.get("link")) if item.get("link") else None,
            )
        )
    return news
