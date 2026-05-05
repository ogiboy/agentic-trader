# Feature Workflow

Use this for runtime, CLI, TUI, WebGUI, docs, sidecar, broker, memory, provider,
or operator-surface changes.

## Inputs

- User request and newest clarification.
- Branch, dirty worktree, and target PR base.
- Relevant `.ai/agents/` role docs.
- Smallest source module surface that owns the behavior.

## Sequence

1. Scope the change in one paragraph: user outcome, affected surfaces, and
   boundaries.
2. Identify the owning contracts instead of inventing a parallel path.
3. Split work into phases:
   - contract/schema
   - implementation
   - operator surface
   - persistence/evidence
   - tests/QA
   - docs/memory updates
4. Prefer additive migrations and explicit unavailable/degraded states.
5. Implement the smallest coherent slice.
6. Run focused tests near the touched modules.
7. Run broader checks when the change crosses module boundaries.
8. Update `.ai/current-state.md`, `.ai/tasks.md`, and `.ai/decisions.md` for
   durable assumptions.

## Advisory Commands

Run when the task is not trivial:

```bash
ruflo route task "feature: <short description>"
ruflo hooks route -t "feature: <short description>"
ruflo analyze diff --risk
```

For cross-module changes:

```bash
ruflo analyze imports agentic_trader --external
ruflo analyze circular agentic_trader
ruflo analyze boundaries agentic_trader
```

For command risk:

```bash
ruflo hooks pre-command -- "pnpm run check"
ruflo hooks pre-command -- "pnpm run qa"
```

## Required Lenses

| Change Type | Required Roles |
| --- | --- |
| Broker, account, PnL, exposure, execution | `finance-ops.md`, `data.md`, `qa.md`, `reviewer.md` |
| Provider, sidecar, research evidence | `researcher.md`, `data.md`, `security-auditor.md`, `qa.md` |
| CLI, Rich, Ink, WebGUI, docs | `operator-ux.md`, `product-docs.md`, `qa.md` |
| Memory/retrieval | `researcher.md`, `reviewer.md`, `qa.md` |
| Release/setup/CI | `release-manager.md`, `qa.md`, `reviewer.md` |

## Acceptance Criteria

- Existing paper-first and live-blocked safety remains intact.
- Training/operation mode behavior is not confused or hidden.
- Operator surfaces agree with shared contracts rather than UI guesses.
- Missing provider data is visible, not treated as neutral support.
- Tests cover the changed branch, fallback branch, and one edge case.
- Version files are bumped before product-impacting feature/V1 branch pushes.

## Implementation Plan Template

```text
Goal:
Owner contract:
Workflow:
Roles:
Files to touch:
Files to avoid:
Edge cases:
Focused tests:
Broad checks:
Version impact:
```
