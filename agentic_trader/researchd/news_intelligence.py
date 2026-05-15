"""News/source planning helpers for source-attributed market intelligence.

This module does not fetch the web. It exposes the runtime-facing query,
source-tier, freshness, and prompt-safety contracts that sidecar providers and
operators can use before a scanner idea is promoted into a proposal.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field

SourceTier = Literal[
    "official_or_regulatory",
    "tier_1_direct",
    "tier_2_browser_or_archive",
    "tier_3_archive_stale",
    "noisy_or_excluded",
    "unknown",
]
QueryKind = Literal["ticker", "company", "sector", "macro", "event"]
FetcherSource = Literal[
    "official_api",
    "search_api",
    "direct_http",
    "browser",
    "archive",
    "manual",
    "unknown",
]
FreshnessState = Literal["fresh", "delayed", "stale", "unknown"]
MaterialityLevel = Literal["high", "medium", "low", "unknown"]

FINANCE_EXCLUDE_PATTERNS = (
    r"youtube\.com",
    r"twitter\.com",
    r"x\.com",
    r"linkedin\.com",
    r"facebook\.com",
    r"reddit\.com",
)

MATERIAL_EVENT_TYPES = (
    "earnings_or_guidance",
    "management_change",
    "merger_or_acquisition",
    "regulatory_or_legal",
    "product_or_customer",
    "capital_structure",
    "macro_policy",
    "sector_supply_demand",
)


@dataclass(frozen=True)
class SourceTierProfile:
    tier: SourceTier
    domains: tuple[str, ...]
    fetcher_expectation: str
    trading_note: str

    def to_payload(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class NewsQueryTemplate:
    kind: QueryKind
    query: str
    freshness_hint: str
    materiality_hint: str

    def to_payload(self) -> dict[str, object]:
        return asdict(self)


class NewsEvidenceContract(BaseModel):
    """Formal normalized event/article shape for proposal-grade news evidence."""

    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1)
    source_tier: SourceTier
    title: str = Field(min_length=1)
    url: str | None = None
    published_at: str | None = None
    fetched_at: str = Field(min_length=1)
    fetcher_source: FetcherSource
    attempts: tuple[str, ...]
    freshness: FreshnessState
    symbols: tuple[str, ...]
    sector: str | None
    macro_theme: str | None
    event_type: str | None
    materiality: MaterialityLevel
    summary: str = Field(min_length=1)
    redacted: bool


SOURCE_TIER_PROFILES: tuple[SourceTierProfile, ...] = (
    SourceTierProfile(
        tier="official_or_regulatory",
        domains=(
            "sec.gov",
            "investor.apple.com",
            "investor.microsoft.com",
            "ir.aboutamazon.com",
            "nvidianews.nvidia.com",
        ),
        fetcher_expectation="direct_or_official_api",
        trading_note="Prefer for filings, earnings releases, and company-confirmed events.",
    ),
    SourceTierProfile(
        tier="tier_1_direct",
        domains=("reuters.com", "cnbc.com", "theguardian.com", "stockanalysis.com"),
        fetcher_expectation="direct_http_or_search_snippet",
        trading_note="Useful fresh reporting, but still cross-check before proposal review.",
    ),
    SourceTierProfile(
        tier="tier_2_browser_or_archive",
        domains=(
            "marketwatch.com",
            "barrons.com",
            "seekingalpha.com",
            "bloomberg.com",
            "ft.com",
        ),
        fetcher_expectation="browser_or_archive_fallback",
        trading_note="Surface fetcher_source and archive staleness before trusting it.",
    ),
    SourceTierProfile(
        tier="tier_3_archive_stale",
        domains=("wsj.com", "nytimes.com", "theinformation.com"),
        fetcher_expectation="archive_fallback_likely",
        trading_note="Treat as stale or corroborating evidence until a fresher source agrees.",
    ),
    SourceTierProfile(
        tier="noisy_or_excluded",
        domains=(
            "youtube.com",
            "twitter.com",
            "x.com",
            "linkedin.com",
            "facebook.com",
            "reddit.com",
        ),
        fetcher_expectation="excluded_from_default_search",
        trading_note="Do not use as primary V1 trade evidence.",
    ),
)


def classify_source_tier(source_or_url: str) -> SourceTier:
    """Classify a source name or URL into the source tier used by researchd."""

    normalized = _normalize_source(source_or_url)
    if not normalized:
        return "unknown"
    for profile in SOURCE_TIER_PROFILES:
        if any(
            normalized == domain or normalized.endswith(f".{domain}")
            for domain in profile.domains
        ):
            return profile.tier
    return "unknown"


def news_research_plan(
    *,
    symbol: str,
    company_name: str | None = None,
    sector: str | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    """Build a source-attributed research plan for a ticker or scanner candidate."""

    clean_symbol = symbol.strip().upper()
    if not clean_symbol:
        raise ValueError("symbol is required")
    timestamp = now or datetime.now(UTC)
    month_year = timestamp.strftime("%B %Y")
    company = (company_name or "").strip()
    sector_name = (sector or "").strip()
    queries = _query_templates(
        symbol=clean_symbol,
        company_name=company or None,
        sector=sector_name or None,
        month_year=month_year,
    )
    return {
        "symbol": clean_symbol,
        "company_name": company or None,
        "sector": sector_name or None,
        "generated_at": timestamp.isoformat().replace("+00:00", "Z"),
        "preferred_engine": "google_news",
        "exclude_regex": list(FINANCE_EXCLUDE_PATTERNS),
        "query_templates": [query.to_payload() for query in queries],
        "source_tiers": [profile.to_payload() for profile in SOURCE_TIER_PROFILES],
        "material_event_types": list(MATERIAL_EVENT_TYPES),
        "evidence_contract": news_evidence_contract_payload(),
        "freshness_policy": {
            "published_at_required_for_event_trade": True,
            "archive_fetcher_source_is_stale": True,
            "unknown_age_requires_secondary_source": True,
            "max_primary_sources_for_digest": 5,
        },
        "prompt_policy": {
            "raw_article_text_allowed_in_core_trading_prompt": False,
            "allowed_prompt_payload": (
                "compact normalized summary, source tier, published_at, "
                "fetcher_source, materiality, citations, and missing fields"
            ),
        },
        "sidecar_policy": {
            "provider_boundary": "researchd",
            "broker_or_policy_mutation_allowed": False,
            "fail_closed_on_missing_sources": True,
        },
    }


def news_evidence_contract_payload() -> dict[str, object]:
    """Return the formal news evidence schema exposed to sidecar adapters."""

    return {
        "schema_name": "NewsEvidenceContract",
        "code_path": "agentic_trader.researchd.news_intelligence.NewsEvidenceContract",
        "json_schema": NewsEvidenceContract.model_json_schema(),
    }


def _query_templates(
    *,
    symbol: str,
    company_name: str | None,
    sector: str | None,
    month_year: str,
) -> tuple[NewsQueryTemplate, ...]:
    templates: list[NewsQueryTemplate] = [
        NewsQueryTemplate(
            kind="ticker",
            query=f"{symbol} stock news {month_year}",
            freshness_hint="fresh ticker news with temporal anchor",
            materiality_hint="look for earnings, guidance, M&A, legal, or product catalysts",
        ),
        NewsQueryTemplate(
            kind="ticker",
            query=f"{symbol} earnings guidance {month_year}",
            freshness_hint="reporting-season catalyst search",
            materiality_hint="earnings surprise, guidance change, margin commentary",
        ),
        NewsQueryTemplate(
            kind="event",
            query=f"{symbol} analyst upgrade downgrade {month_year}",
            freshness_hint="fresh rating-change search",
            materiality_hint="rating, target price, estimate revision, or downgrade risk",
        ),
    ]
    if company_name:
        templates.extend(
            [
                NewsQueryTemplate(
                    kind="company",
                    query=f"{company_name} {symbol} news {month_year}",
                    freshness_hint="company-name disambiguation for ticker collisions",
                    materiality_hint="confirm the article is about the intended issuer",
                ),
                NewsQueryTemplate(
                    kind="event",
                    query=f"{company_name} CEO CFO guidance acquisition lawsuit",
                    freshness_hint="event-driven company search",
                    materiality_hint="management, guidance, M&A, or legal catalyst",
                ),
            ]
        )
    if sector:
        templates.append(
            NewsQueryTemplate(
                kind="sector",
                query=f"{sector} stocks news this week {month_year}",
                freshness_hint="sector breadth and peer-move check",
                materiality_hint="sector tailwind/headwind that can explain a scanner move",
            )
        )
    templates.append(
        NewsQueryTemplate(
            kind="macro",
            query=f"US CPI Fed rates jobs report market reaction {month_year}",
            freshness_hint="macro risk backdrop for US equities",
            materiality_hint="rates, inflation, jobs, liquidity, and risk appetite",
        )
    )
    return tuple(templates)


def _normalize_source(source_or_url: str) -> str:
    value = source_or_url.strip().lower()
    if not value:
        return ""
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = parsed.netloc or parsed.path
    if host.startswith("www."):
        host = host[4:]
    return host.split("/")[0]
