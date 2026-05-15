# QA Workflow

Use this for validation planning, smoke runs, manual QA, browser QA, docs/WebGUI
checks, and agent-cycle evidence.

If a requested tool or surface is unavailable, record the skipped check, the
reason, and the fallback evidence. Do not mark a scenario passed without
observing the changed behavior.

## Test Tiers

| Tier         | Use When                             | Examples                                             |
| ------------ | ------------------------------------ | ---------------------------------------------------- |
| Focused      | Small module or contract change      | targeted pytest, pyright changed files, package lint |
| Static/Build | Cross-surface code changes           | `pnpm run check`, app builds, root type checks       |
| Smoke        | Operator or runtime surface changed  | `pnpm run qa`, smoke script with JSON artifacts      |
| Interactive  | CLI/Rich/Ink/WebGUI behavior changed | pexpect, tmux pane capture, browser screenshots      |
| Agent Cycle  | Runtime execution path changed       | one-cycle paper run with provider/model readiness    |

## Evidence Rules

- Prefer JSON artifacts, smoke summaries, and reproducible commands.
- Keep artifact directories unique.
- Record expected behavior, actual behavior, and pass/fail.
- Redact secrets and provider payloads before writing evidence.
- Use Browser/Computer tooling for WebGUI/docs visual checks when available.
- Use pexpect/tmux/asciinema for terminal UI evidence when a browser is not
  relevant.

## Advisory Commands

```bash
ruflo route task "qa: <short description>"
ruflo hooks coverage-gaps
ruflo hooks coverage-suggest --path tests
ruflo analyze diff --risk
ruflo hooks pre-command -- "pnpm run qa"
```

If coverage data exists, use it as a hint only; prefer product-risk coverage
over chasing percentage points.
If RuFlo or coverage helpers are unavailable, build the QA matrix from changed
files, source contracts, and operator-visible risk.

## Required Surface Checks

- CLI JSON remains machine-readable and honest about unavailable data.
- Rich and Ink menus do not leak internal docstrings or stale state.
- WebGUI route handlers reject bad requests and show section-level errors.
- Docs explain product behavior to operators before contributor internals.
- Observer API remains read-only and local-first.
- Evidence bundle includes the latest relevant smoke report.

## Failure Handling

1. Preserve the failing artifact.
2. Reduce to a focused reproducer.
3. Fix the smallest owning contract.
4. Re-run focused checks.
5. Re-run the relevant smoke/interactive tier.
6. Update `.ai/qa/qa-scenarios.instructions.md` if the scenario should become durable.

## QA Matrix Template

```text
Surface:
Scenario:
Mode: training | operation | paper | sidecar disabled | sidecar enabled
Inputs:
Expected:
Command:
Artifact:
Pass/fail:
Follow-up:
```
