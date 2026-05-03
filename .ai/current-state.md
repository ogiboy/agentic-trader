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
- supervisor stdout/stderr log tails are redacted before CLI/observer/Web-facing payloads so provider, LLM, or subprocess failures do not echo key-like values or bearer tokens to operator surfaces
- operator chat and safe instruction parsing
- Ink chat now includes side-by-side live agent activity and reasoning/tool context instead of a transcript-only view
- a local observer API can now expose runtime contracts over HTTP for future WebUI attach flows
- the observer API remains read-only and local-first: non-loopback binds are rejected by default, intentional nonlocal binds require `--allow-nonlocal` plus `AGENTIC_TRADER_OBSERVER_API_TOKEN`, and responses include no-store/browser hardening headers
- blank observer bind hosts are treated as non-loopback because Python HTTP servers bind an empty host to all interfaces; unit tests and smoke QA now keep that bypass closed
- a first local Web GUI now exists under `webgui/`; it uses a Next.js shell plus server-side route handlers that call the existing CLI/dashboard/runtime/chat/instruction contracts instead of adding a second runtime
- the Web GUI now also validates persona/runtime inputs at the route boundary, rejects cross-origin or malformed POST bodies, uses a sequence guard to prevent stale dashboard polls from overwriting newer state, and uses Next metadata/icon wiring plus `next/image` on the operator hero surface
- the Web GUI route boundary now also has loopback-only unauthenticated access, optional `AGENTIC_TRADER_WEBGUI_TOKEN`, JSON body caps, single-flight/cooldown guards for expensive runtime/chat/instruction actions, and redacted operator-facing subprocess errors
- the Web GUI command runner now prefers an explicit `AGENTIC_TRADER_PYTHON`, an active virtualenv, or the repo-managed uv `.venv` before falling back to legacy Conda/PATH entrypoints, which keeps the browser shell attached to the current worktree more reliably
- the repository now also ships a Fumadocs-based `docs/` app with curated MDX pages for onboarding, architecture, agent pipeline, runtime operations, operator surfaces, frontend guidance, memory/review, QA, and contribution workflow, turning the existing docs scaffold into the canonical operator guide plus contributor-notes starting point
- the docs app now uses locale-prefixed English and Turkish routes (`/en/...` and `/tr/...`) with localized page trees, localized feedback copy, and a modular frontend split across home, feedback, layout, i18n, and content helpers instead of one overloaded docs page file
- the docs landing copy now frames the site as an operator guide for paper-trading operation first, with contributor/developer notes behind that product story rather than in the first viewport
- the docs app is now configured for GitHub Pages static export with a project base path, static Fumadocs search data, and a feedback widget that prepares browser-local GitHub issue drafts instead of relying on Server Actions or filesystem writes
- the repository now has GitHub Actions workflow scaffolding for Python/Web GUI/docs CI, semantic-release versioning with synchronized Python/root/workspace package versions on stable releases, SemVer-compatible branch version previews, stable release changelog/tag creation, prerelease branch GitHub Releases for test binaries, PyInstaller macOS/Windows binaries, and GitHub Pages docs deployment
- JavaScript dependency management is now consolidated at the repository root with a pnpm workspace for `webgui/`, `docs/`, and `tui/`; root `package.json` scripts plus thin Makefile aliases provide shared setup, check, build, and local app entrypoints while uv owns Python locking, sync, command execution, and builds
- `docs/` and `webgui/` currently share the resolved shadcn preset baseline from `pnpm dlx shadcn@latest init --preset b2CQzAxv8 --template next`, which today means `radix-lyra`, `olive`, `lucide`, Tailwind v4, a local-first monospace typography stack, and app-local `components/ui`
- `docs/` and `webgui/` now load bundled JetBrains Mono variable fonts through `next/font/local` from app-local `fonts/` directories, preserving the intended look without build-time Google Fonts/network fetches
- `webgui` remains mid-migration: its route handlers and some primitives follow the new frontend baseline, but much of the live shell still relies on legacy global classes in `src/app/globals.css`
- tool-driven news context surfaces
- operator chat history persisted separately from trading memory
- trade-level context persistence for memory/tool/model/rationale inspection
- explicit memory write policy for trade memory versus chat memory domains
- broker adapter boundary with paper backend, safe live gating, and execution kill-switch semantics
- canonical execution intent and outcome contracts now sit between guard output and broker adapters; the intent carries explicit timestamp/created-at audit fields, and paper execution uses the adapter path while preserving existing fills, positions, journals, and account marks
- a simulated-real adapter scaffold exists for non-live execution rehearsal with slippage, spread, drift, latency metadata, rejection hooks, partial-fill shape, and explicit simulated/non-live status
- an explicit `alpaca_paper` backend now exists behind the broker adapter boundary for US-equities-only external paper readiness; it uses Alpaca paper endpoints, requires credentials plus `AGENTIC_TRADER_ALPACA_PAPER_TRADING_ENABLED=true`, and keeps `live` execution blocked
- execution intent and adapter outcome metadata are persisted and surfaced in trade-context review views so future live integration can be replayed and audited before any real broker is enabled
- structured financial feature contracts now exist for symbol identity, technical summaries, fundamental placeholders, and macro/news context
- technical decision features now expose V1-friendly 30d, 90d, and 180d return windows on top of the existing bar-horizon context, plus a compact price anchor for risk math
- provider interfaces now exist for market, fundamental, news, disclosure, and macro data; provider outputs are normalized into canonical analysis snapshots before feature generation
- SEC EDGAR, Finnhub, FMP, and KAP now have explicit provider scaffold adapters in the canonical provider set; they do not fetch live data yet, but missing outputs are represented as source attribution instead of disappearing silently
- `provider-diagnostics` now exposes model routing, selected market fallback, API-key readiness, provider source ladder, freshness/completeness placeholders, and explicit Yahoo fallback warnings without leaking secrets or fetching network data
- provider diagnostics, V1 readiness, and broker health now flow into the shared dashboard snapshot, observer API endpoints, Rich runtime menu, Ink overview/runtime pages, and Web GUI overview so operator surfaces do not have to shell out separately or invent readiness truth
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
- `.ai/agents/` now defines development-only collaboration roles for planning, implementation, review, QA, data architecture, product docs, operator UX, and finance operations; these are guidance documents and not runtime agents or a new orchestration layer
- a terminal smoke harness now captures timestamped evidence for the installed CLI, primary Ink entrypoint, root launcher, Rich menu, deeper Rich submenu navigation, read-only JSON surfaces, optional one-cycle runtime checks, optional quality gates, coverage XML, SonarQube submission, and a human-readable `qa-report.md`
- smoke QA now also verifies key operator `--help`/`-h` surfaces and fails when internal Python docstring sections such as `Parameters:` or `Raises:` leak into operator-facing CLI help
- `evidence-bundle` now creates a read-only V1 QA bundle under `.ai/qa/artifacts/` with dashboard, status, broker, provider diagnostics, V1 readiness, supervisor, logs, runtime-mode checklist, research status, manifest, and latest smoke summary/report when available
- `hardware-profile` now records CPU, memory, accelerator hints, configured model size, and safe local parallelism/token recommendations before long paper-operation runs; evidence bundles include this profile
- `operator-workflow` now exposes the canonical V1 review sequence as a read-only CLI/JSON payload: doctor, hardware profile, provider diagnostics, V1 readiness, smoke QA, optional one-cycle run, review/trace/context, evidence bundle, then background paper operation
- Ink settings now covers the remaining V1 parity gap for preference visibility, recent runs, and safe operator-instruction editing in a resize-safer compact layout, and smoke QA verifies that page switch through tmux in a 110x30 terminal
- the Rich/live monitor Current Cycle panel now pairs stage progress with runtime mode, watched symbols, interval/lookback, broker backend/state, kill-switch state, and V1 paper gate status so paper-operation safety context stays visible during monitoring
- pyright is now configured as a first-class static check for repository source, tests, and QA scripts
- Python dependency resolution now uses a committed root `uv.lock` file generated from `pyproject.toml`; uv owns root package locking, environment sync, command execution, and builds while local daily development pins Python 3.13 through `.python-version`
- root daily development now defaults to Python 3.13 in the repo-managed uv `.venv`, while the package support range remains `>=3.12,<3.15` until CI expands beyond the current minimum-version signal
- `scripts/install-python.sh` now runs `uv sync --locked --python 3.13 --all-extras --group dev`, creating or updating the root `.venv` visibly instead of silently installing into a system Python or relying on Conda activation
- the Ink TUI is now a pnpm workspace package, and the Python CLI launcher resolves a compatible Node package manager instead of requiring npm specifically
- recurring operator-facing labels and prompts now flow through a lightweight shared UI text catalog, giving future CLI, Rich, Ink, and WebUI localization a safer boundary
- the initial Web GUI development flow now enables Watchpack polling in `webgui` dev mode on port `3210`, avoiding file-watch limit noise in larger local worktree setups while matching the README/browser QA contract
- a first Market Context Pack is generated from the fetched lookback window and persisted with snapshots, run artifacts, trade context, dashboard payloads, observer API payloads, and Ink review surfaces
- Market Context Pack generation now fails closed before operation/runtime agent execution when the fetched data materially under-covers the requested lookback
- a first runtime mode contract exists; `training`/`operation` mode now flows through settings, service-state persistence/migration, status JSON, dashboard snapshots, observer API payloads, Rich status tables, and Ink overview/runtime pages
- Operation mode now requires strict LLM gating and provider/model readiness before any one-shot, launch, or service runtime can execute; Training mode can use diagnostic fallback only inside backtest/evaluation paths
- Market snapshots now carry `as_of`, and backtest reports persist data-window plus first/last decision timestamps so replay decisions can be audited for future-data leakage
- `runtime-mode-checklist` now surfaces a schema-backed transition plan; mode changes remain explicit configuration actions and cannot be silently applied through chat/free-form instruction parsing
- `v1-readiness` now surfaces paper-operation gates and Alpaca paper-readiness gates before longer runs or external paper checks, with optional provider/model health checking behind `--provider-check`
- `v1-readiness` now also carries a `paper_evidence` section that ties V1 readiness to provider source-ladder visibility, source attribution, Market Context Pack explainability fields, review/evidence-bundle artifacts, broker health, and the no-live-until-approved gate
- `finance-ops` now exposes a read-only trading-desk payload that reconciles broker backend, account snapshot, PnL fields, risk report availability, paper evidence, and live-block state without gaining execution authority
- finance/accounting readability now carries currency, paper mark timestamp/source/status, cost-model assumptions, and rejection-evidence wording through `finance-ops`, dashboard payloads, Rich/Ink/Web operator surfaces, and targeted tests
- memory vectors now persist embedding provider, model, version, and dimensionality metadata beside the existing lightweight local-hashing vectors, and legacy rows migrate with local-hashing defaults
- Sonar is split into two explicit targets: local Docker SonarQube Community Build uses project `agentic-trader` through root `sonar-project.properties`, while GitHub-hosted CI and public badges use SonarCloud project `ogiboy_agentic-trader`
- local `pnpm run sonar` uses `pysonar`, local `pnpm run sonar:js` uses `@sonar/scan`, and manual `pnpm run sonar:cloud` uses the npm scanner with SonarCloud organization `ogiboy`; tokens must come from `SONAR_TOKEN` or separate macOS Keychain services (`codex-sonarqube-token` for local, `codex-sonarcloud-token` for cloud)
- VS Code and Codex MCP should route through the same local wrapper, which calls `scripts/secrets/run-sonarqube-mcp.sh`; the repo script reads the local SonarQube token from Keychain and exports it only to the Docker MCP process
- `pnpm run mcp:sonarqube:status` distinguishes the local `sonarqube` server from transient `mcp/sonarqube` client containers and warns when several MCP clients are running
- Sonar findings are treated as full-codebase review input; security/correctness findings, security hotspots, and blocker/critical maintainability issues are not dismissed without a fix or explicit risk acceptance
- the 2026-05-01 comprehensive QA pass verified local SonarQube, `pnpm run check`, `pnpm run qa:quality`, runtime-cycle smoke, CrewAI Flow setup/run, Web GUI, docs, observer API, and a paper one-shot agent cycle; the new-code Sonar gate is green after the SEC research provider refactor
- a first `agentic_trader/researchd/` sidecar foundation now exists with canonical research schemas, sidecar settings, source-health scaffolds for SEC EDGAR, KAP, macro, news/event, and social watchlists, and `research-status` plus dashboard/observer API visibility
- the research sidecar is disabled by default, uses a no-op backend by default, keeps CrewAI behind an optional adapter boundary, and does not call broker, execution, run persistence, or runtime mode transition code
- `research-refresh` can run one isolated sidecar pass and persist a `ResearchSnapshotRecord` to `runtime/research_snapshots.jsonl` plus `runtime/research_latest_snapshot.json`; `research-status`, dashboard, and observer payloads read this feed without opening DuckDB
- runtime feed and research snapshot writes now prefer owner-only local file permissions, keeping `runtime/` evidence safer on shared developer machines without changing the file-backed contract
- `research-flow-setup` reports the tracked `sidecars/research_flow/` uv sidecar path, Python version file, lockfile presence, sidecar `.venv` presence, uv availability, and root setup/check/run commands; CrewAI is still not imported by core runtime modules or added to the root dependency lock
- the CrewAI research backend now uses a subprocess JSON contract through `uv run --locked --no-sync research-flow-contract` when the sidecar is installed; failures stay visible and do not install dependencies implicitly during runtime
- the CrewAI research backend now starts with a narrowed subprocess environment, keeps broker/runtime secrets out of the sidecar by default, and redacts non-JSON stdout/stderr failures before they reach research status or persisted error fields
- the CrewAI Flow sidecar contract now emits deterministic planned deep-dive task definitions for company dossiers, timeline reconstruction, contradiction checks, watch-next lists, and sector briefs without running LLM-backed tasks yet
- SEC EDGAR research can now be enabled explicitly through `AGENTIC_TRADER_RESEARCH_SEC_EDGAR_ENABLED=true` plus `AGENTIC_TRADER_RESEARCH_SEC_EDGAR_USER_AGENT`; when configured, it reads official submissions metadata plus compact official company-facts XBRL metrics into source-attributed research evidence without downloading raw filing text
- research world-state snapshots now preserve fresh source attribution when providers return normalized evidence, instead of labeling every sidecar provider attribution as missing

New production-expansion direction:

- the main operator-trust gap is no longer the absence of a lookback artifact; V1 now has deterministic provider-edge QA for fail-closed context-pack semantics, while live-provider Alpaca feed nuances and global/FX market calendars stay outside the V1 blocker boundary
- the next decision-quality gap is replacing placeholder fundamental/macro inputs with structured provider-backed data while keeping raw noisy text out of agent prompts
- market snapshots now carry a structured multi-horizon context pack, and Training/Operation visibility, behavior-specific gates, as-of audit fields, and transition checklists are present
- memory is currently hybrid and inspectable, and vector metadata is now persisted; true local-first semantic embeddings and richer retrieval explanations are still planned expansions
- Training and Operation should become first-class runtime modes shown across all surfaces instead of informal workflow concepts
- the former V1.1/V1.2 tracks are now part of V1 completion: the research sidecar should reconstruct what happened across 30d/90d/180d windows through normalized evidence packets, while optional CrewAI-backed deep-dive/evaluation loops stay behind the sidecar boundary
- native replay, QA, and strict runtime flows must remain valid without CrewAI installed; V2 starts at IBKR/global/FX, multi-currency live accounting, and actual live brokerage
- QA should grow from smoke coverage into tiered terminal regression evidence with CLI JSON snapshots, pexpect scenarios, optional tmux/asciinema capture, optional Computer Use visual passes, unique artifact directories for parallel runs, and generated failure reports

## Current Constraints

- paper trading only
- local-first assumptions should remain primary
- memory layer is still lightweight compared with a richer future retrieval and policy layer
- lookback analysis has an operator-verifiable fail-closed contract for operation/runtime flows; training replay can preserve growing-window undercoverage as an explicit context flag, and smoke QA now covers partial daily windows, intraday provider limits, non-datetime indexes, and higher-timeframe fallbacks without fetching live providers
- true semantic memory is not implemented yet; current vector-style retrieval with explicit metadata should be treated as a migration bridge, not the destination
- Training vs Operation mode is enforced for the first core boundary: Operation requires strict LLM readiness, while Training diagnostic fallback is limited to evaluation/backtest flows
- live broker adapters are not implemented or enabled; simulated-real remains local and non-live
- research sidecar status, schemas, and file-backed snapshot persistence are implemented; SEC EDGAR submissions metadata and compact company facts are the first opt-in live sources, while broader evidence ingestion, daemon-style polling controls, and trade-memory writes are still future work
- CrewAI is not a core dependency; the CrewAI backend is an isolated placeholder and must not replace the staged specialist graph. The tracked Flow scaffold now lives under `sidecars/research_flow/`, outside `agentic_trader/`, with uv owning its own environment and sidecar package version aligned to the root app version.
- financial provider interfaces and canonical aggregation are implemented, but real SEC/KAP, transcripts, macro indicators, and richer vendor fetchers are still scaffolds or future providers
- SEC 10-K/10-Q/8-K-style filings now have a first metadata-only submissions ingestor when explicitly enabled; earnings transcripts, macro indicators, KAP, Turkey company disclosures, CBRT-style macro data, inflation, and FX source names remain explicit scaffold metadata rather than live ingestors
- Alpaca settings and the `alpaca_paper` broker adapter are config-ready for V1 external paper readiness checks, but the backend is off unless explicitly enabled and live execution remains blocked
- fundamental and macro/news agents currently return structured neutral fallback when only scaffold provider data exists; this is intentional until real provider evidence is present
- external provider support should be additive and adapter-based, not invasive
- conversational surfaces must not silently mutate trading policy
- daemon lifecycle is safer around blocked runtime gates, stale/dead PIDs, stop requests during cycle sleeps, skipped-symbol stops, supervisor log-tail parity, and monitor stage-cycle filtering
- Ink TUI is the primary operator surface, but broader htop-like control affordances, full resize-proofing across every page, and visual refinement are still open
- runtime performance is currently controlled mostly through static settings; `hardware-profile` now gives operator guidance, but automatic hardware-aware runtime tuning for concurrency, model routing, token budgets, and memory use is still a planned next step
- DB-backed review surfaces may intentionally fall back to observer mode while the runtime writer is active
- background runtime supervision now has a sidecar-friendly status and log contract that UI surfaces can read without competing for the writer connection
- behavior-changing work should use the QA docs when it affects operator surfaces or runtime behavior
- Sonar Quality Gate currently requires higher new-code coverage than the repository has; keep adding focused tests before treating the gate as fully green
- the docs surface now supports English and Turkish locale routes, while broader CLI/Rich/Ink/Web GUI localization is still intentionally deferred; outside docs, new repeated UI strings should continue flowing through the shared text catalog instead of ad hoc duplication
- `webgui` lint, typecheck, production build, and the local `pnpm dev:webgui` flow on `localhost:3210` are now green in this worktree
- Web GUI review, portfolio, risk, journal, and memory panels now surface section-level unavailability errors explicitly instead of collapsing them into generic empty states
- `docs` now builds and lints with the new Fumadocs shell and is prepared for GitHub Pages static export, but its content should keep expanding through curated MDX pages rather than ad hoc duplicated repo notes
- the docs surface is being reframed as an operator-first guide: it should explain what Agentic Trader does, how to run paper cycles safely, how to inspect memory/review/broker evidence, and where V1 boundaries are before contributor-only package ownership details
- docs language now distinguishes product trading memory and review evidence from contributor `.ai` project notes so end users do not confuse repo-maintenance memory with runtime decision memory
- root `pnpm check` and `make check` are now the intended static/build validation entrypoints; use `pnpm run qa` or `pnpm run qa:quality` for terminal smoke QA, and focused `pnpm --filter ...`, `uv run ...`, or `pnpm run check:research-flow` commands when narrowing a failure
- `.codex/environments/environment.toml` setup and check actions now include the tracked CrewAI Flow sidecar setup/check commands so Codex workspace actions do not drift from README and root pnpm scripts
- root `pnpm run setup` and `make setup` now install and verify root, `webgui`, `docs`, and `tui` node workspace dependencies before syncing Python; `clean` removes artifacts only, while `clean:deps` and `clean:all` explicitly remove installed dependencies
- release binary uploads should be validated through the release workflow/tag-dispatch path; direct `main` branch binary workflow runs may upload artifacts while intentionally skipping GitHub Release publication
- the stable release workflow now creates a baseline changelog section before the one-time pre-1.0 baseline tag when semantic-release's discovered candidate is below the tracked `0.9.0` baseline, so `main` does not end up with a release tag and an empty `CHANGELOG.md`
- product-impacting feature/V1 branch pushes now carry an explicit tracked patch-version bump in Python, workspace package manifests, sidecar metadata, and lockfile metadata before push; `pnpm run version:plan` still records the branch artifact identity, and `CHANGELOG.md` remains release-flow owned unless explicitly requested
- RuFlo is available as a system-level development MCP/CLI helper, not a project dependency; when its MCP namespace is available, use it for advisory checks such as guidance, route recommendations, and diff-risk/stats without initializing the repository
- Context7 is also available as a system-level documentation helper; when MCP discovery/login state is confusing, call it through `npx ctx7 library ...` and `npx ctx7 docs ...` from the terminal instead of adding project dependencies or repo setup files
- `webgui/src/app/globals.css` currently carries both legacy shell classes and newer token/shadcn groundwork; migration should remain incremental and screen-scoped

## Current Development Posture

The codebase should be treated as:

- active
- modular
- already opinionated
- ready for targeted extension, not a rewrite
- dependent on keeping `.ai/current-state.md`, `.ai/tasks.md`, and `.ai/decisions.md` in sync with meaningful architecture changes
- now in a V1-hardening phase that includes optional app-managed Ollama supervision, provider-aware bootstrap work, and expanding the new Fumadocs operator guide without replacing the existing runtime shape
