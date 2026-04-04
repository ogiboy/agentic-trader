# Roadmap

Product name: `Agentic Trader`

This roadmap is both a build plan and a progress ledger. Status values reflect the current codebase, not only the intended destination.

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
- introduce a unified agent context builder that merges market snapshot, memory, and tool outputs before every cycle
- add model routing layer to select different models per agent role such as regime, strategy, risk, manager, and explainer
- ensure deterministic safe-mode diagnostics when no LLM is available without allowing silent trade generation in the strict runtime
- add runtime guardrails for missing data, tool failures, and low-confidence outputs
  Notes:
- root launcher, strict runtime gate, one-shot mode, continuous mode, background mode, status, logs, and control-room loop are already live
- unified agent context and role-based model routing are the next major orchestration upgrades

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
- introduce memory injection into market context so agents can retrieve historically similar regimes and conditions
- ensure all external knowledge such as news, events, and macro signals is accessed only via tools rather than being assumed by the model
  Notes:
- operator preferences and curated behavior presets already exist
- lightweight retrieval from historically similar runs is now injected into agent context
- multi-timeframe feature enrichment is now part of the market snapshot and already informs fallback coordinator and regime logic
- a first market-session heuristic is now available through the CLI, dashboard snapshot, Ink control room, and agent context tool outputs
- repeatable market snapshot cache management is now available through the CLI and dashboard snapshot
- richer calendar awareness and tool-driven external context are still open

## Phase 4: Operator Experience

Status: in progress.

- build a more impressive ANSI, Rich, or Textual-style control room
- add start, stop, status, logs, and portfolio views from the same UI
- show which symbols, agents, and model stages are active in real time
- display model usage, last decision, and last trade outcome in a dedicated status area
- let the operator configure investment preferences and default strategy posture from the menu before starting runtime
- keep the terminal app open until the operator explicitly exits it
- add a dedicated chat screen inside the TUI so the operator can talk to the system without leaving the control room
- support chatting with either a general operator assistant or a selected agent persona from the menu
- show structured agent activity, recent tool usage, and the current reasoning stage beside the chat transcript
- add a clearer retro-terminal visual language so the control room feels like a serious operator console rather than a plain CLI
- introduce an Ink-based next-generation control room under a dedicated `tui/` application so the operator surface can evolve beyond the current Rich menu
- keep `agentic-trader` as the primary launcher and expose subcommands such as `agentic-trader tui`, `agentic-trader monitor`, and future UI entrypoints
- add memory explorer UI to inspect long-term and vector memory state
- add agent decision trace viewer to inspect reasoning, tool calls, and outputs per cycle
- add retrieval inspection view to show why specific memories were used in a decision
  Notes:
- control room, live monitor, operator chat, journal view, risk report view, and run review are already available
- a first memory explorer surface is now available from the CLI and TUI
- persisted hybrid memory retrieval now combines heuristic market similarity with a lightweight vector-style embedding layer
- persisted per-stage trace viewing is now available from the CLI and TUI
- a first Ink-based control room now exists under `tui/` and consumes JSON status, log, preference, and portfolio surfaces from the Python runtime
- the Ink control room now ships with overview, runtime, portfolio, and review pages plus start/stop hotkeys
- the Ink control room now also includes an operator chat page with persona switching
- the Ink control room now also includes a memory page backed by similar-run retrieval and stage-level retrieval inspection
- richer trace inspection and deeper Ink feature parity are still open

## Phase 5: Backtesting

Status: in progress.

- implement walk-forward replay
- compare agent-assisted plans against deterministic baselines
- track win rate, expectancy, drawdown, and exposure
- export run reports for review
- introduce memory-aware replay mode to reconstruct what the system knew at the time of each decision
- run ablation tests comparing performance with and without vector memory or a RAG layer
Notes:
- a first walk-forward replay and report export path are now available
- agent-versus-deterministic baseline comparison is now available
- a first memory-aware replay surface is now available through `replay-run`, the dashboard snapshot, and the Ink review page
- a first memory ablation surface is now available through `backtest --compare-memory`
- the retrieval layer now has a persisted hybrid heuristic-plus-vector memory path that can be expanded into richer RAG later

## Phase 6: Paper Portfolio Engine

Status: in progress.

- track positions over time instead of single-shot orders
- manage open trades bar by bar
- trigger stop loss, take profit, and invalidation exits as new bars arrive
- support portfolio-level limits and cash usage
- add daily risk reports
- mark portfolio state after each orchestrator cycle
- store fills, open positions, and account state as if the broker were real
- maintain trade journals so the system can review what it planned, what it executed, and what actually happened
- persist full agent decision context for each trade including market snapshot, memory inputs, and tool outputs
Notes:
- open positions, fills, account marks, daily risk reports, run reviews, and trade journals are in place
- portfolio-level gross exposure caps, open-position caps, and cash-aware long entry checks are now enforced in the paper broker
- richer multi-position capital rules and deeper per-trade context persistence still need expansion

## Phase 7: Background Runtime / Daemon

Status: in progress.

- support running the orchestrator as a background service
- add a local status command for daemon health and current cycle state
- persist service heartbeats and runtime logs
- support clean start, stop, and restart from the CLI and TUI
- make the daemon compatible with `launchd` or `systemd`-style supervision later
- allow the operator TUI to attach to a running background service instead of owning the process directly
- allow a future WebUI to connect to the same daemon runtime over a local port without duplicating orchestration logic
Notes:
- background launch, status, logs, stop requests, and live monitor attach surfaces are already implemented
- read-only observer surfaces now attach safely through shared status/log contracts without competing for write locks
- restart controls are now available from the CLI through stored background launch config
- deeper supervisor compatibility and daemon-backed multi-surface UI support remain open

## Phase 8: Live Execution Adapters

Status: not started.

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
- define each agent as a three-layer system composed of reasoning layer, tool layer, and memory layer
- introduce a shared memory bus between agents for cross-agent context consistency
- add a consensus mechanism for conflicting agent outputs before execution
- ensure each agent can independently retrieve relevant historical market regimes from vector memory
  Notes:
- coordinator, manager, review, specialist roles, and persona-aware operator chat are already present
- lightweight similarity-based retrieval is now present
- shared memory bus, calibrated confidence, explicit consensus resolution, and richer vector retrieval are still open

## Phase 10: Agent Governance And Conversation Layer

Status: in progress.

- define a structured operator-to-agent messaging protocol so user instructions change preferences and runtime behavior safely
- separate conversational memory from trading memory so chat history does not silently mutate execution policy
- store agent decisions, disagreements, and manager overrides for later review
- allow the operator to inspect why a manager agent accepted or rejected a specialist recommendation
- add guardrails so conversational interactions can influence policy only through approved schemas and not free-form hidden side effects
- introduce memory write permissions and policy-controlled memory mutation rules per agent role
  Notes:
- safe operator instruction parsing and curated preference application already exist
- persisted run review already exposes coordinator, specialist, manager, execution, and review outputs
- persisted run traces now capture routed model, full context payload, and per-stage outputs
- explicit disagreement storage, conversational-memory isolation, and memory write policy controls remain open

## Cross-Cutting Engineering Track

Status: in progress.

- keep type checking and tests green before moving to the next slice
- prefer schema-first agent contracts over free-form text coupling
- add reproducible fixtures for data-heavy tests
- keep CLI, TUI, and service behavior aligned so operator surfaces do not drift
- preserve strict paper-trading discipline until evaluation quality justifies live adapter work
- keep Python console entrypoints and any future Ink or WebUI shells pointed at the same daemon and command contracts
