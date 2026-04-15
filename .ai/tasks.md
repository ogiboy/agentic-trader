# Active Tasks

## How To Use This File

- Keep this file short
- Only list currently relevant tasks
- Move completed decisions into `.ai/decisions.md`
- Update when the development focus changes

## Current Suggested Focus

### 1. Market Context Pack And Lookback Truth

Make the configured `lookback` window visible, persisted, and reviewable.

Desired shape:

- add a deterministic Market Context Pack generated from the full lookback window
- include multi-horizon returns, volatility, drawdown, trend alignment, range structure, data sufficiency, and anomaly flags
- expose expected bars, analyzed bars, window coverage, cache provenance, and interval semantics
- persist the pack per run and per trade context
- surface the pack through dashboard snapshots, traces, run review, observer API, Rich menu, and Ink control room
- add QA coverage that proves lookback fields are present and coherent

### 2. Training And Operation Modes

Make runtime intent explicit instead of relying on informal workflow naming.

Desired shape:

- add `training` and `operation` mode to settings, service state, run records, dashboard payloads, and observer contracts
- show a mode banner across CLI, Rich, Ink, monitor, and future WebUI
- Operation mode should hard-block unsafe fallbacks and require strict model/provider readiness
- Training mode should enable replay, walk-forward, ablation, and diagnostic evaluation without hidden trade generation
- mode changes should flow through approved schemas, not free-form chat side effects

### 3. Semantic Memory And Retrieval Quality

Build on the current lightweight retrieval layer instead of replacing it.

Desired direction:

- replace hashed-token pseudo-embeddings with true local-first semantic embeddings behind a provider seam
- store embedding model metadata and keep migration compatibility
- rank retrieval by semantic similarity, regime similarity, freshness, outcome weighting, and diversity
- persist stage-level retrieval explanations so operators can see why specific memories were used
- preserve trade-memory versus chat-memory write policies

### 4. Terminal Regression QA And Evidence Bundles

Turn the existing smoke harness into a broader product-surface regression tool.

Desired direction:

- keep the fast smoke path lightweight
- map `.ai/qa/qa-scenarios.md` to deterministic pexpect flows
- use fixed terminal size and stable artifact naming
- capture JSON snapshots, service events, broker state, context-pack excerpts, keypress transcripts, and generated failure reports
- add optional tmux pane dumps and asciinema recordings for visual TUI regressions
- keep quality gates tiered so CI-safe checks, local interactive checks, and manual visual evidence can run separately

### 5. Daemon And Operator Surface Refinement

Keep the background runtime and the Ink control room aligned and more operationally complete.

Desired shape:

- stronger daemon supervision readiness
- richer daemon supervision metadata such as launch counts, restart counts, terminal states, and log-tail visibility
- richer Ink control-room parity with existing CLI and review surfaces
- cleaner runtime attach / restart / stop workflows
- clearer live visibility into stage progress, context-pack usage, model calls, tool usage, safety gates, and runtime outcomes
- observer-safe review and memory surfaces while the writer owns DuckDB
- use `.ai/qa/qa-scenarios.md` for manual validation of daemon, monitor, and control-room changes

### 6. Provider Adapter Foundation

The first provider boundary now exists. Continue from that adapter seam so future providers stay additive.

Desired shape:

- keep Ollama as the default local-first provider
- allow future providers behind a common interface
- preserve role-based model routing
- keep strict runtime gating explicit per provider
- add more provider-aware diagnostics before introducing a second provider

### 7. Operator Surface Depth

Build on the new preset layer so the operator surface feels complete, not just inspectable.

Desired direction:

- carry tone, strictness, and intervention presets consistently across CLI, Rich, Ink, and operator chat
- deepen the new structured agent activity and reasoning context beside chat transcripts
- keep the Ink control room moving toward full parity with the older Rich admin surface

### 8. Per-Trade Context Persistence

The first persisted trade-context layer now exists. Keep building it into a richer review surface.

Desired direction:

- market snapshot summary
- Market Context Pack summary
- retrieved memory summary
- routed model identity
- specialist disagreements
- manager rationale
- guard rejection reason
- surface trade context cleanly in both CLI and Ink review flows

### 9. CLI / TUI / Runtime Contract Consistency

Keep all operator surfaces aligned with the same underlying runtime and status truth.

Desired direction:

- reuse the shared UI text catalog for recurring CLI, Rich, Ink, and future WebUI labels
- defer full localization until operator flows stabilize, but avoid adding new scattered duplicate labels
- keep pyright, ruff, pytest, and smoke QA green as surface contracts evolve

### 10. Future External Provider Readiness

Prepare for future support of remote providers without making the project cloud-first.

Requirements:

- provider adapters
- explicit configuration
- diagnostic-only failure behavior
- no hidden fallback trade generation

### 11. Live Adapter Readiness

The broker boundary now exists. Keep live execution preparation explicit and guarded.

Desired direction:

- preserve paper as the default execution backend
- keep live execution blocked unless explicitly enabled and implemented
- surface broker backend, kill-switch, and readiness state in every operator surface
- add one real live adapter only after paper evaluation quality is stable

### 12. Observer API And WebUI Readiness

The first local observer API now exists. Keep it small, read-only, and aligned with the dashboard contract.

Desired direction:

- expose the same runtime truths to future WebUI clients without duplicating orchestration logic
- keep observer endpoints local-first and read-only
- reuse dashboard/status/log/broker contracts across Ink, CLI, and future web surfaces
- avoid introducing a second runtime state system for web consumers

### 13. Quality Workflow

The QA docs now exist and should stay in sync with the product.

Desired direction:

- keep QA scenarios aligned with actual CLI/TUI/runtime commands
- use `python scripts/qa/smoke_qa.py` for a fast terminal smoke pass before deeper manual QA
- use `python scripts/qa/smoke_qa.py --include-quality` when code-quality checks should travel with terminal smoke evidence
- use `python scripts/qa/smoke_qa.py --include-quality --include-sonar` for the full local QA gate; this now emits coverage XML and submits it to SonarQube without writing the token to artifacts
- add a scenario whenever a new operator-facing surface or safety gate is introduced
- add lookback/context-pack and Training/Operation mode scenarios before treating production-like paper operation as stable
- use QA evidence under `.ai/qa/artifacts/` for reproducible UI/runtime issues
- keep the automated test command in `AGENTS.md` current with the project environment
- next coverage priority: add focused tests around storage service-state transitions, Rich menu branches, and Ink/Rich runtime-control paths so Sonar new-code coverage can approach the 80% gate
- next Sonar cleanup priority: reduce remaining complexity in `agentic_trader/tui.py`, `agentic_trader/workflows/service.py`, `agentic_trader/backtest/walk_forward.py`, and service-state persistence
