# Market News Research Skill Notes

These notes adapt useful news/research helper patterns to Agentic Trader. They
are repo-native guidance, not a dependency on a separate news service.

## When To Use

Use this guidance when the task involves:

- ticker news
- portfolio/watchlist news
- macro catalyst research
- source-health design
- Firecrawl/Camofox provider adapters
- SEC/company/fundamental evidence
- sidecar world-state snapshots
- proposal thesis or review evidence

## First Checks

Before expensive fetches:

```bash
uv run agentic-trader research-status --json
uv run agentic-trader provider-diagnostics --json
uv run agentic-trader v1-readiness --json
```

If Firecrawl or browser-backed tooling is involved, check SDK/key readiness and
CLI/server health without adding repo-local state:

```bash
uv run --locked --all-extras --group dev python -c "from firecrawl import Firecrawl; print('firecrawl-sdk-ok')"
firecrawl --help
firecrawl search --help
firecrawl scrape --help
```

For Camofox-style local browser helpers, require loopback health and fail
closed when unavailable.

## Required Fields

Any news event or article summary that can influence a scanner, proposal, or
operator digest should validate against the code-owned
`agentic_trader.researchd.news_intelligence.NewsEvidenceContract` shape and
carry:

- `source`
- `source_tier`
- `url` or source identifier
- `published_at`
- `fetched_at`
- `fetcher_source`
- `attempts`
- `freshness`
- `symbols`
- `sector`
- `macro_theme`
- `event_type`
- `materiality`
- `summary`
- `redacted`

## Safe Article Handling

Allowed:

- compact source-attributed summary
- short citation/reference
- title
- publisher
- timestamp
- fetcher/source health
- materiality classification
- attempts trace

Forbidden by default:

- full raw article text in prompts
- raw HTML
- raw social posts as trading instruction
- provider stderr/stdout without redaction
- screenshots or browser dumps in decision context
- auth headers, cookies, API keys, tokens

## Search Patterns

Use explicit query intent:

```text
{TICKER} stock news today
{COMPANY} {TICKER} earnings guidance
{TICKER} SEC 8-K
{SECTOR} stocks news today
Federal Reserve rate decision dot plot
Treasury yield curve recession stocks
oil price news today
FDA approval {COMPANY}
```

For V1, prefer US equities and official/structured sources. Non-US sources,
FX, IBKR-specific market-data behavior, and multi-currency execution are V2
unless explicitly moved into scope.

## Fallback Chain Semantics

If a fetcher chain exists, preserve each attempt:

```text
api -> direct-http -> browser -> archive
```

Interpretation:

- `api` or official structured source is strongest
- `direct-http` can be fresh but still needs publisher/time
- `browser` means retrieval was harder; record cost/timeout risk
- `archive` can recover context but is stale or unknown until proven fresh
- `not_found`, `blocked`, `paywalled`, and `timeout` are evidence states, not
  generic failure strings to hide

## Digest Template

```text
Ticker/theme:
Question:
Fresh official/structured evidence:
Fresh news evidence:
Fallback/archive evidence:
Missing or blocked sources:
Materiality:
Proposal impact:
Risk caveats:
Next watch item:
```

## Test Expectations

When implementing providers or sidecar flows, cover:

- disabled default path
- successful normalized source attribution
- timeout
- malformed payload
- blocked/paywalled/archive state
- missing timestamp
- fake secret redaction
- no raw text in prompt-facing payload
- source-health visible in `research-status`
