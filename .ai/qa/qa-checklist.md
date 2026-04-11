# QA Checklist

Use this checklist for behavior-changing work. Not every item applies to every task, but skipped high-risk sections should be intentional.

## Baseline Verification

- [ ] Run terminal smoke QA:
  - `python scripts/qa/smoke_qa.py`
- [ ] For code-quality passes, run:
  - `python scripts/qa/smoke_qa.py --include-quality`
- [ ] When SonarQube is available, run:
  - `SONAR_TOKEN=... python scripts/qa/smoke_qa.py --include-sonar`
- [ ] Run the smallest relevant targeted tests.
- [ ] Run the full suite when feasible:
  - `/opt/anaconda3/envs/trader/bin/python -m pytest -q -p no:cacheprovider`
- [ ] Confirm `git status --short` does not contain accidental runtime artifacts.
- [ ] Confirm smoke artifacts are grouped under a timestamped `.ai/qa/artifacts/smoke-*` directory.
- [ ] Confirm changed roadmap items are checked or left unchecked accurately.
- [ ] Confirm `.ai/current-state.md`, `.ai/tasks.md`, and `.ai/decisions.md` are updated when architecture, runtime contracts, or assumptions change.

## Code Quality

- [ ] `ruff check .` passes or findings are triaged.
- [ ] `pytest -q -p no:cacheprovider` passes or failures are triaged.
- [ ] `pyright` or IDE/Pylance diagnostics are checked when available.
- [ ] SonarQube or `pysonar` findings are reviewed when the local Sonar service is available.
- [ ] `.sonar/` remains ignored and no Sonar token is written to tracked files or artifacts.

## CLI

- [ ] Commands exit cleanly with code `0` for successful paths.
- [ ] Commands show clear error messages for blocked paths.
- [ ] `--json` output is valid JSON where supported.
- [ ] Human-readable output is concise and does not hide critical runtime state.
- [ ] `agentic-trader broker-status` reports paper/live/kill-switch truth accurately.
- [ ] `agentic-trader supervisor-status` reports daemon metadata and log tails without requiring the DuckDB writer lock.
- [ ] `agentic-trader dashboard-snapshot` contains the same truth consumed by Ink.

## Ink TUI

- [ ] `agentic-trader` opens the Ink control room when the console entrypoint is installed.
- [ ] `python main.py` opens the same primary operator surface.
- [ ] Hotkeys work: `1-6`, `r`, `s`, `x`, `R`, `q`.
- [ ] Runtime page shows current stage, daemon metadata, broker state, and recent stage flow.
- [ ] Chat page shows transcript plus live agent activity, reasoning stage, and tool/memory context.
- [ ] Portfolio/review/memory pages degrade gracefully when the runtime writer owns DuckDB.
- [ ] The app can be exited cleanly without traceback.

## Rich Menu

- [ ] `agentic-trader menu` opens the legacy/admin Rich menu.
- [ ] Categories are navigable without excessive scrolling.
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
- [ ] `/health`, `/dashboard`, `/status`, `/logs`, and `/broker` return valid JSON.
- [ ] Observer API does not duplicate orchestration logic.
- [ ] Web-facing payloads match dashboard/CLI contracts.

## UX / Copy

- [ ] No screen claims that real trades were executed.
- [ ] No "active" runtime display when heartbeat is stale.
- [ ] No hidden long-running operation leaves the operator blind.
- [ ] Error text explains what the operator can do next.
- [ ] Dense terminal screens prioritize current cycle, agent activity, broker state, and stop controls.
