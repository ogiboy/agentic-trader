# Active Tasks

## How To Use This File

- Keep this file short
- Only list currently relevant tasks
- Move completed decisions into `.ai/decisions.md`
- Update when the development focus changes

## Current Suggested Focus

### 1. Financial Intelligence Layer

Move the system from compact price-only reasoning toward structured multi-source decision context.

Current state:

- `DecisionFeatureBundle` now carries symbol identity, technical features, fundamental feature placeholders, and macro/news context
- deterministic technical summaries include 30d, 90d, and 180d returns, volatility, drawdown, support/resistance, trend classification, and momentum indicators
- provider contracts now cover market, fundamental, news, disclosure, and macro sources with canonical source attribution and freshness metadata
- explicit SEC EDGAR, Finnhub, FMP, and KAP scaffold providers now feed canonical attribution while marking missing fields instead of pretending live ingestion exists
- source scaffold metadata now names SEC 10-K/10-Q/8-K, earnings transcripts, macro indicators, KAP, Turkey company disclosures, CBRT-style macro data, inflation, and FX readiness without pretending those ingestors are implemented
- fundamental and macro/news analyst stages now run before regime, strategy, risk, and manager synthesis
- consensus excludes fallback-generated fundamental and macro/news assessments from support, keeping unavailable finance evidence visible without overstating alignment
- fundamental assessment output now separates direct evidence, inference, and uncertainty across growth, profitability, cash flow, balance sheet, FX, business quality, macro fit, and forward outlook
- feature-first prompts now expose the underlying fundamental metrics, and Ink review/trade-context surfaces show fundamental bias, red flags, evidence, inference, and uncertainty
- trade context and memory documents now persist canonical analysis snapshots, decision features, and fundamental/macro summaries
- Finnhub, FMP, Polygon/Massive, SEC, KAP, CBRT, macro indicators, FX, and transcript ingestion remain provider-level future work

Next desired shape:

- implement real provider-backed fundamental fetchers behind the canonical provider interfaces without placing secrets in tracked files or QA artifacts
- add structured SEC, transcript, insider, macro, KAP, CBRT, inflation, and FX ingestion
- keep Yahoo as a degraded fallback only once richer market/news providers are available
- surface technical/fundamental/macro/memory/guard evidence side by side in operator review surfaces
- strengthen risk with volatility sizing, sector concentration, portfolio exposure, and macro override checks

### 2. Market Context Pack And Lookback Truth

Make the configured `lookback` window visible, persisted, and reviewable.

Current state:

- first deterministic Market Context Pack exists
- multi-horizon returns, volatility, drawdown, trend votes, range structure, data quality flags, and anomaly flags are computed
- expected bars, analyzed bars, coverage, interval semantics, and window bounds are persisted
- dashboard snapshot, observer API, trade context, run artifacts, memory documents, agent prompts, and Ink review surfaces can now see the pack
- materially under-covered operation/runtime lookback windows now fail closed before agents are invoked
- Training replay can intentionally keep growing-window undercoverage as a context-pack data quality flag

Next desired shape:

- add provider-specific QA cases for partial yfinance windows, intraday provider limits, non-datetime indexes, and higher-timeframe fallbacks
- add compact context-pack rendering to any remaining Rich/admin paths that do not already show the raw persisted run artifact
- connect future Training/Operation mode to context-pack verbosity and bar excerpt rules

### 3. Training And Operation Modes

Make runtime intent explicit instead of relying on informal workflow naming.

Current state:

- `training` and `operation` mode now exist in settings and service-state persistence
- service-state migration preserves legacy rows with an `operation` default
- status JSON, dashboard snapshots, observer API payloads, Rich status tables, and Ink overview/runtime pages expose the mode
- Operation mode hard-blocks disabled strict LLM gating and still requires provider/model readiness for one-shot, launch, and service execution
- Training mode can use diagnostic fallback only inside backtest/evaluation flows such as walk-forward, baseline comparison, and memory ablation
- Market snapshots carry `as_of`, and backtest reports persist data-window plus first/last decision timestamps
- `runtime-mode-checklist` emits a schema-backed transition plan and keeps mode changes out of chat/free-form side effects

Next desired shape:

- add QA smoke coverage for `runtime-mode-checklist` so CLI, Ink, and future WebUI consumers can rely on the transition contract
- decide whether runtime mode should remain env-only or gain an explicit persisted operator profile after the checklist stabilizes

### 4. Semantic Memory And Retrieval Quality

Build on the current lightweight retrieval layer instead of replacing it.

Current state:

- memory vectors persist provider, model, version, and dimensionality metadata for migration compatibility
- legacy memory-vector rows without metadata columns are migrated in place with local-hashing defaults
- the active embedding scheme is still local-first hashed-token pseudo-embedding

Desired direction:

- replace hashed-token pseudo-embeddings with true local-first semantic embeddings behind a provider seam
- keep backwards compatibility with existing lightweight vectors during migration
- rank retrieval by semantic similarity, regime similarity, freshness, outcome weighting, and diversity
- persist stage-level retrieval explanations so operators can see why specific memories were used
- preserve trade-memory versus chat-memory write policies

### 5. Terminal Regression QA And Evidence Bundles

Turn the existing smoke harness into a broader product-surface regression tool.

Desired direction:

- keep the fast smoke path lightweight
- map `.ai/qa/qa-scenarios.md` to deterministic pexpect flows
- use fixed terminal size and stable artifact naming
- capture JSON snapshots, service events, broker state, context-pack excerpts, keypress transcripts, and generated failure reports
- fail smoke evidence when raw provider output or LLM retry diagnostics leak into operator-facing terminal output
- keep the one-cycle runtime check as an explicit opt-in tier because it needs live market data and a healthy local model
- add optional tmux pane dumps and asciinema recordings for visual TUI regressions
- keep a tmux-driven compact-terminal Ink settings navigation check in smoke QA so Rich/TUI parity does not silently regress
- when Computer Use is available, add a real-screen QA pass alongside text artifacts instead of treating screenshots as out of scope
- keep smoke artifact directories unique even when parallel QA runs start in the same second
- keep quality gates tiered so CI-safe checks, local interactive checks, and manual visual evidence can run separately

### 6. Daemon And Operator Surface Refinement

Keep the background runtime and the Ink control room aligned and more operationally complete.

Desired shape:

- stronger daemon supervision readiness
- hardware-aware runtime performance profiles for safe agent concurrency, token budgets, request timeouts, and memory use
- a local capability probe that can recommend lightweight, balanced, or high-throughput profiles from CPU/RAM/GPU/model details
- richer daemon supervision metadata such as launch counts, restart counts, terminal states, and log-tail visibility
- richer Ink control-room parity with existing CLI and review surfaces
- htop-like Ink layout with stable panes, keyboard controls, resize-safe rendering, and less scrollback churn
- quieter Rich/admin fallback with fewer always-on panels and clearer drill-down pages
- cleaner runtime attach / restart / stop workflows
- clearer live visibility into stage progress, context-pack usage, model calls, tool usage, safety gates, and runtime outcomes
- observer-safe review and memory surfaces while the writer owns DuckDB
- use `.ai/qa/qa-scenarios.md` for manual validation of daemon, monitor, and control-room changes

### 7. Provider Adapter Foundation

The first provider boundary now exists. Continue from that adapter seam so future providers stay additive.

Desired shape:

- keep Ollama as the default local-first provider
- allow future providers behind a common interface
- preserve role-based model routing
- keep strict runtime gating explicit per provider
- add more provider-aware diagnostics before introducing a second provider

### 8. Operator Surface Depth

Build on the new preset layer so the operator surface feels complete, not just inspectable.

Desired direction:

- carry tone, strictness, and intervention presets consistently across CLI, Rich, Ink, and operator chat
- deepen the new structured agent activity and reasoning context beside chat transcripts
- keep the Ink control room moving toward full parity with the older Rich admin surface
- preserve the new Settings-page parity for preferences, recent runs, one-shot control, and safe instruction editing as terminals shrink
- run designer-style visual audits with pexpect/tmux/asciinema first, and add Computer Use screenshots when visual evidence is necessary or text captures are insufficient
- define an indirect terminal-visual review path that cross-checks tmux/asciinema captures with dashboard, broker, and observer JSON when a direct terminal session is not available
- run a CLI ergonomics audit for `--help`, `-h`, command examples, option naming, and short/long flag consistency
- simplify Rich menu navigation so back, close, cancel, and exit behaviors are consistent and the repeated logo/header does not dominate every output
- add a finance/accounting readability pass for cash, equity, PnL, exposure, positions, currency, backend, adapter, runtime mode, and rejection reason labels
- turn UX findings into smallest-safe repair recommendations, classified as V1 blocker, V1 polish, or V2 redesign before implementation

### 9. Per-Trade Context Persistence

The first persisted trade-context layer now exists. Keep building it into a richer review surface.

Desired direction:

- market snapshot summary
- Market Context Pack summary
- decision feature bundle
- fundamental and macro summaries
- retrieved memory summary
- routed model identity
- specialist disagreements
- manager rationale
- guard rejection reason
- surface trade context cleanly in both CLI and Ink review flows

### 10. CLI / TUI / Runtime Contract Consistency

Keep all operator surfaces aligned with the same underlying runtime and status truth.

Desired direction:

- reuse the shared UI text catalog for recurring CLI, Rich, Ink, and future WebUI labels
- defer full localization until operator flows stabilize, but avoid adding new scattered duplicate labels
- keep pyright, ruff, pytest, and smoke QA green as surface contracts evolve
- keep `pyproject.toml` and `poetry.lock` in sync when Python dependencies change; use Poetry for add/remove/lock operations rather than ad hoc pip installs

### 11. Future External Provider Readiness

Prepare for future support of remote providers without making the project cloud-first.

Requirements:

- provider adapters
- explicit configuration
- diagnostic-only failure behavior
- no hidden fallback trade generation

### 12. Live Adapter Readiness

The broker boundary now exists. Keep live execution preparation explicit and guarded.

Current state:

- guard output is translated into a canonical timestamped `ExecutionIntent` before broker submission
- broker adapters return an `ExecutionOutcome` with status, backend, adapter, rejection reason, and simulated metadata
- paper remains the default backend and now conforms to the intent/outcome adapter path
- `simulated_real` exists as a non-live scaffold for local rehearsal; it must not be treated as live trading
- live remains blocked unless a real adapter and explicit enablement are added later

Desired direction:

- preserve paper as the default execution backend
- keep live execution blocked unless explicitly enabled and implemented
- keep V1 focused on Alpaca-ready US equities with manual approval and strict safety checks; do not pull IBKR/global/FX work into V1
- defer IBKR, global markets, and multi-currency/FX execution accounting to V2
- surface broker backend, execution outcome, rejection reason, kill-switch, and readiness state in operator review/status surfaces
- add one real live adapter only after paper evaluation quality is stable

### 13. Observer API And WebUI Readiness

The first local observer API now exists. Keep it small, read-only, and aligned with the dashboard contract.

Desired direction:

- expose the same runtime truths to future WebUI clients without duplicating orchestration logic
- keep observer endpoints local-first and read-only
- reuse dashboard/status/log/broker contracts across Ink, CLI, and future web surfaces
- avoid introducing a second runtime state system for web consumers

### 14. Quality Workflow

The QA docs now exist and should stay in sync with the product.

Desired direction:

- keep QA scenarios aligned with actual CLI/TUI/runtime commands
- use `python scripts/qa/smoke_qa.py` for a fast terminal smoke pass before deeper manual QA
- use `python scripts/qa/smoke_qa.py --include-quality` when code-quality checks should travel with terminal smoke evidence
- use `python scripts/qa/smoke_qa.py --include-quality --include-sonar` for the full local QA gate; this now emits coverage XML and submits it to SonarQube without writing the token to artifacts
- add a scenario whenever a new operator-facing surface or safety gate is introduced
- add lookback/context-pack and Training/Operation mode scenarios before treating production-like paper operation as stable
- keep the dashboard contract smoke check aligned with new runtime mode and market context fields consumed by Ink, Rich, CLI, and future WebUI surfaces
- use QA evidence under `.ai/qa/artifacts/` for reproducible UI/runtime issues
- use pexpect, tmux, asciinema, pane captures, and JSON/text artifacts as the primary CLI/Rich/Ink validation path, and add a Computer Use visual pass whenever the environment exposes it and layout/operator clarity is in scope
- keep `.ai/agents/` role guidance aligned with `AGENTS.md`, `.ai/qa/`, and current architecture so development agents remain helpers rather than runtime dependencies
- keep the automated test command in `AGENTS.md` current with the project environment
- keep the opt-in runtime-cycle smoke check aligned with real product retry behavior so it validates operator-facing runtime reliability rather than a first-response-only LLM diagnostic
- next coverage priority: add focused tests around storage service-state transitions, Rich menu branches, and Ink/Rich runtime-control paths so Sonar new-code coverage can approach the 80% gate
- next Sonar cleanup priority: rerun analysis after the complexity cleanup, then address any remaining code smells or security hotspots that Sonar still reports
