# Web GUI Instructions

This app is a local command center for the existing Agentic Trader runtime.
It must stay a thin shell over the Python runtime, CLI contracts, and DuckDB-backed truth.

## Before Editing

Read:

- `README.md`
- `ROADMAP.md`
- `.ai/current-state.md`
- `.ai/tasks.md`
- `.ai/decisions.md`
- `.ai/qa/qa-checklist.md`
- `.ai/qa/qa-scenarios.md`

## Guardrails

- Do not add a second orchestration path inside `webgui/`.
- Route handlers should validate inputs, then delegate to the existing CLI/runtime contract.
- Web GUI state must agree with CLI, Rich, Ink, and observer surfaces.
- Missing data and runtime failures must stay visible; no fake success states.
- Keep changes local-first, paper-first, and V1-safe.

## Frontend Baseline

- Next.js App Router
- Tailwind v4 + shadcn primitives
- app-local components
- server-side routes calling `agentic_trader.cli`

## Validation

Run:

```bash
pnpm --filter webgui run lint
pnpm --filter webgui run typecheck
pnpm --filter webgui run build
```

When UI behavior changes, also do a browser pass against the local dev server.
