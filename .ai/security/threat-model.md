# Security Hardening Threat Model

This document is the living security posture map for the local-first V1 runtime.
It covers operator-facing surfaces, sidecar boundaries, local artifacts, and CI
processes without changing the project's paper-first product scope.

## Assets And Trust Boundaries

| Asset | Why it matters | Boundary |
| --- | --- | --- |
| Runtime mode and execution gates | Prevents training/operation confusion and live execution drift | Python settings, CLI launch/service, broker adapter |
| Broker/account state | Contains cash, positions, fills, PnL, rejection reasons, and paper/live state | DuckDB, dashboard payloads, observer API, Web GUI |
| Provider credentials | Can authorize paid data, broker paper endpoints, LLM providers, Sonar, and future services | Ignored env files, Keychain, CI secrets |
| Research evidence | Can influence future memory and operator decisions | `researchd`, file-backed snapshots, CrewAI Flow sidecar |
| Operator commands | Start/stop/restart/runtime actions and preference instructions | CLI, Rich/Ink, Web GUI route handlers |
| Runtime artifacts | Logs, JSON feeds, evidence bundles, smoke artifacts, research snapshots | `runtime/`, `.ai/qa/artifacts/`, CI artifacts |

## Attack Surface Inventory

| Surface | Entry points | Trust boundary | Current controls | Residual concern |
| --- | --- | --- | --- | --- |
| CLI | Typer commands, env-backed settings, subprocess launch | Local terminal to runtime state | Schema validation, paper-first gates, explicit launch commands | Raw stderr/log output and permissive local artifacts can leak secrets |
| Rich/Ink TUI | Menu actions, chat/instruct flows | Interactive operator to runtime contracts | Uses existing CLI/runtime contracts | UI state confusion if payloads hide degraded truth |
| Web GUI routes | `/api/dashboard`, `/api/runtime`, `/api/chat`, `/api/instruct` | Browser to Python CLI subprocess | Same-origin checks, action/persona allowlists, `execFile` | Needs optional auth, size caps, cooldowns, redacted error responses |
| Observer API | `/health`, `/dashboard`, `/status`, `/logs`, `/supervisor`, broker/provider/research endpoints | HTTP client to read-only runtime truth | Read-only payloads, loopback default | Must reject non-loopback by default and support tokenized local sharing |
| Research sidecar | `research-refresh`, CrewAI Flow subprocess contract | Core runtime to isolated sidecar | Disabled by default, JSON contract, no broker/policy access | Prompt/data poisoning and sidecar stderr/env leakage |
| DuckDB/runtime files | DB, service logs, JSON feeds, research snapshots | Local filesystem | Ignored runtime artifacts | Multi-user machines can read world-readable artifacts |
| Env/secret management | `.env`, `.env.local`, Keychain, CI secrets | Developer/operator machine to runtime | Tracked examples only, Keychain helpers | Logs, errors, and artifacts need central redaction |
| CI/CD and releases | GitHub Actions, release, binaries, docs publish | Repo to public artifacts | Locked uv/pnpm, Sonar, branch release controls | Secret scan, SCA, provenance/signing are incremental hardening items |
| External advisory tools | RuFlo/Context7/GitHub/CodeRabbit/Sonar helpers | System-level development tooling to repo working tree | Repo guidance treats them as helpers only | Generated hooks, daemons, memory stores, or MCP configs can become accidental project state if not cleaned |

## Prioritized Risks

| Priority | Surface | STRIDE | Exploit scenario | Impact | Current controls | Added / recommended control | Verification test |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | Observer API | Information disclosure | Operator binds `--host 0.0.0.0`; another LAN client reads `/dashboard` or `/supervisor` | Runtime, broker, provider, and log truth leaks outside the local machine | Default host is `127.0.0.1`; API is read-only | Reject non-loopback bind by default; require `--allow-nonlocal` plus `AGENTIC_TRADER_OBSERVER_API_TOKEN`; add security headers | `tests/test_observer_api.py` nonlocal rejection and token-required cases |
| P0 | Web GUI route handlers | Spoofing, CSRF, DoS | Exposed dev server receives direct POSTs to start/restart runtime or run long chat/instruction jobs | Hidden runtime actions, resource exhaustion, operator confusion | Same-origin checks, action allowlist, `execFile` argv | Optional `AGENTIC_TRADER_WEBGUI_TOKEN`; loopback-only unauthenticated mode; body caps; per-route single-flight/cooldown | `pnpm --filter webgui run typecheck`, route/browser QA negative curl pass |
| P0 | Logs/artifacts | Information disclosure | Provider or LLM library prints `Authorization` or `*_SECRET_KEY`; Web/observer/CLI returns raw tail | Secrets leak into browser, observer payload, QA artifacts, screenshots | Secrets are kept out of tracked env files | Central redaction for CLI supervisor tails, Web error responses, sidecar failures, provider notes | `tests/test_security_helpers.py`, `tests/test_cli_json.py`, `tests/test_research_sidecar.py` |
| P1 | Research sidecar | Tampering, information disclosure | Sidecar inherits broker credentials or echoes raw provider stderr on malformed JSON | Broker/data secrets leak into research status; sidecar sees more authority than needed | Sidecar disabled by default, no broker calls in contract | Narrow subprocess env to shell/model/CrewAI variables; redact sidecar stdout/stderr | `test_crewai_backend_uses_subprocess_contract_without_core_imports` |
| P1 | Provider aggregation | Information disclosure | Future provider raises exception containing signed URL or `api_key=...`; note is persisted in source attribution | Secrets become part of decision/review context | Provider diagnostics avoid key values | Store provider id, exception type, bounded redacted message | `test_aggregation_redacts_provider_exception_secrets` |
| P1 | Runtime files | Information disclosure | Shared workstation user reads `runtime/*.jsonl`, DB, or service logs created as world-readable | Trading state, prompts, account truth, and evidence leak locally | `runtime/` ignored by git | Owner-only `0700` directories and `0600` runtime feed/log writes | `test_private_runtime_artifact_helpers_use_owner_only_modes` |
| P1 | Mode gates | Elevation, tampering | Operator or automation confuses training fallback with operation readiness | Paper actions based on diagnostic fallback or incomplete provider/model readiness | Operation requires strict LLM/provider readiness; live blocked | Keep mode labels visible across Web/Rich/Ink/observer; QA scenario must compare payloads | `.ai/qa/qa-scenarios.md` security posture smoke |
| P2 | Prompt/data poisoning | Tampering, repudiation | Raw web/social text instructs sidecar or model to ignore rules | Future memory pollution or misleading operator summaries | Raw web text is not injected; evidence/inference split exists | Trust tiering, normalized evidence packets only, provenance in every memory update | Research sidecar contract and future provider tests |
| P2 | CI/CD supply chain | Tampering, repudiation | Dependency, artifact, or binary workflow produces vulnerable or unverifiable release | Public artifacts become hard to trust | uv/pnpm locks, Sonar, release workflows | Dependabot, SCA/secret scan scripts, SBOM/checksums/signing as follow-up gates | PR checklist plus future security workflow |
| P2 | External advisory tooling | Tampering, elevation | Assistant init creates repo-local hooks, auto-commit helpers, daemon state, or MCP configs; later agents treat them as authoritative | Hidden workflow side effects, unexpected commands, repo noise, or architecture drift | External tools are documented as helpers only | Harvest useful process guidance into `.ai/workflows/`, `.ai/playbooks/`, `.ai/helpers/`, `.ai/skills/`, and `.ai/agents/`; delete generated tool-state folders after review | `git status --short` contains no accidental generated advisory folders, daemon logs, or external tool state |

## Immediately Applicable Checklist

- [ ] Keep Web GUI unauthenticated access loopback-only; set `AGENTIC_TRADER_WEBGUI_TOKEN` before exposing it through any proxy or LAN host.
- [ ] Keep observer API on `127.0.0.1`; use `--allow-nonlocal` only with `AGENTIC_TRADER_OBSERVER_API_TOKEN`.
- [ ] Run `agentic-trader supervisor-status --json` after failure paths and confirm log tails redact key-like values.
- [ ] Do not pass broker keys into research sidecars; only model/CrewAI provider env should cross that subprocess boundary.
- [ ] Treat `runtime/` and `.ai/qa/artifacts/` as sensitive local evidence; do not upload them unless scanned and intentionally attached.
- [ ] For any provider change, add a negative test where an exception contains a fake secret and confirm the persisted payload redacts it.
- [ ] For any Web GUI route change, test malformed JSON, oversized JSON, foreign Origin, missing token when token is configured, and repeated runtime actions.
- [ ] For any mode/runtime change, verify operation mode still fails closed and live execution remains blocked by default.
- [ ] For release work, keep lockfiles current, run `pnpm run version:plan`, and do not mutate `CHANGELOG.md` outside the release flow unless requested.
- [ ] After using external advisory init commands, confirm generated tool-state
  folders were harvested into self-contained `.ai/` guidance and removed, not
  tracked or hidden.
