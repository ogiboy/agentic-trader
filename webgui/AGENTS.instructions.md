# Web GUI Instructions

This app is a local command center for the existing Agentic Trader runtime. It
must stay a thin shell over the Python runtime, CLI contracts, and DuckDB-backed
truth.

## Before Editing

Read:

- `README.md`
- `ROADMAP.md`
- `.ai/current-state.instructions.md`
- `.ai/tasks.instructions.md`
- `.ai/decisions.instructions.md`
- `.ai/qa/qa-checklist.instructions.md`
- `.ai/qa/qa-scenarios.instructions.md`

If any required file is missing or has been renamed, report the path, use the
closest current replacement if one is obvious, and continue with the available
repo evidence.

## Guardrails

- Do not add a second orchestration path inside `webgui/`.
- Route handlers must validate inputs before delegating to the existing
  CLI/runtime contract.
- Web GUI state must agree with CLI, Rich, Ink, and observer surfaces.
- Missing data and runtime failures must stay visible; no fake success states.
- Keep changes local-first, paper-first, and V1-safe.

## Frontend Baseline

- Next.js App Router
- Tailwind v4 + shadcn primitives
- app-local components
- server-side routes calling `agentic_trader.cli`

## Validation

Run the check that matches the changed Web GUI surface. Choose in this order:
lint for copy/config changes, typecheck for route/component contracts, build for
routing/runtime packaging changes.

```bash
pnpm --filter webgui run lint
pnpm --filter webgui run typecheck
pnpm --filter webgui run build
```

When UI behavior changes, also do a browser pass against the local dev server.
