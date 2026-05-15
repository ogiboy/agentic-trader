from datetime import UTC, datetime
from typing import cast

import pytest

from agentic_trader.researchd.news_intelligence import (
    NewsEvidenceContract,
    classify_source_tier,
    news_research_plan,
)


def test_news_research_plan_builds_source_attributed_queries() -> None:
    payload = news_research_plan(
        symbol="aapl",
        company_name="Apple",
        sector="consumer technology",
        now=datetime(2026, 5, 6, tzinfo=UTC),
    )

    assert payload["symbol"] == "AAPL"
    assert payload["preferred_engine"] == "google_news"
    queries = cast(list[dict[str, object]], payload["query_templates"])
    assert any(
        query["kind"] == "company"
        and "Apple AAPL news May 2026" in str(query["query"])
        for query in queries
    )
    freshness_policy = cast(dict[str, object], payload["freshness_policy"])
    assert freshness_policy["archive_fetcher_source_is_stale"] is True
    prompt_policy = cast(dict[str, object], payload["prompt_policy"])
    assert (
        prompt_policy["raw_article_text_allowed_in_core_trading_prompt"] is False
    )
    evidence_contract = cast(dict[str, object], payload["evidence_contract"])
    assert evidence_contract["schema_name"] == "NewsEvidenceContract"
    schema = cast(dict[str, object], evidence_contract["json_schema"])
    required = cast(list[str], schema["required"])
    assert "source" in required
    assert "summary" in required


def test_source_tier_classification_handles_urls_domains_and_noise() -> None:
    assert classify_source_tier("https://www.reuters.com/markets/") == "tier_1_direct"
    assert classify_source_tier("wsj.com") == "tier_3_archive_stale"
    assert classify_source_tier("https://x.com/example") == "noisy_or_excluded"
    assert classify_source_tier("unknown.example") == "unknown"


def test_news_research_plan_rejects_blank_symbol() -> None:
    with pytest.raises(ValueError, match="symbol is required"):
        news_research_plan(symbol=" ")


def test_news_evidence_contract_validates_required_source_fields() -> None:
    evidence = NewsEvidenceContract(
        source="Reuters",
        source_tier="tier_1_direct",
        title="Apple shares move after supplier update",
        published_at="2026-05-06T13:00:00Z",
        fetched_at="2026-05-06T13:05:00Z",
        fetcher_source="search_api",
        attempts=("api",),
        freshness="fresh",
        symbols=("AAPL",),
        sector="consumer technology",
        macro_theme=None,
        event_type="product_or_customer",
        materiality="medium",
        summary="Supplier commentary may affect near-term iPhone sentiment.",
        redacted=True,
    )

    assert evidence.source_tier == "tier_1_direct"
    assert evidence.fetcher_source == "search_api"
    assert not hasattr(evidence, "raw_text")

    with pytest.raises(ValueError, match="raw_text"):
        NewsEvidenceContract.model_validate(
            {
                "source": "Reuters",
                "source_tier": "tier_1_direct",
                "title": "Apple shares move after supplier update",
                "published_at": "2026-05-06T13:00:00Z",
                "fetched_at": "2026-05-06T13:05:00Z",
                "fetcher_source": "search_api",
                "attempts": ("api",),
                "freshness": "fresh",
                "symbols": ("AAPL",),
                "sector": "consumer technology",
                "macro_theme": None,
                "event_type": "product_or_customer",
                "materiality": "medium",
                "summary": "Supplier commentary may affect near-term iPhone sentiment.",
                "redacted": True,
                "raw_text": "full article text should not be accepted",
            }
        )
