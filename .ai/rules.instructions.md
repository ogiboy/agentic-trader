# Working Rules

## General

- Read before editing
- Keep changes focused
- Prefer modifying existing flows over introducing parallel systems
- Use existing naming and module boundaries where possible
- Treat modularity as an ownership contract, not file-count cleanup: constants,
  helpers, utilities, assets, copy, styles, fixtures, and tests should live
  near the module or surface that owns them unless a shared contract is proven
  by multiple real consumers
- Avoid anonymous project-wide static string bags; repeated operator copy must
  flow through a typed UI text/i18n seam, and repeated internal constants must
  be grouped with the component, command, provider, or service that owns the
  behavior
- External advisory tools may inform planning, diff-risk, security, test-gap,
  performance, and PR/release checks, but their generated state must not become
  project state; capture durable guidance in `.ai/workflows/`, `.ai/playbooks/`,
  `.ai/helpers/`, `.ai/skills/`, or `.ai/agents/`

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
- If a change affects retrieval or memory injection, document it in `.ai/decisions.instructions.md`

## UI Rules

- CLI, monitor, and TUI should expose the same truth from the runtime
- Do not invent UI-only logic that diverges from backend contracts
- UI copy should be consumed through a small translation accessor such as
  `t("namespace.key")` or the Python equivalent instead of importing large
  label/copy objects into every component or command surface
- React component files should be named clearly as components, normally with
  PascalCase filenames, while hooks, utilities, styles, constants, and copy
  modules should use names that make their role unambiguous

## Implementation Rules

- Prefer schema-first changes
- Prefer typed data flow
- Preserve clear failure modes
- Add or update tests when behavior changes materially
- Commit coherent slices freely, but push only after the touched module/surface
  is in a complete, reviewable state unless a user explicitly asks for an
  earlier checkpoint push
- After pushing, continue useful local work instead of idling for CI; check CI
  and SonarCloud on the next natural validation interval or roughly five
  minutes later, then include fixes in the next module-complete push
