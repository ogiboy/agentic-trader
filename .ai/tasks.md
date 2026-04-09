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

### 4. Per-Trade Context Persistence

The first persisted trade-context layer now exists. Keep building it into a richer review surface.

Desired direction:

- market snapshot summary
- retrieved memory summary
- routed model identity
- specialist disagreements
- manager rationale
- guard rejection reason
- surface trade context cleanly in both CLI and Ink review flows

### 5. CLI / TUI / Runtime Contract Consistency

Keep all operator surfaces aligned with the same underlying runtime and status truth.

### 6. Future External Provider Readiness

Prepare for future support of remote providers without making the project cloud-first.

Requirements:

- provider adapters
- explicit configuration
- diagnostic-only failure behavior
- no hidden fallback trade generation
