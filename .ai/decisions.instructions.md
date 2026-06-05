# Decisions

## Decision Log

### The repository's own runtime remains the orchestration source of truth

Reason:
The project already has a specialist graph, manager layer, memory assembly, storage, replay, and operator surfaces.
Adding an external orchestrator as the central control plane would duplicate and distort existing architecture.

### Research sidecars are evidence companions, not orchestration owners

Reason:
The trading runtime already owns staged specialist execution, manager synthesis, guard decisions, broker adapters, persistence, and operator truth.
The V1 research sidecar may collect and normalize external evidence, produce world-state snapshots, and prepare memory-update packets, but it must not submit orders, mutate trading policy, weaken strict runtime gates, or replace the staged graph.
The former V1.1/V1.2 tracks are now part of V1 completion: CrewAI can be useful for deep-dive/evaluation loops, but it stays behind an optional backend boundary and must not become a required core runtime dependency.

### Research snapshots use the runtime feed before a sidecar database

Reason:
V1 needs sidecar persistence without competing with the active DuckDB runtime writer.
Research-only commands therefore append `ResearchSnapshotRecord` JSON to the runtime feed and update a latest-snapshot JSON file instead of creating a main `research_snapshots` table.
A separate sidecar database can be reconsidered only after real provider volume, query needs, and daemon polling behavior justify it.

### SEC EDGAR ingestion is opt-in and metadata-first

Reason:
The first live research source should be official, structured, and easy to audit without pulling raw filings into prompts.
SEC EDGAR submissions metadata can produce source-attributed filing evidence for watched US symbols, but it must remain disabled by default, require an identifying User-Agent, respect fair-access expectations, and surface missing/network/user-agent failures instead of silently falling back.
The provider may summarize compact official XBRL company facts from the SEC companyfacts API for both sidecar research evidence and canonical US fundamental snapshots, but it still must not download raw filing text, parse arbitrary filing HTML, or mutate trading policy.
When providers return normalized evidence, world-state source attribution must stay fresh and source-attributed rather than being collapsed into missing-source scaffolding.

### CrewAI setup stays isolated until the dependency boundary is proven

Reason:
CrewAI is available as a useful sidecar harness, but adding it to the root lock would widen the runtime dependency surface before the adapter is implemented.
The current path is operator-visible setup/status plus a tracked uv-managed CrewAI Flow sidecar under `sidecars/research_flow/`, then JSON/Pydantic handshakes behind `ResearchSidecarBackend` as V1 deep-dive tasks mature.
The sidecar can own its CrewAI dependency, Python 3.13 `.python-version`, and `uv.lock`; the root runtime must keep working when that sidecar is not installed.

### External AI coding tools are development helpers, not runtime dependencies

Reason:
ChatGPT, Codex, and similar tools may help plan and implement changes, but they should not become assumptions inside the trading runtime.
The `.ai/agents/` role pack documents development workflows for planner, implementer, reviewer, QA, and data-focused helpers only; it must not be interpreted as a runtime agent platform or external orchestration dependency.
RuFlo may be used the same way: as a system-level MCP/CLI advisory layer for task routing, diff-risk, workflow guidance, memory, or sandboxed-agent experiments.
Context7 may be used as a system-level documentation helper through the `npx ctx7` CLI when MCP discovery or login state is unreliable.
Do not initialize Context7 into the repository or let external agents/tools become part of the trading runtime unless that is made an explicit repo decision.
The default RuFlo posture is global Codex MCP first: use stable advisory tools such as status, hook inventory, diff stats, diff/file risk, and workflow guidance before any project-local CLI state.
RuFlo swarm and agent tools are experimental until repeated serial smoke checks prove that the MCP transport stays open, spawned agents are visible, and cleanup leaves no generated repo state.
The project now intentionally tracks a curated local development catalog in `.agents/skills/`, `skills-lock.json`, `CLAUDE.md`, `.claude/`, and the stable `.claude-flow/` config/capability files after the June 2026 manual skill install.
Those files are advisory development surfaces only: they do not create product runtime dependencies, trading agents, broker authority, hidden release behavior, or required setup steps for operators.
Generated runtime state still remains disposable and untracked, including `.claude-flow/data/`, `.claude-flow/logs/`, `.claude-flow/sessions/`, `.claude-flow/neural/`, `.claude-flow/metrics/`, `.claude-flow/security/*.json`, `.ruflo/`, `.swarm/`, `.mcp.json`, local memory databases, daemon pid files, and logs.
Reusable guidance should still be translated into self-contained `.ai/` working agreements whenever it changes repo policy, and `.ai/agents/`, `.ai/workflows/`, `.ai/playbooks/`, `.ai/helpers/`, and `.ai/skills/` remain the durable Codex-facing contract.
System-level RuFlo commands may be used actively from Codex as advisory checks when they do not initialize repository state, start daemons, spawn long-running agents, mutate memory, install dependencies, or replace local tests and source review.

### Operator-facing docs should explain the product before the repo

Reason:
Agentic Trader is now mature enough that docs cannot only speak to developers and AI agents.
The docs site should first help an operator understand what the system does, how to run paper cycles safely, how to inspect decisions, and where V1 boundaries are.
Contributor notes, `.ai` project memory, package ownership, and branch posture still matter, but they should appear as maintenance context rather than the primary product story.
Docs must distinguish product trading memory and review evidence from contributor `.ai` notes so users do not confuse repo-maintenance state with runtime decision memory.

### Frontend typography must be bundled and local-first

Reason:
The Web GUI and docs site should preserve the JetBrains Mono visual direction without relying on build-time Google Fonts fetches.
Both Next.js apps therefore load the bundled JetBrains Mono variable font files from app-local `fonts/` directories through `next/font/local`.
Future typography changes should keep this local-font contract unless a deliberate design decision replaces it.

### Setup verifies workspace dependencies while clean stays explicit

Reason:
The root pnpm workspace should not leave operators guessing whether `webgui`, `docs`, or `tui` dependencies were installed.
`pnpm run setup` and `make setup` now run a node workspace setup script that installs the workspace, approves allowed builds, and checks expected dependency directories before Python sync.
Normal `clean` remains artifact/cache-only to avoid unexpectedly deleting large installs, while `clean:deps` and `clean:all` make dependency removal intentional.

### Optional helper tool roots are not app workspace packages by default

Reason:
The root pnpm workspace represents app surfaces that should be installed by the normal developer/operator setup path: `webgui`, `docs`, and `tui`.
Browser/model/fetcher helpers under `tools/` have different ownership, security, download, and lifecycle rules.
Camofox therefore remains a standalone tool root installed with explicit `pnpm --dir tools/camofox-browser --ignore-workspace ...` commands, with browser binary fetches staying opt-in.
Adding Camofox to `pnpm-workspace.yaml` would make normal workspace setup install browser-helper dependencies and blur optional-helper ownership before the product decides that Camofox should be always-installed infrastructure.

### Guided app lifecycle commands compose existing owners

Reason:
V1 onboarding needs one understandable operator path, but setup/start/update/uninstall must not become hidden side effects.
`app:up` therefore composes the existing lifecycle facades instead of owning a second runtime: it plans by default, runs the safe first-run lane only after explicit scopes plus `--yes`, and delegates setup, service ownership, and readiness checks to the already tested `app:setup`, `app:start`, and `app:doctor` commands.
Optional Camofox dependency setup, browser binary fetches, model-service starts, and Camofox-service starts require matching ownership flags such as app-owned; host-owned, API/key-only, and skipped choices remain visible setup decisions rather than inferred installs or process ownership.
The trading daemon, broker config, provider accounts, secrets, hidden model pulls, and hidden browser downloads remain out of `app:up`.

### Optional tool ownership is persisted operator intent

Reason:
Ollama, Firecrawl, and Camofox can be host-managed, app-managed, API/key-only,
or intentionally skipped, and those choices need to survive beyond a single
`app:up` dry-run.
The first durable contract stores only non-secret ownership intent in
`runtime/setup/tool-ownership.json` with owner-only permissions.
`setup-status`, dashboard snapshots, Web GUI, and TUI read that same payload so
optional-helper readiness does not diverge by surface.
`app:start` and runtime auto-start paths may start model-service or
Camofox-service only when the persisted mode for the matching tool is
`app-owned`; host-owned, API/key-only, skipped, or undecided modes remain
visible degraded/blocker states and must not be installed, started, stopped, or
deleted by lifecycle commands.

### Internal-first model tools keep an explicit adapter escape hatch

Reason:
The default V1 app experience should work from the repo's own local helper
surfaces instead of assuming a host daemon is already running.
App-owned Ollama plus `qwen3:8b` is therefore the default local-first path for
strict LLM readiness, and dashboard/doctor/Web GUI views should report that
app-owned endpoint before falling back to host status.
Fallback remains an operator choice: host-owned tools may be connected to but
not managed, Firecrawl host CLI fallback is disabled unless Firecrawl is
recorded as host-owned, and Camofox still requires a loopback access key before
start.
Operators who want another model stack must select it explicitly through the
provider seam, currently `AGENTIC_TRADER_LLM_PROVIDER=openai-compatible` plus a
base URL, model name, and optional API key.
App-owned Ollama auto-start or dashboard setting rewrites must not override that
non-Ollama adapter.

### Strict Pyright is a zero-diagnostic publishing gate

Reason:
The repository should keep Pylance/Pyright in strict mode because it exposes
real runtime and test-contract weaknesses.
The staged backlog is now cleared for `agentic_trader`, `tests`, `scripts`, and
`sidecars/research_flow/src`, so CI, release, local `check-python`, and smoke
quality checks run `scripts/check_pyright_baseline.py` with a zero-error limit.
Do not add `type: ignore`, Pyright suppression comments, or config weakening as
a workaround; expose typed public seams, protocols, fixtures, stubs, or narrower
data contracts instead.

### Modularity and i18n are project-wide ownership contracts

Reason:
The modularity/i18n goal is not limited to the Web GUI. Python CLI, Rich,
Ink/TUI, WebGUI, docs, tests, helpers, and local assets should all make
ownership visible through file layout and imports.
Large files should be reduced by extracting domain-owned commands, schemas,
constants, helpers, view models, styles, copy, assets, and tests, not by moving
unrelated code into anonymous shared modules.
Repeated operator-facing strings should flow through locale-aware text accessors
so components and commands can call a small context/function such as
`t("namespace.key")` instead of importing broad label objects.
For Next.js App Router surfaces, `next-intl` is a suitable candidate because
its documented setup uses a Next plugin, request configuration, provider
wrapping, and `useTranslations`/`getTranslations` namespace access; adopt it
only with a typed migration plan for `webgui` and `docs`, not as a piecemeal
dependency drop.
For Python operator surfaces, evolve the existing typed UI text catalog into a
small locale-aware accessor before considering heavier third-party libraries.
Stable dashboard, observer, and API JSON keys remain English schema contracts;
localized text belongs at render boundaries.

### V1 can monetize only after compliance, trust, and unit economics are explicit

Reason:
Agentic Trader is moving toward an operator-facing product, but paid access,
personalized trade recommendations, account workflows, or order-routing
features can change the regulatory and support profile of the project.
V1 must stay paper-first and manual-approval-first until the commercial model is
classified with counsel, Alpaca production responsibilities are explicit,
operator risk disclosures and audit exports exist, customer data/privacy and
incident/support responsibilities are documented, LLM/tool-poisoning controls
are tested, and remote-model costs are measured per cycle.
The first paid SKU should therefore favor local-first paper desk, evidence
bundle, education, and personal automation value before managed live trading,
copy trading, account-opening workflows, or performance-fee promises.

### Operator-facing finance truth must be reconciled evidence, not UI copy

Reason:
Paper-operation trust depends on account marks, fills, PnL, exposure, broker backend, source attribution, and timestamps agreeing across runtime, storage, and operator surfaces.
Agents reviewing changes must treat finance/accounting claims like desk evidence: traceable, timestamped, source-attributed, and explicit about missing, stale, degraded, simulated, or blocked data.
No UI, model response, or docs page should infer broker/account state from trade intent or make missing account evidence look neutral.

### Finance operations checks are native read-only runtime surfaces

Reason:
The project needs a Wall-Street/accounting/broker lens inside the actual application, not only developer guidance.
The first V1-safe implementation is a read-only `finance-ops` payload that reconciles broker backend, account snapshot, PnL fields, risk report availability, paper evidence, and live-block state across CLI, dashboard, observer API, and evidence bundles.
It must not submit orders, mutate settings, bypass approval gates, or become a hidden execution path.
Operator-facing finance labels should include currency, paper mark timestamp/source/status, fee/slippage assumptions, and explicit rejection-evidence wording when those fields are present.
UI surfaces must show missing mark time or missing external broker evidence as missing, never as a neutral or clean account state.

### Trade proposals are a manual review queue, not agent authority

Reason:
V1 needs explicit proposal discipline without giving scanners, sidecars, chat, or Web routes direct broker authority.
Trade ideas may be queued as structured `TradeProposalRecord` rows with thesis, size, reference price, source, and review notes, but they remain pending until an explicit operator approval command submits through the existing broker adapter boundary.
V1 proposal creation and paper/external-paper broker submissions accept only the supported simple US-equity symbol shape; Turkey/global symbols and malformed symbol strings stay blocked until a later scoped expansion.
State-changing proposal actions require non-empty operator review notes at the CLI/Web/API boundary: approve, reject, reconcile, and refresh should all leave an audit sentence before mutating proposal state.
Limit proposals are explicit order intents, not soft hints: they require quantity plus `limit_price`, market proposals cannot carry `limit_price`, and Alpaca paper submissions must preserve the order type and carry `client_order_id` from the execution intent so broker orders can be correlated without inference.
Approval records the broker-facing `ExecutionIntent` and `ExecutionOutcome`; rejection, execution, failure, and expiry are terminal states.
External paper broker acknowledgements such as Alpaca paper `accepted` are in-flight approved proposals and open/operator-visible journal orders, not no-fill or executed outcomes; `proposal-refresh` may read the original broker order and update the stored execution/proposal/position-plan state, but it must never resubmit the order.
If a process records the broker execution outcome but exits before the final proposal status update, reconciliation may only read the existing `execution_records.intent_id` row and mark the approved proposal terminal; it must not call the broker adapter again.
The Web GUI Proposal Desk may call only the allowlisted CLI contracts for approve, reject, reconcile, and refresh, with same-origin/token route guards and no generic command execution or proposal creation surface.
This keeps proposal generation useful for a paper desk while preserving paper-first/manual-approval safety and keeping live execution blocked.
Missing exit-plan recovery is also explicit and non-executing: `position-plan-repair` may backfill stored position plans only from already executed proposal records with valid stop-loss/take-profit controls and matching open positions, defaults to dry-run, and must never resubmit orders or infer risk controls from a thesis alone.
Proposal candidates are a pre-review evidence layer, not agent authority. Scanner/research output may be persisted as `ProposalCandidateRecord` rows with score, materiality, freshness, liquidity, sizing intent, controls, redacted evidence, and compact canonical source-attribution context. Promotion may create a pending `TradeProposalRecord` only after deterministic checks pass, and the candidate/proposal handoff must happen inside one database transaction to avoid duplicate pending proposals; it must not approve, execute, or bypass the proposal gate.

### Optional web research helpers stay evidence-only and fail closed

Reason:
Firecrawl and Camofox can improve research coverage, but V1 should not make paid/browser tooling mandatory or let raw web content enter trading prompts.
They therefore live as disabled-by-default `researchd` provider adapters: Firecrawl normalizes search/news snippets with provenance and central redaction, while Camofox currently reports local browser health readiness.
Both adapters are evidence companions only; they do not import into the core runtime, submit orders, mutate runtime mode, or write broker policy.

### Market-intelligence benchmark patterns become native runtime contracts

Reason:
External trading-agent examples contain useful ideas for news freshness,
fetcher-attempt traces, continuous monitoring loops, strategy sweeps,
no-lookahead checks, proposal discipline, and finance reporting.
Those ideas should strengthen Agentic Trader's actual product/runtime behavior
without copying another runtime, importing foreign scripts, or making the
external project structure part of this repository.
The `.ai` folder is the translation workshop and operating memory for this
adaptation: it records the market strategist role, continuous research loop
workflow, news-intelligence playbook, strategy research/sweep playbook, finance
evidence reconciliation playbook, market-news research skill notes, and a V1
strategy catalog so future agents can keep adapting the ideas coherently.
The durable product home is repo-native code, schemas, storage, tests, QA, and
operator surfaces. Adoption should proceed only through existing contracts such as
`researchd`, provider schemas, `finance-ops`, idea scoring, backtests, proposal
records, guard/risk checks, and operator surfaces.
The first adoption slice is now runtime-visible: strategy profiles and readiness
metadata live in `agentic_trader.finance.strategy_catalog`, source-tiered news
planning lives in `agentic_trader.researchd.news_intelligence`, `idea-score`
returns strategy/evidence readiness context, and `finance-ops` exposes ledger
categories for trades, cash, fees/taxes, dividends, interest, and corporate
actions.
The continuous-loop pattern is exposed as `research-cycle-plan`, a read-only
contract for PRE-FLIGHT, MONITOR, ANALYZE, PROPOSE, and DIGEST phases that
names existing runtime commands instead of starting an autonomous executor.
The first bounded executor, `research-cycle-run`, may run sidecar collection
passes, persist snapshot records, and emit preflight/source-health/cadence/digest
payloads for operator surfaces, but it still cannot create or approve proposals,
submit broker intents, mutate policy, or inject raw web text into core prompts.
Any future continuous-loop executor must fail closed: missing provider health,
non-loopback browser endpoints, unredacted provider errors, raw article text, or
sidecar attempts to mutate broker/policy/proposal approval state should stop the
loop or produce degraded evidence instead of trading authority.
Digest and memory writes must stay reviewable, source-normalized, and linked to
snapshots so operators can inspect what was collected, skipped, downgraded, or
used before any proposal review.
Those surfaces are read-only decision-preparation contracts; they do not fetch
the web by themselves, create proposals, approve proposals, submit orders, or
let raw article text enter core trading prompts.
IBKR/global/FX/multi-currency execution, options execution, and flex-style
broker reporting remain later expansion work, not the default V2 path, unless a
later decision explicitly accepts a narrow read-only slice.

### Provider expansion should happen through adapters

Reason:
The project currently assumes Ollama-class local models.
Future providers should be added behind a stable interface so agent workflow, memory, and runtime control surfaces remain consistent.

### Memory must remain inspectable and bounded

Reason:
Trading memory supports context, replay, and review.
It must not turn into a hidden policy mutation layer.
Selected memories should carry explicit retrieval explanations with score components, as-of/freshness status, outcome tag, regime/strategy alignment, and diversity bucket so operators can inspect why context was used before deeper semantic models or outcome weighting are introduced.

### Local-first remains the default posture

Reason:
The project's identity, safety model, and cost profile depend on local-first operation.
Future remote providers may be supported, but they should remain optional and explicit.

### Local observer and Web surfaces are security boundaries, not convenience shortcuts

Reason:
The observer API and Web GUI expose real runtime, broker, provider, research, and
log truth even when they are read-only or paper-first.
They should therefore remain loopback-first by default, require explicit tokens
before intentional nonlocal exposure, reject foreign origins and oversized
payloads, and redact subprocess/provider errors before returning them to
operator surfaces.
These controls harden the local shell without creating a second runtime or
weakening paper-first execution gates.
Web GUI tokenless API access is only valid when the app-owned loopback launcher
sets its explicit loopback marker; reverse-proxied or manually exposed Web GUI
deployments must set `AGENTIC_TRADER_WEBGUI_TOKEN`.
When a token is set, the bundled browser shell must remain usable without a
proxy injecting headers: the operator enters the token in the Web GUI, the
server validates it through same-origin `/api/session`, and subsequent browser
API calls rely on a same-origin HttpOnly cookie plus the existing route guard.
An empty observer host is not local-safe: Python's HTTP server binds `host=""`
as an all-interface listener, so empty/blank hosts must be classified as
non-loopback and covered by negative tests plus smoke QA.

### Runtime and QA artifacts are sensitive local evidence

Reason:
`runtime/` and `.ai/qa/artifacts/` can include account snapshots, paper fills,
provider diagnostics, research snapshots, model/provider errors, and evidence
bundles.
They are ignored by git but still sensitive on shared machines, so writers
should prefer owner-only file modes and all surfaced log tails or provider notes
must pass through central secret redaction before becoming CLI, observer, Web,
or QA output.

### CLI, monitor, and TUI should read from the same contracts

Reason:
Operator trust depends on consistent state across surfaces.
UI-specific hidden logic should be avoided.

### The first Web GUI should stay a thin local shell over existing contracts

Reason:
The project now has a `webgui/` command center, but it should not grow a second orchestration path.
The web shell should call the same CLI/dashboard/runtime/chat/instruction contracts that already power CLI, Rich, and Ink, keeping local-first truth and operator-visible behavior aligned while the Web UI grows.

### Web GUI command execution should prefer the managed Python runtime over a PATH-only CLI fallback

Reason:
The Web GUI shells out to the existing runtime contracts, but relying on whichever `agentic-trader` entrypoint happens to be first on `PATH` can drift onto a stale global install in worktree-heavy setups.
The route layer should therefore prefer an explicit `AGENTIC_TRADER_PYTHON`, then the active virtualenv or repo-managed uv `.venv`, then legacy Conda when it can be resolved locally, and only then fall back to the PATH CLI.
This keeps browser QA and local operator workflows attached to the same code the worktree is editing without inventing a web-only runtime.

### Operator chat memory must remain separate from trading memory

Reason:
Operator conversations are useful for coordination and explanation, but they must not silently mutate execution policy or contaminate trading-context retrieval.

### Hybrid retrieval should extend, not replace, existing inspectable memory

Reason:
The project benefits from richer similarity search, but retrieval must stay local-first, reviewable, and bounded rather than becoming opaque hidden behavior.

### Specialist disagreement should be persisted before manager synthesis

Reason:
When a manager overrides or moderates a plan, operator review should show not only the final decision but also the pre-manager alignment and disagreements that led to it.

### Memory writes must respect explicit domain policies

Reason:
Trading memory and operator chat memory serve different purposes and carry different risks.
Writes should be gated by explicit actor rules so conversational surfaces cannot silently mutate trade-memory retrieval.

### Terminal smoke QA should validate real operator entrypoints and quality gates

Reason:
The installed `agentic-trader` command, `python main.py`, Ink TUI, and Rich menu can drift independently from unit tests.
A small pexpect-based smoke harness should exercise the actual terminal surfaces, leave timestamped text artifacts, and fail loudly when the operator's PATH resolves a stale entrypoint.
Quality gates such as ruff, pytest, pyright, and SonarQube should be attached as optional QA checks without hardcoding tokens or changing the trading runtime.
The same smoke layer should protect operator help text: key CLI help screens must
remain concise, support `--help`/`-h`, and avoid leaking implementation-style
docstring sections such as `Parameters:` or `Raises:`.

### Sonar: explicit local and SonarCloud targets

Reason:
Sonar scanners should keep local Docker SonarQube and SonarCloud explicit: local branch/MCP work targets `agentic-trader` with root `sonar-project.properties`, while GitHub-hosted CI targets SonarCloud project `ogiboy_agentic-trader` with CLI overrides for organization/project key.
Local SonarQube startup must verify server readiness, not only container launch.
The start/status scripts should diagnose common local-state failures such as an
existing `sonarqube_postgres` volume whose stored `sonar` password no longer
matches the current `SONAR_POSTGRES_PASSWORD`, and they should offer
`pnpm run sonar:repair-db-password` before any destructive volume reset.
The local compose default for `SONAR_AUTH_JWTBASE64HS256SECRET` must stay
Base64 encoded because newer SonarQube server images reject plain-text values at
Web Server startup.

### Sonar token sourcing

Reason:
Tokens must come from `SONAR_TOKEN` or target-specific Keychain services, and MCP wrappers should inject tokens at process launch rather than storing them in editor config.

### Sonar findings are full-repo review signals

Reason:
Sonar findings are full-repository review signals, not latest-commit-only signals; security/correctness findings and blocker/critical maintainability findings must be prioritized and either fixed or explicitly accepted with risk notes.

### Localization should start as a shared text boundary, not a full i18n rewrite

Reason:
The CLI, Rich menu, Ink TUI, and future WebUI need consistent operator language, but the product flows are still moving.
A lightweight shared UI text catalog avoids duplicated labels today and creates a safe seam for future multi-language support without introducing translation machinery too early.
Keep legacy constants exported until CLI/Rich/Ink call sites are migrated, but prefer typed catalog access for new Python UI code and typed copy modules for Web GUI components. Web GUI view modules should receive copy through the control-room boundary rather than importing ad hoc strings.

### Lookback must become an operator-verifiable artifact

Reason:
Fetching a long market window is not enough if the agent context and operator surfaces only expose compact latest-row indicators.
The next input layer should persist a Market Context Pack with multi-horizon summaries, data sufficiency, anomaly flags, and window coverage so every run can prove what history was actually considered.
If expected coverage is materially too low in operation/runtime flows, the system should fail before agent execution instead of silently treating an under-covered provider response as a valid long-window decision.
Training replay is allowed to use growing windows, but undercoverage must remain visible as context rather than being confused with production-ready coverage.
V1 release evidence should include deterministic edge cases for partial daily windows, intraday provider limits, non-datetime indexes, and higher-timeframe fallbacks so this contract is tested without requiring live provider availability.

### Daemon lifecycle must leave an auditable terminal state

Reason:
Background operation is only trustworthy if every blocked, stopped, stale, or failed path is visible to the operator.
LLM readiness failures must record a `blocked` service state before exiting; stop requests must be honored during cycle sleeps and after skipped symbols; dead PID recovery must clear the stale PID instead of only promising a later cleanup; and live-but-stale heartbeat state must not allow a second hidden background launch.
Supervisor/log-tail payloads should remain available through CLI and observer-compatible surfaces so Web GUI and QA evidence do not need a separate runtime truth path.

### Training and Operation should be runtime modes, not separate products

Reason:
The project needs a clear distinction between evaluation workflows and continuous paper operation, but forking the runtime would create drift.
Mode should be a shared settings/service/run attribute that changes gates, allowed commands, and UI banners while preserving one orchestration source of truth.
Operation mode therefore fails closed when strict LLM gating is disabled and still requires provider/model readiness for runtime execution.
Training mode may use deterministic diagnostic fallback only in evaluation/backtest flows so replay remains possible without silently generating paper trades.
Every replay decision should carry an auditable `as_of` boundary, and reports should preserve data-window plus decision-window timestamps so future-data leakage is visible in artifacts.
Mode transitions should be surfaced as schema-backed transition plans. The current implementation reports checklist state but does not mutate configuration, keeping chat and free-form instructions from silently changing execution policy.

### Semantic memory must preserve local-first inspectability

Reason:
True embeddings can improve recall over hashed-token pseudo-embeddings, but trading memory must remain reviewable, policy-bound, and separate from chat memory.
Embedding metadata, retrieval explanations, and migration compatibility are required before semantic memory becomes a core decision input.
The current local-hashing vectors now persist provider/model/version/dimension metadata so future semantic vectors can coexist with or migrate from existing memory rows safely.

### QA should graduate from smoke checks to terminal regression evidence

Reason:
Agentic Trader is operator-facing through terminal surfaces, so quality must include repeatable CLI, Rich, Ink, daemon, observer API, and visual-flow evidence.
The smoke harness should remain fast, but deeper tiers should capture JSON snapshots, pexpect transcripts, optional tmux/asciinema artifacts, and human-readable failure reports.
When Computer Use is available, visual CLI/Rich/Ink checks should run through the real terminal screen and capture screenshot or screen-state evidence in addition to the baseline text and JSON artifacts.
Computer Use is an optional QA capability, not a runtime or CI dependency; if it is unavailable, the existing pexpect, tmux, asciinema, text, and JSON evidence flow remains valid.
Indirect terminal review is also valid when direct screen control is unavailable: pane capture, session recording, dashboard/status/broker JSON, and observer API payloads should be cross-checked to reconstruct what the operator would have seen.
Visual evidence must be cross-checked with runtime contracts or persisted truth whenever the screen claims runtime, broker, execution, or review state.
Visual QA should include UX, design, and finance/accounting readability, not only crash or smoke behavior.
The `.ai/agents/operator-ux.agent.md` role exists for this development review lens and should stay separate from runtime agents.
When this role finds a confusing menu, command, layout, or financial display, it should propose the smallest safe repair and classify it as V1 blocker, V1 polish, or V2 redesign.
For Ink specifically, pexpect open/quit coverage is not enough to protect page-switch parity under the Node package-manager wrapper; tmux-driven compact navigation should be the regression check for real page switching and resize-sensitive operator content.

### Structured LLM calls should use provider JSON mode and safe previews

Reason:
Agent outputs are schema-bound contracts, not free-form prose.
Ollama JSON mode reduces malformed/verbose structured responses and makes one-cycle runtime QA more reliable on local models.
Provider payload previews must redact reasoning fields such as `thinking` before they reach operator surfaces or artifacts; the UI should expose stage summaries, tool usage, validation errors, and decision rationale rather than raw hidden reasoning.
When the provider supports it, structured calls should send the concrete Pydantic JSON schema as Ollama's `format`; older/incompatible Ollama responses can fall back to plain JSON mode while keeping the same Pydantic validation boundary.

### Runtime QA should have explicit performance tiers

Reason:
A real agent cycle can take several minutes on local hardware, so it should not be part of every fast smoke run.
The QA harness should keep fast terminal checks lightweight while offering opt-in runtime-cycle validation with isolated runtime storage, bounded token budgets, product-like retry behavior, request timeouts, and artifacts that show the active stage when a run fails.

### Broker execution should flow through an explicit intent and outcome contract

Reason:
Agent and guard outputs are not the same thing as broker orders.
The runtime now translates guard-approved or guard-rejected decisions into a canonical `ExecutionIntent`, sends that through a broker adapter, and records an `ExecutionOutcome`.
This keeps paper execution working while creating a reviewable seam for simulated-real rehearsal and future live broker integration.
Live execution remains blocked until a real adapter, approval gates, paper-operation evidence, and operator-visible readiness checks exist behind the same contract.
The intent contract exposes `timestamp` as the canonical audit field while preserving `created_at` for legacy storage and review payload compatibility.
When only one audit field is supplied, contract validation normalizes it into the canonical timestamp and mirrors it for compatibility.
When both `timestamp` and `created_at` are supplied, they must be identical; any mismatch must be rejected as a validation error before persistence, with storage still asserting the invariant.
Operator review views should show backend, adapter, outcome, and rejection reason without requiring raw JSON.

### No-trade risk output should remain readable without changing execution posture

Reason:
Local models can emit technically valid but operator-hostile sentinel values for no-trade risk levels, such as tiny positive stop/take prices used only to satisfy schema bounds.
Risk output should be finalized after validation so hold/no-trade decisions keep tiny exposure and no execution approval, while operator surfaces still display reference stop/take levels around the latest close.

### Financial intelligence should flow through structured feature bundles

Reason:
Future fundamentals, news, macro, SEC, KAP, transcript, and broker data can become noisy or provider-specific quickly.
Agents should consume typed summaries rather than raw documents or hidden provider state.
The new `DecisionFeatureBundle` is the boundary between data ingestion and reasoning: it carries symbol identity, technical summaries, fundamental features, and macro/news context.
Fundamental and macro/news analysts are now specialist roles in the staged graph, but real provider ingestion remains additive future work behind the feature layer.
API keys must stay in ignored local env files and should never be serialized into prompts, logs, QA artifacts, or tracked config.
Prompt rendering should use the feature bundle as the primary agent input when it exists, while compact market snapshots remain internal runtime state for deterministic fallbacks, risk math, audit, and compatibility.
The V1 technical feature contract should expose calendar-friendly 30d, 90d, and 180d return windows even though the underlying market context still computes bar horizons.
Feature-first prompts must still surface technical data-quality flags so agents do not lose lookback or provider-quality truth when raw snapshots stay internal.
Fallback-generated fundamental and macro/news assessments must not count as consensus support; unavailable finance evidence can be noted as missing or neutral, but it must not make manager synthesis look more complete than the provider evidence actually is.
The fundamental analyst contract should behave like a cautious financial analyst: every bias must be traceable to evidence, inference, or uncertainty, and incomplete inputs must remain neutral/cautious instead of being filled with imagined business facts.
Non-neutral LLM-generated fundamental bias must include direct evidence, and prompt-facing feature summaries must expose the actual fundamental metrics instead of asking the model to infer from labels or summaries alone.

## Runtime, Tooling, And Lifecycle Decisions

Detailed runtime/provider/dependency/lifecycle/release/tooling decisions continue in [decisions-runtime-tooling.instructions.md](decisions-runtime-tooling.instructions.md).
