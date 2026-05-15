# QA Scenarios

Use these scenarios as manual product checks. Each scenario should produce either a pass note or a reproducible issue report.

Choose scenarios by changed surface. If a prerequisite is unavailable, record
the missing prerequisite and expected impact, then run the closest lower-risk
scenario that still checks the same operator truth. Do not treat unavailable
optional helper tools as success.

## Pre-Push Product Gate

Purpose: make every meaningful push prove product behavior, not just code
health.

Minimum before a broad/V1/security/runtime push:

```bash
pnpm run check
pnpm run qa
agentic-trader setup-status --json
agentic-trader model-service status --probe-generation --json
agentic-trader v1-readiness --provider-check --json
agentic-trader research-status --json
agentic-trader dashboard-snapshot --provider-check > .ai/qa/artifacts/dashboard-prepush.json
```

Add when the change touches the relevant surface:

```bash
agentic-trader
agentic-trader tui
agentic-trader menu
agentic-trader webgui-service start --no-open-browser --json
agentic-trader webgui-service stop --json
agentic-trader research-cycle-run --symbols AAPL,MSFT --cycles 1 --no-sleep --json
```

Expected:

- first-run launcher opens cleanly and does not start hidden work
- setup/model/WebGUI/Camofox/Firecrawl/CrewAI readiness is truthful
- WebGUI, Rich, and Ink surfaces agree with dashboard JSON for changed fields
- strict runtime remains blocked if the configured local model cannot generate
- optional helper failures are degraded or blocked visibly, not hidden
- no unowned background process remains after exit/stop
- security posture checks cover route origins/tokens, loopback binds, secret
  redaction, sidecar/provider poisoning, artifacts, and fallback behavior
- any real V1 blocker is either fixed before push or recorded as a GitHub issue
  with reproduction evidence

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
agentic-trader operator-workflow --json
agentic-trader hardware-profile --json
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
- operator workflow reports the canonical V1 review order without executing
  hidden runtime actions
- hardware profile reports CPU, memory, accelerator hints, configured model size,
  and safe parallelism recommendations without applying hidden overrides
- provider diagnostics reports source ladder, fallback warnings, and API-key
  readiness without printing secret values
- V1 readiness reports paper-operation and Alpaca paper checks, with provider
  readiness marked unchecked unless `--provider-check` is used
- evidence bundle writes dashboard/status/broker/provider/readiness/log artifacts
  plus a manifest under `.ai/qa/artifacts/` without mutating runtime state
- supervisor status exposes daemon metadata and log tails without requiring the runtime writer lock
- broker payload reports `paper` unless environment variables override it

## Scenario 1A: Setup And Model-Service Readiness

Purpose: confirm onboarding/tool readiness is visible without hidden installs and app-managed Ollama cannot hijack external services.

Steps:

```bash
make bootstrap-dry-run
agentic-trader setup-status --json
agentic-trader setup --json
agentic-trader model-service status --probe-generation --json
agentic-trader webgui-service status --json
AGENTIC_TRADER_RESEARCH_CAMOFOX_BASE_URL=http://0.0.0.0:9377 agentic-trader setup-status --json
AGENTIC_TRADER_RESEARCH_CAMOFOX_BASE_URL=http://0.0.0.0:9377 agentic-trader camofox-service status --json
AGENTIC_TRADER_MODEL_SERVICE_HOST=0.0.0.0 agentic-trader model-service start --json
scripts/start-camofox-browser.sh
```

Optional when intentionally testing local model setup:

```bash
agentic-trader model-service start --json
agentic-trader model-service pull qwen3:8b --json
agentic-trader v1-readiness --provider-check --json
agentic-trader runtime-mode-checklist operation --provider-check --json
agentic-trader model-service stop --json
agentic-trader webgui-service start --no-open-browser --json
agentic-trader webgui-service stop --json
```

Expected:

- dry-run prints intended install/check actions without installing anything
- setup status reports `uv`, Node, `pnpm`, the console entrypoint, Ollama,
  CrewAI Flow sidecar, Firecrawl, Camofox, RuFlo, and Docker readiness
- Firecrawl unauthenticated or missing state is degraded readiness, not a core blocker
- Camofox missing/unhealthy state is degraded readiness, not a core blocker
- Camofox non-loopback base URLs are marked unsafe without probing the URL
- Camofox wrapper refuses to start without `CAMOFOX_ACCESS_KEY` or `CAMOFOX_API_KEY`
- app-managed Camofox may mirror `CAMOFOX_API_KEY` into the local helper's access token so browser routes stay bearer-gated
- app-managed Camofox reports degraded health when the Node server is reachable but recent logs show Camoufox browser launch failures
- Camofox `/health` payloads with `browserRunning=false` or `browserConnected=false` are acceptable for the default on-demand browser-launch mode, but the first actual browser-backed fetch must still fail closed if launch produces SIGABRT or other launch-failure logs
- non-loopback model-service host is rejected before starting a process
- app-managed Ollama state and logs live under `runtime/model_service/`
- app-managed stop only targets the recorded app-owned PID, escalates only for that PID if SIGTERM does not exit, and keeps ownership state visible if the process cannot be stopped
- provider-check readiness and model-service `--probe-generation` fail closed
  when Ollama is reachable and the model is listed but generation fails
- app-owned Web GUI state and logs live under `runtime/webgui_service/`
- app-owned Web GUI stop only targets the recorded app-owned PID
- fake provider/broker secrets do not appear in model-service log tails, JSON output, or setup artifacts

## Scenario 2: Primary Operator Launcher

Purpose: verify the installed product entrypoint is usable, explains the available surfaces, and does not start hidden work.

Steps:

```bash
agentic-trader
```

Interact:

- verify the launcher shows Web GUI, daemon, Ink, Rich, model-service, setup, and exit choices
- press `7` or `q`

Expected:

- no traceback on entry or exit
- no daemon or Web GUI starts unless explicitly selected
- setup/model-service/WebGUI-service messages are visible before selection
- pexpect/tmux/asciinema evidence confirms the launcher is readable and truthful

## Scenario 2B: Primary Ink Control Room

Purpose: verify the main terminal control room is usable and does not hide runtime truth.

Steps:

```bash
agentic-trader tui
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
curl -s http://127.0.0.1:8765/supervisor
curl -s http://127.0.0.1:8765/broker
curl -s http://127.0.0.1:8765/provider-diagnostics
curl -s http://127.0.0.1:8765/v1-readiness
```

Expected:

- every endpoint returns JSON
- observer API is read-only
- non-loopback binds fail unless `--allow-nonlocal` is used with `AGENTIC_TRADER_OBSERVER_API_TOKEN`
- token-protected observer requests reject missing or invalid tokens
- supervisor payload includes daemon status and stdout/stderr log tails
- supervisor stdout/stderr tails redact key-like values and bearer tokens
- payloads match dashboard/status/log/supervisor/broker CLI truth

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

Token-protected smoke:

```bash
AGENTIC_TRADER_WEBGUI_TOKEN=local-token AGENTIC_TRADER_WEBGUI_LOOPBACK_ONLY=1 pnpm --filter webgui exec next dev --hostname 127.0.0.1 -p 3210
curl -i http://127.0.0.1:3210/api/dashboard
curl -i -H "Origin: http://127.0.0.1:3210" -H "Content-Type: application/json" --data '{"token":"local-token"}' http://127.0.0.1:3210/api/session
curl -i -H "Cookie: agentic_trader_webgui_session=local-token" http://127.0.0.1:3210/api/dashboard
curl -i -H "Origin: http://evil.local" -H "Cookie: agentic_trader_webgui_session=local-token" -H "Content-Type: application/json" --data '{"kind":"restart"}' http://127.0.0.1:3210/api/runtime
```

Expected token-protected results:

- missing token returns `401`
- session unlock returns `Set-Cookie` with `HttpOnly` and `SameSite=Strict`
- cookie-authenticated dashboard is not `401`
- foreign-origin runtime mutation remains `403`
- browser UI shows a token prompt, unlocks with the local token, then loads dashboard/chat/runtime calls without external header injection

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

## Scenario 16: Security Posture Smoke

Purpose: verify local-first hardening controls without changing runtime product
scope or enabling live execution.

Steps:

```bash
uv run --locked --all-extras --group dev python -m pytest -q tests/test_security_helpers.py tests/test_observer_api.py tests/test_research_sidecar.py tests/test_cli_json.py tests/test_data_providers.py
pnpm --filter webgui run typecheck
pnpm --filter webgui run lint
AGENTIC_TRADER_OBSERVER_API_TOKEN=local-token agentic-trader observer-api --host 127.0.0.1 --port 8765
```

Manual negative checks:

```bash
agentic-trader observer-api --host 0.0.0.0 --port 8765
agentic-trader observer-api --host '' --port 8765
curl -i http://127.0.0.1:8765/health
curl -i -H "X-Agentic-Trader-Observer-Token: local-token" http://127.0.0.1:8765/health
curl -i -H "Origin: http://evil.local" -H "Content-Type: application/json" --data '{"kind":"restart"}' http://localhost:3210/api/runtime
```

Expected:

- non-loopback and empty observer binds are rejected by default
- token-protected observer endpoint returns `401` without the token and JSON with the token
- observer responses include `Cache-Control: no-store` and browser hardening headers
- Web GUI mutating routes reject foreign origins and oversized/malformed JSON
- repeated runtime/chat/instruction API calls are cooldown or single-flight guarded
- CLI supervisor tails, Web errors, provider exception notes, and sidecar errors redact fake key/token values
- runtime feed and service log artifacts prefer owner-only permissions on local filesystems
- operation/live gates are unchanged: paper remains default and live execution remains blocked
