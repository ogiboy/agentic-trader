# QA Checklist

Use this checklist for behavior-changing work. Not every item applies to every task, but skipped high-risk sections should be intentional.

## Baseline Verification

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
- [ ] For workflow/release changes, preview version identity without mutating files:
  - `pnpm run release:preview`
  - `pnpm run version:plan`
- [ ] Before pushing release/version/package metadata work, confirm agents did not
  manually drift `pyproject.toml`, `agentic_trader/__init__.py`, workspace
  `package.json` files, `sidecars/research_flow/pyproject.toml`, or
  `CHANGELOG.md` outside the documented semantic-release path.
- [ ] Confirm `git status --short` does not contain accidental runtime artifacts.
- [ ] Confirm smoke artifacts are grouped under a timestamped `.ai/qa/artifacts/smoke-*` directory.
- [ ] Confirm changed roadmap items are checked or left unchecked accurately.
- [ ] Confirm `.ai/current-state.md`, `.ai/tasks.md`, and `.ai/decisions.md` are updated when architecture, runtime contracts, or assumptions change.
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
- [ ] `agentic-trader supervisor-status` reports daemon metadata and log tails without requiring the DuckDB writer lock.
- [ ] Observer-compatible supervisor payloads expose the same daemon metadata and log-tail truth.
- [ ] `agentic-trader dashboard-snapshot` contains the same truth consumed by Ink.

## Ink TUI

- [ ] Use pexpect/tmux/asciinema to open the Ink control room and inspect the changed page or flow; add a Computer Use visual pass when available.
- [ ] `agentic-trader` opens the Ink control room when the console entrypoint is installed.
- [ ] `python main.py` opens the same primary operator surface.
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
- [ ] The Web GUI uses the same dashboard/runtime/chat/instruction truth as CLI, Rich, and Ink.
- [ ] Browser-visible cards surface section-level errors explicitly instead of collapsing them into empty-state copy.
- [ ] Route handlers reject malformed JSON or foreign origins for POST actions.
- [ ] Browser Use or equivalent localhost QA confirms overview, review, memory, and settings flows without a second runtime path.

## UX / Copy

- [ ] Visual evidence, when captured, agrees with CLI JSON/status/runtime truth.
- [ ] A designer-style pass checks spacing, hierarchy, visual density, repeated chrome, resize behavior, and focus order.
- [ ] A finance/accounting-style pass checks cash, equity, PnL, exposure, positions, backend, adapter, runtime mode, rejection reason, and audit labels for clarity.
- [ ] Confusing menu, command, or layout behavior has a smallest-safe repair recommendation, not only a pass/fail note.
- [ ] UX repair recommendations are classified as V1 blocker, V1 polish, or V2 redesign.
- [ ] No screen claims that real trades were executed.
- [ ] No "active" runtime display when heartbeat is stale.
- [ ] No hidden long-running operation leaves the operator blind.
- [ ] Error text explains what the operator can do next.
- [ ] Dense terminal screens prioritize current cycle, agent activity, broker state, and stop controls.
