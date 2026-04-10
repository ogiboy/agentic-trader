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

## Current Constraints

- paper trading only
- local-first assumptions should remain primary
- memory layer is still lightweight compared with a richer future retrieval and policy layer
- live broker adapters are not started
- external provider support should be additive and adapter-based, not invasive
- conversational surfaces must not silently mutate trading policy
- Ink TUI is the primary operator surface, but deeper feature parity and refinement are still open
- DB-backed review surfaces may intentionally fall back to observer mode while the runtime writer is active
- background runtime supervision now has a sidecar-friendly status and log contract that UI surfaces can read without competing for the writer connection
- behavior-changing work should use the QA docs when it affects operator surfaces or runtime behavior

## Current Development Posture

The codebase should be treated as:

- active
- modular
- already opinionated
- ready for targeted extension, not a rewrite
- dependent on keeping `.ai/current-state.md`, `.ai/tasks.md`, and `.ai/decisions.md` in sync with meaningful architecture changes
