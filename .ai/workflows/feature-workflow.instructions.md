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
5. Map module-owned files before editing: code, constants, helpers, styles,
   copy/i18n, tests, fixtures, and assets should have an obvious owner.
6. Implement the smallest coherent slice.
7. Run focused tests near the touched modules.
8. Run broader checks when the change crosses module boundaries.
9. Commit logical slices when they are internally consistent.
10. Push only after the touched module or surface is complete enough to be
   reviewed as a finished unit, unless the user explicitly asks for an earlier
   checkpoint.
11. Update `.ai/current-state.instructions.md`, `.ai/tasks.instructions.md`, and
   `.ai/decisions.instructions.md` when the change creates durable assumptions.

## Modularity And I18n Discipline

- Python, CLI, Rich, Ink/TUI, WebGUI, and docs all follow the same modularity
  rule: repeated functions, constants, labels, and static data belong in
  explicit module-local seams before they become shared project-level helpers.
- Shared helpers must earn their scope through real cross-module use. Avoid
  dumping unrelated strings, options, or formatting helpers into global files.
- Terminal and browser copy must be localizable. Dashboard/observer JSON keys
  stay stable English contract keys, but rendered labels and operator text
  should flow through the UI text/i18n layer.
- For Next.js surfaces, prefer a translation accessor model such as
  `useTranslations("ControlRoom")` plus `t("section.key")` over large imported
  label objects in component files. A future dependency such as `next-intl`
  should be introduced only with routing/provider setup, typed message
  organization, and WebGUI/docs migration tests.
- For Python surfaces, keep the current typed text catalog direction but evolve
  usage toward a small locale-aware accessor so commands and TUI components
  import a function/context rather than broad copy tables.
- React component files should be clearly identifiable, normally PascalCase for
  components, with hooks, utilities, constants, styles, copy, and route helpers
  named separately by role.

## Push And CI Cadence

- A feature branch may contain several small commits for one module, but pushes
  should normally happen at module-complete checkpoints.
- Do not pause the whole goal after every push just to watch CI. Keep working
  locally, then inspect CI/SonarCloud after the next natural break or after a
  short delay, and fold any failures into the next coherent push.
- Treat SonarCloud issues as local quality work, not remote noise. Reproduce
  locally where possible through lint, typecheck, coverage, and focused tests
  before assuming a cloud-only false positive.

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
VS Code checks:
Version impact:
```
