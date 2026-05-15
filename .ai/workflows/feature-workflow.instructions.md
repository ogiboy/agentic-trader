# Feature Workflow

Use this for runtime, CLI, TUI, WebGUI, docs, sidecar, broker, memory, provider,
or operator-surface changes.

## Inputs

- User request and newest clarification.
- Branch, dirty worktree, and target PR base.
- Relevant `.ai/agents/` role docs.
- Smallest source module surface that owns the behavior.

If any input is missing, report it and continue only when the owning contract
can still be identified from source. If ownership is unclear, stop at a plan and
ask for clarification rather than creating a parallel path.

## Sequence

1. Scope the change in one paragraph: user outcome, affected surfaces, and
   boundaries.
2. Identify the owning contracts instead of inventing a parallel path.
3. Split work into these phases in order: contract/schema,
   implementation, operator surface, persistence/evidence, tests/QA, and
   docs/memory updates.
4. Prefer additive migrations and explicit unavailable/degraded states.
5. Implement the smallest coherent slice.
6. Run focused tests near the touched modules.
7. Run broader checks when the change crosses module boundaries.
8. Update `.ai/current-state.instructions.md`, `.ai/tasks.instructions.md`, and
   `.ai/decisions.instructions.md` when the change creates durable assumptions.

## Advisory Commands

Run when the task is not trivial:

```bash
ruflo route task "feature: <short description>"
ruflo hooks route -t "feature: <short description>"
ruflo analyze diff --risk
```

If RuFlo is unavailable or unstable, skip advisory commands and rely on source
inspection, targeted tests, and Codex-native review.

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

| Change Type                               | Required Roles                                                                     |
| ----------------------------------------- | ---------------------------------------------------------------------------------- |
| Broker, account, PnL, exposure, execution | `finance-ops.agent.md`, `data.agent.md`, `qa.agent.md`, `reviewer.agent.md`        |
| Provider, sidecar, research evidence      | `researcher.agent.md`, `data.agent.md`, `security-auditor.agent.md`, `qa.agent.md` |
| CLI, Rich, Ink, WebGUI, docs              | `operator-ux.agent.md`, `product-docs.agent.md`, `qa.agent.md`                     |
| Memory/retrieval                          | `researcher.agent.md`, `reviewer.agent.md`, `qa.agent.md`                          |
| Release/setup/CI                          | `release-manager.agent.md`, `qa.agent.md`, `reviewer.agent.md`                     |

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
