# Roadmap

Product name: `Agentic Trader`

## Phase 1: Guardrailed Core

Status: completed in the initial scaffold.

- fetch market data
- compute a compact feature snapshot
- run regime, strategy, and risk agents
- validate with deterministic execution guard
- persist runs and paper orders

## Phase 2: Strict Runtime And Orchestration

Status: in progress.

- add a single root launcher for the whole system
- block trading runtime when Ollama or the configured model is unavailable
- make fallback logic diagnostic-only rather than silently generating trades
- support one-shot and continuous orchestrator modes
- expose system health and runtime gating from the CLI
- keep the control room open in the terminal until the user exits it
- show agent/runtime status and recent activity from one menu surface

## Phase 3: Better Inputs

Status: in progress.

- add multi-timeframe features
- add market calendar awareness
- add optional news and event feeds
- add cached data snapshots for repeatable tests
- let the user choose regions, exchanges, currencies, sectors, and default strategy posture
- let the user define portfolio preferences from the TUI instead of editing files

## Phase 4: Operator Experience

- build a more impressive ANSI/Rich/Textual-style control room
- add start, stop, status, logs, and portfolio views from the same UI
- show which symbols, agents, and model stages are active in real time
- display model usage, last decision, and last trade outcome in a dedicated status area
- let the operator configure investment preferences and default strategy posture from the menu before starting runtime
- keep the terminal app open until the operator explicitly exits

## Phase 5: Backtesting

- implement walk-forward replay
- compare agent-assisted plans against deterministic baselines
- track win rate, expectancy, drawdown, and exposure
- export run reports for review

## Phase 6: Paper Portfolio Engine

Status: in progress.

- track positions over time instead of single-shot orders
- manage open trades bar by bar
- support portfolio-level limits and cash usage
- add daily risk reports
- mark portfolio state after each orchestrator cycle
- store fills, open positions, and account state as if the broker were real

## Phase 7: Background Runtime / Daemon

- support running the orchestrator as a background service
- add a local status command for daemon health and current cycle state
- persist service heartbeats and runtime logs
- support clean start/stop/restart from the CLI/TUI
- make the daemon compatible with launchd/systemd-style supervision later

## Phase 8: Live Execution Adapters

- define a broker adapter interface
- start with a safe paper/live switch
- add approval gates and kill switches
- implement one live broker only after paper results are stable

## Phase 9: Smarter Agent Layer

- let the regime agent select strategy families dynamically
- let the risk agent adapt size by volatility and portfolio state
- add memory from past trades and post-trade review
- add confidence calibration based on historical results
