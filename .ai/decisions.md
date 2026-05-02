# Decisions

## Decision Log

### The repository's own runtime remains the orchestration source of truth

Reason:
The project already has a specialist graph, manager layer, memory assembly, storage, replay, and operator surfaces.
Adding an external orchestrator as the central control plane would duplicate and distort existing architecture.

### Research sidecars are evidence companions, not orchestration owners

Reason:
The trading runtime already owns staged specialist execution, manager synthesis, guard decisions, broker adapters, persistence, and operator truth.
The V1.1 research sidecar may collect and normalize external evidence, produce world-state snapshots, and prepare memory-update packets, but it must not submit orders, mutate trading policy, weaken strict runtime gates, or replace the staged graph.
CrewAI can be useful later for V1.2 deep-dive/evaluation loops, but it stays behind an optional backend boundary and must not become a required core runtime dependency.

### Research snapshots use the runtime feed before a sidecar database

Reason:
V1.1 needs sidecar persistence without competing with the active DuckDB runtime writer.
Research-only commands therefore append `ResearchSnapshotRecord` JSON to the runtime feed and update a latest-snapshot JSON file instead of creating a main `research_snapshots` table.
A separate sidecar database can be reconsidered only after real provider volume, query needs, and daemon polling behavior justify it.

### SEC EDGAR ingestion is opt-in and metadata-first

Reason:
The first live research source should be official, structured, and easy to audit without pulling raw filings into prompts.
SEC EDGAR submissions metadata can produce source-attributed filing evidence for watched US symbols, but it must remain disabled by default, require an identifying User-Agent, respect fair-access expectations, and surface missing/network/user-agent failures instead of silently falling back.
This provider does not parse full filing text, XBRL company facts, or trading policy; it only writes normalized research evidence packets for sidecar snapshots.

### CrewAI setup stays isolated until the dependency boundary is proven

Reason:
CrewAI is available as a useful sidecar harness, but adding it to the root lock would widen the runtime dependency surface before the adapter is implemented.
The current path is operator-visible setup/status plus a tracked uv-managed CrewAI Flow sidecar under `sidecars/research_flow/`, then a JSON/Pydantic handshake behind `ResearchSidecarBackend` when V1.2 begins.
The sidecar can own its CrewAI dependency, Python 3.13 `.python-version`, and `uv.lock`; the root runtime must keep working when that sidecar is not installed.

### External AI coding tools are development helpers, not runtime dependencies

Reason:
ChatGPT, Codex, and similar tools may help plan and implement changes, but they should not become assumptions inside the trading runtime.
The `.ai/agents/` role pack documents development workflows for planner, implementer, reviewer, QA, and data-focused helpers only; it must not be interpreted as a runtime agent platform or external orchestration dependency.

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

### Provider expansion should happen through adapters

Reason:
The project currently assumes Ollama-class local models.
Future providers should be added behind a stable interface so agent workflow, memory, and runtime control surfaces remain consistent.

### Memory must remain inspectable and bounded

Reason:
Trading memory supports context, replay, and review.
It must not turn into a hidden policy mutation layer.

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

### Sonar: explicit local and SonarCloud targets

Reason:
Sonar scanners should keep local Docker SonarQube and SonarCloud explicit: local branch/MCP work targets `agentic-trader` with root `sonar-project.properties`, while GitHub-hosted CI targets SonarCloud project `ogiboy_agentic-trader` with CLI overrides for organization/project key.

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
The `.ai/agents/operator-ux.md` role exists for this development review lens and should stay separate from runtime agents.
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

### External data must normalize into canonical analysis snapshots

Reason:
Provider payloads differ by source, market, region, and availability.
The runtime now uses provider interfaces for market, fundamental, news, disclosure, and macro data, then aggregates them into a `CanonicalAnalysisSnapshot`.
Agents still consume the compact `DecisionFeatureBundle`, but the canonical snapshot preserves source attribution, freshness, completeness, and explicit missing sections for prompts, persistence, memory, dashboard JSON, and future UI review surfaces.
Yahoo remains a fallback market/news source rather than the sole source of truth, while SEC EDGAR, KAP, macro indicators, transcripts, and vendor APIs can be added behind the same adapter seam.
Provider scaffolds for SEC EDGAR, KAP, Finnhub, and FMP should return explicit missing snapshots or empty-source attributions until real ingestion exists; absence of provider data must remain visible and must not be converted into neutral supporting evidence.

### Yahoo is degraded fallback evidence, not the target source of truth

Reason:
Yahoo/yfinance is useful for local-first bootstrap, tests, and fallback market/news evidence, but V1 financial intelligence should prefer explicit regulatory, public, or configured provider sources when available.
SEC 10-K/10-Q/8-K, earnings transcripts, macro indicators, KAP, Turkey company disclosures, CBRT-style macro data, inflation, and FX sources should normalize into canonical snapshots before reaching agents.
Finnhub, FMP, Polygon/Massive, and similar APIs are optional enrichers; their keys must remain configuration-only and their absence must be visible as missing/degraded evidence rather than hidden fallback completeness.

### V1 is Alpaca-ready and paper-first; V2 owns IBKR/global/FX expansion

Reason:
The execution boundary is ready for future broker adapters, but V1 should remain narrow enough to ship reliably.
Alpaca readiness belongs to V1 as US-equities-only preparation with manual approval, paper defaults, strict safety gates, kill switch, and broker/readiness health checks.
Interactive Brokers, global markets, multi-currency account state, FX conversion assumptions, and region-specific market QA belong in V2 so V1 does not become a broad multi-broker production rewrite.

### Alpaca paper is an explicit external-paper backend

Reason:
V1 needs real Alpaca readiness without making external broker submission a
hidden default. The local `paper` backend remains the default and continues to
own local portfolio simulation. The `alpaca_paper` backend is separate from
both local paper and `live`: it can use Alpaca paper endpoints for US equities
only, but only when credentials, the paper endpoint, and
`AGENTIC_TRADER_ALPACA_PAPER_TRADING_ENABLED=true` are explicit.
`v1-readiness`, `provider-diagnostics`, and `broker-status` are the operator
surfaces for seeing whether those gates are satisfied, and their network-free
payloads should also travel through dashboard, observer, Rich, Ink, and Web GUI
surfaces. The generic `live` backend still fails closed until a real live
adapter, manual approval gate, and paper-operation evidence are intentionally
implemented.

### Python dependencies should be locked with uv

Reason:
The project is expected to run consistently on multiple machines, but Conda, Poetry, uv sidecars, and ad hoc pip installs created too many overlapping Python ownership layers.
`pyproject.toml` remains the direct dependency manifest and root `uv.lock` is now the committed resolver output.
uv owns root package add, remove, lock, sync, run, and build commands; daily root development defaults to Python 3.13 in the root `.venv`, while CI can still sync against Python 3.12 for the current minimum-support signal.
Poetry is no longer a root package-management requirement.

### JavaScript surfaces should share a root pnpm workspace

Reason:
`webgui/`, `docs/`, and the Ink `tui/` are separate UI surfaces, but they should not each own independent package-manager islands.
A root pnpm workspace keeps Node dependency locking, CI cache keys, setup, build, and local start commands in one place without merging Python and JavaScript dependency ownership.
uv remains the Python truth, while root `package.json` scripts and thin Makefile aliases provide the human-facing command surface.
The Makefile must stay an alias layer over pnpm and uv commands rather than becoming a second build system.

### CrewAI Flow sidecar uses uv without turning the repo into a uv workspace

Reason:
CrewAI currently requires a narrower Python range than the root package wants to support, and its dependency graph should not become part of the strict trading runtime by accident.
The repository should therefore keep `sidecars/research_flow/` as an independent uv project with its own lockfile and smoke checks.
Root pnpm and Make commands may call into that sidecar for setup, check, and gated runs, but the root project should not add CrewAI to the root dependency graph or adopt a repository-wide uv workspace until there is a proven need.
Runtime integration should use `uv run --locked --no-sync` against an already-installed sidecar environment so normal trading commands do not silently create or update a CrewAI environment.
The core Python runtime may spawn the sidecar process and parse its JSON contract, but it must not import CrewAI modules directly.
The sidecar pyproject version is synced with the root application version through semantic-release `version_toml`, while its Python pin remains `3.13` to stay under CrewAI's current `<3.14` support boundary.

### Root uv migration replaces Poetry but not the project runtime architecture

Reason:
Using Conda, Poetry, uv sidecars, and multiple Python versions at once became operationally noisy.
The root now uses uv for dependency resolution, environment sync, command execution, and package builds, while pnpm remains the JavaScript workspace owner and the CrewAI Flow sidecar keeps its own isolated uv lock.
This changes developer environment management only; it does not replace the staged specialist runtime, broker adapter boundary, memory rules, or paper-first safety gates.

### Environment templates document targets, local env files own secrets

Reason:
Tracked `.env.example` files are templates only; real runtime and provider overrides belong in ignored `.env.local` files or GitHub repository secrets.

### Product-impacting branch pushes bump tracked version metadata

Reason:
Branch artifact identity from `pnpm run version:plan` is useful, but the project owner expects pushed product work to also advance the visible application version in tracked metadata.
When a feature/V1 branch push changes runtime behavior, operator surfaces, docs, sidecars, setup, or workflow contracts, agents should bump the patch version consistently across `pyproject.toml`, `agentic_trader/__init__.py`, root/workspace `package.json` files, `sidecars/research_flow/pyproject.toml`, and lockfile metadata before pushing.
`CHANGELOG.md` remains release-flow owned unless the user explicitly asks for a changelog update.
The Python runtime loads root `.env` and `.env.local` through Pydantic settings, so root API keys and model/runtime overrides should stay at the repository root.
The Web GUI may run without `webgui/.env.local` because it auto-detects the worktree and managed Python runtime; that app-local env file should only override command execution details.
The docs app should keep local `GITHUB_PAGES=false`; GitHub Actions and `pnpm build:docs:pages` set `GITHUB_PAGES=true` at build time so Pages gets the `/agentic-trader` base path without committing production env files.
`AGENTIC_TRADER_MODEL_NAME` is the canonical model setting, while the legacy `AGENTIC_TRADER_MODEL` env alias remains accepted for existing local files.

### Service state updates should use an explicit update contract

Reason:
Runtime supervision writes many related fields whenever cycle, symbol, daemon, and stop-request state changes.
Keeping those fields in a `ServiceStateUpdate` contract makes persistence updates easier to evolve and avoids long, fragile method signatures while preserving the sidecar service-state mirror used by CLI, Rich, Ink, observer, and daemon surfaces.

### App-managed Ollama should extend the existing daemon supervision surface

Reason:
The repository already has runtime supervision metadata, status commands, log tails, observer attach flows, and a Web GUI that reads those contracts.
If the application starts or stops Ollama for the operator, it should do so through the same local supervision and diagnostics surface rather than by creating a second orchestration/runtime layer.
That keeps model-service truth visible to CLI, Ink, observer, and Web GUI users, and it preserves the existing local-first architecture.

### V1 bootstrap should be provider-aware and opt-in around model installs

Reason:
V1 needs a smoother onboarding flow, but forced Ollama or default-model installation would over-assume the user's adapter and local setup choices.
The bootstrap path should detect missing prerequisites, offer sensible defaults such as Ollama plus a default local model, and still allow users to skip or replace that path without hidden behavior.

### The existing docs scaffold should be activated, not replaced

Reason:
The repository already contains a `docs/` Next.js scaffold, while developer orientation still partly lives in repo notes such as `dev/code-map.md`.
The right next step is to refresh links, migrate/update content, and grow the existing docs site into the canonical documentation surface instead of creating a second documentation project.
Fumadocs is a good fit for that work because it gives the existing app a docs-native MDX layout, page tree, and search flow without changing the repository's runtime architecture.

### Shared frontend surfaces should preserve the current shadcn preset baseline

Reason:
Both `docs/` and `webgui/` were initialized from `pnpm dlx shadcn@latest init --preset b2CQzAxv8 --template next`.
Future component additions should preserve the resolved baseline that command produced today: `radix-lyra`, `olive`, `lucide`, Tailwind v4, CSS-variable theming, and app-local `components/ui`.
If the design system changes later, it should be an explicit decision rather than accidental drift from one surface to another.
Typography should stay visually close to the JetBrains Mono direction but must use a local-first monospace stack so production builds do not depend on fetching Google Fonts.

### Web GUI CSS migration should be incremental

Reason:
`webgui/src/app/globals.css` currently carries both legacy shell classes and the newer token/shadcn groundwork.
Rewriting that file in one sweep would create too much operator-surface risk.
Migration should happen screen by screen or primitive family by primitive family, and new work should prefer shadcn primitives plus utility composition over adding more global shell classes.

### Docs feedback should stay honest about the hosting surface

Reason:
The public docs target is GitHub Pages, which cannot write local JSONL files or run Server Actions.
The feedback widget should therefore prepare a browser-local GitHub issue draft and say plainly that submission remains manual.
If a future Node-hosted docs surface reintroduces server-side local logging or GitHub forwarding, that should be an explicit hosting decision with credentials in ignored local env files and failure states visible to the operator.

### Docs should use locale-prefixed routes and modular content ownership

Reason:
The docs surface now needs real bilingual coverage, but the broader product is not ready for a full repo-wide i18n rewrite.
Keeping docs under explicit `/en/...` and `/tr/...` routes provides a practical English/Turkish split for navigation, search, and page trees without changing the trading runtime.
Within the docs app, route files, feedback flows, i18n helpers, and landing-page content should be split into smaller modules whenever that improves readability, reviewability, and long-term maintenance.

### Docs deployment should be static-first for GitHub Pages

Reason:
The public documentation target is GitHub Pages, so the docs app should export static assets rather than depending on a Node runtime, Server Actions, request headers, middleware/proxy behavior, or repository filesystem writes.
Search should use exported Fumadocs search data, locale routes should remain statically generated, and feedback should clearly prepare a browser-local GitHub issue draft instead of pretending to write `runtime/docs-feedback.jsonl` on a static host.

### Release automation should follow conventional commits

Reason:
The project needs practical solo-maintainer release hygiene without changing the runtime toolchain.
`python-semantic-release` should read conventional commits on `main`, bump `project.version` in `pyproject.toml`, update `CHANGELOG.md`, and create a `v*` tag without publishing the GitHub Release directly.
Stable release version stamping should also keep the root, Web GUI, docs, and TUI `package.json` versions aligned with the Python project version so the repo presents one coherent product baseline.
The binary workflow owns GitHub Release creation so immutable releases can be created with PyInstaller assets attached in one publish step.
The binary assets are convenience builds for the Python CLI layer; they do not bundle the Web GUI, docs app, Node runtime, Ollama, or external provider services.
If semantic-release previews a tag below the tracked pre-1.0 baseline and that baseline tag does not exist yet, the release workflow should create a baseline changelog section, create the baseline tag once, and dispatch binary packaging with that tag. Plain `main` branch binary pushes may still upload workflow artifacts without publishing a GitHub Release; release publishing should happen from a tag/dispatch path.

Stable release identity and branch build identity are intentionally separate.
Strict SemVer release tags keep the `MAJOR.MINOR.PATCH` core, such as `v0.9.5`; CI/build counters must not become a fourth core segment like `v0.9.5.9870`.
Integration branches such as `V1` should use `next` artifact identities, for example `v0.9.6-next.9870+gabc1234`, while feature branches should use `beta` artifact identities such as `v0.9.6-beta.9870+gabc1234`.
Only `main` should mutate tracked version and changelog files automatically.
Non-main branch pushes may publish SemVer-compatible prerelease tags/releases for testing, but they should not edit `pyproject.toml`, workspace package versions, or `CHANGELOG.md`.
The pre-1.0 baseline is `0.9.0`; `allow_zero_version=true` and `major_on_zero=false` keep V1-hardening releases on the 0.x line until the project intentionally declares a stable `1.0.0`.

### Development agents must verify version identity before publishing

Reason:
Branch publishing and stable release publishing now have different version
ownership rules. Stable app versions are owned by `pyproject.toml` plus
semantic-release on `main`, and the release config stamps
`agentic_trader/__init__.py`, the workspace package manifests, and the CrewAI
Flow sidecar version. Feature and V1 branch pushes should use
`pnpm run version:plan` for SemVer-compatible artifact identity without
hand-editing stable version files or `CHANGELOG.md`.
Any exception that manually changes `pyproject.toml`,
`agentic_trader/__init__.py`, root/workspace `package.json` files,
`sidecars/research_flow/pyproject.toml`, or `CHANGELOG.md` must be documented
with the reason and validated with `pnpm run version:plan` and
`pnpm run release:preview` before push.

### PyInstaller builds should use a tracked CLI spec

Reason:
Release binaries should come from a reproducible packaging contract instead of whatever spec PyInstaller generates in a CI runner.
The canonical tracked spec is `agentic-trader.spec`, points at `main.py`, names the executable `agentic-trader`, and disables UPX to reduce platform-specific packaging variance and antivirus false positives.
CI smoke builds and release binary builds should use this spec directly.
