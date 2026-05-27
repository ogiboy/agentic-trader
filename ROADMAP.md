# Roadmap

Product name: `Agentic Trader`

This roadmap is both a build plan and a progress ledger. Status values reflect the current codebase, not only the intended destination.

## V1 Completion Boundary

V1 readiness means the product is ready to actively trade supported US equities
through the existing broker boundary: local paper remains the default, Alpaca
paper is the external broker rehearsal path, and any real-money activation must
stay explicit, manually approved, audited, and kill-switch protected. Source and
provider gaps must stay visible instead of being hidden behind model prose.
Former V1.1/V1.2 research, CrewAI-sidecar, evaluation, and memory-quality loops
now belong to the V1 completion track so V1 ends with a stronger evidence
companion rather than only a runtime shell. V2 is the Turkey expansion track.

### V1 Commercial Readiness Blockers

Research refreshed during the type-safety branch audit keeps V1 paper-first until the product can prove
operator trust, compliance posture, and unit economics without overpromising
autonomous advice or live execution. This is not legal advice; it is the
engineering blocker ledger that must be reviewed with qualified counsel before
paid users or real-money claims.

- [ ] classify the commercial model before accepting paid users: personalized
      investment advice, advisory fees, account workflow involvement,
      discretionary authority, copy trading, or order routing can change the
      product from local software into a regulated investment-adviser,
      broker-dealer, Form CRS/Reg BI, SRO, books-and-records, custody,
      disclosure, and state-law problem; see SEC investment-adviser
      registration guidance
      (https://www.sec.gov/investment/how-to-register-with-sec-investment-adviser),
      SEC broker-dealer registration guidance
      (https://www.sec.gov/about/reports-publications/investor-publications/guide-broker-dealer-registration),
      SEC Reg BI/Form CRS resources
      (https://www.sec.gov/regulation-best-interest),
      SEC automated-investment-tool investor guidance
      (https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-84),
      and FINRA algorithmic-trading supervision notes
      (https://www.finra.org/rules-guidance/key-topics/algorithmic-trading).
- [ ] choose a first paid SKU that avoids hidden broker authority: local-first
      paper desk, evidence bundle export, operator education, personal
      automation, and team workflow value are V1-safe candidates; managed live
      trading, account opening, copy trading, performance-fee products,
      bundled brokerage, and "AI adviser" positioning are blocked until the
      compliance model is accepted.
- [ ] complete Alpaca external-paper and production-readiness evidence before
      real-money claims: paper/live credential separation, paper account
      reset/replay discipline, `client_order_id` correlation, order-state
      websocket/reconciliation, account authorization, insufficient-balance and
      rejected-order handling, PDT/margin disclosure, and any
      account-opening/KYC/CIP responsibilities if the product becomes an
      end-user brokerage app; see Alpaca paper trading
      (https://docs.alpaca.markets/docs/paper-trading),
      trading API (https://docs.alpaca.markets/docs/trading-api),
      orders (https://docs.alpaca.markets/docs/orders-at-alpaca),
      trading updates (https://docs.alpaca.markets/us/docs/websocket-streaming),
      market-data streaming
      (https://docs.alpaca.markets/us/docs/streaming-market-data),
      and broker/account-opening docs
      (https://docs.alpaca.markets/docs/about-broker-api,
      https://docs.alpaca.markets/us/docs/account-opening).
- [ ] add a revenue-ready trust layer: onboarding terms, risk disclosure,
      billing/subscription boundary, support and incident channel, audit
      export, data-retention/deletion policy, privacy/security review,
      provider-status telemetry, stale/degraded/no-action UX, and explicit
      "paper evidence only" wording. If the product handles customer financial
      information, include SEC Regulation S-P and FTC Safeguards-style controls
      (https://www.sec.gov/newsroom/press-releases/2024-58,
      https://www.ftc.gov/business-guidance/privacy-security/safeguards-rule).
- [ ] make AI/security risk management product-visible: map model/provider,
      prompt-injection, tool-poisoning, raw web text, sidecar, and
      operator-action risks to NIST AI RMF, NIST Cybersecurity Framework 2.0,
      and OWASP LLM Top 10 controls before claiming trusted automation
      (https://www.nist.gov/itl/ai-risk-management-framework,
      https://www.nist.gov/cyberframework,
      https://owasp.org/www-project-top-10-for-large-language-model-applications/).
- [ ] define model-cost unit economics before cloud AI becomes default: keep
      local Ollama as the default, add per-cycle remote-model cost telemetry,
      hard monthly budgets, role-level routing policies, and quality/cost
      comparison gates; use current provider pages such as OpenAI pricing
      (https://openai.com/api/pricing/), Anthropic pricing
      (https://www.anthropic.com/pricing#api), and Gemini API pricing
      (https://ai.google.dev/gemini-api/docs/pricing) as live inputs, not
      hardcoded assumptions.
- [ ] match market-tool expectations without copying their scope: a paid V1
      paper desk must offer clear paper/live separation, backtest/replay
      evidence, watchlist/scanner flows, audit exports, and degraded-source
      messaging at least comparable to the expectations set by tools such as
      TradingView paper trading
      (https://www.tradingview.com/support/categories/paper-trading/),
      QuantConnect live/paper workflows
      (https://www.quantconnect.com/docs/v2/cloud-platform/live-trading/overview),
      and Alpaca's paper/broker ecosystem, while staying local-first and
      manual-approval-first.

#### Commercial Work Plan

- [ ] C0 - Product/legal classification: document the exact paid SKU,
      disallowed claims, allowed users, data handled, broker/account touch
      points, and legal review outcome before billing is enabled.
- [ ] C1 - Paper-desk packaging: turn `evidence-bundle`, `finance-ops`,
      `v1-readiness`, proposal review, replay, and provider diagnostics into a
      coherent local paper-desk workflow with supportable onboarding copy.
- [ ] C2 - Trust/security controls: ship terms/disclaimers, privacy/data
      retention, audit export, incident/support path, provider status page or
      local equivalent, red-team prompts, and LLM/tool-poisoning regression
      tests.
- [ ] C3 - Alpaca external-paper proof: run repeated AAPL/MSFT paper cycles
      with order correlation, refresh/reconcile, reject/no-fill/cancel cases,
      and evidence artifacts before claiming broker readiness.
- [ ] C4 - Unit economics: measure local vs remote model quality/cost per
      operator workflow, define budgets, and block remote defaults until the
      paper-desk SKU has a positive support and inference margin.
- [ ] C5 - Revenue pilot gate: only after C0-C4 pass, run a limited
      non-live/paper-only pilot with explicit disclaimers, no account custody,
      no managed execution, and support/incident coverage.

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
- [ ] prepare a future model/provider menu so Ollama, LM Studio/OpenAI-compatible endpoints, remote APIs, and agent profiles can be switched from the operator surface
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
- [x] keep `agentic-trader` as the primary operator launcher and expose subcommands such as `agentic-trader tui`, `agentic-trader monitor`, and future UI entrypoints
- [x] show the Market Context Pack in operator surfaces so the user can verify what data window and derived context each cycle used
- [x] add a mode banner across CLI, Rich, Ink, monitor, and observer API so Training and Operation runs are never confused (completed 2026-04-15; keep parity in future UI additions)
- [x] add memory explorer UI to inspect long-term and vector memory state
- [x] add agent decision trace viewer to inspect reasoning, tool calls, and outputs per cycle
- [x] add retrieval inspection view to show why specific memories were used in a decision
- [x] prepare a UI text catalog and localization boundary for CLI, Rich, Ink, and future WebUI surfaces
- [x] add a first Web GUI i18n catalog with stable tab ids, English/Turkish copy, persisted language selection, and localized shell/overview/auth labels
- [ ] add full multi-language support after operator flows stabilize
- [ ] run a designer-style visual audit for Ink and Rich surfaces, including first-launch logo fit, resize behavior, visual density, and hotkey visibility
- [ ] run a CLI ergonomics audit for `--help`, `-h`, examples, option naming, and short/long flag consistency
- [ ] simplify Rich menu navigation so back, close, cancel, and exit controls feel consistent across sections
- [x] add a first finance/accounting read-only check for cash, equity, PnL, exposure, positions, backend, adapter, runtime mode, risk report availability, and live-block evidence
- [x] deepen finance/accounting readability across CLI/Rich/Ink/Web GUI displays for currency, mark timestamp/source/status, fee/slippage assumptions, and rejection-evidence labels
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
- a typed shared Python UI text catalog now exists as the first step toward future multi-language operator surfaces while preserving legacy CLI/Rich/Ink constants
- the Web GUI now has a first local i18n seam plus per-view control-room modules; shell, auth, overview, runtime, portfolio, proposals, review, memory, chat, settings, loading/unavailable states, and the overview helper-generated readiness/provider/local-tool evidence lines now flow through typed per-locale English/Turkish modules; deeper review/portfolio/memory evidence strings still need a broader catalog pass
- the Ink overview and review pages now surface context-pack summaries, lookback coverage, quality flags, anomalies, and horizon votes from the Python dashboard contract
- the next operator trust upgrade is adding a Training/Operation mode banner and deeper retrieval explanations beside the context pack
- richer trace inspection and deeper Ink feature parity are still open
- finance/accounting surfaces now use shared payload truth for currency, paper mark context, cost assumptions, and rejection-evidence wording instead of display-only guesses
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
- a first app-managed Ollama CLI/runtime foundation now exists through `model-service status/start/stop/pull` plus strict runtime auto-start when enabled; it records separate owner-only model-service state/logs, never stops external Ollama processes, preserves ownership state when a recorded process cannot be stopped, and strict provider readiness now verifies generation rather than only `/api/tags`; `model-service status --probe-generation` exposes the same model-load truth directly, but richer Ink/Web/observer controls are still open
- a first app-managed Camofox helper foundation now exists through `camofox-service status/start/stop` plus research auto-start when the Camofox provider is enabled; it binds loopback, requires a local access key, narrows subprocess env, records owner-only state/logs, disables telemetry/prewarm by default, and reports health as evidence only
- a first app-owned Web GUI service foundation now exists through `webgui-service status/start/stop`; it binds loopback, records owner-only state/logs, and refuses to stop stale PID-reuse candidates
- no-argument `agentic-trader` now acts as an operator launcher for Web GUI, default strict paper daemon, Ink, Rich, model-service, setup, and exit choices instead of assuming one terminal surface

## Phase 8: Live Execution Adapters

Status: in progress.

- [x] introduce a canonical Execution Intent contract between guard output and broker adapters
- [x] define a broker adapter interface
- [x] start with a safe paper/live switch
- [x] refactor the paper execution path to submit intents through the adapter boundary while preserving paper fills, positions, journals, and risk reports
- [x] add a simulated-real adapter scaffold that remains local, non-live, and paper-safe while modeling slippage, spread, drift, latency metadata, rejection hooks, and partial-fill shape
- [x] persist execution intent and outcome metadata for future replay/live-readiness audits
- [x] add approval gates and kill switches
- [ ] harden the Alpaca broker path until V1 can prove active US buy/sell readiness with explicit operator approval, audit trail, kill switch, and paper-to-real promotion gates
      Notes:
- a broker adapter boundary now sits in front of execution and the paper broker implements the first adapter through `ExecutionIntent -> place_order() -> ExecutionOutcome`
- simulated-real is intentionally not a live broker; it records non-live simulated metadata while still using local paper-safe persistence
- runtime surfaces now expose broker backend state, live-request status, and kill-switch status
- real-money execution remains opt-in and gated; V1 work should make the supported Alpaca path demonstrably trade-ready without making hidden live execution possible

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
- enforce Pyright/Pylance strictness as a zero-diagnostic gate for
  `agentic_trader`, `tests`, `scripts`, and `sidecars/research_flow/src`;
  strict backlog is now zero, no suppression comments are allowed, and CI,
  release, local `check-python`, and smoke quality checks should fail on any
  new strict diagnostic
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
- broader live-provider interval scenarios such as Alpaca IEX versus SIP/delayed feeds belong to the V1 evidence track; IBKR session/calendar edge cases and FX/global market data windows remain V2 scope

## Phase 12: Semantic Memory And Retrieval Quality

Status: in progress.

- [ ] replace hashed-token pseudo-embeddings with true local-first semantic embeddings behind a provider seam
- [x] store embedding model name, version, dimensionality, and created-at metadata with memory vectors
- [x] keep backwards compatibility with existing lightweight vectors during migration
- [ ] rank retrieval with semantic similarity, market-regime similarity, freshness, outcome weighting, and diversity constraints
- [x] bucket or tag selected memories by regime, strategy family, outcome, and diversity context so retrievals can justify their rationale
- [ ] expand memory documents with Market Context Pack summaries, explicit success/failure tags, and post-trade review facts
- [x] persist stage-level retrieval explanations showing which memories were used, why they were selected, and how strongly they influenced the decision
- [ ] preserve chat-memory and trade-memory separation through explicit write policies while improving recall quality
      Notes:
- this phase keeps memory useful without making it an opaque hidden policy layer
- memory vectors now persist provider/model/version/dimension metadata so future true-embedding migrations can distinguish old lightweight vectors from newer semantic vectors
- legacy `memory_vectors` rows without metadata columns are migrated in place with local-hashing defaults
- selected memory matches now carry explanation payloads with score components, as-of/freshness, outcome tag, regime/strategy alignment, and diversity bucket across traces and operator surfaces
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
- [ ] map `.ai/qa/qa-scenarios.instructions.md` scenarios to deterministic pexpect flows with fixed terminal size, environment, and artifact naming
- [x] capture core CLI JSON snapshots, status payloads, broker state, provider diagnostics, V1 readiness, and dashboard contract sections in fast smoke QA
- [ ] expand captured keypress transcripts, service events, and context-pack excerpts across every `.ai/qa/qa-scenarios.instructions.md` scenario
- [ ] use Computer Use for visual CLI/Rich/Ink inspection when available, with pexpect, tmux, asciinema, and text artifacts as the fallback path
- [ ] optionally capture tmux pane dumps and asciinema recordings for Ink and Rich visual regressions
- [x] generate a human-readable `qa-report.md` from structured check results for each smoke run
- [ ] add a sectional external-review workflow for large V1 diffs so CodeRabbit/Sonar review stays under per-tool file limits while still covering runtime, trading, provider, operator-surface, and docs/setup risk
- [x] add an evidence bundle command or mode that packages recent logs, dashboard snapshot, readiness, broker state, observer-compatible payloads, and QA results under a timestamped artifact directory
- [ ] keep quality gates tiered: CI-safe CLI/static checks first, local interactive TUI checks second, manual visual recordings third
- [ ] include daemon lifecycle, mode banner, memory retrieval, and observer API consistency in regression coverage
      Notes:
- QA should validate the product the operator actually touches, not just unit-level internals
- smoke QA now includes dashboard, provider diagnostics, V1 readiness, broker health, runtime-mode checklist, deterministic market-context edge-case checks, deep Rich-menu navigation, raw terminal-noise detection, a generated `qa-report.md`, and an optional isolated one-cycle runtime check
- smoke QA now also includes a CLI help contract for key operator commands so `--help`/`-h` output stays concise and does not leak implementation-oriented docstring sections
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
- [ ] stabilize terminal UI refresh behavior by preventing overlapping Ink dashboard polls and closing Rich monitor DB handles per refresh tick
- [ ] reduce Rich/admin visual density or keep it as a compact fallback surface once Ink reaches full operational parity
- [x] add a paper-operations readiness checklist that must pass before longer continuous runs
- [x] tie V1 readiness to paper evidence, provider health, source attribution, context-pack explainability, broker health checks, and an explicit no-live-until-approved gate
- [x] add a native read-only `finance-ops` trading-desk payload across CLI, dashboard, observer API, and evidence bundles for broker/account/PnL/exposure/risk/evidence reconciliation
- [ ] compare paper operation results against deterministic baselines and memory/no-memory ablations before considering any live adapter
- [ ] keep ungated real-money broker work blocked while finishing the supported V1 paper/Alpaca approval path, stable QA evidence, context-pack explainability, and reviewable trade journals
      Notes:
- this phase is about earning operator trust in continuous paper operation before expanding execution risk
- the product should feel like an inspectable operator system, not a black-box trading bot
- `v1-readiness` is now the first paper-operations checklist and is visible through CLI, dashboard, observer API, Rich, Ink, and Web GUI surfaces; it also reports paper evidence expectations, source-ladder visibility, context-pack explainability fields, review/evidence-bundle artifacts, and the explicit no-live-until-approved gate
- daemon lifecycle now records blocked runtime gates, recovers dead PID state through `stop-service`, treats stale live-heartbeat PID state as unsafe to double-launch, honors stop requests during cycle sleeps and after skipped symbols, exposes supervisor log tails through observer-compatible payloads, and filters live monitor stage rows to the active cycle
- live monitor Current Cycle output now keeps data context, runtime mode, broker backend/state, kill-switch state, and V1 paper gate visible beside stage progress

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
- [x] add deterministic idea-scanner presets for momentum, gap-up/down, mean-reversion, breakout, and volatile candidates as research-only scoring surfaces
- [x] add first concentration visibility in daily risk reports through portfolio HHI and top-position symbols
- [x] translate external market-intelligence benchmark patterns into repo-native `.ai` guidance for continuous research loops, source-attributed news, strategy research/sweeps, finance evidence reconciliation, and a V1 strategy catalog
- [x] add an opt-in SEC companyfacts fundamental provider behind the canonical feature interface for US equities, with User-Agent gating, no raw filing text, redacted failures, and missing-section truth
- [ ] continue implementing real fundamental providers behind the feature interface beyond the first SEC companyfacts slice, including richer SEC filing references and optional vendor APIs
- [ ] implement structured news and macro ingestion from Finnhub, FMP, Polygon/Massive, SEC, earnings transcripts, macro indicators, KAP, CBRT, inflation, and FX feeds
- [x] turn the first V1 strategy/catalog/news/loop slice into incremental code through existing contracts: idea-scanner metadata, `strategy-catalog`, `strategy-profile`, `idea-score` readiness context, `news-intelligence`, `research-cycle-plan`, and `finance-ops` ledger categories
- [x] add a broker-free proposal-candidate queue that records scanner materiality, freshness, liquidity, spread, sizing intent, risk controls, and evidence before promotion into pending paper proposals
- [x] attach redacted, broker-free canonical source-attribution context to proposal candidates through the existing provider contracts, defaulting to network-light missing-data truth and requiring explicit opt-in before news refreshes
- [ ] continue enriching proposal candidates with real live provider/news/fundamental materiality before treating scanner output as proposal-ready
- [ ] extend the runtime strategy catalog into feature bundles, backtest comparison, proposal records, guard/risk layers, and broader operator surfaces
- [ ] add no-lookahead, declarative sweep, and confidence-review checks before opening-range, VWAP, Keltner/Bollinger, regime-adaptive, pairs, or ensemble research candidates become proposal-capable
- [ ] add operator-visible reasoning panels that explain how technical, fundamental, macro, memory, and guard evidence combined
- [ ] improve risk engine with volatility-based sizing, portfolio exposure limits, sector concentration checks, and macro risk overrides
      Notes:
- this phase moves the system from "price plus simple agent reasoning" toward a financially-aware, multi-source decision system
- agents now consume a compact `DecisionFeatureBundle`; raw noisy data should stay behind feature/provider boundaries
- the prompt-facing feature bundle is the primary agent input; compact runtime snapshots remain available internally for deterministic fallback and risk math
- canonical analysis snapshots now sit below the feature bundle so provider source, freshness, and missing-data truth can travel into prompts, persistence, memory, and dashboard JSON without coupling agents to provider-specific payloads
- idea-scanner presets are intentionally score/watch helpers, not execution agents; output must pass through proposal review and explicit approval before any broker adapter call
- proposal candidates are persisted as broker-free review records; promotion creates a pending `TradeProposalRecord` only after watch/blocking-warning/sizing/stop-take checks pass, and still requires explicit approval before broker submission
- market-intelligence guidance now exists under `.ai/agents/market-strategist.md`, `.ai/workflows/continuous-research-loop.md`, `.ai/playbooks/news-intelligence.md`, `.ai/playbooks/strategy-research-and-sweeps.md`, `.ai/playbooks/finance-evidence-reconciliation.md`, `.ai/skills/market-news-research.md`, and `.ai/strategies/`; these files are development contracts and not a second runtime
- HHI/top-position concentration is the first finance-ops concentration signal; ATR/confidence sizing, ADV/spread penalties, group budgets, and correlation clusters are still open
- Yahoo should be treated as fallback/degraded evidence once stronger provider data is configured, not as the long-term source of truth
- API keys are configuration-only and must stay in ignored local env files, never in tracked files or QA artifacts
- active broker use remains behind explicit proposal approval and runtime gates; this is decision intelligence groundwork feeding the V1 trade-ready path, not hidden broker activation

## Phase 17: V1 Alpaca Readiness - US Active Trading Path

Status: in progress.

- [x] add settings-only Alpaca paper credentials/feed fields so env readiness can be checked without enabling live trading
- [x] add an Alpaca adapter behind the existing broker adapter contract for US equities only
- [x] default to Alpaca paper endpoints and IEX-class data assumptions unless the operator explicitly configures otherwise
- [x] keep paper, simulated-real, Alpaca external paper, and live backends explicitly separated in settings, status, persistence, and operator UI
- [x] require manual approval before any live execution path can submit an order
- [x] add a V1 manual-review proposal queue with explicit create/list/approve/reject/reconcile commands and persisted execution intent/outcome audit fields
- [x] enforce strict risk caps, kill switch, and unsupported-backend failures before live adapter activation
- [x] enforce simple V1 US-equity symbol scope at proposal creation and across local/external paper broker submissions
- [x] enforce Alpaca paper max-position and gross-exposure caps before external paper order submission
- [x] preserve explicit order semantics for approved proposals: limit proposals require quantity plus `limit_price`, market proposals reject stray `limit_price`, and Alpaca paper orders carry `client_order_id` from the execution intent
- [x] keep externally accepted paper orders visible as open journal entries instead of mislabeling broker acknowledgements as no-fill outcomes
- [x] add a read-only proposal refresh path that rechecks accepted broker orders without resubmitting an order
- [x] add account, order, position, and feed health checks before any Alpaca live-readiness banner can pass
- [x] restrict V1 active trading scope to US equities until paper evidence, manual approval, and strict safety gates are proven
- [x] persist full execution audit trail including intent, approval, adapter health, broker response, fills, rejection reason, and trace link
- [x] add paper-to-real readiness checklist that compares paper performance, QA evidence, and broker health before any real-money activation can pass
- [x] add an isolated V1 paper desk rehearsal lane that collects readiness, research-cycle, memory, proposal, journal, finance, and evidence-bundle artifacts
- [x] prove the full V1 customer path with real operator QA: choose US symbols, collect/cache evidence, run at least two learning-aware cycles, inspect retrieved memory, create/review a proposal, submit through paper or Alpaca paper, and verify portfolio/journal/PnL persistence
- [ ] make model-provider selection agnostic enough that V1 paper/Alpaca operation is not blocked on one local model family such as qwen
      Notes:
- V1 readiness is Alpaca-first and US-equities-only to limit blast radius
- V1 must be active-trading ready for the supported US path; default operation remains paper-first and any real-money activation remains explicit, manually approved, audited, and kill-switch protected
- `paper` remains the default; `alpaca_paper` is an explicit external-paper backend gated by credentials, paper endpoint, and `AGENTIC_TRADER_ALPACA_PAPER_TRADING_ENABLED=true`
- real-money execution remains gated; V1 readiness is expressed through `v1-readiness`, `provider-diagnostics`, `broker-status`, dashboard/observer payloads, the Alpaca paper adapter health path, and the persisted execution intent/outcome audit trail, not through hidden brokerage
- proposal approval submits through the existing broker adapter boundary and paper/external-paper safety gates; approve/reject/reconcile/refresh all require operator review notes, and the Web GUI Proposal Desk can invoke only those explicit commands while scanner, sidecar, chat, and Web surfaces must not approve or execute implicitly
- scanner/research candidates enter the broker-free `proposal_candidates` bridge first; promotion may create a pending proposal, but broker submission remains a separate approval action
- broker acknowledgements such as Alpaca paper `accepted` remain in-flight approved proposals with operator-visible open journal entries; `proposal-refresh` can read the original broker order without resubmitting and update proposal/execution/position-plan truth when the broker later reports fill, partial-fill, cancel, or reject state
- `proposal-reconcile` repairs an already approved in-flight proposal from the idempotent `execution_records.intent_id` row without resubmitting to the broker, covering interrupted final-status writes before external paper/live adapters grow broader
- `pnpm run qa:v1-paper-desk` passed on the current V1 branch with an isolated AAPL/MSFT paper rehearsal, producing provider, readiness, research-cycle, memory, proposal, journal, finance, and evidence-bundle artifacts under `.ai/qa/artifacts/codex-v1-paper-desk-smoke/`

## V1 Research Sidecar - Local Evidence Companion

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
- [x] add compact official SEC companyfacts XBRL summaries with fresh source attribution and no raw filing text injection
- [x] add optional disabled-by-default Firecrawl news search and Camofox local-browser health providers behind `researchd`, with redaction, provenance, and raw-text-free prompt boundaries
- [x] document the safe news/browser evidence envelope: source tier, fetcher source, attempts, published/fetched timestamps, freshness, materiality, classification, and redaction before any scanner/proposal/review use
- [x] add a first bounded CLI research-cycle executor for cadence/watchlist-aware sidecar snapshot collection, preflight/source-health/digest output, and no broker/proposal authority
- [x] add advisory pause/resume/trigger-now research-cycle control state plus latest digest replay artifacts across CLI, dashboard JSON, Ink, and Web GUI visibility
- [ ] wire remaining real official/structured sources: SEC full filing parsing, KAP disclosures, FRED/CBRT-style macro series, GDELT/news event feeds
- [ ] write only normalized research packets into trade-memory-facing surfaces; never inject raw web/social text directly into trading prompts
- [ ] add active daemon controls for start, stop, cadence, watchlist mutation, source health actions, and trigger consumption as the sidecar matures
      Notes:
- this is a local-first V1 evidence companion for the current runtime, not a re-platforming
- the sidecar may eventually run beside the daemon, but it must not submit orders, mutate trading policy, or weaken strict runtime gates
- SEC EDGAR submissions and canonical companyfacts ingestion are disabled by default and require a configured User-Agent; full filing text and downstream memory writes remain separate planned steps
- Firecrawl/Camofox support is optional helper infrastructure, not a mandatory runtime dependency or broker-capable sidecar
- `research-cycle-run` now executes bounded evidence-only sidecar cycles, can persist research snapshots, supports QA-friendly `--no-sleep`, and reports preflight status, source-health delta, cadence/next-run, digest, and disabled broker/proposal/raw-web-prompt authority
- `research-cycle-control` persists advisory operator intent without starting a daemon; future continuous runners may consume the pause/resume/trigger-now file, while the latest digest replay artifact stays raw-text-free and broker-disabled
- missing provider data must stay visible as missing; source diversity, staleness, evidence/inference separation, and contradiction tracking are core contracts

## V1 Evaluation And Crew Loops - Optional Sidecar Harness

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

## Phase 18: V2 Turkey Expansion

Status: planned.

- [ ] add Turkey-specific symbol identity, exchange/session calendars, and market-data QA without weakening the V1 US/Alpaca path
- [ ] integrate KAP disclosures, company disclosures, CBRT-style macro data, inflation, rates, and TRY/FX context into the feature layer
- [ ] model TRY account currency, conversion assumptions, conversion source, and as-of timestamps explicitly before execution
- [ ] preserve realized and unrealized PnL by instrument currency and account base currency
- [ ] choose the Turkey broker/data route through a separate decision before coding execution adapters
- [ ] add region-specific data QA for Borsa Istanbul sessions, holidays, delayed feeds, and currency conversion gaps
      Notes:
- V2 should reuse the V1 contracts instead of creating a separate Turkey trading runtime
- Turkey expansion depends on symbol identity, TRY/FX accounting, session calendars, KAP/CBRT/provider evidence, and broker-specific QA being mature first
- broader IBKR/global support is not the next expansion target unless a later decision changes the roadmap

## Phase 19: Onboarding, Docs, And Frontend System

Status: in progress.

- [x] refresh developer orientation notes and keep README links pointed at the current code-map instead of stale `docs/dev/*` paths
- [x] activate the existing `docs/` app as a Fumadocs-based local documentation site for setup, architecture, runtime, data/execution, operator surfaces, and QA
- [x] expand docs with project-state, bootstrap, and frontend-system pages without duplicating repository truth
- [x] reframe the docs entrypoint, project state, getting started, operator surfaces, and memory/review pages as an operator-first guide rather than a contributor-only manual
- [ ] expand docs with contributing and deeper reference pages without duplicating repository truth
- [ ] add feature deep dives for paper operation, broker/account truth, memory/review evidence, research sidecar, runtime modes, and evidence bundles
- [ ] add a guided `app:up` flow for macOS, Linux, and Windows that checks prerequisites, installs or repairs Python/Node/sidecar/tool dependencies, asks provider/tool ownership questions, starts app-owned services where configured, and opens the Web GUI
- [x] make first-run bootstrap ownership prompts idempotent by reusing persisted Ollama/Firecrawl/Camofox decisions, and make deferred setup summaries show concrete next actions
- [x] add explicit accelerated lifecycle commands for normal operators: `app:setup`, `app:start`, `app:stop`, `app:update`, `app:doctor`, and `app:uninstall`, with matching Make aliases; keep the existing focused scripts available for debugging
- [x] add the first read-only `app:doctor` lifecycle facade so operators can inspect setup, provider, V1 readiness, and app-owned service status without hidden installs, starts, model pulls, browser opens, or trading-daemon launches
- [x] add the first conservative `app:setup` lifecycle facade with dry-run planning by default and explicit `--core --yes` repair for only the root pnpm workspace plus root uv Python environment
- [x] add conservative `app:start` and `app:stop` lifecycle facades that default to dry-run, require explicit service selection plus `--yes`, and call only selected app-owned service commands without installs, browser fetches, model pulls, browser opens by default, or trading-daemon starts
- [x] add a scoped `app:update` lifecycle facade that defaults to dry-run and can update selected native dependency owners, then run checks/status, without browser fetches, model pulls, service starts/stops, runtime-state deletion, or trading-daemon starts
- [x] add a conservative `app:uninstall` lifecycle facade that defaults to dry-run, requires explicit removal scopes plus `--yes`, removes only generated/app-owned local artifacts, and blocks service-state cleanup while recorded service state remains
- [x] add the first guided `app:up` lifecycle orchestrator with dry-run-first planning, safe `--all` first-run composition, explicit ownership flags for optional helpers, Web GUI launch through app-owned service safeguards, and no hidden model pulls, browser fetches, provider accounts, broker config, or trading-daemon starts
- [x] persist optional Ollama/Firecrawl/Camofox ownership decisions in owner-only runtime setup state, expose them through setup-status, dashboard/Web/TUI readiness, and require persisted app-owned ownership before app:start can start model or Camofox helper services
- [ ] add a whole-app stop path that requests runtime shutdown with a bounded wait before stopping app-owned Web GUI, Camofox, and model-service helpers
- [ ] add a V1 side-application installer/check script for the local tools needed to run the full app experience: WebGUI/docs/TUI workspace deps, CrewAI Flow sidecar setup, optional Ollama/default-model setup, optional Firecrawl API/CLI readiness, optional Camofox dependency plus browser-binary setup, and clear post-install service checks
- [x] migrate optional Camofox helper setup from npm-owned commands to a pnpm-owned tool-root flow using `pnpm --dir tools/camofox-browser --ignore-workspace ...`, with browser binary fetch remaining explicit and opt-in
- [ ] keep optional helper package ownership documented and enforceable: root `pnpm-workspace.yaml` includes always-installed app packages (`webgui`, `docs`, `tui`), while `tools/camofox-browser` stays a standalone tool-root installed through explicit `pnpm --dir ... --ignore-workspace` commands until a future decision makes it a normal workspace package
- [x] define a repo-owned local tool root under `tools/` for optional runtime/development helpers: Camofox browser infrastructure, Ollama service metadata notes, Firecrawl adapter metadata notes, and explicit fallback rules to host-system tools or pure Python/JS fetchers
- [ ] extend the first `tool_roots` helper into a central tool registry/readiness contract so setup, researchd, model-service, WebGUI, QA, and docs describe the same local helper truth instead of each probing Ollama, Firecrawl, Camofox, and browser tooling independently
- [x] add a first setup-status and macOS bootstrap script foundation that detects core tools, optional Ollama/Firecrawl/Camofox/RuFlo readiness, and the `agentic-trader` PATH entrypoint without hidden installs
- [x] keep bootstrap provider-aware so users can skip or replace the default Ollama/model path without hidden behavior
- [ ] split oversized runtime/CLI/helper files incrementally into domain modules, constants, render helpers, and service helpers so V1 remains inspectable as a product codebase rather than a single-developer script pile
- [ ] continue splitting the Web GUI control room into screen-scoped style modules so `webgui/src/components/control-room.tsx` stays a small state/render coordinator
- [x] extract the first Web GUI control-room typed view-model, locale/loading hooks, action request helpers, shared formatting helpers, and diagnostics/context evidence helpers so the facade can keep shrinking without changing runtime contracts
- [x] extract the first Web GUI control-room primitives and copy catalog so shared panel/list/JSON rendering and shell/overview labels no longer live inside the monolithic control-room component
- [x] split the Web GUI control room into per-view modules plus dedicated shell chrome, dashboard polling, runtime/proposal/tool/chat/instruction actions, request/auth helpers, shared primitives, and a typed English/Turkish copy catalog, leaving `control-room.tsx` as the state/render coordinator
- [x] move the main Web GUI control-room view copy for runtime, portfolio, proposal desk, review, memory, chat, and settings into the typed English/Turkish catalog so new view work has one localization boundary
- [ ] make project-wide modularity measurable before the next broad refactor: add a reporting-only audit for oversized modules, long functions, repeated helper patterns, docs locale parity, and hardcoded UI string candidates in CLI/Rich/Ink/Web/docs surfaces
- [ ] promote the Python UI text catalog from a small compatibility seam into a terminal-locale contract: `AGENTIC_TRADER_UI_LOCALE`, a CLI override, a locale command, and dashboard locale metadata should drive CLI, Rich, and Ink copy without changing JSON contract keys
- [ ] split the Python CLI incrementally so `agentic_trader/cli.py` remains a Typer registration facade while dashboard payloads, runtime rendering, finance/proposal rendering, shared options, and command helpers live in focused modules with targeted tests
- [ ] split the Rich TUI incrementally into terminal UI modules for menu, monitor, runtime, portfolio, preferences, copy, and table rendering while preserving the existing entrypoint and smoke behavior
- [ ] split the Ink TUI entrypoint into `tui/src/` copy, state, command, formatting, component, and view modules so `tui/index.mjs` becomes a thin launcher rather than the long-lived owner of every surface
- [ ] finish the WebGUI/docs i18n cleanup by moving remaining fallback labels, inline locale ternaries, and control-room global styles into screen-scoped modules and typed copy/content boundaries
- [x] investigate why `CHANGELOG.md` only received the `v0.12.5` heading: prerelease `v0.12.5-beta.*` tags on the merged feature branch consumed release-history entries before the stable main release, so the stable workflow now backfills an empty stable section from the previous stable tag while ignoring prerelease tags
- [ ] preserve the current shared shadcn preset baseline from `pnpm dlx shadcn@latest init --preset b2CQzAxv8 --template next` across both `docs/` and `webgui/`, using a local-first monospace typography stack without build-time Google Fonts fetches
- [ ] migrate `webgui` incrementally from legacy global shell classes toward shadcn primitives and Tailwind v4 token composition
- [x] resolve the current `webgui` `next dev` multi-lockfile/Turbopack Tailwind issue so local interactive frontend work matches the green lint/build path
      Notes:
- `docs/` and `webgui/` should stay visually related, but neither should become a second runtime or a cross-app shared-package experiment before the surfaces stabilize
- the docs app should stay curated and source-linked rather than mirroring whole repository files blindly
- operator-facing docs should distinguish trading memory/review evidence from contributor `.ai` notes, and should explain V1 paper/live/broker boundaries before package ownership details
- the docs landing page now presents an operator guide first, with developer/contributor details as secondary context
- `webgui` dev mode now runs on `localhost:3210` with Watchpack polling so browser QA matches the README and avoids file-watch noise in this worktree
- app-managed Ollama and bootstrap work should plug into the existing daemon/log/status surfaces rather than inventing separate setup helpers with hidden runtime state
- the first bootstrap slice is intentionally explicit: `make bootstrap` prompts before system installs, `agentic-trader setup-status` is read-only, Firecrawl auth remains user-owned, Camofox install is opt-in because it may download a browser binary, and the secure Camofox wrapper requires `CAMOFOX_ACCESS_KEY`
- `agentic-trader setup-status` now includes model-service and WebGUI-service readiness, and the bootstrap script can offer PATH symlink repair when `agentic-trader` resolves to a stale checkout
- `pnpm run app:doctor` is the first lifecycle slice: it resolves the existing `agentic-trader` entrypoint without invoking uv sync, then reads setup-status, model-service, Camofox-service, WebGUI-service, provider diagnostics, and network-light V1 readiness; mutating lifecycle commands remain future slices
- `pnpm run app:setup -- --dry-run` now previews the setup lifecycle without mutation; `pnpm run app:setup -- --core --yes` intentionally runs only root Node workspace setup plus root uv Python sync, while sidecars, Camofox browser fetches, model pulls, app-owned service starts, and Web GUI launch remain deferred to later opt-in slices
- `pnpm run app:start` and `pnpm run app:stop` now provide the first selected-service lifecycle layer: dry-run by default, `--webgui`/`--model-service`/`--camofox-service`/`--all` plus `--yes` before mutation, `webgui-service start --no-open-browser` by default, and all ownership safety delegated to the existing service surfaces
- `pnpm run app:update` now provides the first scoped update lane: dry-run by default, `--core`/`--sidecar`/`--camofox`/`--build`/`--status`/`--all` plus `--yes` before mutation, with root pnpm, root uv, sidecar uv, Camofox pnpm, build, and app:doctor steps narrated separately
- `pnpm run app:uninstall` now provides the first conservative cleanup lane: dry-run by default, `--artifacts`/`--deps`/`--service-state`/`--all` plus `--yes` before removal, preserving secrets, host services, brokerage config, global tools, and trading runtime evidence while blocking service-state deletion if recorded service state remains
- Camofox helper setup commands now use standalone `pnpm --dir tools/camofox-browser --ignore-workspace ...`; the npm lockfile was replaced by a tool-root `pnpm-lock.yaml` after install/test smoke, and browser binary fetch stays explicit
- Camofox helper setup uses `camoufox-js` as the expected Node.js Camoufox bridge/fetch CLI; bootstrap and helper docs should call this out so the package name does not look like an unrelated install
- Camofox is intentionally not listed in root `pnpm-workspace.yaml` today: it is optional helper infrastructure under `tools/`, not an always-installed app surface, and adding it to the workspace should wait until setup policy changes from explicit opt-in tool-root install to normal workspace ownership
- `agentic_trader.system.tool_roots` now provides the first central registry for optional repo tools, including status IDs, consumers, fallback order, manifest notes, and install hints for Ollama, Firecrawl, and Camofox; setup-status, model-service status, Camofox-service status, dashboard snapshot, Web overview, Ink overview, and research provider metadata consume or display this registry-backed truth, while QA/docs parity remains open
- side-application setup must be explicit and opt-in for paid/browser/provider helpers; missing optional tools should be reported as degraded readiness, not silently installed, auto-started, or treated as blockers for core paper operation
- optional tool ownership now has a persisted first contract: `app:up` can record Ollama, Firecrawl, and Camofox as host-owned, app-owned, API/key-only, or skipped; `setup-status`, dashboard, Web GUI, and TUI show the decision; model/Camofox `app:start` requires persisted app-owned ownership and must never kill host-owned processes
- the Web GUI Local Tools panel now exposes the same internal-first ownership contract: app-owned local tools can be selected from the UI, host fallback ownership can be selected explicitly, app-owned Ollama status is applied to dashboard/doctor truth, Camofox start remains access-key gated, and `openai-compatible` is the explicit adapter escape hatch for non-Ollama model endpoints
- `app:update` should be a planned dependency/source refresh lane, not a hidden install side effect: pnpm workspace updates, optional tool-root pnpm updates, root uv lock upgrades, sidecar uv lock upgrades, rebuilds, and setup/service status checks should be reported step by step
- `app:uninstall` should be explicit about deleting app-owned dependency/runtime/tool artifacts and must preserve user secrets, host services, brokerage/provider accounts, and manually managed tools unless the operator confirms a separate destructive action
- `tools/` is the intended home for optional local helper infrastructure; `sidecars/` stays for isolated runtime packages such as CrewAI Flow, and root Python/Node dependencies should not absorb browser/model/provider helper internals prematurely
- refactors should be architectural cleanup with tests, not broad rewrites: extract duplicated strings/constants, Web GUI panels/hooks, and service helpers when a touched file is already hard to audit, especially around CLI rendering, setup/service status, research provider fallbacks, proposal desk flows, and i18n-ready operator text
