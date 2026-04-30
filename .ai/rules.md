# Working Rules

## General

- Read before editing
- Keep changes focused
- Prefer modifying existing flows over introducing parallel systems
- Use existing naming and module boundaries where possible

## Runtime Rules

- Never silently bypass strict LLM runtime gating
- Never allow silent trade generation when the runtime should be diagnostic-only
- Keep operator-visible status accurate
- Keep paper-trading behavior safe and conservative
- Sidecars must not submit orders, mutate policy, overwrite runtime service state, or hide missing/fallback provider data

## Agent Rules

- Preserve the staged specialist graph unless the task explicitly changes it
- Keep specialist roles distinct
- Keep manager and guard responsibilities explicit
- Do not blur conversational behavior with execution policy
- Keep financial intelligence schema-first: agents should consume structured feature bundles, not raw noisy provider text

## Storage Rules

- Treat DuckDB-backed persistence as a core part of the system
- Preserve run review, trade journal, and portfolio continuity
- Prefer additive schema changes over destructive rewrites

## Memory Rules

- Treat memory as execution-supporting context, not as uncontrolled hidden behavior
- Keep conversational memory separate from trading memory
- If a change affects retrieval or memory injection, document it in `.ai/decisions.md`

## UI Rules

- CLI, monitor, and TUI should expose the same truth from the runtime
- Do not invent UI-only logic that diverges from backend contracts

## Implementation Rules

- Prefer schema-first changes
- Prefer typed data flow
- Preserve clear failure modes
- Add or update tests when behavior changes materially
