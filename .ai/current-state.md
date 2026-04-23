# Current State

## Current Identity

The repository is already beyond an initial scaffold.
It has a meaningful local-first agent runtime, memory injection, role-based routing, operator chat, replay, and TUI surfaces.

## Known System Shape

Implemented or substantially present:

- strict runtime and launcher surfaces
- one-shot and continuous modes
- background runtime support
- provider adapter foundation with Ollama behind a provider boundary
- specialist + manager graph
- specialist consensus before manager execution
- execution guard
- DuckDB-backed paper broker
- operator preferences and curated behavior presets
- operator tone, strictness, and intervention presets across TUI and instruction parsing
- hybrid heuristic + vector-style similar-run retrieval
- shared memory bus across agent stages
- downside-aware confidence calibration from historical results
- memory explorer and retrieval inspection surfaces
- backtest and replay surfaces
- control room / monitor / TUI surfaces
- derived agent-activity summaries across the control-room surfaces
- daemon supervision metadata including launch counts, restart counts, terminal states, and stdout or stderr log tails
- operator chat and safe instruction parsing
- Ink chat now includes side-by-side live agent activity and reasoning/tool context instead of a transcript-only view
- a local observer API can now expose runtime contracts over HTTP for future WebUI attach flows
- a first local Web GUI now exists under `webgui/`; it uses a Next.js shell plus server-side route handlers that call the existing CLI/dashboard/runtime/chat/instruction contracts instead of adding a second runtime
- the Web GUI now also validates persona/runtime inputs at the route boundary, uses a sequence guard to prevent stale dashboard polls from overwriting newer state, and uses Next metadata/icon wiring plus `next/image` on the operator hero surface
- the repository now also ships a Fumadocs-based `docs/` app with curated MDX pages for onboarding, architecture, agent pipeline, runtime operations, operator surfaces, frontend guidance, memory/review, QA, and contribution workflow, turning the existing docs scaffold into the canonical developer-docs starting point
- the docs app now uses locale-prefixed English and Turkish routes (`/en/...` and `/tr/...`) with localized page trees, localized feedback copy, and a modular frontend split across home, feedback, layout, i18n, and content helpers instead of one overloaded docs page file
- the docs app now also exposes a page-feedback panel on MDX docs pages; feedback is always mirrored to `runtime/docs-feedback.jsonl` locally and can additionally forward into GitHub Discussions when `docs/.env.local` is populated from `docs/.env.example` with `GITHUB_APP_ID` and `GITHUB_APP_PRIVATE_KEY`
- `docs/` and `webgui/` currently share the resolved shadcn preset baseline from `pnpm dlx shadcn@latest init --preset b2CQzAxv8 --template next`, which today means `radix-lyra`, `olive`, `lucide`, Tailwind v4, JetBrains Mono typography, and app-local `components/ui`
- `webgui` remains mid-migration: its route handlers and some primitives follow the new frontend baseline, but much of the live shell still relies on legacy global classes in `src/app/globals.css`
- tool-driven news context surfaces
- operator chat history persisted separately from trading memory
- trade-level context persistence for memory/tool/model/rationale inspection
- explicit memory write policy for trade memory versus chat memory domains
- broker adapter boundary with paper backend, safe live gating, and execution kill-switch semantics
- canonical execution intent and outcome contracts now sit between guard output and broker adapters; the intent carries explicit timestamp/created-at audit fields, and paper execution uses the adapter path while preserving existing fills, positions, journals, and account marks
- a simulated-real adapter scaffold exists for non-live execution rehearsal with slippage, spread, drift, latency metadata, rejection hooks, partial-fill shape, and explicit simulated/non-live status
- execution intent and adapter outcome metadata are persisted and surfaced in trade-context review views so future live integration can be replayed and audited before any real broker is enabled
- structured financial feature contracts now exist for symbol identity, technical summaries, fundamental placeholders, and macro/news context
- technical decision features now expose V1-friendly 30d, 90d, and 180d return windows on top of the existing bar-horizon context, plus a compact price anchor for risk math
- provider interfaces now exist for market, fundamental, news, disclosure, and macro data; provider outputs are normalized into canonical analysis snapshots before feature generation
- SEC EDGAR, Finnhub, FMP, and KAP now have explicit provider scaffold adapters in the canonical provider set; they do not fetch live data yet, but missing outputs are represented as source attribution instead of disappearing silently
- the staged graph now includes fundamental and macro/news analyst roles before regime/strategy/risk, and manager synthesis receives those structured outputs
- prompt rendering now uses the `DecisionFeatureBundle` as the primary agent input when it is attached; raw compact snapshots remain available only for compatibility and deterministic fallback paths
- feature-first prompts now keep technical data-quality flags visible, and fallback-generated fundamental/macro assessments are not counted as consensus support
- fundamental assessments now use a richer analyst contract covering growth, profitability, cash flow, balance sheet quality, FX risk, business quality, macro fit, forward outlook, red flags, strengths, and evidence/inference/uncertainty separation
- prompt-facing fundamental context now carries the actual structured metrics, and non-neutral LLM fundamental bias requires direct evidence before it can influence manager or consensus surfaces
- structured LLM calls now prefer Ollama JSON-schema format with a compatibility fallback to plain JSON mode, making local model agent-cycle output more reliable without weakening schema validation
- no-trade risk plans are normalized after LLM validation so operator surfaces show meaningful reference stop/take levels instead of tiny schema-sentinel values
- canonical analysis snapshots, decision feature snapshots, fundamental summaries, and macro summaries are persisted into trade context and memory documents for future replay/retrieval
- QA workflow docs now define product-specific checklist, runbook, scenarios, and evidence conventions for CLI, Rich, Ink, daemon, observer API, memory, governance, and paper broker validation
- QA workflow docs now treat pexpect, tmux, asciinema, text, and JSON evidence as the baseline contract for CLI/Rich/Ink operator surfaces, while re-adding a Computer Use visual pass whenever the environment exposes it
- `.ai/agents/operator-ux.md` now defines a development-only reviewer for visual design, CLI ergonomics, terminal resize behavior, menu navigation, and finance/accounting readability
- `.ai/agents/` now defines development-only collaboration roles for planning, implementation, review, QA, and data architecture; these are guidance documents and not runtime agents or a new orchestration layer
- a terminal smoke harness now captures timestamped evidence for the installed CLI, primary Ink entrypoint, root launcher, Rich menu, deeper Rich submenu navigation, read-only JSON surfaces, optional one-cycle runtime checks, optional quality gates, coverage XML, and SonarQube submission
- Ink settings now covers the remaining V1 parity gap for preference visibility, recent runs, and safe operator-instruction editing in a resize-safer compact layout, and smoke QA verifies that page switch through tmux in a 110x30 terminal
- pyright is now configured as a first-class static check for repository source, tests, and QA scripts
- Python dependency resolution now uses a committed `poetry.lock` file generated from `pyproject.toml`; Conda remains the recommended Python environment layer while Poetry owns package locking and install synchronization
- recurring operator-facing labels and prompts now flow through a lightweight shared UI text catalog, giving future CLI, Rich, Ink, and WebUI localization a safer boundary
- the initial Web GUI development flow now enables Watchpack polling in `webgui` dev mode to avoid file-watch limit noise in larger local worktree setups while the shell is still young
- a first Market Context Pack is generated from the fetched lookback window and persisted with snapshots, run artifacts, trade context, dashboard payloads, observer API payloads, and Ink review surfaces
- Market Context Pack generation now fails closed before operation/runtime agent execution when the fetched data materially under-covers the requested lookback
- a first runtime mode contract exists; `training`/`operation` mode now flows through settings, service-state persistence/migration, status JSON, dashboard snapshots, observer API payloads, Rich status tables, and Ink overview/runtime pages
- Operation mode now requires strict LLM gating and provider/model readiness before any one-shot, launch, or service runtime can execute; Training mode can use diagnostic fallback only inside backtest/evaluation paths
- Market snapshots now carry `as_of`, and backtest reports persist data-window plus first/last decision timestamps so replay decisions can be audited for future-data leakage
- `runtime-mode-checklist` now surfaces a schema-backed transition plan; mode changes remain explicit configuration actions and cannot be silently applied through chat/free-form instruction parsing
- memory vectors now persist embedding provider, model, version, and dimensionality metadata beside the existing lightweight local-hashing vectors, and legacy rows migrate with local-hashing defaults
- SonarQube MCP is connected for project `agentic-trader-dev`; the latest known gate is blocked primarily by coverage, while recent cleanup reduced major complexity hotspots in walk-forward backtesting, service runtime flow, Rich TUI menus, service-state persistence, and float-equality tests

New production-expansion direction:

- the main operator-trust gap is no longer the absence of a lookback artifact; the next gap is adding provider-specific QA around the new fail-closed context-pack semantics
- the next decision-quality gap is replacing placeholder fundamental/macro inputs with structured provider-backed data while keeping raw noisy text out of agent prompts
- market snapshots now carry a structured multi-horizon context pack, and Training/Operation visibility, behavior-specific gates, as-of audit fields, and transition checklists are present
- memory is currently hybrid and inspectable, and vector metadata is now persisted; true local-first semantic embeddings and richer retrieval explanations are still planned expansions
- Training and Operation should become first-class runtime modes shown across all surfaces instead of informal workflow concepts
- QA should grow from smoke coverage into tiered terminal regression evidence with CLI JSON snapshots, pexpect scenarios, optional tmux/asciinema capture, optional Computer Use visual passes, unique artifact directories for parallel runs, and generated failure reports

## Current Constraints

- paper trading only
- local-first assumptions should remain primary
- memory layer is still lightweight compared with a richer future retrieval and policy layer
- lookback analysis has a first operator-verifiable fail-closed contract for operation/runtime flows; training replay can preserve growing-window undercoverage as an explicit context flag, but provider-limit edge cases still need broader QA coverage
- true semantic memory is not implemented yet; current vector-style retrieval with explicit metadata should be treated as a migration bridge, not the destination
- Training vs Operation mode is enforced for the first core boundary: Operation requires strict LLM readiness, while Training diagnostic fallback is limited to evaluation/backtest flows
- live broker adapters are not implemented or enabled; simulated-real remains local and non-live
- financial provider interfaces and canonical aggregation are implemented, but real SEC/KAP, transcripts, macro indicators, and richer vendor fetchers are still scaffolds or future providers
- SEC 10-K/10-Q/8-K, earnings transcripts, macro indicators, KAP, Turkey company disclosures, CBRT-style macro data, inflation, and FX source names are now explicit scaffold metadata; they are not live ingestors yet
- Alpaca settings are config-ready for V1 readiness checks, but no Alpaca adapter or live execution path is enabled
- fundamental and macro/news agents currently return structured neutral fallback when only scaffold provider data exists; this is intentional until real provider evidence is present
- external provider support should be additive and adapter-based, not invasive
- conversational surfaces must not silently mutate trading policy
- Ink TUI is the primary operator surface, but broader htop-like control affordances, full resize-proofing across every page, and visual refinement are still open
- runtime performance is currently controlled mostly through static settings; hardware-aware profiles for safe concurrency, token budgets, model routing, and memory use are a planned next step
- DB-backed review surfaces may intentionally fall back to observer mode while the runtime writer is active
- background runtime supervision now has a sidecar-friendly status and log contract that UI surfaces can read without competing for the writer connection
- behavior-changing work should use the QA docs when it affects operator surfaces or runtime behavior
- Sonar Quality Gate currently requires higher new-code coverage than the repository has; keep adding focused tests before treating the gate as fully green
- the docs surface now supports English and Turkish locale routes, while broader CLI/Rich/Ink/Web GUI localization is still intentionally deferred; outside docs, new repeated UI strings should continue flowing through the shared text catalog instead of ad hoc duplication
- `webgui` lint and production build are currently green in this worktree, but `next dev` still needs a follow-up for the multi-lockfile/Turbopack Tailwind resolution issue observed during manual QA
- `docs` now builds and lints with the new Fumadocs shell, but its content should keep expanding through curated MDX pages rather than ad hoc duplicated repo notes
- `webgui/src/app/globals.css` currently carries both legacy shell classes and newer token/shadcn groundwork; migration should remain incremental and screen-scoped

## Current Development Posture

The codebase should be treated as:

- active
- modular
- already opinionated
- ready for targeted extension, not a rewrite
- dependent on keeping `.ai/current-state.md`, `.ai/tasks.md`, and `.ai/decisions.md` in sync with meaningful architecture changes
- now in a V1-hardening phase that includes optional app-managed Ollama supervision, provider-aware bootstrap work, and expanding the new Fumadocs developer docs without replacing the existing runtime shape
