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

Status: completed.

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
- let the user choose high-level investment behavior presets from curated options rather than raw free-form config only
- prepare a future model/provider menu so Ollama, remote APIs, and agent profiles can be switched from the operator surface

## Phase 4: Operator Experience

Status: in progress.

- build a more impressive ANSI/Rich/Textual-style control room
- add start, stop, status, logs, and portfolio views from the same UI
- show which symbols, agents, and model stages are active in real time
- display model usage, last decision, and last trade outcome in a dedicated status area
- let the operator configure investment preferences and default strategy posture from the menu before starting runtime
- keep the terminal app open until the operator explicitly exits
- add a dedicated chat screen inside the TUI so the operator can talk to the system without leaving the control room
- support chatting with either a general operator assistant or a selected agent persona from the menu
- show structured agent activity, recent tool usage, and the current reasoning stage beside the chat transcript
- add a clearer retro-terminal visual language so the control room feels like a serious operator console rather than a plain CLI

## Phase 5: Backtesting

Status: in progress.

- implement walk-forward replay
- compare agent-assisted plans against deterministic baselines
- track win rate, expectancy, drawdown, and exposure
- export run reports for review
Notes:
- run review and Markdown export are now available for live/paper runs
- a first walk-forward replay is now available
- deterministic baseline comparison and richer scoring still need to be added

## Phase 6: Paper Portfolio Engine

Status: in progress.

- track positions over time instead of single-shot orders
- manage open trades bar by bar
- trigger stop loss / take profit / invalidation exits as new bars arrive
- support portfolio-level limits and cash usage
- add daily risk reports
- mark portfolio state after each orchestrator cycle
- store fills, open positions, and account state as if the broker were real
- maintain trade journals so the system can review what it planned, what it executed, and what actually happened
Notes:
- open positions, fills, account state, account marks, daily risk reports, and trade journals are now in place
- portfolio-level limits and richer multi-position capital controls still need to be expanded

## Phase 7: Background Runtime / Daemon

Status: in progress.

- support running the orchestrator as a background service
- add a local status command for daemon health and current cycle state
- persist service heartbeats and runtime logs
- support clean start/stop/restart from the CLI/TUI
- make the daemon compatible with launchd/systemd-style supervision later
- allow the operator TUI to attach to a running background service instead of owning the process directly

## Phase 8: Live Execution Adapters

- define a broker adapter interface
- start with a safe paper/live switch
- add approval gates and kill switches
- implement one live broker only after paper results are stable

## Phase 9: Smarter Agent Layer

Status: in progress.

- let the regime agent select strategy families dynamically
- let the risk agent adapt size by volatility and portfolio state
- add memory from past trades and post-trade review
- add confidence calibration based on historical results
- add configurable agent personas so the operator can choose cautious, balanced, aggressive, contrarian, or trend-biased behavior profiles
- let the operator set agent tone, strictness, and intervention style from curated presets in the TUI
- split the agent graph into clearer specialist roles such as research coordinator, regime analyst, strategy selector, risk steward, execution guard, portfolio manager, and review agent
- add a dedicated operator-facing liaison agent that explains what the system is doing and answers portfolio questions in plain language
- introduce manager agents that orchestrate specialist agents, resolve conflicts, and decide whether a cycle should advance or pause

## Phase 10: Agent Governance And Conversation Layer

Status: in progress.

- define a structured operator-to-agent messaging protocol so user instructions change preferences and runtime behavior safely
- separate conversational memory from trading memory so chat history does not silently mutate execution policy
- store agent decisions, disagreements, and manager overrides for later review
- allow the operator to inspect why a manager agent accepted or rejected a specialist recommendation
- add guardrails so conversational interactions can influence policy only through approved schemas and not free-form hidden side effects
Notes:
- safe operator instruction parsing and preference application are implemented
- persisted run review now exposes coordinator, specialist, manager, execution, and review outputs
- richer disagreement storage and explicit override tracking still need deeper agent-state plumbing
