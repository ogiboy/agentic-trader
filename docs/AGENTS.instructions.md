# Docs App Instructions

This app is the canonical developer-docs surface for Agentic Trader. It
documents the existing local-first runtime and must not define a parallel
product architecture.

## Before Editing

Read the repository-level guidance first:

- `README.md`
- `ROADMAP.md`
- `.ai/current-state.instructions.md`
- `.ai/tasks.instructions.md`
- `.ai/decisions.instructions.md`

If any required file is missing or has been renamed, report the path, use the
closest current replacement if one is obvious, and continue with the available
repo evidence.

If the change affects operator behavior, also read these QA notes:

- `.ai/qa/qa-checklist.instructions.md`
- `.ai/qa/qa-scenarios.instructions.md`

## Guardrails

- Keep `docs/` aligned with the real Python runtime, CLI, Rich menu, Ink TUI,
  observer API, and Web GUI.
- Do not document speculative behavior as if it already exists.
- Treat `docs/` as a thin explanatory shell around the repo, not a second source of truth.
- Keep `docs/` and `webgui/` visually related, but do not invent a shared package before the surfaces stabilize.
- When behavior or workflow assumptions move, update the relevant docs page
  together with `.ai/current-state.instructions.md`, `.ai/tasks.instructions.md`,
  and `.ai/decisions.instructions.md`.

## Frontend Baseline

- Next.js App Router
- Tailwind v4 + shadcn primitives
- app-local `components/ui`
- GitHub Pages-compatible feedback flow that prepares browser-local GitHub issue drafts without server writes

## Validation

Run the smallest check that covers the changed docs surface before finishing.
Choose in this order: lint for copy/config changes, typecheck for TypeScript or
component changes, build for routing/static-export changes.

```bash
pnpm --filter docs run lint
pnpm --filter docs run typecheck
pnpm --filter docs run build
```
