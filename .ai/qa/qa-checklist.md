# QA Checklist

Use this checklist for behavior-changing work. Not every item applies to every task, but skipped high-risk sections should be intentional.

## Baseline Verification

- [ ] Treat every push as a product-readiness checkpoint, not only a code-green
  checkpoint: verify first-run entry, app-owned/helper-tool truth, operator
  surfaces, security posture, and clean shutdown behavior when the change could
  affect V1 operation.
- [ ] Run terminal smoke QA:
  - `pnpm run qa`
- [ ] For code-quality passes, run:
  - `pnpm run qa:quality`
- [ ] When SonarQube is available, run:
  - `pnpm run sonar:status`
  - `pnpm run mcp:sonarqube:status`
  - `pnpm run sonar`
  - `pnpm run sonar:js` when validating the npm scanner path specifically
  - `pnpm run sonar:cloud` only when intentionally uploading to SonarCloud
- [ ] Run the smallest relevant targeted tests.
- [ ] Run the full suite when feasible:
  - `pnpm run check`
- [ ] For workflow/release changes, preview version identity:
  - `pnpm run version:plan`
  - `pnpm run release:preview` when release/CI/package metadata changed
- [ ] For product-impacting feature/V1 branch pushes, confirm the tracked patch
  version was bumped consistently across Python, workspace package manifests,
  sidecar metadata, and lockfile metadata before push.
- [ ] Before pushing release/version/package metadata work, confirm
  `pyproject.toml`, `agentic_trader/__init__.py`, workspace `package.json`
  files, `sidecars/research_flow/pyproject.toml`, and lock metadata agree, and
  `CHANGELOG.md` moved only when the task explicitly asked for release/changelog
  ownership.
- [ ] Confirm `git status --short` does not contain accidental runtime artifacts.
- [ ] Confirm smoke artifacts are grouped under a timestamped `.ai/qa/artifacts/smoke-*` directory.
- [ ] Confirm changed roadmap items are checked or left unchecked accurately.
- [ ] Confirm `.ai/current-state.md`, `.ai/tasks.md`, and `.ai/decisions.md` are updated when architecture, runtime contracts, or assumptions change.
- [ ] For non-trivial, security-sensitive, broker, storage, Web route, release,
  performance, or 5+ file changes, run the relevant `.ai/workflows/` checklist
  and an advisory diff-risk/file-risk pass when RuFlo MCP is available.
- [ ] For CLI/Rich/Ink visual changes, use pexpect/tmux/asciinema for baseline interaction and layout verification, and add a Computer Use screenshot/screen-state pass when the environment exposes it.
- [ ] For Web GUI changes, run the local `webgui/` shell, check the route handlers and browser surface, and add a Browser Use or equivalent localhost visual pass when the environment exposes it.

## Code Quality

- [ ] `ruff check .` passes or findings are triaged.
- [ ] `pytest -q -p no:cacheprovider` passes or failures are triaged.
- [ ] `pyright` or IDE/Pylance diagnostics are checked when available.
- [ ] SonarQube, `pysonar`, `@sonar/scan`, and SonarCloud findings are reviewed against the intended target/project key.
- [ ] Sonar findings are triaged across the full codebase, not only the latest commit, and are prioritized as security/correctness, blocker/critical maintainability, then minor cleanup.
- [ ] Any accepted Sonar finding has a written reason and residual-risk note; no finding is dismissed as "unimportant" without review.
- [ ] `.sonar/` remains ignored and no Sonar token is written to tracked files or artifacts.

## Security Posture

- [ ] Run a pre-push security posture pass for security-sensitive or broad
  changes: Web GUI routes, observer API, subprocess helpers, provider/sidecar
  fetchers, proposal approval, runtime modes, artifacts, and dependency drift.
- [ ] Web GUI mutating routes reject foreign origins, malformed JSON, oversized bodies, missing/invalid token when `AGENTIC_TRADER_WEBGUI_TOKEN` is set, and rapid repeated runtime/chat/instruction calls.
- [ ] Web GUI session/token/cookie assumptions are explicit: if no session
  model exists yet, local-loopback plus optional token controls must be stated,
  and route handlers must not imply authenticated multi-user operation.
- [ ] Observer API keeps loopback-only as the default and rejects non-loopback binds unless `--allow-nonlocal` and `AGENTIC_TRADER_OBSERVER_API_TOKEN` are both used.
- [ ] Supervisor log tails, sidecar subprocess failures, provider exception notes, and Web error responses redact fake `*_KEY`, `*_SECRET`, `TOKEN`, and `Authorization: Bearer ...` values.
- [ ] `runtime/` feed/log writes and research snapshots prefer owner-only file permissions where the local filesystem supports them.
- [ ] Research sidecars do not inherit broker/runtime credentials unless a future explicit allowlist says so.
- [ ] Artifact bundles and smoke reports do not contain `.env`, real provider keys, bearer tokens, raw provider payloads, or unredacted subprocess stderr.
- [ ] Dependency/security scan findings are triaged as runtime/security risk, not auto-upgraded blindly.

## CLI

- [ ] Commands exit cleanly with code `0` for successful paths.
- [ ] Commands show clear error messages for blocked paths.
- [ ] Changed commands have clear `--help` text and, where supported by Typer, `-h`/`--help` behavior is checked.
- [ ] Common options have consistent short and long forms where a shortcut exists; missing shortcuts are intentional, not accidental.
- [ ] Help output includes safe examples for non-obvious trading/runtime commands.
- [ ] Command names and option names are understandable to an operator without reading source code.
- [ ] `--json` output is valid JSON where supported.
- [ ] Human-readable output is concise and does not hide critical runtime state.
- [ ] `agentic-trader broker-status` reports paper/live/kill-switch truth accurately.
- [ ] `agentic-trader provider-diagnostics --json` reports selected source,
  fallback/degraded-mode warnings, freshness/completeness placeholders, and
  API-key readiness without leaking secret values.
- [ ] `agentic-trader v1-readiness --json` reports paper-operation gates and
  Alpaca paper-readiness gates before longer operation or external paper checks.
- [ ] For product-readiness evidence, run `agentic-trader v1-readiness
  --provider-check --json`, `agentic-trader dashboard-snapshot --provider-check`,
  or `agentic-trader evidence-bundle --provider-check --json` so the V1 paper
  gate reflects actual model/provider readiness rather than the safe
  network-free "not checked" state.
- [ ] `agentic-trader supervisor-status` reports daemon metadata and log tails without requiring the DuckDB writer lock.
- [ ] Observer-compatible supervisor payloads expose the same daemon metadata and log-tail truth.
- [ ] `agentic-trader dashboard-snapshot` contains the same truth consumed by Ink.
- [ ] `agentic-trader setup-status --json` reports core and optional side-application readiness without installing anything.
- [ ] `agentic-trader model-service status --probe-generation --json` and
  `model-service start/stop/pull --json` paths are tested with mocked or
  intentional local Ollama behavior; non-loopback hosts fail closed,
  generation-load failures block provider-check readiness and model-service
  generation probes, and app-owned stop never kills external Ollama or forgets a
  still-running app-owned PID. Stale app-managed Ollama listeners on
  11435-11465 should be detected and cleaned by stop/start, while a remaining
  11434 listener is reported as host/default Ollama instead of killed silently.
- [ ] `agentic-trader webgui-service status/start/stop --json` paths are tested with mocked or intentional local Web GUI behavior; binds stay loopback-only and app-owned stop never kills unrelated PIDs.
- [ ] `agentic-trader` without arguments shows operator-launcher choices and does not start the daemon unless the operator explicitly selects that path.

## Ink TUI

- [ ] Use pexpect/tmux/asciinema to open the Ink control room and inspect the changed page or flow; add a Computer Use visual pass when available.
- [ ] `agentic-trader tui` opens the Ink control room when the console entrypoint is installed.
- [ ] `agentic-trader` and `python main.py` open the same primary operator launcher before any surface is selected.
- [ ] First-launch logo/header fits without pushing the primary controls off screen.
- [ ] Layout remains readable after terminal resize, including compact, normal, and wide sizes when feasible.
- [ ] Text wraps or truncates intentionally; critical state is not clipped.
- [ ] Navigation hints and hotkeys are visible before the operator needs them.
- [ ] Hotkeys work: `1-6`, `r`, `s`, `x`, `R`, `q`.
- [ ] Runtime page shows current stage, daemon metadata, broker state, and recent stage flow.
- [ ] Chat page shows transcript plus live agent activity, reasoning stage, and tool/memory context.
- [ ] Portfolio/review/memory pages degrade gracefully when the runtime writer owns DuckDB.
- [ ] The app can be exited cleanly without traceback.

## Rich Menu

- [ ] Use pexpect/tmux/asciinema to open the Rich menu and inspect the changed page or flow; add a Computer Use visual pass when available.
- [ ] `agentic-trader menu` opens the legacy/admin Rich menu.
- [ ] Logo/header usage does not consume so much space that menu output becomes hard to scan.
- [ ] Categories are navigable without excessive scrolling.
- [ ] Back, close, cancel, and exit options are named consistently across menus.
- [ ] Menu labels explain the action or destination clearly enough for a non-developer operator.
- [ ] Runtime start does not block the menu.
- [ ] Live monitor can attach without DuckDB lock crashes.
- [ ] Observer mode messages are explicit when DB-backed views are temporarily unavailable.
- [ ] Ctrl+C exits cleanly.

## Runtime / Daemon

- [ ] Strict LLM gate blocks trading runtime when the configured model is unavailable.
- [ ] A fresh-user path is tested or explicitly blocked: `agentic-trader`
  starts the operator launcher cleanly, shows setup/model/WebGUI truth, and does
  not leave unowned background processes after exit.
- [ ] App-managed helper tools are accounted for: Ollama, Camofox, Firecrawl,
  CrewAI Flow, WebGUI, Docker/RuFlo advisory tooling, and degraded fallbacks
  show accurate readiness and do not pretend missing optional tools are healthy.
- [ ] Background start records PID, heartbeat, launch count, restart count, stdout/stderr paths, and current symbol.
- [ ] Stop request works without needing the DB writer lock.
- [ ] Restart uses the stored launch configuration and increments restart metadata.
- [ ] Stale PID state does not permanently block a new launch.
- [ ] Live monitor shows agent-stage progress, not only system status.

## Agent Pipeline

- [ ] Stage events are emitted for coordinator, regime, strategy, risk, consensus, manager, execution, and review.
- [ ] Agent traces persist model name, context payload, output payload, and fallback flag.
- [ ] Manager conflicts, consensus, override notes, and guard results are visible in review surfaces.
- [ ] Tool outputs and retrieved memories are visible in trace/retrieval inspection surfaces.
- [ ] Fallback behavior is diagnostic-only unless explicitly allowed for non-trading diagnostic paths.

## Paper Portfolio / Broker

- [ ] Paper broker remains the default execution backend.
- [ ] Live backend is blocked unless explicitly enabled and implemented.
- [ ] Kill switch blocks broker adapter creation.
- [ ] Paper fills, positions, journals, account marks, and risk reports stay consistent after runs.
- [ ] Stop-loss, take-profit, invalidation, and time exits are reflected in the trade journal.

## Memory / Governance

- [ ] Trading memory and chat memory remain separated.
- [ ] Training-mode runs that claim to learn are checked against runtime
  artifacts and DuckDB/memory inspection: what was written, where it appears,
  and whether the next session can explain why it retrieved that context.
- [ ] Operation-mode runs are checked for explicit reuse of approved memory and
  research evidence without letting memory mutate policy or bypass gates.
- [ ] Memory write policy is visible from CLI/TUI surfaces.
- [ ] Retrieval inspection explains why memories were attached.
- [ ] Chat/instruction flows update preferences only through approved schemas.
- [ ] Chat history must not silently mutate execution policy.

## Observer API / Future WebUI

- [ ] `observer-api` exposes read-only local endpoints only.
- [ ] `/health`, `/dashboard`, `/status`, `/logs`, `/supervisor`, and `/broker` return valid JSON.
- [ ] Observer API does not duplicate orchestration logic.
- [ ] Web-facing payloads match dashboard/CLI contracts.

## Web GUI

- [ ] `pnpm dev:webgui` serves the local shell on `http://localhost:3210`.
- [ ] First-run product expectation is clear: if `agentic-trader` does not
  auto-open the Web GUI yet, that is documented as an open V1 launcher task
  rather than silently accepted.
- [ ] The Web GUI uses the same dashboard/runtime/chat/instruction truth as CLI, Rich, and Ink.
- [ ] Browser-visible cards surface section-level errors explicitly instead of collapsing them into empty-state copy.
- [ ] Route handlers reject malformed JSON or foreign origins for POST actions.
- [ ] Browser Use or equivalent localhost QA confirms overview, review, memory, and settings flows without a second runtime path.

## UX / Copy

- [ ] Visual evidence, when captured, agrees with CLI JSON/status/runtime truth.
- [ ] Ink/TUI and Rich visual passes include scroll/resize artifacts, stray
  symbols, clipped labels, and whether exit keys leave the terminal in a clean
  state.
- [ ] A designer-style pass checks spacing, hierarchy, visual density, repeated chrome, resize behavior, and focus order.
- [ ] A finance/accounting-style pass checks cash, equity, PnL, exposure, positions, backend, adapter, runtime mode, rejection reason, and audit labels for clarity.
- [ ] Confusing menu, command, or layout behavior has a smallest-safe repair recommendation, not only a pass/fail note.
- [ ] UX repair recommendations are classified as V1 blocker, V1 polish, or V2 redesign.
- [ ] No screen claims that real trades were executed.
- [ ] No "active" runtime display when heartbeat is stale.
- [ ] No hidden long-running operation leaves the operator blind.
- [ ] Error text explains what the operator can do next.
- [ ] Dense terminal screens prioritize current cycle, agent activity, broker state, and stop controls.
