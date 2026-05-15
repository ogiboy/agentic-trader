# Workflow Pack

This folder turns useful external-agent workflow ideas into Agentic Trader
working agreements. These files are self-contained repo guidance. They are not
runtime agents, dependency manifests, hooks, daemon state, or external
orchestration framework setup.

Use this pack with the role docs in `.ai/agents/`:

- `feature-workflow.instructions.md`: product or runtime changes from scope to validation.
- `security-workflow.instructions.md`: STRIDE-style review, secrets, origin/auth, artifacts,
  sidecar/provider poisoning, and safe fallback behavior.
- `release-pr-workflow.instructions.md`: version, changelog, branch, PR, and release-preview
  rules.
- `qa-workflow.instructions.md`: smoke, manual QA, browser/docs/WebGUI, and agent-cycle
  evidence rules.
- `.ai/qa/pre-push-checklist.instructions.md`: tiered push gate for code checks, product
  readiness, runtime behavior, visual/browser QA, and security posture.
- `performance-workflow.instructions.md`: bottleneck, cache, setup/check runtime, and
  concurrency review.
- `continuous-research-loop.instructions.md`: PRE-FLIGHT -> MONITOR -> ANALYZE -> PROPOSE
  -> DIGEST research-loop design without broker authority.
- `multi-agent-handoff.instructions.md`: when and how to split work across development
  agents without changing the runtime architecture.
- `external-tooling-policy.instructions.md`: how to use system-level advisory tools without
  making their generated state part of the repository.
- `generated-artifact-harvest.instructions.md`: one-time record of what was adopted or
  rejected from generated advisory scaffolding.

If a referenced role, workflow, or playbook is missing, report the path and use
the nearest current file only when the replacement is obvious from its name.
Otherwise continue with `feature-workflow.instructions.md` plus the relevant
QA checklist and record the missing guidance.

## Default Sequence

1. Confirm branch, dirty worktree, and requested PR base.
2. Read the relevant role contract in `.ai/agents/`.
3. Run an advisory route check for non-trivial work when RuFlo is available:
   `ruflo route task "describe the current task"`.
4. Pick one workflow from this folder and write a short file-level plan. For
   strategy/news/provider intelligence work, pair the workflow with the matching
   playbook in `.ai/playbooks/`.
5. Use `multi-agent-handoff.instructions.md` only when independent sidecar tasks will shorten
   the work without causing write conflicts.
6. Make the smallest useful change.
7. Run focused checks, then broader checks when the blast radius justifies it.
8. Run `ruflo analyze diff --risk` before publishing broad or high-risk work
   when RuFlo is available.
9. Update `.ai/current-state.instructions.md`, `.ai/tasks.instructions.md`, and `.ai/decisions.instructions.md` when the
   change alters architecture, release rules, QA expectations, operator truth,
   or future assumptions.
10. Before push, verify version files when the branch changes product behavior,
    operator surfaces, docs, sidecars, setup, or workflow contracts.

For documentation-only or prompt-only work, stop after the smallest relevant
validation and repo-hygiene check; do not run product-runtime QA unless the
content changes runtime expectations.

## Non-Goals

- Do not create a second runtime orchestration layer.
- Do not auto-commit, auto-merge, or auto-upgrade dependencies.
- Do not put provider secrets, runtime logs, tool memory, daemon state, or local
  MCP configs into tracked project files.
- Do not let generated tool instructions override `AGENTS.instructions.md`, `.ai/rules.instructions.md`,
  or the existing trading runtime contracts.
