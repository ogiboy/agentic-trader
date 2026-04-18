# Agent Role Pack

This folder defines role-specific working agreements for AI collaborators on
Agentic Trader. These agents are development roles only. They are not runtime
agents and must not be wired into the trading system as an external
orchestration framework.

## Shared Contract

Every role must follow the repository root `AGENTS.md` first. The existing
runtime remains the source of truth.

Required reading before role work:

- `README.md`
- `ROADMAP.md`
- `AGENTS.md`
- `.ai/profile.md`
- `.ai/rules.md`
- `.ai/architecture.md`
- `.ai/current-state.md`
- `.ai/memory.md`
- `.ai/tasks.md`
- `.ai/decisions.md`

For runtime, CLI, TUI, daemon, broker, memory, or operator-facing changes,
also read the QA documents under `.ai/qa/`.

## Role Map

- `planner.md`: shapes scoped implementation plans and separates V1 from later work.
- `implementer.md`: applies approved plans with small, tested, reviewable changes.
- `reviewer.md`: reviews diffs for safety, architecture drift, and operator truth.
- `qa.md`: validates the operator experience and records reproducible evidence.
- `data.md`: protects provider, canonical data, freshness, and attribution boundaries.

## Hand-Off Rules

- Planner output should be file-level and bounded enough for an implementer to act.
- Implementer output should list changed files, validation run, and assumptions.
- Reviewer output should lead with blockers and safety regressions before praise.
- QA output should include commands, expected behavior, actual behavior, and evidence.
- Data output should keep raw provider payloads behind canonical contracts.

## Non-Negotiables

- Paper remains the default execution backend.
- Live trading remains blocked unless intentionally implemented behind explicit gates.
- Strict runtime gating must not be weakened.
- Operator chat and instruction flows must not become hidden execution paths.
- Storage changes should be additive and replay/audit friendly.
- CLI, Rich, Ink, observer API, and storage should expose the same underlying truth.
