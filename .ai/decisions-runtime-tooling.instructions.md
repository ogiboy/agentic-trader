# Runtime, Tooling, And Lifecycle Decisions

This file continues [decisions.instructions.md](decisions.instructions.md) for runtime, provider, dependency, lifecycle, release, and tooling decisions.

## Decision Log

### External data must normalize into canonical analysis snapshots

Reason:
Provider payloads differ by source, market, region, and availability.
The runtime now uses provider interfaces for market, fundamental, news, disclosure, and macro data, then aggregates them into a `CanonicalAnalysisSnapshot`.
Agents still consume the compact `DecisionFeatureBundle`, but the canonical snapshot preserves source attribution, freshness, completeness, and explicit missing sections for prompts, persistence, memory, dashboard JSON, and future UI review surfaces.
Yahoo remains a fallback market/news source rather than the sole source of truth, while SEC EDGAR, KAP, macro indicators, transcripts, and vendor APIs can be added behind the same adapter seam.
SEC companyfacts is the first opt-in live canonical fundamental provider for US issuers; KAP, Finnhub, FMP, and future providers should still return explicit missing snapshots or empty-source attributions until their real ingestion exists. Absence of provider data must remain visible and must not be converted into neutral supporting evidence.

### Yahoo is degraded fallback evidence, not the target source of truth

Reason:
Yahoo/yfinance is useful for local-first bootstrap, tests, and fallback market/news evidence, but V1 financial intelligence should prefer explicit regulatory, public, or configured provider sources when available.
SEC 10-K/10-Q/8-K, earnings transcripts, macro indicators, KAP, Turkey company disclosures, CBRT-style macro data, inflation, and FX sources should normalize into canonical snapshots before reaching agents.
Finnhub, FMP, Polygon/Massive, and similar APIs are optional enrichers; their keys must remain configuration-only and their absence must be visible as missing/degraded evidence rather than hidden fallback completeness.

### V1 is Alpaca-ready and active-trading capable; V2 owns Turkey expansion

Reason:
The execution boundary is ready for future broker adapters, but V1 should remain narrow enough to ship reliably.
Alpaca readiness belongs to V1 as the US-equities active trading path with manual approval, paper defaults, external-paper rehearsal, strict safety gates, kill switch, broker/readiness health checks, and an auditable paper-to-real promotion gate.
V1 should not be described as a non-trading demo or only a research shell: it must be capable of submitting approved buy/sell intents through the supported broker boundary once the configured gates pass.
V2 is the Turkey expansion track: Turkish symbols, KAP/company disclosures, CBRT-style macro context, TRY/FX accounting, local session calendars, and the eventual Turkey broker/data route.
Broader IBKR/global expansion is deferred unless a later decision explicitly changes the product sequence.

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
implemented. This gating language must not be misread as "V1 will not trade";
it means V1 trades only through explicit, approved, auditable supported paths.

### Python dependencies should be locked with uv

Reason:
The project is expected to run consistently on multiple machines, but Conda, Poetry, uv sidecars, and ad hoc pip installs created too many overlapping Python ownership layers.
`pyproject.toml` remains the direct dependency manifest and root `uv.lock` is now the committed resolver output.
uv owns root package add, remove, lock, sync, run, and build commands; daily root development and GitHub Actions use Python 3.13 from the root `.python-version`. The root package metadata still allows `>=3.12,<3.15`, but 3.12 compatibility is no longer the primary CI lane unless a separate compatibility matrix is added.
Poetry is no longer a root package-management requirement.
New root dependencies must be added with `uv add <package>` so the manifest and
lockfile change together. Dependency upgrades should use `uv lock --upgrade`
followed by a root dev sync such as
`uv sync --locked --all-extras --group dev`. Avoid plain `uv sync` for local V1
work because it can prune dev tools such as ruff, pytest, pyright, and coverage
from the active `.venv`.

### JavaScript surfaces should share a root pnpm workspace

Reason:
`webgui/`, `docs/`, and the Ink `tui/` are separate UI surfaces, but they should not each own independent package-manager islands.
A root pnpm workspace keeps Node dependency locking, CI cache keys, setup, build, and local start commands in one place without merging Python and JavaScript dependency ownership.
uv remains the Python truth, while root `package.json` scripts and thin Makefile aliases provide the human-facing command surface.
The Makefile must stay an alias layer over pnpm and uv commands rather than becoming a second build system.

### CrewAI Flow sidecar is a uv workspace dependency without becoming trading authority

Reason:
CrewAI currently requires a narrower Python range than the root package advertises, and its dependency graph must not become part of the strict trading runtime by direct import.
The repository therefore keeps `sidecars/research_flow/` as the `research-flow` package in the root uv workspace: the root `pyproject.toml` declares it as a dependency, `[tool.uv.sources]` maps it to the workspace source, and root `uv.lock` owns shared resolution.
Root pnpm and Make commands may call into that sidecar for setup, check, and gated runs through `uv sync --all-packages --all-extras --group dev` and `uv run --package research-flow`.
Runtime integration should use `uv run --locked --package research-flow --no-sync` against an already-installed workspace environment so normal trading commands do not silently create or update a CrewAI environment.
The core Python runtime may spawn the sidecar process and parse its JSON contract, but it must not import CrewAI modules directly.
The sidecar pyproject version is synced with the root application version through semantic-release `version_toml`, while its Python pin remains `3.13` to stay under CrewAI's current `<3.14` support boundary. Because uv workspaces use a shared lock, local and CI sync commands should use Python 3.13.

### Root uv migration replaces Poetry but not the project runtime architecture

Reason:
Using Conda, Poetry, uv sidecars, and multiple Python versions at once became operationally noisy.
The root now uses uv for dependency resolution, environment sync, command execution, and package builds, while pnpm remains the JavaScript workspace owner and the CrewAI Flow sidecar participates as a runtime-controlled subprocess uv workspace package.
This changes developer environment management only; it does not replace the staged specialist runtime, broker adapter boundary, memory rules, or paper-first safety gates.

### Environment templates document targets, local env files own secrets

Reason:
Tracked `.env.example` files are templates only; real runtime and provider overrides belong in ignored `.env.local` files or GitHub repository secrets.

### Product-impacting branch pushes bump tracked version metadata

Reason:
Branch artifact identity from `pnpm run version:plan` is useful, but the project owner expects pushed product work to also advance the visible application version in tracked metadata.
When a feature/V1 branch push changes runtime behavior, operator surfaces, docs, sidecars, setup, or workflow contracts, agents should bump the patch version consistently across `pyproject.toml`, `agentic_trader/__init__.py`, root/workspace `package.json` files, `sidecars/research_flow/pyproject.toml`, and lockfile metadata before pushing.
`CHANGELOG.md` remains release-flow owned unless the user explicitly asks for a changelog update.
If `CHANGELOG.md` does not change when a stable release is expected to update it,
that is a release-flow finding to investigate rather than a reason to hand-edit
the changelog on V1 feature work.
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
The first implementation keeps model-service state separate from orchestrator state under `runtime/model_service/`, starts only loopback-bound app-owned Ollama, narrows the subprocess environment so broker/provider secrets are not inherited, and stops only the PID recorded in app-owned state.
Stopping an app-owned model service must preserve state unless the recorded process is actually gone; SIGTERM may be escalated to SIGKILL for the recorded Ollama PID, but an OS/permission failure must leave the state visible so setup/status surfaces do not lose track of a still-listening process.
When command-line inspection is unavailable or sandbox-restricted, loopback port
ownership is sufficient evidence that the recorded app-owned Ollama process is
still alive; the app must not delete state merely because `ps` is unavailable.
Duplicate/stale process detection should also avoid a hard dependency on `ps`.
If `ps` is denied, loopback listener evidence from `lsof` may identify Ollama
listeners for operator diagnostics and stale app-managed cleanup. Cleanup may
target app-owned alternate ports 11435-11465, but host-default 11434 remains a
user-managed service unless the operator explicitly chooses otherwise.
If a user-managed Ollama is already running, app-managed startup should choose another loopback port and make the base-url mismatch visible instead of killing or hijacking the external service.
Runtime adoption of an app-owned model-service or Camofox endpoint must also
match the current host identity. App-owned state copied from another checkout or
machine should remain inspectable, but it must not override host-owned or
explicitly configured endpoints unless the persisted service owner equals the
current `AGENTIC_TRADER_HOST_ID`.

### Strict model readiness must verify generation, not just tags

Reason:
Ollama `/api/tags` can report a model as installed while `/api/generate` fails because of hardware backend, memory, or model-load errors.
Operation-mode readiness, strict daemon startup, and explicit `--provider-check` evidence should therefore run a tiny generation probe and fail closed when the configured model cannot produce output.
Default observer-style payloads may stay network-light, but product-readiness evidence must distinguish "service reachable", "model listed", and "model can generate".
`model-service status` should keep its default lightweight behavior, while
`model-service status --probe-generation` is the operator-facing diagnostic for
the same listed-but-not-loadable model failure caught by V1 readiness.

### The no-argument launcher chooses surfaces, it does not auto-trade

Reason:
The installed `agentic-trader` command should feel like a product entrypoint for humans, not a hidden background action.
No-argument launch may show runtime, setup, model-service, and WebGUI-service truth, then ask whether to open Web GUI, start the strict paper daemon, open Ink, open Rich, inspect setup/model-service, or exit.
Starting a daemon remains an explicit operator choice and still passes strict LLM/provider readiness before any paper cycle can run.

### App-owned Web GUI follows the same PID and loopback discipline

Reason:
The local Web GUI is useful as the first browser command center, but it should not become a separate long-lived process manager with looser security.
`webgui-service` records owner-only state and log paths under `runtime/webgui_service/`, binds Next.js to loopback, starts the local Next.js CLI through Node from the `webgui/` working directory, and stops only a recorded listener PID whose command line or loopback port ownership still matches the expected Web GUI process.
This protects users from stale PID reuse while keeping browser startup visible through CLI, setup-status, dashboard, observer-compatible payloads, and Web GUI operator panels.
If a Web GUI dev server is already reachable but was not started by `webgui-service`, the app should report it as external and must not kill or claim it.

### Optional web fetcher subprocesses inherit only explicit research env

Reason:
Firecrawl and Camofox are evidence helpers, not trusted runtime peers.
Firecrawl prefers the Python SDK when `FIRECRAWL_API_KEY` is available and can fall back to CLI calls for local/operator tooling; CLI calls receive a narrowed environment that includes only basic OS variables plus `FIRECRAWL_API_KEY`; broker/provider/runtime secrets stay out of optional research subprocesses by default.
Camofox must be started on loopback, and the bundled wrapper refuses to start without `CAMOFOX_ACCESS_KEY`.
The product-owned service path follows the same rule: `camofox-service` starts only a loopback helper, reads Camofox keys from ignored env/settings, disables crash telemetry and browser prewarm by default, narrows subprocess env to browser-helper variables, and records owner-only state/logs.
If only `CAMOFOX_API_KEY` is configured, the app-owned loopback helper mirrors it into `CAMOFOX_ACCESS_KEY` so routes are globally bearer-gated instead of starting an unkeyed local browser API.
Research collection may auto-start this helper only when the Camofox provider is explicitly enabled; Camofox remains browser-health/evidence infrastructure and does not become a broker, policy, or prompt-raw-text authority.
Helper `/health` alone is not enough for browser-backed research readiness: app-managed helper health may pass before the first on-demand browser launch, but if recent app-owned logs show Camoufox browser launch failures, status should degrade even when the Node server is reachable.

### V1 bootstrap should be provider-aware and opt-in around model installs

Reason:
V1 needs a smoother onboarding flow, but forced Ollama or default-model installation would over-assume the user's adapter and local setup choices.
The bootstrap path should detect missing prerequisites, offer sensible defaults such as Ollama plus a default local model, and still allow users to skip or replace that path without hidden behavior.
The setup surface therefore starts as read-only `setup-status` plus an interactive script that prompts before system installs.
Firecrawl remains optional and user-authenticated through `FIRECRAWL_API_KEY` for the SDK path or `firecrawl login --browser` for the CLI fallback; Camofox remains an optional local browser helper, installs Node dependencies with scripts disabled by default, and may download a browser binary only after explicit user approval.
The installer may create a user-local `agentic-trader` PATH symlink after uv has installed the console entrypoint, but it must not mutate trading policy, pull large models, start daemons, or create provider accounts without operator approval.
Runtime actions may start already-installed app-owned helper services only when the matching `AGENTIC_TRADER_RUNTIME_AUTO_START_*` flag is enabled. This is service supervision, not installation: missing binaries, missing models, missing Node dependencies, or missing access/API keys stay visible failures or degraded evidence.

### Onboarding uses a layered lifecycle surface, not a script maze

Reason:
The repo now has enough Python, pnpm workspace, sidecar, model-service, WebGUI-service, Firecrawl, and Camofox setup pieces that asking an operator to run them one by one is no longer a good V1 product experience.
The next setup architecture should keep focused debug commands intact, but add a small operator lifecycle vocabulary: `app:up`, `app:setup`, `app:start`, `app:stop`, `app:update`, `app:doctor`, and `app:uninstall`.
`app:up` is the guided happy path: detect prerequisites, install or repair dependencies, ask tool ownership questions, configure app-owned helper services where approved, start the Web GUI, and end with either an opened local URL or a precise blocker report.
`app:start` may start only already configured app-owned services; it must not secretly install binaries, pull models, accept provider terms, create accounts, or start a trading daemon.
`app:stop` and `app:uninstall` must operate only on app-owned state unless the operator confirms a separate destructive action for a host/global resource.

### Optional browser helper setup should be pnpm-owned inside the tool root

Reason:
The root JavaScript policy is pnpm, and `tools/camofox-browser` is optional tool infrastructure rather than a root workspace package.
Camofox should remain outside the root workspace until it needs shared package ownership, but its local dependency commands should use standalone `pnpm --dir tools/camofox-browser --ignore-workspace ...` commands so install, update, test, and lockfile behavior match the rest of the repo without accidentally running the root workspace install.
Dependency install stays separate from `camoufox-js fetch`: browser binary downloads are large, platform-sensitive, and should only run after explicit approval.
`camoufox-js` is the expected Node.js Camoufox bridge/fetch CLI for this helper, so installer output and docs should identify it clearly instead of leaving the operator to infer why that package appears.
The secure runtime boundary remains unchanged: loopback host only, access-key required, telemetry/prewarm off by default, narrowed environment, owner-only state/logs, and no raw browser content in trading prompts or broker/policy paths.

### Update and uninstall are first-class product workflows

Reason:
V1 local setup has multiple dependency owners, and "just rerun random scripts" is too easy to misapply.
`app:update` should become the single narrated update lane that calls each native owner: pnpm for the root workspace and Camofox tool root, uv for root Python, uv for the CrewAI Flow sidecar, then build/typecheck/setup-status/service-status checks.
`app:uninstall` should distinguish generated artifacts, installed dependency directories, downloaded helper assets, app-owned runtime state, ignored env files, keychain/API secrets, host services, and global tools.
By default it may remove only app-owned/generated pieces after confirmation; user secrets, provider accounts, broker config, host-owned Ollama/Firecrawl/Camofox processes, and unrelated global tools are preserved.

### Tool roots carry manifests, runtime code stays packaged

Reason:
The repo-level `tools/` tree is the product's local helper root, not a dump for generated projects.
Camofox, Ollama, and Firecrawl each carry a self-contained `agentic-tool.json` manifest describing setup/status/start commands, owning runtime modules, optional env, safety properties, and fallback order.
Python runtime code that must be installed with the package stays under `agentic_trader/system/` or `agentic_trader/researchd/`; the tool roots hold helper source, manifests, setup wrappers, and adapter metadata that setup/readiness can inspect.
`agentic_trader.system.tool_roots` is the first central registry for those tools: it maps repo tool IDs to setup/status IDs, consumers, fallback order, manifest notes, and install hints so setup-status, service status payloads, research provider metadata, and later runtime surfaces do not invent separate tool truths.
Nested upstream git metadata, `node_modules`, browser binaries, crash telemetry workers, broad plugin packs, generated init state, and runtime logs must stay untracked.

### Camofox is local browser infrastructure, not a research authority

Reason:
Camofox can help future browser-backed research fetchers, but browser automation is a high-risk surface for cookies, traces, proxy credentials, and raw page text.
V1 therefore treats `tools/camofox-browser` as optional local helper infrastructure.
Runtime integration is limited to loopback health/status evidence behind `researchd`; non-loopback base URLs fail closed, telemetry should be disabled when Agentic Trader starts the helper, and raw browser content, screenshots, cookies, traces, and proxy details must not enter trading prompts or broker/policy paths.

### Local tool roots are product infrastructure, sidecars are isolated runtimes

Reason:
The project now has optional local tools that are useful at runtime or during research, but they should not sprawl across setup scripts, global installs, root dependencies, and sidecar packages with inconsistent ownership.
`tools/` is the repo-owned home for optional helper infrastructure such as Camofox, future Ollama service assets/config, and future Firecrawl adapter metadata.
`sidecars/` remains the home for isolated runtime packages such as CrewAI Flow.
Setup and runtime code should detect a repo tool first, then a configured host-system tool, then a safe built-in fallback when available.
Every fallback path must remain explicit, redacted, source-attributed, loopback-aware for browser/model services, and outside broker/policy mutation.

### V1 maintainability can favor corporate-grade modularity over single-file convenience

Reason:
The early solo-developer bias kept changes small, but several files have grown large enough that auditability now matters more than keeping everything in one place.
When touching complex areas, prefer extracting domain constants, render helpers, service helpers, typed copy catalogs, and provider/fetcher adapters into named modules with focused tests.
This is still incremental architecture cleanup, not a license for broad rewrites or a new orchestration framework.

### Modularity and i18n debt is measured and gate-enforced

Reason:
The repository has enough modular seams in WebGUI, docs, Python CLI/Rich, Ink TUI, scripts, and optional tool helpers that new broad debt should fail locally and in CI instead of becoming another cleanup backlog.
Run `pnpm run qa:modularity` as the failing gate for oversized modules, long functions, repeated helper patterns, docs locale parity, and hardcoded operator-copy candidates.
Use `pnpm run qa:modularity:report` for exploratory cleanup, then tighten thresholds only after the current baseline has been reduced intentionally.
The audit must not classify runtime JSON field names, protocol enum values, database column names, provider identifiers, or test fixture data as localization debt by default.

### The existing docs scaffold should be activated, not replaced

Reason:
The repository already contains a `docs/` Next.js scaffold, while developer orientation still partly lives in repo notes such as `dev-docs/code-map.md`.
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
`CHANGELOG.md` must keep the `<!-- version list -->` insertion marker exactly once; semantic-release update mode uses that marker to prepend new release notes and can otherwise leave the changelog unchanged.
Any branch work that reaches `main` must preserve conventional commit subjects or use a conventional squash/PR title; the release workflow fails non-release, non-merge commits without a supported conventional prefix so branch changes do not silently disappear from `CHANGELOG.md`.
Stable release version stamping should also keep the root, Web GUI, docs, and TUI `package.json` versions aligned with the Python project version so the repo presents one coherent product baseline.
The binary workflow owns GitHub Release creation so immutable releases can be created with PyInstaller assets attached in one publish step.
The binary assets are convenience builds for the Python CLI layer; they do not bundle the Web GUI, docs app, Node runtime, Ollama, or external provider services.
GitHub Release bodies should be informative artifacts too: stable release bodies must include the matching `CHANGELOG.md` section when it exists plus a direct changelog link, and branch preview release bodies must include channel, branch, commit, workflow run, and changelog link metadata.
If semantic-release previews a tag below the tracked pre-1.0 baseline and that baseline tag does not exist yet, the release workflow should create a baseline changelog section, create the baseline tag once, and dispatch binary packaging with that tag. Plain `main` branch binary pushes may still upload workflow artifacts without publishing a GitHub Release; release publishing should happen from a tag/dispatch path.
If feature-branch prerelease tags such as `v0.12.5-beta.*` are already reachable from `main`, python-semantic-release can assign those commits to prerelease history before the final stable section is rendered. The stable workflow should therefore treat an empty stable section as a release-flow defect and backfill it from the previous stable tag to `HEAD`, ignoring prerelease tags, before committing the release files.

Stable release identity and branch build identity are intentionally separate.
Strict SemVer release tags keep the `MAJOR.MINOR.PATCH` core, such as `v0.9.5`; CI/build counters must not become a fourth core segment like `v0.9.5.9870`.
Integration branches such as `V1` should use `next` artifact identities, for example `v0.9.6-next.9870+gabc1234`, while feature branches should use `beta` artifact identities such as `v0.9.6-beta.9870+gabc1234`.
Only `main` should mutate `CHANGELOG.md` automatically.
Non-main branch pushes may publish SemVer-compatible prerelease tags/releases for testing, but product-impacting feature and V1 branch pushes should still bump the tracked patch version consistently across Python, workspace package manifests, sidecar metadata, and lockfile metadata before push so the tested branch artifact is identifiable.
The pre-1.0 baseline is `0.9.0`; `allow_zero_version=true` and `major_on_zero=false` keep V1-hardening releases on the 0.x line until the project intentionally declares a stable `1.0.0`.

### Development agents must verify version identity before publishing

Reason:
Branch publishing and stable release publishing now have different version
ownership rules. Stable changelog/tag publication is owned by semantic-release
on `main`, while feature and V1 branch pushes that change product behavior,
operator surfaces, docs, sidecars, setup, or workflow contracts should bump the
tracked patch version across `pyproject.toml`, `agentic_trader/__init__.py`,
root/workspace `package.json` files, `sidecars/research_flow/pyproject.toml`,
and lockfile metadata. `CHANGELOG.md` remains release-flow owned unless the
maintainer explicitly asks for a manual changelog edit.
Before pushing, agents should validate the branch identity with
`pnpm run version:plan`; use `pnpm run release:preview` when release config
behavior itself changed.

### PyInstaller builds should use a tracked CLI spec

Reason:
Release binaries should come from a reproducible packaging contract instead of whatever spec PyInstaller generates in a CI runner.
The canonical tracked spec is `agentic-trader.spec`, points at `main.py`, names the executable `agentic-trader`, and disables UPX to reduce platform-specific packaging variance and antivirus false positives.
CI smoke builds and release binary builds should use this spec directly.

### app:doctor is the first lifecycle slice and stays read-only

Reason:
The planned operator lifecycle needs a safe foothold before any mutating
`app:setup`, `app:start`, `app:stop`, `app:up`, `app:update`, or
`app:uninstall` behavior lands. `app:doctor` therefore resolves an already
installed `agentic-trader` entrypoint and reads existing status contracts only:
`setup-status`, model-service status, Camofox-service status, WebGUI-service
status, provider diagnostics, and network-light `v1-readiness`.
It must not call `uv run`, silently create or repair an environment, start or
stop services, pull Ollama models, fetch browser binaries, open the Web GUI, or
start a trading daemon. Provider/model generation checks remain explicit
through `v1-readiness --provider-check` or
`model-service status --probe-generation`.

### app:setup starts as dry-run plus explicit core repair

Reason:
The first mutating lifecycle command should prove the operator contract before
it grows side-application ownership.
`app:setup` therefore defaults to a dry-run plan and requires `--core --yes`
before running the existing root dependency owners: `pnpm run setup:node` and
`pnpm run install:python`.
It does not start a trading daemon, launch the Web GUI, start model-service or
Camofox, fetch browser binaries, pull Ollama models, modify provider accounts,
change secrets, or touch brokerage configuration.
Sidecar setup, Camofox setup/fetch, app-owned service starts, update,
uninstall, and guided `app:up` remain later opt-in lifecycle slices after
ownership choices such as host-owned, app-owned, API/key-only, or skipped are
explicit.

### app:start and app:stop are selected app-owned service slices

Reason:
Starting or stopping helper processes is riskier than setup planning, so the
first lifecycle service slice stays narrow and delegates ownership checks to the
existing service commands.
`app:start` and `app:stop` default to a dry-run plan. They require selecting
`--webgui`, `--model-service`, `--camofox-service`, or `--all` plus `--yes`
before they mutate anything.
`app:start` may call only `model-service start --host 127.0.0.1 --json`,
`camofox-service start --host 127.0.0.1 --json`, and
`webgui-service start --no-open-browser --json` for the selected service
surfaces; browser opening requires the extra `--open-browser` flag.
`app:stop` calls only the matching app-owned service stop commands and relies on
their recorded-PID/loopback ownership safeguards, preserving host-owned Ollama,
Camofox/browser helpers, and external Web GUI listeners. If a recorded
app-owned Web GUI process cannot be stopped, the state file must remain in
place so the operator can retry or inspect the still-owned listener instead of
having it reclassified as an external process.
Neither command installs dependencies, fetches a browser, pulls a model, creates
provider accounts, touches secrets or brokerage configuration, approves
proposals, or starts a trading daemon.

### app:update is a scoped native-owner lane

Reason:
Dependency and lockfile updates are broad enough that they should be narrated in
one operator command instead of scattered across manual `pnpm`, `uv`, sidecar,
tool-root, build, and status commands.
`app:update` therefore defaults to a dry-run plan and requires at least one
explicit scope plus `--yes` before it mutates anything.
The first scopes are `--core` for root pnpm plus uv workspace lock/env updates,
`--sidecar` for CrewAI Flow workspace member sync, `--camofox` for optional
Camofox helper package dependencies, `--build` for repository/sidecar/tool-root
checks, and `--status` for the post-update `app:doctor` payload.
`--all` selects the full lane.
The command must not fetch Camofox browser binaries, pull Ollama models, start
or stop app-owned services, create provider accounts, touch secrets or brokerage
configuration, delete runtime state, approve proposals, or start a trading
daemon.

### app:uninstall is a conservative app-owned cleanup lane

Reason:
Uninstall is a destructive product surface, so the first lifecycle slice should
prefer a precise local cleanup contract over a broad machine cleanup.
`app:uninstall` therefore defaults to a dry-run plan and requires at least one
explicit scope plus `--yes` before it removes files.
The first scopes are `--artifacts` for generated build/test/cache outputs,
`--deps` for local dependency directories plus the repo-local pnpm store, and
`--service-state` for app-owned helper service log/state directories.
`--all` selects those cleanup scopes, but it still preserves ignored env files,
secrets, provider accounts, brokerage configuration, host-owned services,
global tools, Keychain items, and trading runtime evidence such as DuckDB.
Service-state cleanup blocks when a recorded state file remains, so operators
must stop app-owned services through `app:stop` before deleting their service
records and logs.

### Camofox tool-root commands are pnpm-owned, browser fetch remains separate

Reason:
The root JavaScript policy is pnpm, and optional tool infrastructure should not
teach a second package-manager path unless there is a clear isolation reason.
Root scripts and docs should call standalone `pnpm --dir tools/camofox-browser
--ignore-workspace ...` commands for dependency install, browser fetch, and
syntax checks. The dependency install must still use `--ignore-scripts`, and the
Camoufox browser binary download must remain a separate explicit command because
it is large and platform-sensitive. The npm lockfile was removed only after a
dedicated pnpm tool-root install/test smoke proved the migration clean.
