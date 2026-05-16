[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=ogiboy_agentic-trader&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=ogiboy_agentic-trader)
[![Bugs](https://sonarcloud.io/api/project_badges/measure?project=ogiboy_agentic-trader&metric=bugs)](https://sonarcloud.io/summary/new_code?id=ogiboy_agentic-trader)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=ogiboy_agentic-trader&metric=coverage)](https://sonarcloud.io/summary/new_code?id=ogiboy_agentic-trader)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=ogiboy_agentic-trader&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=ogiboy_agentic-trader)
[![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=ogiboy_agentic-trader&metric=vulnerabilities)](https://sonarcloud.io/summary/new_code?id=ogiboy_agentic-trader)
[![Python](https://img.shields.io/badge/python-3.12--3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Node](https://img.shields.io/badge/node-%3E%3D22-339933?logo=node.js&logoColor=white)](https://nodejs.org/)
[![pnpm](https://img.shields.io/badge/pnpm-11.0.9-F69220?logo=pnpm&logoColor=white)](https://pnpm.io/)
[![CI](https://github.com/ogiboy/agentic-trader/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ogiboy/agentic-trader/actions/workflows/ci.yml)
[![SonarCloud CI](https://github.com/ogiboy/agentic-trader/actions/workflows/sonar.yml/badge.svg?branch=main)](https://github.com/ogiboy/agentic-trader/actions/workflows/sonar.yml)
[![Version Check](https://github.com/ogiboy/agentic-trader/actions/workflows/version-check.yml/badge.svg?branch=main)](https://github.com/ogiboy/agentic-trader/actions/workflows/version-check.yml)
[![Release](https://github.com/ogiboy/agentic-trader/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/ogiboy/agentic-trader/actions/workflows/release.yml)
[![Binaries](https://github.com/ogiboy/agentic-trader/actions/workflows/binaries.yml/badge.svg?branch=main)](https://github.com/ogiboy/agentic-trader/actions/workflows/binaries.yml)
[![Docs](https://github.com/ogiboy/agentic-trader/actions/workflows/docs.yml/badge.svg?branch=main)](https://github.com/ogiboy/agentic-trader/actions/workflows/docs.yml)
[![Latest Release](https://img.shields.io/github/v/release/ogiboy/agentic-trader?sort=semver&display_name=tag)](https://github.com/ogiboy/agentic-trader/releases)
[![License: LGPL-3.0-or-later](https://img.shields.io/badge/license-LGPL--3.0--or--later-blue.svg)](LICENSE)

```text
 █████╗  ██████╗ ███████╗███╗   ██╗████████╗██╗ ██████╗
██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝██║██╔════╝
███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   ██║██║
██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   ██║██║
██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   ██║╚██████╗
╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝ ╚═════╝

████████╗██████╗  █████╗ ██████╗ ███████╗██████╗
╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗
   ██║   ██████╔╝███████║██║  ██║█████╗  ██████╔╝
   ██║   ██╔══██╗██╔══██║██║  ██║██╔══╝  ██╔══██╗
   ██║   ██║  ██║██║  ██║██████╔╝███████╗██║  ██║
   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝╚═╝  ╚═╝
```

# Agentic Trader

Agentic Trader is a strict, local-first, multi-agent paper trading system for Ollama-class models. It keeps the Python runtime as the source of truth, uses deterministic guardrails before any paper order, and records decision context so operator-facing surfaces can be inspected instead of trusted blindly.

## Navigation

| Section              | Link                                     |
| -------------------- | ---------------------------------------- |
| Overview             | [What it is](#overview)                  |
| Features             | [Core capabilities](#features)           |
| Installation         | [Install paths](#installation)           |
| Quick Start          | [First commands](#quick-start)           |
| Binaries / Releases  | [Release builds](#releases--binaries)    |
| Web UI               | [Local command center](#web-gui)         |
| Documentation        | [Docs site](#documentation)              |
| Development          | [Contributor workflow](#development)     |
| Uninstall / Cleanup  | [Local cleanup](#uninstall--cleanup)     |
| License / Disclaimer | [Terms and safety](#license--disclaimer) |

## Overview

Agentic Trader is not a generic chat bot or a live broker. The runtime uses a staged specialist graph, structured model outputs, a deterministic execution guard, DuckDB-backed persistence, and paper broker accounting. The default posture is local-first, paper-first, and explicit about missing data, model readiness, and blocked execution paths.

The repository is now a small monorepo-style workspace:

| Path              | Purpose                                                                        |
| ----------------- | ------------------------------------------------------------------------------ |
| `agentic_trader/` | Python core runtime, CLI, agents, storage, workflows, and broker contracts     |
| `main.py`         | Root launcher for the Python CLI layer                                         |
| `webgui/`         | Local Next.js Web GUI that shells out to existing Python CLI/runtime contracts |
| `docs/`           | Separate Next.js documentation site intended for GitHub Pages                  |
| `tui/`            | Ink terminal control room managed through the root pnpm workspace              |

## Features

- Python CLI entrypoint: `agentic-trader = "agentic_trader.cli:app"`
- Strict paper-trading runtime with model/provider readiness checks
- Specialist agent pipeline with manager synthesis and execution guardrails
- DuckDB-backed run records, traces, trade context, journal, and portfolio state
- Optional research sidecar feed for source health, world-state snapshots, and future CrewAI-backed deep dives without replacing the core runtime
- Ink TUI, Rich/admin menu, live monitor, and JSON status surfaces
- Local Web GUI that delegates to the Python runtime instead of replacing it
- Static-exportable docs site for setup, architecture, QA, and development notes
- Root pnpm workspace and thin Makefile aliases for setup, checks, builds, and local app startup
- Release automation for semantic versioning, changelog updates, GitHub Releases, and packaged CLI binaries

## Installation

### Optional System Bootstrap

For a fresh machine, start with the interactive system-tool check. It detects
the tools around the app without silently installing paid/browser helpers:

```bash
make bootstrap-dry-run
make bootstrap
```

`bootstrap` can offer macOS installs for `uv`, Node, `pnpm`, Ollama, Firecrawl,
and the optional Camofox/RuFlo tooling when requested. It also offers a
`~/.local/bin/agentic-trader` symlink after the uv environment has created the
console entrypoint and warns when PATH resolves to a stale entrypoint from
another checkout. Firecrawl still requires user-owned authentication through
`firecrawl login --browser` or `FIRECRAWL_API_KEY` in an ignored env file.
Runtime auto-start flags only supervise already-installed local helpers; they
do not install tools, pull models, create accounts, or mutate trading policy.
For Camofox, `make setup-camofox` installs helper dependencies without running
browser-download scripts; `make fetch-camofox` downloads the optional Camoufox
browser binary only when you approve that step.

### Python / uv From Source

```bash
uv python install 3.13
pnpm run install:python
```

Daily source development now defaults to uv-managed Python 3.13 in the root
`.venv`. The root package still declares `>=3.12,<3.15` support so CI can keep
exercising the current minimum version signal, but local installs should not
drift onto the system Python. `scripts/install-python.sh` runs
`uv sync --locked --python 3.13 --all-extras --group dev`.

When changing Python dependencies, use uv as the source of truth:
`uv add <package>` for new packages, `uv lock --upgrade` for upgrades, and
`uv sync --locked --all-extras --group dev` to restore the full developer
environment. A plain `uv sync` can remove dev-only tools from `.venv`, so use
the locked dev sync above for normal source work.

Copy `.env.example` to a local ignored env file only when you need provider/model overrides. Do not put secrets in tracked files.

### Node Workspace

`pnpm` manages the Web GUI, docs site, and Ink TUI from the repository root:

```bash
pnpm install
pnpm approve-builds --all
```

For one-command workspace setup, use:

```bash
pnpm run setup
# or
make setup
```

`setup` installs the root pnpm workspace and verifies that `webgui/`, `docs/`,
and `tui/` each have their workspace `node_modules` links before syncing the
root uv Python environment. If you only need the JavaScript side, run
`pnpm run setup:node` or `make setup-node`.

For a read-only lifecycle check that does not install dependencies, start
services, pull models, open a browser, or start trading, run:

```bash
pnpm run app:doctor
# or
make app-doctor
```

For the first conservative setup lifecycle facade, start with the plan view:

```bash
pnpm run app:setup -- --dry-run
# or
make app-setup ARGS="--dry-run"
```

The only mutating `app:setup` path currently implemented is explicit core
repair:

```bash
pnpm run app:setup -- --core --yes
# or
make app-setup ARGS="--core --yes"
```

That path runs the existing root Node workspace setup and root uv Python sync
only. It does not start a trading daemon, start app-owned services, pull Ollama
models, fetch browser binaries, open the Web GUI, change provider accounts, or
touch brokerage configuration. Sidecar, Camofox, model-service, Web GUI launch,
update, and uninstall lanes remain separate opt-in lifecycle slices.

For app-owned services, preview first and then start or stop only the selected
service surfaces:

```bash
pnpm run app:start -- --dry-run
pnpm run app:start -- --webgui --yes
pnpm run app:stop -- --all --yes
```

`app:start` and `app:stop` do not install dependencies, fetch browsers, pull
models, open the Web GUI browser by default, or start the trading daemon. They
delegate ownership checks to `model-service`, `camofox-service`, and
`webgui-service`, so host-owned tools are not claimed or stopped. If an
app-owned Web GUI process cannot be stopped, its state is preserved for retry
instead of being reclassified as an external listener.

For the explicit update lane, preview first and then choose native dependency
owners:

```bash
pnpm run app:update -- --dry-run
pnpm run app:update -- --core --sidecar --build --status --yes
```

`app:update` can update root pnpm, root uv, CrewAI Flow sidecar uv, and optional
Camofox helper package dependencies, then run checks and `app:doctor`. It does
not fetch browser binaries, pull Ollama models, start or stop services, delete
runtime state, touch secrets or brokerage config, or start the trading daemon.

For conservative local uninstall, preview first and select only app-owned
generated scopes:

```bash
pnpm run app:uninstall -- --dry-run
pnpm run app:uninstall -- --artifacts --deps --yes
```

`app:uninstall` can remove generated build/test caches, local dependency
directories, the repo-local pnpm store, and app-owned helper service logs/state.
Recorded service state files block `--service-state` removal until the matching
`app:stop` command has cleared the app-owned process record. It preserves
ignored env files, secrets, provider accounts, brokerage configuration,
host-owned services, global tools, and trading runtime evidence such as DuckDB.

### Optional Web GUI

```bash
pnpm dev:webgui
agentic-trader webgui-service start
```

The Web GUI runs on loopback, normally
[http://localhost:3210](http://localhost:3210). The `webgui-service` commands
record app-owned state and log tails under `runtime/webgui_service/`; `stop`
only targets the recorded app-owned process.
If `AGENTIC_TRADER_WEBGUI_TOKEN` is set for a token-protected or proxied local
setup, the browser shell prompts for that token and exchanges it for a
same-origin HttpOnly session cookie before dashboard, chat, or runtime API calls
are allowed. Do not expose the Web GUI without either the app-owned loopback
launcher marker or an explicit token.

### Optional Docs Site

```bash
pnpm dev:docs
```

### Optional Ink TUI

```bash
pnpm start:tui
```

### Optional CrewAI Research Flow Sidecar

CrewAI is tracked as an isolated uv-managed Flow sidecar under
`sidecars/research_flow/`. It is not a root dependency and the core runtime does
not import it. When the research backend is set to `crewai`, the root process
calls the Flow sidecar through a subprocess JSON contract after the sidecar
environment has been installed.

```bash
pnpm run setup:research-flow
pnpm run check:research-flow
```

`pnpm run run:research-flow` is intentionally gated. It exits with a clear
message unless `OPENAI_API_KEY` is present in the shell, present in the sidecar's
ignored `.env`, or the local no-op flag is set for scaffold validation.

### Optional SEC EDGAR Research Source

The research sidecar can read recent SEC submissions metadata from the official
EDGAR JSON APIs, but it is off by default. Enable it only from an ignored local
env file and include an identifying SEC User-Agent/contact string:

```bash
AGENTIC_TRADER_RESEARCH_MODE=training
AGENTIC_TRADER_RESEARCH_SIDECAR_ENABLED=true
AGENTIC_TRADER_RESEARCH_SYMBOLS=AAPL,MSFT
AGENTIC_TRADER_RESEARCH_SEC_EDGAR_ENABLED=true
AGENTIC_TRADER_RESEARCH_SEC_EDGAR_USER_AGENT="Agentic Trader local contact@example.com"
```

This first provider normalizes recent filing metadata plus compact official
company-facts metrics into source-attributed research evidence. It does not
download full filing text, and it does not write directly into trading memory.

### Optional Firecrawl And Camofox Research Helpers

Firecrawl and Camofox are optional research fetcher/development helpers behind
`researchd`. They are disabled by default and only produce normalized
source-attributed evidence or provider-health records. Firecrawl uses the
Python SDK when `FIRECRAWL_API_KEY` is present and falls back to the CLI path
when needed. Raw web text is not passed into trading prompts.

```bash
AGENTIC_TRADER_RESEARCH_MODE=training
AGENTIC_TRADER_RESEARCH_SIDECAR_ENABLED=true
AGENTIC_TRADER_RESEARCH_SYMBOLS=AAPL
AGENTIC_TRADER_RESEARCH_FIRECRAWL_ENABLED=true
AGENTIC_TRADER_RESEARCH_FIRECRAWL_CLI=firecrawl
AGENTIC_TRADER_RESEARCH_CAMOFOX_ENABLED=true
AGENTIC_TRADER_RESEARCH_CAMOFOX_BASE_URL=http://127.0.0.1:9377
```

Start the bundled Camofox helper only through the loopback/auth wrapper:

```bash
CAMOFOX_ACCESS_KEY=$(openssl rand -hex 24) make start-camofox
```

The helper starts the HTTP service first and launches the browser on demand by
default. Set `CAMOFOX_BROWSER_PREWARM=true` only when you explicitly want a
warm browser and have confirmed the local Camoufox binary is stable.

Keep real provider keys in ignored local env files. The app-managed helper
prefers `CAMOFOX_ACCESS_KEY`; when only `CAMOFOX_API_KEY` is configured it is
mirrored into the loopback helper as the global access token so browser routes
are not left open during local research. These adapters cannot submit orders,
change runtime mode, or mutate broker policy.

When `AGENTIC_TRADER_RUNTIME_AUTO_START_MODEL_SERVICE=true`, strict runtime
actions can start an app-owned loopback Ollama process before checking model
generation. When `AGENTIC_TRADER_RUNTIME_AUTO_START_CAMOFOX=true` and the
Camofox research provider is enabled, research refreshes can start an app-owned
loopback Camofox helper before collecting browser-health evidence. Camofox
status treats a reachable HTTP server with `browserRunning=false` as ready for
on-demand launch by default, while recent browser launch failures in app-owned
logs still degrade readiness instead of treating a crash-looping helper as
usable. Inspect or control these helpers directly with:

```bash
agentic-trader model-service status --probe-generation --json
agentic-trader model-service stop --json
agentic-trader camofox-service status --json
agentic-trader camofox-service start
agentic-trader camofox-service stop
```

### Optional Release Binary

Download packaged CLI binaries from [GitHub Releases](https://github.com/ogiboy/agentic-trader/releases) when available. Binaries package the Python CLI layer; they do not bundle Ollama, the Web GUI, or the docs app.

## Quick Start

| Command                                                          | Purpose                                                           |
| ---------------------------------------------------------------- | ----------------------------------------------------------------- |
| `python main.py doctor`                                          | Check local runtime, model, database, and configuration readiness |
| `agentic-trader doctor --json`                                   | Emit the same health check as machine-readable JSON               |
| `python main.py run --symbol AAPL --interval 1d --lookback 180d` | Run one strict paper-trading cycle                                |
| `agentic-trader`                                                 | Open the operator launcher for Web GUI, daemon, Ink, Rich, setup, and model-service choices |
| `agentic-trader tui`                                             | Open the primary Ink terminal control room directly               |
| `agentic-trader menu`                                            | Open the Rich/admin fallback menu                                 |
| `agentic-trader dashboard-snapshot`                              | Print the shared dashboard payload used by UI surfaces; add `--provider-check` for product-readiness evidence |
| `agentic-trader setup-status --json`                             | Inspect source, side-application, and optional-tool readiness     |
| `pnpm --silent run app:doctor -- --json`                         | Read setup, provider, V1, and app-owned service readiness without mutating local state |
| `pnpm --silent run app:setup -- --json --dry-run`                 | Preview setup lifecycle steps without installing, starting services, pulling models, or fetching browsers |
| `pnpm --silent run app:setup -- --json --core --yes`              | Run only explicit core repair: root Node workspace setup plus root uv Python sync |
| `pnpm --silent run app:start -- --json --webgui --yes`            | Start only the selected app-owned service surfaces; Web GUI browser open stays opt-in |
| `pnpm --silent run app:stop -- --json --all --yes`                | Stop only app-owned service PIDs recorded by the app                 |
| `pnpm --silent run app:update -- --json --dry-run`                | Preview the scoped update lane across native dependency owners       |
| `pnpm --silent run app:uninstall -- --json --dry-run`             | Preview app-owned artifact/dependency/service-state removal          |
| `agentic-trader model-service status --probe-generation --json`  | Inspect configured/app-managed Ollama readiness, generation, and log tails |
| `agentic-trader model-service start`                             | Start only an app-owned loopback Ollama process                   |
| `agentic-trader model-service pull qwen3:8b`                     | Pull an Ollama model through the configured/app-owned service     |
| `agentic-trader webgui-service status --json`                    | Inspect app-owned Web GUI readiness and log tails                 |
| `agentic-trader webgui-service start`                            | Start/open the loopback Web GUI command center                    |

`--provider-check` readiness performs a tiny generation probe, not just a
reachability/model-list check. If Ollama can list a model but cannot load it,
strict operation gates fail closed before an agent cycle starts.

Advanced usage belongs in the docs site, not in this landing README.

## Releases / Binaries

Stable releases are driven by conventional commits on `main` through `python-semantic-release`. A release bump updates `pyproject.toml`, syncs root/workspace `package.json` versions, prepends `CHANGELOG.md`, creates a strict SemVer `v*` tag such as `v0.9.5`, and opens a GitHub Release.

Preview builds keep SemVer compatibility by using prerelease and build metadata instead of a fourth core version segment. Integration branches such as `V1` produce `next` prereleases like `v0.9.6-next.9870+gabc1234`; feature branches produce `beta` prereleases like `v0.9.6-beta.9870+gabc1234`.

Tagged stable builds attach PyInstaller CLI binaries for macOS and Windows to the matching release. Branch pushes also upload the same binaries as workflow artifacts and publish prerelease GitHub Releases for branch testing. Source install remains the most complete developer path; release binaries are for quick CLI/admin use.

## Usage

| Command                                                                                | Notes                                      |
| -------------------------------------------------------------------------------------- | ------------------------------------------ |
| `agentic-trader doctor`                                                                | Human-readable environment check           |
| `agentic-trader operator-workflow`                                                     | Show the canonical V1 review order         |
| `agentic-trader hardware-profile --json`                                               | Inspect local hardware/runtime sizing hints |
| `agentic-trader run --symbol AAPL --interval 1d --lookback 180d`                       | One paper cycle with strict gates          |
| `agentic-trader launch --symbols AAPL,MSFT --interval 1d --lookback 180d --continuous` | Continuous paper runtime                   |
| `agentic-trader monitor --refresh-seconds 1`                                           | Attach to runtime status                   |
| `agentic-trader supervisor-status --json`                                              | Inspect daemon state and log tails         |
| `agentic-trader broker-status --json`                                                  | Inspect paper/live/simulated backend truth |
| `agentic-trader finance-ops --json`                                                    | Inspect broker/account/PnL/exposure evidence as a read-only trading-desk check |
| `agentic-trader setup-status --json`                                                   | Inspect root/sidecar/tool readiness without installing anything |
| `pnpm --silent run app:doctor -- --json`                                               | Inspect setup, service, provider, and V1 readiness without installing or starting anything |
| `pnpm --silent run app:setup -- --json --dry-run`                                      | Preview setup lifecycle steps and deferred optional tool/service actions |
| `pnpm --silent run app:setup -- --json --core --yes`                                   | Repair only core root dependencies after explicit approval |
| `pnpm --silent run app:start -- --json --webgui --yes`                                 | Start selected app-owned helper services without installing, pulling models, or launching a trading daemon |
| `pnpm --silent run app:stop -- --json --all --yes`                                     | Stop only app-owned helper services recorded by the app |
| `pnpm --silent run app:update -- --json --dry-run`                                     | Preview root/sidecar/tool-root update, build, and status lanes |
| `pnpm --silent run app:uninstall -- --json --dry-run`                                  | Preview app-owned generated artifact and dependency removal |
| `agentic-trader model-service status --probe-generation --json`                        | Inspect local Ollama/service/model/generation readiness |
| `agentic-trader webgui-service status --json`                                          | Inspect loopback Web GUI service readiness |
| `agentic-trader provider-diagnostics --json`                                           | Inspect model, source, key, and fallback readiness |
| `agentic-trader v1-readiness --json`                                                   | Inspect V1 paper-operation and Alpaca paper-readiness checks; add `--provider-check` before longer paper runs and to verify local-model generation |
| `agentic-trader trade-proposals --json`                                                | Inspect the manual-review proposal queue |
| `agentic-trader proposal-create ...`                                                   | Queue a non-executing paper proposal for approval |
| `agentic-trader proposal-reconcile PROPOSAL_ID --json`                                 | Repair an in-flight proposal from a recorded execution outcome without resubmitting |
| `agentic-trader idea-presets` / `agentic-trader idea-score ...`                        | Explore V1 idea-scanner presets without creating orders |
| `agentic-trader strategy-catalog --json` / `agentic-trader strategy-profile NAME`       | Inspect strategy-family evidence, risk, and validation gates |
| `agentic-trader news-intelligence --symbol AAPL --json`                                | Build a source-tiered news/materiality research plan without fetching the web |
| `agentic-trader research-cycle-plan --symbols AAPL,MSFT --json`                        | Inspect the safe PRE-FLIGHT/MONITOR/ANALYZE/PROPOSE/DIGEST cycle contract |
| `agentic-trader research-cycle-run --symbols AAPL,MSFT --cycles 2 --no-sleep --json`    | Run bounded evidence-only research cycles with preflight, source-health delta, cadence, and digest output but no broker authority |
| `agentic-trader evidence-bundle --provider-check --json`                               | Package read-only QA/release evidence with active model/provider readiness |
| `agentic-trader research-status --json`                                                | Inspect optional research sidecar health   |
| `agentic-trader research-refresh --json`                                               | Run one isolated sidecar snapshot pass     |
| `agentic-trader research-flow-setup --json`                                            | Inspect optional CrewAI Flow sidecar readiness |
| `agentic-trader review-run`                                                            | Review the latest persisted run            |

## Web GUI

`webgui/` is a local command center for the existing runtime. It validates browser inputs, then calls the Python CLI/dashboard/runtime/chat/instruction contracts from server-side route handlers. It is intentionally not a second orchestrator.

```bash
pnpm dev:webgui
```

## Documentation

The docs app lives in `docs/` and is intended to deploy to GitHub Pages:

[https://ogiboy.github.io/agentic-trader/](https://ogiboy.github.io/agentic-trader/)

Use it for deeper setup, architecture, runtime, QA, frontend, and contribution guidance. Local development uses `pnpm dev:docs`.

## Development

This repo favors small, inspectable changes over broad rewrites. Keep Python runtime behavior, Web GUI delegation, and docs content aligned.

```bash
pnpm check
make check
pnpm run app:doctor
pnpm run app:setup -- --dry-run
pnpm run app:start -- --dry-run
pnpm run app:stop -- --dry-run
pnpm run app:update -- --dry-run
pnpm run app:uninstall -- --dry-run
pnpm run qa:quality
pnpm run setup:research-flow
pnpm run check:research-flow
pnpm run version:plan
pnpm run release:preview
pnpm run sonar:status
pnpm run mcp:sonarqube:status
pnpm run sonar
```

`pnpm check` is the canonical static/build validation entrypoint. Use `pnpm run qa` or `pnpm run qa:quality` for terminal smoke QA and operator-surface checks. The Makefile is a thin alias layer for developers who prefer `make setup`, `make check`, `make webgui`, `make docs`, or `make tui`.

Sonar is split by target on purpose:

| Target                          | Project key             | Use                                                              |
| ------------------------------- | ----------------------- | ---------------------------------------------------------------- |
| Local SonarQube Community Build | `agentic-trader`        | Local Docker server, branch QA, Codex/MCP inspection             |
| SonarCloud                      | `ogiboy_agentic-trader` | GitHub-hosted CI, public badge, repository-level quality history |

`sonar-project.properties` is the local default scanner file. `pnpm run sonar` runs the local Python scanner path through `pysonar`; `pnpm run sonar:js` runs the local npm scanner through `@sonar/scan`. Both read `SONAR_TOKEN` from the environment or macOS Keychain service `codex-sonarqube-token`. Use `pnpm run sonar:cloud` only when manually uploading to SonarCloud; it expects a SonarCloud token in `SONAR_TOKEN` or Keychain service `codex-sonarcloud-token`.

`pnpm run sonar:start` waits until the local server is actually ready instead of only starting Docker containers. If an existing `sonarqube_postgres` volume was initialized with an older `SONAR_POSTGRES_PASSWORD`, the start/status scripts diagnose the password mismatch and suggest `pnpm run sonar:repair-db-password`, which aligns the stored local `sonar` database user password without deleting local Sonar history. If you provide `SONAR_AUTH_JWTBASE64HS256SECRET`, it must be Base64 encoded; unset it to use the repository's local-development default.

Use `pnpm run secret:sonar:check`, `pnpm run mcp:sonarqube:dry-run`, or `pnpm run mcp:sonarqube:status` to verify the local Keychain/MCP wiring without printing tokens. The editor/Codex MCP wrapper uses `SONARQUBE_URL=http://host.docker.internal:9000` so Docker can reach the local host SonarQube server. Multiple running `mcp/sonarqube` containers usually mean multiple active MCP clients, not multiple SonarQube servers.

GitHub Actions needs only `SONAR_TOKEN` as a repository secret for SonarCloud. Docs deployment uses GitHub Pages permissions, releases/binaries use the built-in `GITHUB_TOKEN`, and local Docker SonarQube tokens should stay on the developer machine.

uv selects and syncs the root Python interpreter from `.python-version`, owns root dependency locking, command execution, and builds, while the tracked CrewAI Flow sidecar owns its own nested `uv.lock`. pnpm owns JavaScript workspace dependencies plus the shared command surface. The two uv projects intentionally stay separate below the root scripts so CrewAI can evolve without widening the core runtime dependency graph.

Commit messages should follow conventional commits so release automation can infer version bumps:

| Type     | Example                                           |
| -------- | ------------------------------------------------- |
| Feature  | `feat: add docs deployment workflow`              |
| Fix      | `fix: correct pyinstaller smoke build entrypoint` |
| Docs     | `docs: rewrite root readme`                       |
| Breaking | `feat!: change release packaging flow`            |

`main` is the only branch that mutates `CHANGELOG.md` automatically. Product-impacting feature and V1 branch pushes still bump the tracked patch version across Python, workspace package manifests, sidecar metadata, and lockfile metadata before push so local artifacts identify the tested build clearly; `pnpm run version:plan` remains the branch preview check.

## Uninstall / Cleanup

Normal cleanup removes build/test/cache artifacts but keeps installed
dependencies:

```bash
pnpm run clean
# or
make clean
```

Remove dependency installs explicitly when you want a fresh setup:

```bash
pnpm run app:uninstall -- --dry-run
pnpm run app:uninstall -- --artifacts --deps --yes
# or the older focused cleanup commands:
pnpm run clean:deps
# or remove artifacts and dependencies together:
pnpm run clean:all
```

If an older Poetry/Conda setup is still present, remove it separately:

```bash
conda remove -n trader --all
```

## License / Disclaimer

Agentic Trader is released under the GNU Lesser General Public License v3.0 or
later (`LGPL-3.0-or-later`). See [LICENSE](LICENSE).
Bundled or adapted third-party helper components keep their own notices when
their package metadata says so.

Agentic Trader is a paper-trading research and operator-tooling project. It does not provide financial advice, and it must not be treated as a live brokerage system. Live execution remains blocked unless a real adapter, explicit approval gates, and operator-visible safety checks are implemented.
