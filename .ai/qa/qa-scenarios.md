# QA Scenarios

Use these scenarios as manual product checks. Each scenario should produce either a pass note or a reproducible issue report.

## Scenario 1: Environment Smoke

Purpose: confirm the project starts from the installed entrypoint and the root launcher.

Steps:

```bash
agentic-trader doctor
agentic-trader dashboard-snapshot > .ai/qa/artifacts/dashboard.json
python main.py doctor
```

Expected:

- commands exit cleanly
- dashboard JSON is valid
- doctor reports model/base URL/runtime/database
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
AGENTIC_TRADER_EXECUTION_BACKEND=live AGENTIC_TRADER_LIVE_EXECUTION_ENABLED=false agentic-trader broker-status
AGENTIC_TRADER_EXECUTION_KILL_SWITCH_ACTIVE=true agentic-trader broker-status
```

Expected:

- default backend is `paper`
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
```

Expected:

- every endpoint returns JSON
- observer API is read-only
- payloads match dashboard/status/log/broker CLI truth

## Scenario 10: Memory And Governance

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

## Scenario 11: Safe Operator Instruction

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

## Scenario 12: Paper Portfolio Consistency

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
