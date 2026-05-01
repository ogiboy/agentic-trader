# QA Scenarios

Use these scenarios as manual product checks. Each scenario should produce either a pass note or a reproducible issue report.

## Scenario 0: Automated Terminal Smoke

Purpose: confirm core operator-facing terminal surfaces open, emit usable output, and leave evidence.

Steps:

```bash
pnpm run qa
```

Optional quality extension:

```bash
pnpm run qa:quality
```

Optional SonarQube extension:

```bash
pnpm run sonar:status
pnpm run mcp:sonarqube:status
pnpm run sonar
pnpm run sonar:js
# Only when intentionally validating the SonarCloud path:
pnpm run sonar:cloud
```

Expected:

- summary exits `0` when all enabled checks pass
- artifacts are written under `.ai/qa/artifacts/smoke-YYYYMMDD-HHMMSS/`
- installed `agentic-trader` entrypoint drift is caught as a failed smoke check
- no Sonar token is written to artifacts or tracked files
- local scans target `agentic-trader`; cloud scans target `ogiboy_agentic-trader`
- MCP status distinguishes the local `sonarqube` server from transient `mcp/sonarqube` client containers
- any Sonar findings are reviewed across the full project backlog, not only recent commits

## Scenario 1: Environment Smoke

Purpose: confirm the project starts from the installed entrypoint and the root launcher.

Steps:

```bash
agentic-trader doctor
agentic-trader provider-diagnostics --json
agentic-trader v1-readiness --json
agentic-trader evidence-bundle --json
agentic-trader dashboard-snapshot > .ai/qa/artifacts/dashboard.json
python main.py doctor
```

Expected:

- commands exit cleanly
- dashboard JSON is valid
- doctor reports model/base URL/runtime/database
- provider diagnostics reports source ladder, fallback warnings, and API-key
  readiness without printing secret values
- V1 readiness reports paper-operation and Alpaca paper checks, with provider
  readiness marked unchecked unless `--provider-check` is used
- evidence bundle writes dashboard/status/broker/provider/readiness/log artifacts
  plus a manifest under `.ai/qa/artifacts/` without mutating runtime state
- broker payload reports `paper` unless environment variables override it

## Scenario 2: Primary Ink Control Room

Purpose: verify the main operator surface is usable and does not hide runtime truth.

Steps:

```bash
agentic-trader
```

Interact:

- press `1` through `6`
- press `r`
- press `q`

Expected:

- no traceback on entry or exit
- pages switch correctly
- runtime page shows current stage, daemon metadata, broker state, and event flow
- chat page shows transcript plus live activity/reasoning/tool context
- pexpect/tmux/asciinema evidence confirms the changed Ink page is readable, focused, and truthful
- when Computer Use is available, a real-screen visual pass confirms the same page is readable, focused, and truthful at the tested size

## Scenario 3: Rich Admin Menu

Purpose: verify the legacy/admin menu remains usable as a fallback.

Steps:

```bash
agentic-trader menu
```

Interact:

- open Runtime Control
- run Doctor
- open Portfolio and Risk
- open Research and Memory
- exit

Expected:

- no traceback
- menu does not become a blind long-running terminal
- observer mode is clear if runtime writer owns DuckDB
- Ctrl+C exits cleanly
- pexpect/tmux/asciinema evidence confirms the changed Rich page is readable, navigable, and truthful
- when Computer Use is available, a real-screen visual pass confirms the same page is readable, navigable, and truthful at the tested size

## Scenario 4: One-Shot Strict Cycle

Purpose: verify one complete agent cycle is observable and persisted.

Precondition:

- Ollama is running
- configured model is available

Steps:

```bash
agentic-trader run --symbol AAPL --interval 1d --lookback 180d
agentic-trader review-run
agentic-trader trace-run
agentic-trader trade-context
agentic-trader journal --limit 5
```

Expected:

- runtime does not use hidden fallback trade generation
- output shows whether execution was approved or rejected
- trace contains coordinator, regime, strategy, risk, manager, execution, and review stages
- trade context includes model routing, memory/tool context, and rationale
- journal state matches whether a fill occurred

## Scenario 5: Background Runtime And Live Monitor

Purpose: verify daemon-style runtime can be started, watched, and stopped without locking observer surfaces.

Steps:

```bash
agentic-trader launch --symbols AAPL,MSFT --interval 1d --lookback 180d --continuous --background
agentic-trader supervisor-status
agentic-trader monitor --refresh-seconds 1
agentic-trader stop-service
agentic-trader supervisor-status
```

Expected:

- background launch records PID, launch count, and log paths
- monitor shows live agent stage progress, not only static system status
- stop request does not require DuckDB writer access
- final supervisor status shows terminal state or stop request truth

## Scenario 6: Stale Runtime Recovery

Purpose: verify stale PID/state does not permanently block launch.

Steps:

1. Start a background runtime.
2. Stop or kill the process.
3. Run:

```bash
agentic-trader status
agentic-trader launch --symbols AAPL --interval 1d --lookback 180d --continuous --background
```

Expected:

- UI/status labels stale runtime as stale
- a dead PID does not produce a permanent "service already active" block
- new launch updates supervision metadata

## Scenario 7: Model Failure Gate

Purpose: verify strict runtime blocks when model/provider readiness fails.

Steps:

```bash
AGENTIC_TRADER_BASE_URL=http://127.0.0.1:9 agentic-trader doctor
AGENTIC_TRADER_BASE_URL=http://127.0.0.1:9 agentic-trader launch --symbols AAPL --interval 1d --lookback 180d
```

Expected:

- doctor explains provider/model failure
- launch blocks before trading runtime
- no paper order or trade journal entry is created
- fallback remains diagnostic-only

## Scenario 8: Broker Safety Gate

Purpose: verify live execution is blocked and paper remains default.

Steps:

```bash
agentic-trader broker-status
AGENTIC_TRADER_EXECUTION_BACKEND=simulated_real agentic-trader broker-status
AGENTIC_TRADER_EXECUTION_BACKEND=alpaca_paper agentic-trader broker-status
AGENTIC_TRADER_EXECUTION_BACKEND=live AGENTIC_TRADER_LIVE_EXECUTION_ENABLED=false agentic-trader broker-status
AGENTIC_TRADER_EXECUTION_KILL_SWITCH_ACTIVE=true agentic-trader broker-status
```

Expected:

- default backend is `paper`
- `simulated_real` is clearly labeled simulated and non-live
- `alpaca_paper` is clearly labeled external paper and blocked until explicit
  enablement, paper endpoint, and credentials are configured
- requested live backend is blocked without enablement
- kill switch is visible
- no command claims a live adapter exists

## Scenario 9: Observer API

Purpose: verify future WebUI clients can read the same runtime truth without owning orchestration.

Steps:

```bash
agentic-trader observer-api --host 127.0.0.1 --port 8765
curl -s http://127.0.0.1:8765/health
curl -s http://127.0.0.1:8765/dashboard
curl -s http://127.0.0.1:8765/status
curl -s http://127.0.0.1:8765/logs
curl -s http://127.0.0.1:8765/broker
curl -s http://127.0.0.1:8765/provider-diagnostics
curl -s http://127.0.0.1:8765/v1-readiness
```

Expected:

- every endpoint returns JSON
- observer API is read-only
- payloads match dashboard/status/log/broker CLI truth

## Scenario 10: Local Web GUI

Purpose: verify the local browser shell stays aligned with dashboard truth and does not invent a second runtime.

Steps:

```bash
pnpm install
pnpm dev:webgui
curl -s http://localhost:3210/api/dashboard > .ai/qa/artifacts/webgui-dashboard.json
```

Interact:

- open `http://localhost:3210` in Browser Use or another localhost-capable browser tool
- confirm Overview loads and reflects runtime mode, backend, and last refresh
- open Review, Memory, and Settings
- compare any unavailable panels with `webgui-dashboard.json`

Expected:

- the app serves on `localhost:3210`
- the page reads the same dashboard/runtime/chat/instruction contracts as other operator surfaces
- section-level review/memory/portfolio errors are shown explicitly instead of masquerading as empty states
- no browser flow suggests a second runtime or hidden execution path

## Scenario 11: Memory And Governance

Purpose: verify memory is inspectable and chat memory does not mutate trading policy.

Steps:

```bash
agentic-trader memory-explorer --symbol AAPL --interval 1d --lookback 180d --limit 5
agentic-trader retrieval-inspection
agentic-trader memory-policy
agentic-trader chat --persona operator_liaison --message "What do you remember about recent decisions?"
agentic-trader preferences
```

Expected:

- memory explorer and retrieval inspection explain attached context
- memory policy distinguishes trade memory and chat memory
- chat response is explanatory, not an execution path
- preferences do not change unless `instruct --apply` is used

## Scenario 12: Safe Operator Instruction

Purpose: verify preference updates only happen through schemas.

Steps:

```bash
agentic-trader preferences
agentic-trader instruct --message "Make the system conservative, forensic, strict, and protective." --apply
agentic-trader preferences
```

Expected:

- instruction summary explains the change
- preferences update only curated fields
- no runtime action is executed as a hidden side effect

## Scenario 13: Paper Portfolio Consistency

Purpose: verify paper account views stay coherent.

Steps:

```bash
agentic-trader portfolio
agentic-trader journal --limit 20
agentic-trader risk-report
```

Expected:

- cash/equity/open positions are readable
- trade journal status matches persisted fills
- risk report includes warnings when limits are stressed

## Scenario 14: Computer Use Visual Operator Pass

Purpose: verify the real terminal screen, not only stdout snapshots, for changed
CLI/Rich/Ink operator flows.

Precondition:

- Computer Use is available in the current Codex/Desktop environment.
- If Computer Use is unavailable, record that this scenario was skipped and run
  the matching pexpect/tmux/asciinema flow instead.

Steps:

```bash
agentic-trader
agentic-trader tui
agentic-trader menu
agentic-trader dashboard-snapshot
agentic-trader broker-status
```

Interact:

- navigate to the changed Ink or Rich page
- trigger the changed hotkey or command path
- capture a screenshot or screen observation
- cross-check visible runtime/broker/review claims against JSON output

Expected:

- screen layout is readable and stable at the tested terminal size
- critical state is not truncated, hidden, or contradicted by JSON/runtime truth
- first-launch logo/header fits without hiding the primary controls
- resize behavior is checked at compact, normal, and wide terminal sizes when feasible
- Rich menu navigation has consistent back, cancel, close, and exit behavior
- menu labels explain the purpose and destination clearly enough for a non-developer operator
- CLI help for changed commands is checked with `--help` and `-h` when supported
- finance/accounting values such as cash, equity, PnL, exposure, positions, currency, and backend state are clearly labeled
- execution backend, paper/live status, kill switch, runtime mode, and rejection
  reasons are visible wherever the scenario requires them
- no screenshot or visual report is treated as proof by itself without a
  contract or persistence cross-check
- confusing or inconsistent behavior produces a repair recommendation, not only
  a pass/fail result

## Scenario 15: CLI Help And Operator Language Audit

Purpose: verify command discoverability and language clarity from an operator
perspective, not only command success.

Steps:

```bash
agentic-trader --help
agentic-trader -h
agentic-trader run --help
agentic-trader broker-status --help
agentic-trader trade-context --help
agentic-trader tui --help
agentic-trader menu --help
```

Expected:

- top-level and changed commands explain what they do in operator language
- short and long help forms work where supported
- examples or defaults are present for commands that can affect runtime,
  broker, review, or portfolio state
- option names are consistent across CLI, Rich, and Ink mental models
- blocked/live/safety wording is explicit and not ambiguous
- confusing help or naming produces a smallest-safe repair recommendation and a
  V1/V2 classification
