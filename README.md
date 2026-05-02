[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=ogiboy_agentic-trader&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=ogiboy_agentic-trader)
[![Python](https://img.shields.io/badge/python-3.12--3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![CI](https://github.com/ogiboy/agentic-trader/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ogiboy/agentic-trader/actions/workflows/ci.yml)
[![SonarCloud CI](https://github.com/ogiboy/agentic-trader/actions/workflows/sonar.yml/badge.svg?branch=main)](https://github.com/ogiboy/agentic-trader/actions/workflows/sonar.yml)
[![Version Check](https://github.com/ogiboy/agentic-trader/actions/workflows/version-check.yml/badge.svg?branch=main)](https://github.com/ogiboy/agentic-trader/actions/workflows/version-check.yml)
[![Release](https://github.com/ogiboy/agentic-trader/actions/workflows/release.yml/badge.svg?branch=main)](https://github.com/ogiboy/agentic-trader/actions/workflows/release.yml)
[![Docs](https://github.com/ogiboy/agentic-trader/actions/workflows/docs.yml/badge.svg?branch=main)](https://github.com/ogiboy/agentic-trader/actions/workflows/docs.yml)
[![Latest Release](https://img.shields.io/github/v/release/ogiboy/agentic-trader?sort=semver&display_name=tag)](https://github.com/ogiboy/agentic-trader/releases)

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

### Optional Web GUI

```bash
pnpm dev:webgui
```

The Web GUI runs at [http://localhost:3210](http://localhost:3210).

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

This first provider normalizes recent filing metadata into source-attributed
research evidence. It does not download full filing text or XBRL facts yet, and
it does not write directly into trading memory.

### Optional Release Binary

Download packaged CLI binaries from [GitHub Releases](https://github.com/ogiboy/agentic-trader/releases) when available. Binaries package the Python CLI layer; they do not bundle Ollama, the Web GUI, or the docs app.

## Quick Start

| Command                                                          | Purpose                                                           |
| ---------------------------------------------------------------- | ----------------------------------------------------------------- |
| `python main.py doctor`                                          | Check local runtime, model, database, and configuration readiness |
| `agentic-trader doctor --json`                                   | Emit the same health check as machine-readable JSON               |
| `python main.py run --symbol AAPL --interval 1d --lookback 180d` | Run one strict paper-trading cycle                                |
| `agentic-trader`                                                 | Open the primary Ink terminal control room                        |
| `agentic-trader menu`                                            | Open the Rich/admin fallback menu                                 |
| `agentic-trader dashboard-snapshot`                              | Print the shared dashboard payload used by UI surfaces            |

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
| `agentic-trader provider-diagnostics --json`                                           | Inspect model, source, key, and fallback readiness |
| `agentic-trader v1-readiness --json`                                                   | Inspect V1 paper-operation and Alpaca paper-readiness checks |
| `agentic-trader evidence-bundle --json`                                                | Package read-only QA/release evidence      |
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

`main` is the only branch that mutates `pyproject.toml`, workspace package versions, and `CHANGELOG.md` automatically. Other branches run version previews and publish SemVer-compatible prerelease tags/releases without changing tracked version files.

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
pnpm run clean:deps
# or remove artifacts and dependencies together:
pnpm run clean:all
```

If an older Poetry/Conda setup is still present, remove it separately:

```bash
conda remove -n trader --all
```

## License / Disclaimer

No license has been granted yet; usage restrictions apply until a `LICENSE` file is added.

Agentic Trader is a paper-trading research and operator-tooling project. It does not provide financial advice, and it must not be treated as a live brokerage system. Live execution remains blocked unless a real adapter, explicit approval gates, and operator-visible safety checks are implemented.
