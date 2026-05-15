# Security Policy

Agentic Trader is a local-first, paper-first trading runtime. Security reports
are welcome, especially when they affect local operator safety, secret
handling, execution gating, or research/provider isolation.

## Supported Versions

The project is pre-1.0. Security fixes target the active development branches
and the latest published release artifacts when they exist.

| Version / branch | Supported |
| ---------------- | --------- |
| `main`           | yes       |
| active V1 branch | yes       |
| older prerelease branches | best effort |
| unsupported forks or modified local deployments | no guarantee |

## What To Report

Please report vulnerabilities or hardening issues involving:

- live or paper execution gates being bypassed
- broker credentials, API keys, bearer tokens, or provider secrets leaking
- Web GUI route handlers accepting foreign-origin, oversized, or malformed
  mutating requests
- observer API or app-owned helper services binding outside loopback unexpectedly
- sidecars, Firecrawl, Camofox, or research providers injecting raw or poisoned
  content into trading prompts
- subprocess helpers executing unexpected commands or losing ownership state
- runtime logs, evidence bundles, QA artifacts, or dashboards exposing secrets
- proposal approval/reconciliation bypassing manual review
- training/operation mode confusion that can change trading behavior

Out of scope:

- results of paper trades or model predictions
- generic market-loss claims
- reports that require live trading, because live execution is intentionally
  blocked in the current runtime
- social engineering or denial-of-service against third-party providers

## How To Report

Use GitHub's private vulnerability reporting feature for this repository when
available. If that is not available, open a minimal public issue that says you
have a security report without posting exploit details, secrets, or private
logs.

Include:

- affected branch or commit
- affected command, route, or workflow
- clear reproduction steps
- expected and actual behavior
- whether secrets, broker state, runtime artifacts, or local network exposure
  are involved
- suggested mitigation if you have one

Do not include real API keys, broker credentials, account identifiers, or full
runtime artifacts in public issues.

## Response Expectations

For valid reports, maintainers aim to:

- acknowledge the report as soon as practical
- reproduce or ask clarifying questions
- decide whether the issue is a V1 blocker, V1 hardening task, or later
  follow-up
- credit the reporter when a fix is published, if they want credit

This is a small project, so response times may vary. Reports that include a
small, safe reproduction are much easier to triage.

## Security Posture

The intended defaults are:

- local-first operation
- paper broker by default
- live execution blocked
- loopback-only observer/Web/helper surfaces unless explicitly configured
- optional tokens for local Web GUI and observer exposure
- centralized redaction before logs and error payloads reach operator surfaces
- research sidecars as evidence companions only
- manual proposal approval before any broker adapter submission

If a change weakens one of these defaults, it should be treated as a security
regression unless an explicit design decision accepts the risk.
