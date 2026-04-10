# Active Tasks

## How To Use This File

- Keep this file short
- Only list currently relevant tasks
- Move completed decisions into `.ai/decisions.md`
- Update when the development focus changes

## Current Suggested Focus

### 1. Daemon And Operator Surface Refinement

Keep the background runtime and the Ink control room aligned and more operationally complete.

Desired shape:

- stronger daemon supervision readiness
- richer daemon supervision metadata such as launch counts, restart counts, terminal states, and log-tail visibility
- richer Ink control-room parity with existing CLI and review surfaces
- cleaner runtime attach / restart / stop workflows
- clearer live visibility into stage progress and runtime outcomes
- observer-safe review and memory surfaces while the writer owns DuckDB
- use `.ai/qa/qa-scenarios.md` for manual validation of daemon, monitor, and control-room changes

### 2. Provider Adapter Foundation

The first provider boundary now exists. Continue from that adapter seam so future providers stay additive.

Desired shape:

- keep Ollama as the default local-first provider
- allow future providers behind a common interface
- preserve role-based model routing
- keep strict runtime gating explicit per provider
- add more provider-aware diagnostics before introducing a second provider

### 3. Memory Layer Expansion

Build on the current lightweight retrieval layer instead of replacing it.

Desired direction:

- richer retrieval summaries
- memory write policy controls per role
- stronger inspection and replay support
- better persistence of what context each stage actually received
- keep memory-policy visibility aligned across CLI and Ink surfaces

### 4. Operator Surface Depth

Build on the new preset layer so the operator surface feels complete, not just inspectable.

Desired direction:

- carry tone, strictness, and intervention presets consistently across CLI, Rich, Ink, and operator chat
- deepen the new structured agent activity and reasoning context beside chat transcripts
- keep the Ink control room moving toward full parity with the older Rich admin surface

### 5. Per-Trade Context Persistence

The first persisted trade-context layer now exists. Keep building it into a richer review surface.

Desired direction:

- market snapshot summary
- retrieved memory summary
- routed model identity
- specialist disagreements
- manager rationale
- guard rejection reason
- surface trade context cleanly in both CLI and Ink review flows

### 6. CLI / TUI / Runtime Contract Consistency

Keep all operator surfaces aligned with the same underlying runtime and status truth.

### 7. Future External Provider Readiness

Prepare for future support of remote providers without making the project cloud-first.

Requirements:

- provider adapters
- explicit configuration
- diagnostic-only failure behavior
- no hidden fallback trade generation

### 8. Live Adapter Readiness

The broker boundary now exists. Keep live execution preparation explicit and guarded.

Desired direction:

- preserve paper as the default execution backend
- keep live execution blocked unless explicitly enabled and implemented
- surface broker backend, kill-switch, and readiness state in every operator surface
- add one real live adapter only after paper evaluation quality is stable

### 9. Observer API And WebUI Readiness

The first local observer API now exists. Keep it small, read-only, and aligned with the dashboard contract.

Desired direction:

- expose the same runtime truths to future WebUI clients without duplicating orchestration logic
- keep observer endpoints local-first and read-only
- reuse dashboard/status/log/broker contracts across Ink, CLI, and future web surfaces
- avoid introducing a second runtime state system for web consumers

### 10. Quality Workflow

The QA docs now exist and should stay in sync with the product.

Desired direction:

- keep QA scenarios aligned with actual CLI/TUI/runtime commands
- add a scenario whenever a new operator-facing surface or safety gate is introduced
- use QA evidence under `.ai/qa/artifacts/` for reproducible UI/runtime issues
- keep the automated test command in `AGENTS.md` current with the project environment
