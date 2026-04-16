# Current State

## Current Identity

The repository is already beyond an initial scaffold.
It has a meaningful local-first agent runtime, memory injection, role-based routing, operator chat, replay, and TUI surfaces.

## Known System Shape

Implemented or substantially present:

- strict runtime and launcher surfaces
- one-shot and continuous modes
- background runtime support
- provider adapter foundation with Ollama behind a provider boundary
- specialist + manager graph
- specialist consensus before manager execution
- execution guard
- DuckDB-backed paper broker
- operator preferences and curated behavior presets
- operator tone, strictness, and intervention presets across TUI and instruction parsing
- hybrid heuristic + vector-style similar-run retrieval
- shared memory bus across agent stages
- downside-aware confidence calibration from historical results
- memory explorer and retrieval inspection surfaces
- backtest and replay surfaces
- control room / monitor / TUI surfaces
- derived agent-activity summaries across the control-room surfaces
- daemon supervision metadata including launch counts, restart counts, terminal states, and stdout or stderr log tails
- operator chat and safe instruction parsing
- Ink chat now includes side-by-side live agent activity and reasoning/tool context instead of a transcript-only view
- a local observer API can now expose runtime contracts over HTTP for future WebUI attach flows
- tool-driven news context surfaces
- operator chat history persisted separately from trading memory
- trade-level context persistence for memory/tool/model/rationale inspection
- explicit memory write policy for trade memory versus chat memory domains
- broker adapter boundary with paper backend, safe live gating, and execution kill-switch semantics
- QA workflow docs now define product-specific checklist, runbook, scenarios, and evidence conventions for CLI, Rich, Ink, daemon, observer API, memory, governance, and paper broker validation
- a terminal smoke harness now captures timestamped evidence for the installed CLI, primary Ink entrypoint, root launcher, Rich menu, deeper Rich submenu navigation, read-only JSON surfaces, optional one-cycle runtime checks, optional quality gates, coverage XML, and SonarQube submission
- pyright is now configured as a first-class static check for repository source, tests, and QA scripts
- recurring operator-facing labels and prompts now flow through a lightweight shared UI text catalog, giving future CLI, Rich, Ink, and WebUI localization a safer boundary
- a first Market Context Pack is generated from the fetched lookback window and persisted with snapshots, run artifacts, trade context, dashboard payloads, observer API payloads, and Ink review surfaces
- Market Context Pack generation now fails closed before operation/runtime agent execution when the fetched data materially under-covers the requested lookback
- a first runtime mode contract exists; `training`/`operation` mode now flows through settings, service-state persistence/migration, status JSON, dashboard snapshots, observer API payloads, Rich status tables, and Ink overview/runtime pages
- Operation mode now requires strict LLM gating and provider/model readiness before any one-shot, launch, or service runtime can execute; Training mode can use diagnostic fallback only inside backtest/evaluation paths
- Market snapshots now carry `as_of`, and backtest reports persist data-window plus first/last decision timestamps so replay decisions can be audited for future-data leakage
- `runtime-mode-checklist` now surfaces a schema-backed transition plan; mode changes remain explicit configuration actions and cannot be silently applied through chat/free-form instruction parsing
- memory vectors now persist embedding provider, model, version, and dimensionality metadata beside the existing lightweight local-hashing vectors, and legacy rows migrate with local-hashing defaults
- SonarQube MCP is connected for project `agentic-trader-dev`; the latest QA pass reports zero bugs, zero vulnerabilities, 8 open code smells, 46.7% overall coverage, and a Quality Gate blocked primarily by coverage and remaining complexity refactors

New production-expansion direction:

- the main operator-trust gap is no longer the absence of a lookback artifact; the next gap is adding provider-specific QA around the new fail-closed context-pack semantics
- market snapshots now carry a structured multi-horizon context pack, and Training/Operation visibility, behavior-specific gates, as-of audit fields, and transition checklists are present
- memory is currently hybrid and inspectable, and vector metadata is now persisted; true local-first semantic embeddings and richer retrieval explanations are still planned expansions
- Training and Operation should become first-class runtime modes shown across all surfaces instead of informal workflow concepts
- QA should grow from smoke coverage into tiered terminal regression evidence with CLI JSON snapshots, pexpect scenarios, optional tmux/asciinema capture, and generated failure reports

## Current Constraints

- paper trading only
- local-first assumptions should remain primary
- memory layer is still lightweight compared with a richer future retrieval and policy layer
- lookback analysis has a first operator-verifiable fail-closed contract for operation/runtime flows; training replay can preserve growing-window undercoverage as an explicit context flag, but provider-limit edge cases still need broader QA coverage
- true semantic memory is not implemented yet; current vector-style retrieval with explicit metadata should be treated as a migration bridge, not the destination
- Training vs Operation mode is enforced for the first core boundary: Operation requires strict LLM readiness, while Training diagnostic fallback is limited to evaluation/backtest flows
- live broker adapters are not started
- external provider support should be additive and adapter-based, not invasive
- conversational surfaces must not silently mutate trading policy
- Ink TUI is the primary operator surface, but deeper feature parity, htop-like control affordances, resize-safe rendering, and visual refinement are still open
- runtime performance is currently controlled mostly through static settings; hardware-aware profiles for safe concurrency, token budgets, model routing, and memory use are a planned next step
- DB-backed review surfaces may intentionally fall back to observer mode while the runtime writer is active
- background runtime supervision now has a sidecar-friendly status and log contract that UI surfaces can read without competing for the writer connection
- behavior-changing work should use the QA docs when it affects operator surfaces or runtime behavior
- Sonar Quality Gate currently requires higher new-code coverage than the repository has; keep adding focused tests before treating the gate as fully green
- full multi-language support is intentionally deferred until operator flows stabilize; new repeated UI strings should be added to the shared catalog rather than duplicated per surface

## Current Development Posture

The codebase should be treated as:

- active
- modular
- already opinionated
- ready for targeted extension, not a rewrite
- dependent on keeping `.ai/current-state.md`, `.ai/tasks.md`, and `.ai/decisions.md` in sync with meaningful architecture changes
