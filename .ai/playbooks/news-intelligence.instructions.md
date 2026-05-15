# News Intelligence Playbook

Use this playbook when adding or reviewing news, filings, event, macro, social,
or browser-backed evidence collection.

The purpose is to build source-attributed market intelligence, not to let raw
web text steer the trading runtime.

If a provider, Firecrawl key, Camofox helper, browser process, API quota, or
official-source endpoint is unavailable, record the attempted source and the
failure category in the fetcher envelope. Continue only with lower-tier evidence
when it is clearly labeled as fallback; never upgrade missing news into positive
support for a trade idea.

## Operator Outcome

An operator should be able to ask:

- what happened to this symbol today?
- what changed across my watchlist this week?
- which sources are fresh, stale, blocked, paywalled, archived, or disabled?
- why did a scanner idea become a proposal or stay as watch-only?
- what evidence is missing before this can be trusted?

## Source Tiers

| Tier                           | Examples                                                                                              | Usage                                                         |
| ------------------------------ | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| Official / regulatory          | SEC company submissions/facts, exchange disclosures, issuer IR, central-bank and statistical releases | Preferred for durable facts and filings                       |
| Paid or structured market APIs | Alpaca, Polygon/Massive, Finnhub, FMP, IEX-style feeds                                                | Useful for normalized quotes, fundamentals, news, and events  |
| Reputable news                 | Reuters, AP, CNBC, FT, WSJ, Bloomberg, MarketWatch, official company newsrooms                        | Useful when freshness and attribution are preserved           |
| Browser or scraper fallback    | Firecrawl, Camofox, local browser fetchers, archive lookups                                           | Optional evidence helpers; must record fallback and staleness |
| Social/community               | X, Reddit, forums, influencer posts                                                                   | Watch-only unless corroborated by stronger tiers              |

## Query Templates

Use provider-specific APIs first. When a search provider is the right tool,
make the query explicit:

```text
{TICKER} stock news today
{COMPANY NAME} {TICKER} earnings guidance
{TICKER} SEC 8-K material event
semiconductor stocks news today
AI stocks news this week
oil stocks news {MONTH} {YEAR}
Federal Reserve rate decision dot plot {MONTH} {YEAR}
Treasury yields stocks today
FDA approval {COMPANY}
earnings surprise {COMPANY} {QUARTER}
```

For ambiguous tickers, include company name, exchange, sector, and region.
For V1, prefer US equities language unless the roadmap explicitly moves a
non-US source forward.

## Fetcher/Fallback Envelope

Any fetcher adapter should normalize into a small envelope:

```json
{
  "ok": true,
  "url": "https://source/article",
  "final_url": "https://source/article",
  "title": "Title",
  "summary": "Compact source-attributed summary",
  "source": "Reuters",
  "fetcher_source": "api|http|browser|archive|firecrawl|camofox",
  "published_at": "2026-05-06T12:00:00Z",
  "fetched_at": "2026-05-06T12:05:00Z",
  "freshness": "fresh|stale|unknown",
  "source_tier": "official|structured|news|fallback|social",
  "attempts": [
    { "fetcher": "api", "status": "blocked|ok|timeout|paywalled|not_found" }
  ],
  "classifications": ["ticker:AAPL", "sector:semiconductors", "event:earnings"],
  "materiality": "high|medium|low|unknown",
  "redacted": true
}
```

If no fetcher can produce a valid envelope, return an explicit unavailable
state to the caller instead of a blank summary. The caller should degrade to
digest/watch-only behavior or fail closed for proposal-sensitive flows.

Full article text, scraped HTML, provider stderr, and auth headers should stay
out of prompts, logs, snapshots, and QA artifacts.

## Envelope Field Definitions

`redacted` is a boolean evidence-state flag. Set `redacted: true` when full
article text, raw HTML, auth headers, cookies, provider stderr/stdout, PII, or
other sensitive content was removed before storage, logging, digest generation,
or prompt use. Set `redacted: false` only when the envelope was built from
non-sensitive title, timestamp, URL/source id, and compact summary fields and
no sensitive/raw payload was present. This flag complements central redaction:
redaction removes unsafe content, while `redacted` tells later reviewers that
removal happened.

## Firecrawl Use

Firecrawl is optional. Use it for search/scrape support when a normalized API
or official source does not cover the question.

Suggested development checks:

```bash
uv run --locked --all-extras --group dev python -c "from firecrawl import Firecrawl; print('firecrawl-sdk-ok')"
firecrawl --help
firecrawl scrape --help
firecrawl search --help
```

Runtime integration rules:

- disabled by default
- configured through environment variables stored in a local env file that is
  excluded from version control, or through a user-owned secret manager
- command timeouts and output caps
- central redaction on stdout/stderr
- source/freshness/materiality fields required
- raw markdown summarized before any prompt-facing use

## Camofox Use

Camofox is optional browser infrastructure. Use it only when a local browser
fetcher is explicitly configured and health-checked.

Runtime integration rules:

- bind to loopback
- health check before use
- fail closed on timeout, non-loopback URL, or malformed payload
- do not pass browser HTML/raw screenshots to trading prompts
- record browser health separately from evidence trust

## Freshness Rules

- `published_at` from the source is stronger than search-result date.
- `fetched_at` proves retrieval time, not article freshness.
- archive/browser fallback can be useful, but it must be marked stale or
  unknown unless the source timestamp is clear.
- "No news found" is not positive evidence; record sources tried and whether the
  search was rate-limited, blocked, or empty.

## Materiality Rules

Classify each event before proposal review:

- `high`: earnings, guidance, regulatory filing, major order, M&A, credit event,
  halt, lawsuit, downgrade/upgrade with clear source, macro shock
- `medium`: sector move, analyst commentary, product launch, insider disclosure,
  supply-chain development
- `low`: generic market wrap, duplicated article, unsourced commentary
- `unknown`: missing timestamp/source/body or failed fetch

Materiality should change confidence and review priority, not bypass approval.

## Negative Tests

Add tests for:

- malformed JSON from fetcher
- timeout
- blocked/paywalled response
- archive/stale result
- missing `published_at`
- fake secret in provider error
- raw body accidentally entering prompt context
- social/community evidence with no corroboration
- provider disabled by default

## Review Output

```text
Question:
Sources tried:
Fresh sources:
Stale/blocked/missing sources:
Material events:
Affected symbols/sectors:
Proposal impact:
Evidence that must not enter prompts:
Tests added:
```
