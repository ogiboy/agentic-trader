# Roadmap

Product name: `Agentic Trader`

This roadmap is both a build plan and a progress ledger. Status values reflect the current codebase, not only the intended destination.

## V1 Completion Boundary

V1 readiness means local paper operation is inspectable, strict, and testable;
Alpaca is ready for explicit external paper checks; source/provider gaps are
visible; and live execution remains blocked. Open V1.1/V1.2/V2 items such as
deeper research ingestion, CrewAI deep-dive execution, true semantic embeddings,
IBKR/global/FX, app-managed Ollama supervision, and actual live brokerage are
not V1 blockers unless a later decision moves them back into V1 scope.

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
- [x] add optional news and event feeds
- [x] add source/provider diagnostics for selected source, fallback reason, freshness, completeness, API-key readiness, rate-limit or degraded-mode state, and explicit Yahoo fallback warnings
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
- `provider-diagnostics` now exposes the current source ladder, model routing, API-key readiness, freshness/completeness placeholders, and explicit Yahoo fallback warnings without fetching network data or leaking secrets
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
- [ ] run a designer-style visual audit for Ink and Rich surfaces, including first-launch logo fit, resize behavior, visual density, and hotkey visibility
- [ ] run a CLI ergonomics audit for `--help`, `-h`, examples, option naming, and short/long flag consistency
- [ ] simplify Rich menu navigation so back, close, cancel, and exit controls feel consistent across sections
- [x] add a first finance/accounting read-only check for cash, equity, PnL, exposure, positions, backend, adapter, runtime mode, risk report availability, and live-block evidence
- [ ] deepen finance/accounting readability across every CLI/Rich/Ink/Web GUI display for currency, mark timestamp, stale state, fees, slippage, and rejection labels
- [ ] convert UX audit findings into smallest-safe repair recommendations before deciding whether they are V1 fixes or V2 redesign work
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
- [ ] let the runtime optionally supervise the local Ollama service lifecycle, health checks, and operator-visible log tails instead of assuming Ollama was started in a separate terminal
      Notes:
- background launch, status, logs, stop requests, and live monitor attach surfaces are already implemented
- read-only observer surfaces now attach safely through shared status/log contracts without competing for write locks
- restart controls are now available from the CLI through stored background launch config
- daemon supervision metadata now records background mode, launch counts, restart counts, last terminal state, and stdout or stderr log tails for operator surfaces
- a local observer API now exposes the same runtime contracts over HTTP endpoints such as `/health`, `/dashboard`, `/status`, `/logs`, and `/broker`
- a first `webgui/` shell now exists and uses those shared contracts through local server-side route handlers instead of introducing a separate runtime
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
- [x] add fundamental and macro/news analyst specialist roles that consume structured feature bundles before manager synthesis
- [ ] upgrade vector-style memory from hashed-token pseudo-embeddings to true local-first semantic embeddings with metadata and migration compatibility
- [ ] improve retrieval ranking with freshness, outcome weighting, regime buckets, and diversity constraints
- [ ] persist per-stage retrieval explanations so the operator can inspect why a memory influenced a decision
      Notes:
- coordinator, manager, review, specialist roles, and persona-aware operator chat are already present
- lightweight similarity-based retrieval is now present
- historical confidence calibration is now present as a downside-aware signal in agent context and manager overrides
- a first shared memory bus now propagates normalized stage summaries across the agent graph and into persisted traces
- a first specialist consensus layer now scores pre-manager alignment and persists the result into reviews and replays
- the agent graph now includes fundamental and macro/news analyst stages between coordinator and regime so manager synthesis sees technical, fundamental, and macro context together
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
- treat research sidecars as optional local evidence companions, not a second trading runtime or a replacement for the staged specialist graph
- keep the root runtime on uv with Python 3.13 as the daily developer default while preserving `>=3.12,<3.15` package support until CI broadens the matrix
- keep optional CrewAI Flow work in a tracked but isolated uv sidecar instead of adding CrewAI to the root dependency graph or turning the repository into a repo-wide uv workspace
- keep Conda/Poetry references as legacy fallback knowledge only; active setup, checks, QA, release, and CI should use root uv commands
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
- [x] add deterministic V1 edge-case coverage for partial Yahoo-style windows, intraday provider limits, non-datetime indexes, higher-timeframe fallbacks, and Training replay undercoverage visibility
      Notes:
- this phase answers the operator question: "Did the system really analyze the configured history?"
- token pressure should be controlled by separating deterministic summaries from optional raw bar excerpts
- the pack is now part of snapshot JSON, agent prompt rendering, memory documents, run artifacts, trade context, dashboard payloads, observer API payloads, and Ink review surfaces
- under-covered operation/runtime windows now stop before agent execution when expected coverage falls below the safety threshold
- training replay can intentionally keep growing-window undercoverage as an explicit context-pack flag instead of treating it as production-ready coverage
- V1 smoke QA now includes a network-free market-context edge-case contract so release evidence proves both Operation fail-closed behavior and Training replay visibility without requiring live providers
- broader live-provider interval scenarios such as Alpaca IEX versus SIP/delayed feeds, IBKR session/calendar edge cases, and FX/global market data windows belong to V1.1/V2 unless they are moved back into the V1 boundary

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

Status: in progress.

- [x] expand `scripts/qa/smoke_qa.py` into a tiered terminal regression harness while keeping the fast smoke path lightweight (fast smoke plus optional quality, Sonar, and runtime-cycle tiers)
- [ ] map `.ai/qa/qa-scenarios.md` scenarios to deterministic pexpect flows with fixed terminal size, environment, and artifact naming
- [x] capture core CLI JSON snapshots, status payloads, broker state, provider diagnostics, V1 readiness, and dashboard contract sections in fast smoke QA
- [ ] expand captured keypress transcripts, service events, and context-pack excerpts across every `.ai/qa/qa-scenarios.md` scenario
- [ ] use Computer Use for visual CLI/Rich/Ink inspection when available, with pexpect, tmux, asciinema, and text artifacts as the fallback path
- [ ] optionally capture tmux pane dumps and asciinema recordings for Ink and Rich visual regressions
- [x] generate a human-readable `qa-report.md` from structured check results for each smoke run
- [x] add an evidence bundle command or mode that packages recent logs, dashboard snapshot, readiness, broker state, observer-compatible payloads, and QA results under a timestamped artifact directory
- [ ] keep quality gates tiered: CI-safe CLI/static checks first, local interactive TUI checks second, manual visual recordings third
- [ ] include daemon lifecycle, mode banner, memory retrieval, and observer API consistency in regression coverage
      Notes:
- QA should validate the product the operator actually touches, not just unit-level internals
- smoke QA now includes dashboard, provider diagnostics, V1 readiness, broker health, runtime-mode checklist, deterministic market-context edge-case checks, deep Rich-menu navigation, raw terminal-noise detection, a generated `qa-report.md`, and an optional isolated one-cycle runtime check
- visual QA can now use Computer Use in Codex/Desktop environments, but it remains optional and must be paired with contract/runtime truth checks
- artifacts must stay token- and secret-safe, and generated evidence should remain ignored unless explicitly promoted to docs

## Phase 15: Production-Like Paper Operations

Status: in progress.

- [x] define a canonical operator workflow: doctor, hardware profile, provider diagnostics, V1 readiness, smoke QA, one strict cycle, trace review, evidence bundle, then background paper operation
- [x] harden daemon lifecycle semantics for stale PIDs, stop requests, restarts, log tails, and terminal outcomes
- [ ] add runtime performance profiles that tune concurrent agents, model routing, token budgets, request timeouts, and memory limits based on local hardware class
- [x] add a hardware capability probe that records CPU, RAM, GPU/accelerator, model size, and safe parallelism recommendations before starting long-running operation
- [ ] make live monitor stage progress show agent stage, current symbol, data context, last tool usage, current model call, terminal outcome, and safety gate result
- [ ] redesign the Ink control room toward an htop-like operator console with stable panes, visible controls, resize-safe layout, and less scrollback noise
- [ ] reduce Rich/admin visual density or keep it as a compact fallback surface once Ink reaches full operational parity
- [x] add a paper-operations readiness checklist that must pass before longer continuous runs
- [x] tie V1 readiness to paper evidence, provider health, source attribution, context-pack explainability, broker health checks, and an explicit no-live-until-approved gate
- [x] add a native read-only `finance-ops` trading-desk payload across CLI, dashboard, observer API, and evidence bundles for broker/account/PnL/exposure/risk/evidence reconciliation
- [ ] compare paper operation results against deterministic baselines and memory/no-memory ablations before considering any live adapter
- [ ] keep live broker work blocked until paper operation has stable QA evidence, context-pack explainability, and reviewable trade journals
      Notes:
- this phase is about earning operator trust in continuous paper operation before expanding execution risk
- the product should feel like an inspectable operator system, not a black-box trading bot
- `v1-readiness` is now the first paper-operations checklist and is visible through CLI, dashboard, observer API, Rich, Ink, and Web GUI surfaces; it also reports paper evidence expectations, source-ladder visibility, context-pack explainability fields, review/evidence-bundle artifacts, and the explicit no-live-until-approved gate
- daemon lifecycle now records blocked runtime gates, recovers dead PID state through `stop-service`, treats stale live-heartbeat PID state as unsafe to double-launch, honors stop requests during cycle sleeps and after skipped symbols, exposes supervisor log tails through observer-compatible payloads, and filters live monitor stage rows to the active cycle

## Phase 16: Financial Intelligence Layer

Status: in progress.

- [x] introduce structured symbol identity with symbol, exchange, currency, region, and asset class
- [x] add a deterministic feature bundle that summarizes technical, fundamental, and macro/news context before agent prompts
- [x] add technical feature summaries for 30d, 90d, and 180d returns, volatility, drawdown, support/resistance, trend classification, and momentum indicators
- [x] scaffold fundamental feature contracts for revenue growth, profitability stability, cash-flow alignment, debt risk, FX exposure, and reinvestment potential
- [x] scaffold macro/news context with company-specific, sector-level, and macro-level classification plus relevance scores
- [x] add fundamental analyst and macro/news analyst roles with structured schemas instead of free-form LLM output
- [x] expand the fundamental analyst contract so growth, profitability, cash flow, balance sheet, FX, business quality, macro fit, forward outlook, evidence, inference, uncertainty, red flags, strengths, and overall bias are explicit
- [x] persist decision feature snapshots, fundamental summaries, and macro summaries into trade context and memory documents
- [x] introduce provider interfaces for market, fundamental, news, disclosure, and macro data sources
- [x] add a canonical analysis snapshot that preserves source attribution, freshness, completeness, and missing-section metadata
- [x] add explicit SEC EDGAR, KAP, Finnhub, and FMP provider scaffolds that surface missing data without fetching or fabricating live fundamentals/disclosures
- [x] aggregate runtime market context, fundamental scaffolds, news events, disclosure scaffolds, and macro scaffolds before feature generation
- [x] document the V1 source ladder: regulatory/public data first, free-friendly APIs such as Finnhub/FMP as optional enrichers, and Yahoo only as a degraded fallback
- [x] make SEC 10-K/10-Q/8-K, earnings transcripts, macro indicators, KAP, Turkey company disclosures, CBRT-style macro data, inflation, and FX sources explicit scaffold metadata
- [ ] implement real fundamental providers behind the feature interface, starting with API-backed US equities and SEC filings
- [ ] implement structured news and macro ingestion from Finnhub, FMP, Polygon/Massive, SEC, earnings transcripts, macro indicators, KAP, CBRT, inflation, and FX feeds
- [ ] add operator-visible reasoning panels that explain how technical, fundamental, macro, memory, and guard evidence combined
- [ ] improve risk engine with volatility-based sizing, portfolio exposure limits, sector concentration checks, and macro risk overrides
      Notes:
- this phase moves the system from "price plus simple agent reasoning" toward a financially-aware, multi-source decision system
- agents now consume a compact `DecisionFeatureBundle`; raw noisy data should stay behind feature/provider boundaries
- the prompt-facing feature bundle is the primary agent input; compact runtime snapshots remain available internally for deterministic fallback and risk math
- canonical analysis snapshots now sit below the feature bundle so provider source, freshness, and missing-data truth can travel into prompts, persistence, memory, and dashboard JSON without coupling agents to provider-specific payloads
- Yahoo should be treated as fallback/degraded evidence once stronger provider data is configured, not as the long-term source of truth
- API keys are configuration-only and must stay in ignored local env files, never in tracked files or QA artifacts
- live trading remains blocked; this is decision intelligence groundwork, not broker activation

## Phase 17: V1 Alpaca Readiness - US Paper First

Status: completed.

- [x] add settings-only Alpaca paper credentials/feed fields so env readiness can be checked without enabling live trading
- [x] add an Alpaca adapter behind the existing broker adapter contract for US equities only
- [x] default to Alpaca paper endpoints and IEX-class data assumptions unless the operator explicitly configures otherwise
- [x] keep paper, simulated-real, Alpaca external paper, and live backends explicitly separated in settings, status, persistence, and operator UI
- [x] require manual approval before any live execution path can submit an order
- [x] enforce strict risk caps, kill switch, and unsupported-backend failures before live adapter activation
- [x] add account, order, position, and feed health checks before any Alpaca live-readiness banner can pass
- [x] restrict V1 live-readiness scope to US equities until paper evidence, manual approval, and strict safety gates are proven
- [x] persist full execution audit trail including intent, approval, adapter health, broker response, fills, rejection reason, and trace link
- [x] add paper-to-live readiness checklist that compares paper performance, QA evidence, and broker health before enabling any live mode
      Notes:
- V1 readiness is Alpaca-first and US-equities-only to limit blast radius
- V1 does not mean live trading is enabled; it means the system is Alpaca-ready while remaining paper-first with manual approval and strict safety gates
- `paper` remains the default; `alpaca_paper` is an explicit external-paper backend gated by credentials, paper endpoint, and `AGENTIC_TRADER_ALPACA_PAPER_TRADING_ENABLED=true`
- `live` remains blocked; V1 readiness is expressed through `v1-readiness`, `provider-diagnostics`, `broker-status`, dashboard/observer payloads, the Alpaca paper adapter health path, and the persisted execution intent/outcome audit trail, not through hidden live brokerage

## V1.1 Research Sidecar - Local Evidence Companion

Status: in progress.

- [x] add a `researchd` module boundary for optional sidecar intelligence without moving the trading runtime into CrewAI or any external orchestration framework
- [x] add canonical research schemas for raw evidence, macro events, social signals, findings, entity dossiers, world-state snapshots, provider health, and sidecar status
- [x] add sidecar settings for mode, enablement, backend, symbols, cadence, and per-source limits with safe defaults
- [x] add SEC EDGAR, KAP, macro, news/event, and social-watchlist provider scaffolds that expose missing ingestion instead of fabricating evidence
- [x] add `research-status`, dashboard, and observer API visibility for mode, enabled/disabled state, backend, watched symbols, source health, and last update fields
- [x] keep the initial CrewAI integration as an optional backend boundary rather than a required dependency or runtime replacement
- [x] add file-backed sidecar persistence for raw-evidence references, world-state snapshots, and memory-update previews without opening or competing with the active DuckDB runtime writer
- [x] move CrewAI Flow scaffolding into a tracked uv-managed sidecar at `sidecars/research_flow/` while keeping it outside the root dependency graph
- [x] add a first opt-in official SEC EDGAR submissions metadata provider with User-Agent gating and normalized filing evidence
- [ ] wire remaining real official/structured sources: SEC company facts/full filing parsing, KAP disclosures, FRED/CBRT-style macro series, GDELT/news event feeds
- [ ] write only normalized research packets into trade-memory-facing surfaces; never inject raw web/social text directly into trading prompts
- [ ] add operator controls for start, stop, mode, cadence, watchlist, and source health across CLI, Ink, Rich, and Web GUI as the sidecar matures
      Notes:
- V1.1 is a local-first evidence companion for the current runtime, not a re-platforming
- the sidecar may eventually run beside the daemon, but it must not submit orders, mutate trading policy, or weaken strict runtime gates
- SEC EDGAR submissions ingestion is metadata-first and disabled by default; full filing text, XBRL facts, and downstream memory writes remain separate planned steps
- missing provider data must stay visible as missing; source diversity, staleness, evidence/inference separation, and contradiction tracking are core contracts

## V1.2 Evaluation And Crew Loops - Optional Sidecar Harness

Status: planned.

- [x] add an operator-visible CrewAI setup/status preflight that keeps CrewAI out of the core runtime dependency graph
- [x] add a minimal tracked CrewAI Flow package with Python 3.13 `.python-version`, root-version-aligned pyproject metadata, uv lock/install flow, and root pnpm/Make setup and smoke-check commands
- [x] add a subprocess JSON contract between the root `ResearchSidecarBackend` and tracked CrewAI Flow sidecar without importing CrewAI in core runtime modules
- [ ] add optional CrewAI Flow/Crew adapters behind the sidecar backend boundary for deep-dive research tasks
- [x] scaffold focused task definitions for company dossiers, sector briefs, contradiction checks, timeline reconstruction, and watch-next lists
- [ ] add evaluation harnesses that compare research packets against later market behavior, paper outcomes, and memory/no-memory ablations
- [ ] link simulated training trades back to the exact world-state snapshot, evidence packet, prompt context, and sidecar version used
- [ ] add scenario memory, contradiction files, source-diversity scoring, and freshness/outcome weighting before research packets influence manager confidence
- [ ] keep native replay, QA, and runtime paths valid when CrewAI is not installed or disabled
      Notes:
- CrewAI is useful here as a sidecar research harness, not as the owner of execution, broker state, or runtime orchestration
- the tracked sidecar is intentionally isolated: uv owns `sidecars/research_flow/`, root uv owns the core runtime lock, and native runtime/replay/QA must keep working when the sidecar is not installed
- training intelligence loops should improve evaluation and memory quality while Operation remains strict, paper-first, and explicitly gated

## Phase 18: V2 Global Expansion - IBKR And FX

Status: planned.

- [ ] add an Interactive Brokers adapter behind the same broker adapter boundary
- [ ] decide and document the IBKR integration route, such as TWS/Gateway versus Web API, before coding the adapter
- [ ] support multi-market symbol identity across US, EU, TR, and future venues
- [ ] add currency awareness to account state, intent sizing, fills, PnL, and risk reports
- [ ] model FX exposure, conversion assumptions, conversion source, and as-of timestamps explicitly before execution
- [ ] preserve realized and unrealized PnL by instrument currency and account base currency
- [ ] add timezone/session awareness for global exchanges and market-specific trading calendars
- [ ] integrate Turkey-specific KAP disclosures, company disclosures, CBRT-style macro data, inflation, rates, and FX context into the feature layer
- [ ] add region-specific data QA for global sessions, holidays, delayed feeds, and currency conversion gaps
      Notes:
- v2 should reuse the v1 contracts instead of creating a separate global trading runtime
- global expansion depends on symbol identity, currency/FX accounting, session calendars, and provider-specific QA evidence being mature first
- IBKR/global support belongs in V2; it should not pull V1 away from the US-only Alpaca paper-first path

## Phase 19: Onboarding, Docs, And Frontend System

Status: in progress.

- [x] refresh developer orientation notes and keep README links pointed at the current code-map instead of stale `docs/dev/*` paths
- [x] activate the existing `docs/` app as a Fumadocs-based local documentation site for setup, architecture, runtime, data/execution, operator surfaces, and QA
- [x] expand docs with project-state, bootstrap, and frontend-system pages without duplicating repository truth
- [x] reframe the docs entrypoint, project state, getting started, operator surfaces, and memory/review pages as an operator-first guide rather than a contributor-only manual
- [ ] expand docs with contributing and deeper reference pages without duplicating repository truth
- [ ] add feature deep dives for paper operation, broker/account truth, memory/review evidence, research sidecar, runtime modes, and evidence bundles
- [ ] add a cross-platform bootstrap flow for macOS, Linux, and Windows that checks prerequisites, sets up the environment, offers optional Ollama plus default-model installation, and opens the Web GUI
- [ ] keep bootstrap provider-aware so users can skip or replace the default Ollama/model path without hidden behavior
- [ ] preserve the current shared shadcn preset baseline from `pnpm dlx shadcn@latest init --preset b2CQzAxv8 --template next` across both `docs/` and `webgui/`, using a local-first monospace typography stack without build-time Google Fonts fetches
- [ ] migrate `webgui` incrementally from legacy global shell classes toward shadcn primitives and Tailwind v4 token composition
- [x] resolve the current `webgui` `next dev` multi-lockfile/Turbopack Tailwind issue so local interactive frontend work matches the green lint/build path
      Notes:
- `docs/` and `webgui/` should stay visually related, but neither should become a second runtime or a cross-app shared-package experiment before the surfaces stabilize
- the docs app should stay curated and source-linked rather than mirroring whole repository files blindly
- operator-facing docs should distinguish trading memory/review evidence from contributor `.ai` notes, and should explain V1 paper/live/broker boundaries before package ownership details
- `webgui` dev mode now runs on `localhost:3210` with Watchpack polling so browser QA matches the README and avoids file-watch noise in this worktree
- app-managed Ollama and bootstrap work should plug into the existing daemon/log/status surfaces rather than inventing separate setup helpers with hidden runtime state
