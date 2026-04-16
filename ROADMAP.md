# Roadmap

Product name: `Agentic Trader`

This roadmap is both a build plan and a progress ledger. Status values reflect the current codebase, not only the intended destination.

## Phase 1: Guardrailed Core

Status: completed in the initial scaffold.

- [x] fetch market data
- [x] compute a compact feature snapshot
- [x] run regime, strategy, and risk agents
- [x] validate with deterministic execution guard
- [x] persist runs and paper orders

## Phase 2: Strict Runtime And Orchestration

Status: completed.

- [x] add a single root launcher for the whole system
- [x] block trading runtime when Ollama or the configured model is unavailable
- [x] make fallback logic diagnostic-only rather than silently generating trades
- [x] support one-shot and continuous orchestrator modes
- [x] expose system health and runtime gating from the CLI
- [x] keep the control room open in the terminal until the user exits it
- [x] show agent/runtime status and recent activity from one menu surface
- [x] introduce a unified agent context builder that merges market snapshot, memory, and tool outputs before every cycle
- [x] add model routing layer to select different models per agent role such as regime, strategy, risk, manager, and explainer
- [x] ensure deterministic safe-mode diagnostics when no LLM is available without allowing silent trade generation in the strict runtime
- [x] add runtime guardrails for missing data, tool failures, and low-confidence outputs
  Notes:
- root launcher, strict runtime gate, one-shot mode, continuous mode, background mode, status, logs, and control-room loop are already live
- unified agent context and role-based model routing are the next major orchestration upgrades

## Phase 3: Better Inputs

Status: in progress.

- [x] add multi-timeframe features
- [x] add market calendar awareness
- [x] introduce a persisted Market Context Pack so `lookback` becomes operator-verifiable rather than only implied by latest-row indicators
- [x] add multi-horizon context summaries for returns, volatility, drawdown, trend alignment, range structure, data sufficiency, and anomalies
- [x] expose bars expected, bars analyzed, window coverage, cache provenance, and interval semantics in CLI, TUI, dashboard, review, and observer surfaces
- [ ] add optional news and event feeds
- [x] add cached data snapshots for repeatable tests
- [x] let the user choose regions, exchanges, currencies, sectors, and default strategy posture
- [x] let the user define portfolio preferences from the TUI instead of editing files
- [x] let the user choose high-level investment behavior presets from curated options rather than raw free-form config only
- [ ] prepare a future model/provider menu so Ollama, remote APIs, and agent profiles can be switched from the operator surface
- [x] introduce memory injection into market context so agents can retrieve historically similar regimes and conditions
- [x] ensure all external knowledge such as news, events, and macro signals is accessed only via tools rather than being assumed by the model
  Notes:
- operator preferences and curated behavior presets already exist
- lightweight retrieval from historically similar runs is now injected into agent context
- multi-timeframe feature enrichment is now part of the market snapshot and already informs fallback coordinator and regime logic
- a first market-session heuristic is now available through the CLI, dashboard snapshot, Ink control room, and agent context tool outputs
- repeatable market snapshot cache management is now available through the CLI and dashboard snapshot
- a first optional news tool contract now exists and only enters agent context through explicit tool outputs
- a first Market Context Pack now makes the full lookback window visible, persisted, and reviewable through run artifacts, trade context, dashboard JSON, observer API, and Ink review surfaces
- richer calendar awareness and tool-driven external context are still open

## Phase 4: Operator Experience

Status: in progress.

- [x] build a more impressive ANSI, Rich, or Textual-style control room
- [x] add start, stop, status, logs, and portfolio views from the same UI
- [x] show which symbols, agents, and model stages are active in real time
- [x] display model usage, last decision, and last trade outcome in a dedicated status area
- [x] let the operator configure investment preferences and default strategy posture from the menu before starting runtime
- [x] keep the terminal app open until the operator explicitly exits it
- [x] add a dedicated chat screen inside the TUI so the operator can talk to the system without leaving the control room
- [x] support chatting with either a general operator assistant or a selected agent persona from the menu
- [x] show structured agent activity, recent tool usage, and the current reasoning stage beside the chat transcript
- [x] add a clearer retro-terminal visual language so the control room feels like a serious operator console rather than a plain CLI
- [x] introduce an Ink-based next-generation control room under a dedicated `tui/` application so the operator surface can evolve beyond the current Rich menu
- [x] keep `agentic-trader` as the primary launcher and expose subcommands such as `agentic-trader tui`, `agentic-trader monitor`, and future UI entrypoints
- [x] show the Market Context Pack in operator surfaces so the user can verify what data window and derived context each cycle used
- [x] add a mode banner across CLI, Rich, Ink, monitor, and observer API so Training and Operation runs are never confused (completed 2026-04-15; keep parity in future UI additions)
- [x] add memory explorer UI to inspect long-term and vector memory state
- [x] add agent decision trace viewer to inspect reasoning, tool calls, and outputs per cycle
- [x] add retrieval inspection view to show why specific memories were used in a decision
- [x] prepare a UI text catalog and localization boundary for CLI, Rich, Ink, and future WebUI surfaces
- [ ] add full multi-language support after operator flows stabilize
  Notes:
- control room, live monitor, operator chat, journal view, risk report view, and run review are already available
- a first memory explorer surface is now available from the CLI and TUI
- persisted hybrid memory retrieval now combines heuristic market similarity with a lightweight vector-style embedding layer
- persisted per-stage trace viewing is now available from the CLI and TUI
- a first Ink-based control room now exists under `tui/` and consumes JSON status, log, preference, and portfolio surfaces from the Python runtime
- the Ink control room now ships with overview, runtime, portfolio, and review pages plus start/stop hotkeys
- the Ink control room now also includes an operator chat page with persona switching
- the Ink control room now also includes a memory page backed by similar-run retrieval and stage-level retrieval inspection
- the Ink chat page now embeds live agent activity, recent tool-role usage, and reasoning-stage context beside the transcript
- a lightweight shared UI text catalog now exists as the first step toward future multi-language operator surfaces
- the Ink overview and review pages now surface context-pack summaries, lookback coverage, quality flags, anomalies, and horizon votes from the Python dashboard contract
- the next operator trust upgrade is adding a Training/Operation mode banner and deeper retrieval explanations beside the context pack
- richer trace inspection and deeper Ink feature parity are still open
- full multi-language support should wait until operator flows stabilize, then build on the shared text catalog instead of scattering strings per surface

## Phase 5: Backtesting

Status: completed.

- [x] implement walk-forward replay
- [x] compare agent-assisted plans against deterministic baselines
- [x] track win rate, expectancy, drawdown, and exposure
- [x] export run reports for review
- [x] introduce memory-aware replay mode to reconstruct what the system knew at the time of each decision
- [x] run ablation tests comparing performance with and without vector memory or a RAG layer
Notes:
- a first walk-forward replay and report export path are now available
- agent-versus-deterministic baseline comparison is now available
- a first memory-aware replay surface is now available through `replay-run`, the dashboard snapshot, and the Ink review page
- a first memory ablation surface is now available through `backtest --compare-memory`
- the retrieval layer now has a persisted hybrid heuristic-plus-vector memory path that can be expanded into richer RAG later

## Phase 6: Paper Portfolio Engine

Status: completed.

- [x] track positions over time instead of single-shot orders
- [x] manage open trades bar by bar
- [x] trigger stop loss, take profit, and invalidation exits as new bars arrive
- [x] support portfolio-level limits and cash usage
- [x] add daily risk reports
- [x] mark portfolio state after each orchestrator cycle
- [x] store fills, open positions, and account state as if the broker were real
- [x] maintain trade journals so the system can review what it planned, what it executed, and what actually happened
- [x] persist full agent decision context for each trade including market snapshot, memory inputs, and tool outputs
Notes:
- open positions, fills, account marks, daily risk reports, run reviews, and trade journals are in place
- portfolio-level gross exposure caps, open-position caps, and cash-aware long entry checks are now enforced in the paper broker
- richer multi-position capital rules and deeper per-trade context persistence still need expansion

## Phase 7: Background Runtime / Daemon

Status: in progress.

- [x] support running the orchestrator as a background service
- [x] add a local status command for daemon health and current cycle state
- [x] persist service heartbeats and runtime logs
- [x] support clean start, stop, and restart from the CLI and TUI
- [ ] make the daemon compatible with `launchd` or `systemd`-style supervision later
- [x] allow the operator TUI to attach to a running background service instead of owning the process directly
- [x] allow a future WebUI to connect to the same daemon runtime over a local port without duplicating orchestration logic
Notes:
- background launch, status, logs, stop requests, and live monitor attach surfaces are already implemented
- read-only observer surfaces now attach safely through shared status/log contracts without competing for write locks
- restart controls are now available from the CLI through stored background launch config
- daemon supervision metadata now records background mode, launch counts, restart counts, last terminal state, and stdout or stderr log tails for operator surfaces
- a local observer API now exposes the same runtime contracts over HTTP endpoints such as `/health`, `/dashboard`, `/status`, `/logs`, and `/broker`
- deeper supervisor compatibility and daemon-backed multi-surface UI support remain open

## Phase 8: Live Execution Adapters

Status: in progress.

- [x] introduce a canonical Execution Intent contract between guard output and broker adapters
- [x] define a broker adapter interface
- [x] start with a safe paper/live switch
- [x] refactor the paper execution path to submit intents through the adapter boundary while preserving paper fills, positions, journals, and risk reports
- [x] add a simulated-real adapter scaffold that remains local, non-live, and paper-safe while modeling slippage, spread, drift, latency metadata, rejection hooks, and partial-fill shape
- [x] persist execution intent and outcome metadata for future replay/live-readiness audits
- [x] add approval gates and kill switches
- [ ] implement one live broker only after paper results are stable
Notes:
- a broker adapter boundary now sits in front of execution and the paper broker implements the first adapter through `ExecutionIntent -> place_order() -> ExecutionOutcome`
- simulated-real is intentionally not a live broker; it records non-live simulated metadata while still using local paper-safe persistence
- runtime surfaces now expose broker backend state, live-request status, and kill-switch status
- live execution remains intentionally blocked until a real live adapter is added behind the same interface

## Phase 9: Smarter Agent Layer

Status: in progress.

- [x] let the regime agent select strategy families dynamically
- [x] let the risk agent adapt size by volatility and portfolio state
- [x] add memory from past trades and post-trade review
- [x] add confidence calibration based on historical results
- [x] add configurable agent personas so the operator can choose cautious, balanced, aggressive, contrarian, or trend-biased behavior profiles
- [x] let the operator set agent tone, strictness, and intervention style from curated presets in the TUI
- [x] split the agent graph into clearer specialist roles such as research coordinator, regime analyst, strategy selector, risk steward, execution guard, portfolio manager, and review agent
- [x] add a dedicated operator-facing liaison agent that explains what the system is doing and answers portfolio questions in plain language
- [x] introduce manager agents that orchestrate specialist agents, resolve conflicts, and decide whether a cycle should advance or pause
- [x] define each agent as a three-layer system composed of reasoning layer, tool layer, and memory layer
- [x] introduce a shared memory bus between agents for cross-agent context consistency
- [x] add a consensus mechanism for conflicting agent outputs before execution
- [x] ensure each agent can independently retrieve relevant historical market regimes from vector memory
- [ ] upgrade vector-style memory from hashed-token pseudo-embeddings to true local-first semantic embeddings with metadata and migration compatibility
- [ ] improve retrieval ranking with freshness, outcome weighting, regime buckets, and diversity constraints
- [ ] persist per-stage retrieval explanations so the operator can inspect why a memory influenced a decision
  Notes:
- coordinator, manager, review, specialist roles, and persona-aware operator chat are already present
- lightweight similarity-based retrieval is now present
- historical confidence calibration is now present as a downside-aware signal in agent context and manager overrides
- a first shared memory bus now propagates normalized stage summaries across the agent graph and into persisted traces
- a first specialist consensus layer now scores pre-manager alignment and persists the result into reviews and replays
- TUI and operator instruction flows now expose curated tone, strictness, and intervention presets alongside behavior and agent profile
- current vector-style retrieval is intentionally lightweight; richer semantic embeddings, retrieval explanations, and outcome-aware ranking are still open

## Phase 10: Agent Governance And Conversation Layer

Status: completed.

- [x] define a structured operator-to-agent messaging protocol so user instructions change preferences and runtime behavior safely
- [x] separate conversational memory from trading memory so chat history does not silently mutate execution policy
- [x] store agent decisions, disagreements, and manager overrides for later review
- [x] allow the operator to inspect why a manager agent accepted or rejected a specialist recommendation
- [x] add guardrails so conversational interactions can influence policy only through approved schemas and not free-form hidden side effects
- [x] introduce memory write permissions and policy-controlled memory mutation rules per agent role
  Notes:
- safe operator instruction parsing and curated preference application already exist
- persisted run review already exposes coordinator, specialist, manager, execution, and review outputs
- persisted run traces now capture routed model, full context payload, and per-stage outputs
- explicit disagreement storage is now present through manager conflicts and specialist consensus snapshots
- operator chat history is now persisted separately from trading memory through a dedicated sidecar transcript feed
- memory write policy controls remain open

## Cross-Cutting Engineering Track

Status: in progress.

- keep type checking and tests green before moving to the next slice
- prefer schema-first agent contracts over free-form text coupling
- add reproducible fixtures for data-heavy tests
- keep CLI, TUI, and service behavior aligned so operator surfaces do not drift
- preserve strict paper-trading discipline until evaluation quality justifies live adapter work
- keep Python console entrypoints and any future Ink or WebUI shells pointed at the same daemon and command contracts
- keep recurring operator-facing text behind a shared catalog so future localization does not fragment CLI, Rich, Ink, and WebUI surfaces
- make lookback truth a first-class artifact: every trading decision should expose the data window, context summary, memory inputs, and safety gates that shaped it
- treat Training vs Operation as a shared runtime mode overlay, not a forked product or separate orchestration path
- evolve QA from smoke testing into repeatable terminal regression evidence with deterministic CLI JSON checks, pexpect flows, optional tmux/asciinema capture, and human-readable failure reports
- keep memory local-first, inspectable, and policy-bound even as embeddings become more semantic and retrieval becomes more powerful

## Phase 11: Market Context Pack And Verifiable Lookback

Status: in progress.

- [x] add a `MarketContextPack` schema that summarizes the full lookback window, not just the latest feature row
- [x] compute multi-horizon returns, volatility, drawdown, trend alignment, range structure, ATR-normalized distances, data sufficiency, and anomaly flags
- [x] include expected bars, analyzed bars, window coverage, interval semantics, cache provenance, and data quality warnings in the pack
- [x] persist the pack per run and per trade context so later reviews can reconstruct exactly what the agents saw
- [x] expose the pack through `dashboard-snapshot`, run review, trace inspection, observer API, Rich menu, and Ink control room
- [x] include compact summaries by default and only include bar excerpts when Training mode, low confidence, or diagnostic depth requires it
- [x] fail closed with a clear operator-facing reason when data is too thin for the configured lookback instead of silently behaving like a short-window run
- [x] add QA coverage that asserts context-pack fields are present and coherent for representative lookback/interval combinations
  Notes:
- this phase answers the operator question: "Did the system really analyze the configured history?"
- token pressure should be controlled by separating deterministic summaries from optional raw bar excerpts
- the pack is now part of snapshot JSON, agent prompt rendering, memory documents, run artifacts, trade context, dashboard payloads, observer API payloads, and Ink review surfaces
- under-covered operation/runtime windows now stop before agent execution when expected coverage falls below the safety threshold
- training replay can intentionally keep growing-window undercoverage as an explicit context-pack flag instead of treating it as production-ready coverage
- remaining work is adding broader QA scenarios around provider-specific interval edge cases

## Phase 12: Semantic Memory And Retrieval Quality

Status: in progress.

- [ ] replace hashed-token pseudo-embeddings with true local-first semantic embeddings behind a provider seam
- [x] store embedding model name, version, dimensionality, and created-at metadata with memory vectors
- [x] keep backwards compatibility with existing lightweight vectors during migration
- [ ] rank retrieval with semantic similarity, market-regime similarity, freshness, outcome weighting, and diversity constraints
- [ ] bucket or tag memories by regime, strategy family, outcome, and data quality so retrievals can justify their rationale
- [ ] expand memory documents with Market Context Pack summaries, explicit success/failure tags, and post-trade review facts
- [ ] persist stage-level retrieval explanations showing which memories were used, why they were selected, and how strongly they influenced the decision
- [ ] preserve chat-memory and trade-memory separation through explicit write policies while improving recall quality
  Notes:
- this phase keeps memory useful without making it an opaque hidden policy layer
- memory vectors now persist provider/model/version/dimension metadata so future true-embedding migrations can distinguish old lightweight vectors from newer semantic vectors
- legacy `memory_vectors` rows without metadata columns are migrated in place with local-hashing defaults
- DuckDB can remain the source of truth at first; a dedicated vector index or service should wait until memory volume justifies the added operational cost

## Phase 13: Training And Operation Modes

Status: completed.

- [x] add an explicit runtime mode such as `training` or `operation` to settings, service state, run records, dashboard payloads, observer API, and operator surfaces
- [x] show a mode banner in CLI, Rich, Ink, monitor, and future WebUI surfaces
- [x] enforce Operation mode as strict paper operation: provider/model readiness must pass, unsafe fallbacks are blocked, and live execution remains disabled unless a real adapter and approval gates exist
- [x] allow Training mode to run replay, walk-forward, ablation, and diagnostic-only evaluation flows without enabling hidden trade generation
- [x] persist data as-of timestamps and prevent leakage in training/replay scenarios
- [x] gate mode transitions through approved schemas so chat or free-form instructions cannot silently mutate execution policy
- [x] document and surface the checklist for switching from Training to Operation
  Notes:
- this should be a configuration overlay on the existing runtime contracts, not a forked runtime
- a first runtime mode field now flows through settings, service state migration, status JSON, dashboard snapshots, observer API, Rich status tables, and Ink overview/runtime pages
- Operation mode now fails before provider access when strict LLM gating is disabled, and all one-shot/background runtime paths still require model readiness before paper execution
- Training mode can use diagnostic fallback only for backtest/evaluation flows such as walk-forward, baseline comparison, and memory ablation; `run`, `launch`, and service orchestration remain no-fallback
- Market snapshots now carry an `as_of` timestamp, and backtest reports persist data-window plus first/last decision timestamps so replay leakage can be audited
- `runtime-mode-checklist` now emits a schema-backed transition plan so mode changes are explicit operator actions rather than chat side effects
- Operation mode still means paper-first until paper performance, QA evidence, and broker adapters are mature

## Phase 14: Terminal Regression QA And Evidence Bundles

Status: planned.

- [x] expand `scripts/qa/smoke_qa.py` into a tiered terminal regression harness while keeping the fast smoke path lightweight (fast smoke plus optional quality, Sonar, and runtime-cycle tiers)
- [ ] map `.ai/qa/qa-scenarios.md` scenarios to deterministic pexpect flows with fixed terminal size, environment, and artifact naming
- [ ] capture CLI JSON snapshots, status payloads, broker state, service events, context-pack excerpts, and keypress transcripts for each scenario
- [ ] optionally capture tmux pane dumps and asciinema recordings for Ink and Rich visual regressions
- [ ] generate a human-readable `qa-report.md` from structured check results when failures occur
- [ ] add an evidence bundle command or mode that packages recent logs, dashboard snapshot, trace, context pack, and QA results under a timestamped artifact directory
- [ ] keep quality gates tiered: CI-safe CLI/static checks first, local interactive TUI checks second, manual visual recordings third
- [ ] include lookback-context, daemon lifecycle, mode banner, memory retrieval, and observer API consistency in regression coverage
  Notes:
- QA should validate the product the operator actually touches, not just unit-level internals
- smoke QA now includes dashboard and runtime-mode checklist contract checks, deep Rich-menu navigation, raw terminal-noise detection, and an optional isolated one-cycle runtime check
- artifacts must stay token- and secret-safe, and generated evidence should remain ignored unless explicitly promoted to docs

## Phase 15: Production-Like Paper Operations

Status: planned.

- [ ] define a canonical operator workflow: doctor, broker status, dashboard snapshot, Training review, one strict cycle, trace review, then background paper operation
- [ ] harden daemon lifecycle semantics for stale PIDs, stop requests, restarts, log tails, and terminal outcomes
- [ ] add runtime performance profiles that tune concurrent agents, model routing, token budgets, request timeouts, and memory limits based on local hardware class
- [ ] add a hardware capability probe that records CPU, RAM, GPU/accelerator, model size, and safe parallelism recommendations before starting long-running operation
- [ ] make live monitor stage progress show agent stage, current symbol, data context, last tool usage, current model call, terminal outcome, and safety gate result
- [ ] redesign the Ink control room toward an htop-like operator console with stable panes, visible controls, resize-safe layout, and less scrollback noise
- [ ] reduce Rich/admin visual density or keep it as a compact fallback surface once Ink reaches full operational parity
- [ ] add a paper-operations readiness checklist that must pass before longer continuous runs
- [ ] compare paper operation results against deterministic baselines and memory/no-memory ablations before considering any live adapter
- [ ] keep live broker work blocked until paper operation has stable QA evidence, context-pack explainability, and reviewable trade journals
  Notes:
- this phase is about earning operator trust in continuous paper operation before expanding execution risk
- the product should feel like an inspectable operator system, not a black-box trading bot
