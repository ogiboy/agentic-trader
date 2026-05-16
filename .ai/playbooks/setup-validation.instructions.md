# Setup Validation Playbook

Use this after environment, package-manager, sidecar, or Codex workspace setup
changes.

If a command, package manager, sidecar, Docker service, browser helper, or local
model service is unavailable, report the missing prerequisite and choose the
smallest non-mutating status check that still describes setup health. Do not
install, upgrade, or delete dependencies unless the task explicitly allows it.

## Root Checks

- `pnpm run setup`
- `pnpm run check`
- `pnpm run version:plan`
- New dependency: `uv add <package>` rather than editing `pyproject.toml` by hand
- Dependency upgrade: `uv lock --upgrade`, then `uv sync --locked --all-extras --group dev`
- `ruflo doctor -c version`
- `ruflo doctor -c node`
- `ruflo doctor -c npm`
- `ruflo hooks pre-command -- "pnpm run setup"`
- `ruflo hooks pre-command -- "pnpm run check"`

## Planned Lifecycle Checks

When the accelerated setup layer lands, validate the lifecycle commands by intent
instead of treating them as aliases for the same script:

- `pnpm run app:doctor`: read-only setup, PATH, sidecar, service, provider, and
  optional tool-root status
- `pnpm run app:setup -- --dry-run`: setup lifecycle preview only
- `pnpm run app:setup -- --core --yes`: root pnpm workspace plus root uv Python
  repair only; no trading daemon start, no app-owned service start, and no
  hidden browser/model download
- `pnpm run app:start -- --dry-run`: app-owned service start preview only
- `pnpm run app:start -- --webgui --yes`: start only the selected app-owned
  Web GUI service with browser opening disabled unless `--open-browser` is
  provided
- `pnpm run app:stop -- --dry-run`: app-owned service stop preview only
- `pnpm run app:stop -- --all --yes`: stop only app-owned service records
  through existing service ownership safeguards
- `pnpm run app:update -- --dry-run`: update lifecycle preview across native
  dependency owners only
- `pnpm run app:update -- --core --sidecar --build --status --yes`: selected
  root/sidecar update lane plus checks/status; no browser fetch, model pull, or
  service start/stop
- `pnpm run app:up`: guided first-run path that may repair setup, start approved
  app-owned helper services, and open Web GUI
- `pnpm run app:start`: start configured app-owned services and Web GUI only
- `pnpm run app:stop`: stop only app-owned service PIDs recorded by the app
- `pnpm run app:update`: update native dependency owners, rebuild, and report
  setup/service status
- `pnpm run app:uninstall`: remove confirmed app-owned artifacts while preserving
  secrets, provider accounts, brokerage config, host services, and global tools
- `pnpm run app:uninstall -- --dry-run`: uninstall lifecycle preview only
- `pnpm run app:uninstall -- --artifacts --deps --yes`: remove generated
  artifacts and dependency directories only
- `pnpm run app:uninstall -- --service-state --yes`: remove app-owned service
  logs/state only after recorded service state files are already cleared
- `pnpm run app:up -- --dry-run`: preview the guided first-run orchestration
  without mutating dependencies, optional helpers, services, or browser state
- `pnpm run app:up -- --all --yes`: run only the safe first-run lane: core
  repair, CrewAI Flow sidecar setup, app-owned Web GUI start, and final doctor
- `pnpm run app:up -- --model-service --ollama-owner=app-owned --yes`: start
  the app-owned model-service only after the ownership decision is explicit

Every lifecycle command should have a dry-run or preview path before it mutates
system tools, dependency locks, downloaded browser/model assets, PATH symlinks,
or app-owned runtime state.

## Focused Checks

- Python only: `uv run python -m pytest -q -p no:cacheprovider <target>`
- Root lock: `uv lock --check`
- WebGUI: `pnpm --filter webgui lint && pnpm --filter webgui typecheck && pnpm --filter webgui build`
- Docs: `pnpm --filter docs lint && pnpm --filter docs typecheck && pnpm --filter docs build`
- TUI: `pnpm --filter tui check`
- Research Flow sidecar:
  - `pnpm run setup:research-flow`
  - `pnpm run check:research-flow`
  - `cd sidecars/research_flow && uv lock --check`
- Camofox tool root:
  - `pnpm --dir tools/camofox-browser install --ignore-workspace --ignore-scripts`
  - `pnpm --dir tools/camofox-browser --ignore-workspace run fetch:browser`
  - `pnpm --dir tools/camofox-browser --ignore-workspace run test`
  - keep dependency install separate from browser binary fetch

## Validate Semantics

- `setup` installs dependencies.
- `clean` removes generated artifacts only.
- `clean:deps` or `clean:all` removes installed dependencies.
- `app:up` may launch the Web GUI but must not auto-start a trading daemon.
- `app:up --all` must not imply browser binary fetches, model pulls, Camofox
  service start, provider account creation, brokerage config edits, or hidden
  tool ownership.
- `app:start`, `app:stop`, and `app:uninstall` affect app-owned resources only
  unless the operator explicitly approves broader host/global changes.
- `app:start` and `app:stop` require an explicit service selection plus `--yes`
  before mutation, and must not install dependencies, fetch browser binaries,
  pull Ollama models, open a browser by default, or start a trading daemon.
- `webgui-service stop` should preserve app-owned state if the recorded process
  cannot be stopped, so retry/debug remains possible and the process is not
  reclassified as external.
- `app:update` must require explicit scopes plus `--yes` before mutation and
  must not fetch browser binaries, pull Ollama models, start/stop services,
  create provider accounts, touch brokerage config, delete runtime state, or
  start a trading daemon.
- `app:uninstall` must require explicit scopes plus `--yes` before removal,
  preserve ignored env files/secrets/provider accounts/brokerage config/global
  tools/host services/trading evidence, and block service-state removal while a
  recorded service state file remains.
- Optional Ollama, Firecrawl, and Camofox setup records host-owned, app-owned,
  API/key-only, or skipped ownership instead of guessing silently.
- Root Python is uv-managed; Conda/Poetry are not the default path.
- A plain `uv sync` is not enough for local V1 development because it can omit
  the dev dependency group. Recover with
  `uv sync --locked --all-extras --group dev`.
- Sidecar runtime does not implicitly install dependencies.

## Failure Triage

| Failure                | First Check                              | Follow-Up                                        |
| ---------------------- | ---------------------------------------- | ------------------------------------------------ |
| root uv sync           | `uv lock --check`                        | inspect `pyproject.toml` and `uv.lock` diff      |
| workspace deps missing | `pnpm install --frozen-lockfile`         | verify `pnpm-workspace.yaml` and package scripts |
| Camofox deps missing   | `pnpm --dir tools/camofox-browser install --ignore-workspace --ignore-scripts` | verify tool-root lockfile and no hidden browser fetch |
| Camofox browser missing | `pnpm --dir tools/camofox-browser --ignore-workspace run fetch:browser` | require explicit operator approval first |
| WebGUI build           | `pnpm --filter webgui build`             | run Browser QA if UI behavior changed            |
| docs build             | `pnpm --filter docs build`               | verify static export assumptions                 |
| sidecar check          | `pnpm run check:research-flow`           | verify sidecar `.venv` and `uv.lock`             |
| app-owned model absent | `agentic-trader model-service status --probe-generation --json` | verify host-owned vs app-owned vs skipped provider choice |
| command runtime risk   | `ruflo hooks pre-command -- "<command>"` | document residual risk before running            |

When setup validation changes runtime-managed tools, verify both directions:
fresh-user readiness when the host tool is absent and host-tool coexistence when
the user already has a service running. No app-owned stop command may kill an
unrelated host process.
