# QA Runbook

## Goal

Validate Agentic Trader as a real operator would experience it across CLI, Ink TUI, Rich menu, daemon runtime, observer API, memory/review surfaces, and paper portfolio behavior.

This QA layer observes and reports. It does not fix code during the QA pass.

## Baseline Environment

Use the project environment unless the task says otherwise:

```bash
conda activate trader
pnpm run setup
```

If the shell cannot find the console entrypoint:

```bash
hash -r
which agentic-trader
python -m agentic_trader.cli doctor
```

Recommended core verification:

```bash
pnpm run check
```

This wraps `ruff check .`, `pyright agentic_trader tests scripts`, `python -m pytest -q`, and the Node workspace lint/type/build checks.

Recommended terminal smoke pass:

```bash
pnpm run qa
```

Recommended terminal + code-quality pass:

```bash
pnpm run qa:quality
```

Optional SonarQube pass:

```bash
pnpm run sonar:status
pnpm run mcp:sonarqube:status
pnpm run sonar
pnpm run sonar:js
```

## Evidence Directory

Store manual QA evidence under:

```text
.ai/qa/artifacts/
```

Automated smoke QA writes each run into a timestamped subdirectory:

```text
.ai/qa/artifacts/smoke-YYYYMMDD-HHMMSS/
```

Parallel smoke runs may append a numeric suffix such as `-2`; keep each run directory intact so evidence remains traceable.

Suggested files:

- `run.log`
- `tui-pane.txt`
- `rich-menu-pane.txt`
- `observer-api.json`
- `session.cast`
- `screen-01.png`

Do not commit large binary evidence unless the task explicitly asks for it. Prefer text captures and concise reports.
Do not commit `.sonar/` output or Sonar tokens.

## Tooling

### Computer Use

Use pexpect, tmux pane capture, asciinema, and CLI JSON checks as the primary
operator-facing QA path for CLI, Rich, and Ink terminal surfaces. These tools
provide repeatable evidence for truth, layout, focus, hotkeys, truncation, and
screen hierarchy. When Computer Use is available, add a real-screen visual pass
instead of relying on text artifacts alone for layout-sensitive changes.

Computer Use is optional. It must not become a runtime dependency, test-suite
dependency, or reason to skip QA in headless environments. If it is available,
use it for the final visual/operator pass. If it is unavailable, continue with
text artifacts and JSON/runtime cross-checks.

Recommended visual QA flow:

1. Start a fresh terminal session.
2. Run the same product command documented in the scenario.
3. Resize the terminal when layout is in scope: compact around 80x24, normal
   around 100x30, and wide around 140x40 when feasible.
4. Navigate the changed page or flow with normal keyboard input.
5. Capture a screenshot or summarize the visible screen state.
6. Cross-check visible claims against `dashboard-snapshot`, `broker-status`,
   `status`, `logs`, trade context, or observer API JSON as appropriate.
7. Save durable evidence under `.ai/qa/artifacts/` only when the task requires
   it.
8. Do not commit large binary screenshots unless explicitly requested.

Visual QA should include more than crash checks:

- UX clarity: can the operator find the next safe action without guessing?
- CLI ergonomics: are `--help`, `-h`, examples, aliases, and option names clear?
- Design quality: does the logo/header fit, does visual chrome repeat too much,
  and do important panes survive resizing?
- Navigation: do Rich menu back/exit/cancel controls mean the same thing across
  screens?
- Finance/accounting readability: are cash, equity, PnL, exposure, currency,
  backend, adapter, runtime mode, and rejection reason labeled clearly enough to
  audit?
- Repair phase: when the product feels confusing, propose the smallest
  V1-safe repair and the verification path instead of stopping at criticism.

## UX Repair Workflow

Use this loop when a visual/UX/menu issue is found:

1. Capture the current behavior with pexpect/tmux/asciinema text artifacts, then add Computer Use screenshots or screen observations when available.
2. Name the operator confusion in one sentence.
3. Classify the issue as V1 blocker, V1 polish, or V2 redesign.
4. Propose the smallest repair that preserves runtime truth and paper-first
   safety.
5. If implementation is in scope, patch the existing surface rather than
   creating a parallel UI path.
6. Re-run the relevant visual scenario and contract check.

### pexpect

Use for repeatable CLI/Rich menu/Ink interaction.

Install only if missing:

```bash
pnpm run setup
```

### tmux

Use for stable terminal sessions and pane capture:

```bash
tmux new-session -d -s agentic-trader-qa 'python main.py'
tmux capture-pane -t agentic-trader-qa -S - -p > .ai/qa/artifacts/tui-pane.txt
tmux kill-session -t agentic-trader-qa
```

### asciinema

Use when a complete terminal session recording is useful:

```bash
asciinema rec .ai/qa/artifacts/session.cast
```

### Screenshots

Use screenshots for visual rendering issues that are hard to explain from text
capture. Prefer Computer Use screenshots/screen observations when available.

### Indirect Terminal Review

When you cannot directly drive or observe the terminal screen:

1. capture pane text with `tmux capture-pane`
2. record the interaction with `asciinema` when timing matters
3. save `dashboard-snapshot`, `status`, `broker-status`, `logs`, or observer API JSON
4. compare the captured text with the structured payloads to reconstruct what the operator would have seen
5. treat mismatches between screen-like captures and structured truth as QA findings

### Code Quality

Use `ruff`, `pytest`, IDE/Pylance or `pyright`, and SonarQube as complementary signals.

```bash
python -m ruff check .
python -m pytest -q -p no:cacheprovider
pyright
pnpm run sonar
```

Never hardcode the Sonar token in tracked files. Prefer `SONAR_TOKEN`, or store the local Docker token in macOS Keychain service `codex-sonarqube-token`. `pnpm run sonar` and `pnpm run sonar:js` upload to local project `agentic-trader`. `pnpm run sonar:cloud` uploads to SonarCloud project `ogiboy_agentic-trader` and should use a separate token, preferably Keychain service `codex-sonarcloud-token`. Root `sonar-project.properties` is the local default scanner file; CI overrides project key and organization for SonarCloud. Use `pnpm run secret:sonar:check`, `pnpm run mcp:sonarqube:dry-run`, and `pnpm run mcp:sonarqube:status` to verify Keychain/MCP wiring without printing the token.

Sonar review is repository-wide by default. Do not limit investigation to the last commit unless the task explicitly says so. Review bugs, vulnerabilities, security hotspots, blocker/critical issues, maintainability issues, and scanner suggestions across the intended project key. Prioritize security and correctness first, then high-complexity maintainability findings, then minor style or formatting issues. If a finding is accepted rather than fixed, record the reason and residual risk instead of dismissing it as unimportant.

Sonar topology:

- `sonarqube` and `sonarqube-db` are the local analysis server.
- `pnpm run sonar` / `pnpm run sonar:js` are scanner uploads into that server.
- `mcp/sonarqube` containers are MCP clients used by Codex or VS Code to query the server.
- Multiple running `mcp/sonarqube` containers usually mean multiple active editor/agent sessions, not multiple SonarQube servers. Use `pnpm run mcp:sonarqube:status` before assuming the server or token is broken.

### Release and Build Identity

Use `pnpm run release:preview` to ask `python-semantic-release` what tag the current conventional-commit history implies, and `pnpm run version:plan` to inspect the branch artifact identity.

Stable releases should happen only from `main` and should use strict SemVer tags such as `v0.9.5`.
Branch builds must not use a fourth SemVer core segment. Use prerelease/build metadata instead: integration branches such as `V1` use `next` artifact identities like `v0.9.6-next.9870+gabc1234`, while feature branches use `beta` identities like `v0.9.6-beta.9870+gabc1234`.

## Standard QA Workflow

1. Read `AGENTS.md`, `.ai/current-state.md`, `.ai/tasks.md`, `.ai/debugging.md`, and the QA scenario being executed.
2. Start from a clean terminal.
3. Run the smallest relevant automated tests.
4. Exercise the target scenario manually.
5. Capture output, pane text, API JSON, and Computer Use visual evidence when available and relevant.
6. Compare actual behavior against `.ai/qa/qa-checklist.md`.
7. Report issues with exact reproduction steps.
8. If no issues are found, record what was exercised and what evidence exists.

## Command Matrix

Core:

```bash
agentic-trader doctor
agentic-trader dashboard-snapshot
agentic-trader broker-status
agentic-trader supervisor-status
```

Primary UI:

```bash
agentic-trader
agentic-trader tui
python main.py
```

Admin / legacy UI:

```bash
agentic-trader menu
python main.py menu
```

Runtime:

```bash
agentic-trader launch --symbols AAPL,MSFT --interval 1d --lookback 180d --continuous --background
agentic-trader status
agentic-trader logs --limit 20
agentic-trader monitor --refresh-seconds 1
agentic-trader stop-service
agentic-trader restart-service
```

Review:

```bash
agentic-trader review-run
agentic-trader trace-run
agentic-trader trade-context
agentic-trader replay-run
```

Memory:

```bash
agentic-trader memory-explorer --symbol AAPL --interval 1d --lookback 180d --limit 5
agentic-trader retrieval-inspection
agentic-trader memory-policy
```

Portfolio:

```bash
agentic-trader portfolio
agentic-trader journal --limit 20
agentic-trader risk-report
```

Observer API:

```bash
agentic-trader observer-api --host 127.0.0.1 --port 8765
curl -s http://127.0.0.1:8765/health
curl -s http://127.0.0.1:8765/dashboard
curl -s http://127.0.0.1:8765/broker
```

## Failure Triage

When a scenario fails, classify the failing boundary:

- environment or entrypoint
- LLM/provider readiness
- market data or feature generation
- agent structured output contract
- manager/consensus/guard logic
- broker adapter or paper persistence
- runtime feed or daemon state
- DuckDB writer/observer behavior
- CLI/TUI/API presentation only

Start with the smallest failing boundary. Do not hide a product issue by only fixing presentation.

## QA Report Template

```text
Scenario:
Date:
Commit:
Environment:
Commands:
Expected:
Actual:
Evidence:
Severity:
Recommendation:
```
