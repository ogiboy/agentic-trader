# Workflow Pack

This folder turns useful external-agent workflow ideas into Agentic Trader
working agreements. These files are self-contained repo guidance. They are not
runtime agents, dependency manifests, hooks, daemon state, or external
orchestration framework setup.

Use this pack with the role docs in `.ai/agents/`:

- `feature-workflow.md`: product or runtime changes from scope to validation.
- `security-workflow.md`: STRIDE-style review, secrets, origin/auth, artifacts,
  sidecar/provider poisoning, and safe fallback behavior.
- `release-pr-workflow.md`: version, changelog, branch, PR, and release-preview
  rules.
- `qa-workflow.md`: smoke, manual QA, browser/docs/WebGUI, and agent-cycle
  evidence rules.
- `.ai/qa/pre-push-checklist.md`: tiered push gate for code checks, product
  readiness, runtime behavior, visual/browser QA, and security posture.
- `performance-workflow.md`: bottleneck, cache, setup/check runtime, and
  concurrency review.
- `continuous-research-loop.md`: PRE-FLIGHT -> MONITOR -> ANALYZE -> PROPOSE
  -> DIGEST research-loop design without broker authority.
- `multi-agent-handoff.md`: when and how to split work across development
  agents without changing the runtime architecture.
- `external-tooling-policy.md`: how to use system-level advisory tools without
  making their generated state part of the repository.
- `generated-artifact-harvest.md`: one-time record of what was adopted or
  rejected from generated advisory scaffolding.

## Default Sequence

1. Confirm branch, dirty worktree, and requested PR base.
2. Read the relevant role contract in `.ai/agents/`.
3. Run an advisory route check for non-trivial work when RuFlo is available:
   `ruflo route task "describe the current task"`.
4. Pick one workflow from this folder and write a short file-level plan. For
   strategy/news/provider intelligence work, pair the workflow with the matching
   playbook in `.ai/playbooks/`.
5. Use `multi-agent-handoff.md` only when independent sidecar tasks will shorten
   the work without causing write conflicts.
6. Make the smallest useful change.
7. Run focused checks, then broader checks when the blast radius justifies it.
8. Run `ruflo analyze diff --risk` before publishing broad or high-risk work
   when RuFlo is available.
9. Update `.ai/current-state.md`, `.ai/tasks.md`, and `.ai/decisions.md` when the
   change alters architecture, release rules, QA expectations, operator truth,
   or future assumptions.
10. Before push, verify version files when the branch changes product behavior,
   operator surfaces, docs, sidecars, setup, or workflow contracts.

## Non-Goals

- Do not create a second runtime orchestration layer.
- Do not auto-commit, auto-merge, or auto-upgrade dependencies.
- Do not put provider secrets, runtime logs, tool memory, daemon state, or local
  MCP configs into tracked project files.
- Do not let generated tool instructions override `AGENTS.md`, `.ai/rules.md`,
  or the existing trading runtime contracts.
