# Continuous Research Loop Workflow

Use this workflow when designing or reviewing daemon-adjacent research,
news-monitoring, scanner, or proposal-preparation behavior.

This workflow is not an external orchestrator. It adapts the useful loop shape
into the existing Agentic Trader runtime and `researchd` sidecar boundaries.

If a provider, sidecar, model, broker status, or proposal queue check is
unavailable, the loop must surface that state in PRE-FLIGHT and either degrade
to digest-only evidence or fail closed. It must not continue as if the source is
healthy.

## Goal

Continuously maintain a reviewable market world-state without allowing research
or scanner logic to execute trades.

The safe loop shape is:

```text
PRE-FLIGHT -> MONITOR -> ANALYZE -> PROPOSE -> DIGEST -> sleep
```

## Phase Contract

| Phase      | Purpose                                                                                   | Allowed Actions                                                                               | Must Not Do                                                                                |
| ---------- | ----------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| PRE-FLIGHT | Check model/provider, broker backend, research providers, source health, and runtime mode | read `provider-diagnostics`, `v1-readiness`, `finance-ops`, `research-status`                 | call broker execution, hide missing providers, continue as if disabled sources are healthy |
| MONITOR    | Cheaply detect whether anything changed                                                   | read watchlist, last snapshot, source-health, portfolio/risk summaries, latest proposal queue | fetch every source every cycle, flood prompts with raw documents                           |
| ANALYZE    | Enrich changed symbols/sectors/macro themes                                               | run normalized provider fetches, idea scoring, materiality classification, freshness checks   | inject raw article/social text into trading prompts, treat stale archive evidence as fresh |
| PROPOSE    | Queue reviewable trade ideas when evidence clears gates                                   | create pending proposals only, with thesis/invalidation/source notes                          | approve, execute, mutate policy, or bypass risk gates                                      |
| DIGEST     | Persist compact cycle summary and operator evidence                                       | write snapshot links, source health, findings, missing data, proposal ids                     | write hidden policy memory or erase failed attempts                                        |

## Pre-Flight Checks

Before a loop cycle can spend real provider or browser work, confirm every item
in this checklist:

- runtime mode is explicit
- live execution is still blocked
- broker backend is known and paper-safe
- model/provider readiness is visible
- sidecar mode and backend are visible
- Firecrawl/Camofox/SEC or other providers are enabled only by explicit config
- source-health status includes disabled, stale, timeout, blocked, and degraded
  states
- no broker/runtime secrets are inherited by sidecar subprocesses
- proposal queue is readable and terminal states remain immutable

## Monitor Rules

Monitor work must stay cheap and structured:

- compare last world-state snapshot with the new one
- track watched symbols, sectors, and macro themes
- track portfolio exposure, HHI, top positions, and pending proposal count
- detect stale market data, wide spreads, halts, source outages, and missing
  provider evidence
- skip expensive analysis when nothing changed and no scheduled digest is due

## Analyze Rules

Analysis may gather evidence, but only normalized packets can cross into the
core decision layer. Every packet must preserve:

- `source`
- `fetcher_source`
- `published_at`
- `fetched_at`
- freshness/staleness
- source tier
- attempts/failure notes
- ticker, sector, macro, or event classification
- materiality
- summary or citation, not raw full text
- redaction status

If evidence comes from an archive, delayed feed, degraded API, or browser
fallback, the digest and proposal notes must say so.
Observer or research helper endpoints must stay loopback-only by default; any
intentional nonlocal exposure must be explicit, token-gated, and surfaced as an
operator security state rather than treated as normal local readiness.

## Proposal Rules

Proposal creation is allowed only when:

- source attribution is present
- materiality is explicit
- stale or missing evidence is named
- liquidity/spread warnings are included
- sizing is bounded by confidence, volatility, exposure, and concentration
- invalidation is written in operator language
- the proposal source says whether it came from scanner, research sidecar, or a
  manual operator idea

Approval is out of scope for the loop. Approval remains an explicit operator
action through the existing proposal/broker adapter boundary.

## Digest Rules

Each cycle digest must be small, durable, and inspectable:

```text
Cycle:
Mode:
Watchlist:
Sources checked:
Changed symbols/themes:
Findings:
Missing/stale evidence:
Risk/exposure notes:
Proposals queued:
Next scheduled run:
```

Digest memory is allowed to improve review and replay. It must not silently
change trading policy.

## Failure Behavior

Fail closed on:

- nonlocal observer/research exposure without explicit token
- missing provider credentials required for an enabled provider
- malformed provider payload
- secret-bearing provider error
- stale market data when freshness is required
- raw article/social text about to enter a prompt
- sidecar subprocess failure
- proposal approval requested outside explicit approval command

## Validation

Use these checks as the implementation matures:

```bash
uv run agentic-trader provider-diagnostics --json
uv run agentic-trader v1-readiness --json
uv run agentic-trader finance-ops --json
uv run agentic-trader research-status --json
uv run agentic-trader trade-proposals --json
uv run agentic-trader idea-presets --json
```

Add focused tests for:

- disabled provider remains visible
- stale/archive evidence downgrades confidence
- secret-bearing provider errors are redacted
- raw text is not passed into trading prompts
- sidecar cannot submit or approve proposals
- proposal terminal states cannot reopen
- cycle digest records failed fetch attempts
