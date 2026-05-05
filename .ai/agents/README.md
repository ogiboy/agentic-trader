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
- `.ai/workflows/README.md`
- `.ai/workflows/external-tooling-policy.md`

For runtime, CLI, TUI, daemon, broker, memory, or operator-facing changes,
also read the QA documents under `.ai/qa/`.

For `webgui/` or `docs/` work, also read the local app guidance:

- `webgui/AGENTS.md`
- `docs/AGENTS.md`

## Role Map

- `planner.md`: shapes scoped implementation plans and separates V1 from later work.
- `implementer.md`: applies approved plans with small, tested, reviewable changes.
- `reviewer.md`: reviews diffs for safety, architecture drift, and operator truth.
- `qa.md`: validates the operator experience and records reproducible evidence.
- `operator-ux.md`: reviews CLI/Rich/Ink UX, visual design, resize behavior, and finance/accounting readability.
- `data.md`: protects provider, canonical data, freshness, and attribution boundaries.
- `product-docs.md`: keeps docs useful to operators first, with contributor notes only where they help.
- `finance-ops.md`: reviews broker, account, portfolio, PnL, exposure, and audit truth through a trading-desk lens.
- `researcher.md`: grounds codebase, provider, sidecar, and documentation research in source contracts.
- `security-auditor.md`: reviews threat models, route/auth/origin, secrets, artifacts, and sidecar/provider poisoning.
- `release-manager.md`: protects branch, PR, version, changelog, CI, and release-preview hygiene.
- `performance-engineer.md`: measures setup/check/build/runtime bottlenecks without hidden auto-optimization.
- `repo-architect.md`: maps module ownership and architecture boundaries before cross-module changes.
- `code-quality.md`: reviews complexity, static analysis findings, duplicated logic, and small maintainability repairs.
- `browser-qa.md`: verifies WebGUI/docs browser behavior against runtime contracts.
- `test-long-runner.md`: coordinates expensive checks, smoke runs, coverage, and evidence summaries.

## Workflow Map

The concrete workflow agreements live under `.ai/workflows/` and `.ai/playbooks/`.
Use those files instead of generated assistant init files.

Use these role pairings when routing is helpful:

- Bug fix: `planner.md`, `implementer.md`, `qa.md`, then `reviewer.md`; use `.ai/workflows/feature-workflow.md`.
- Feature/API change: `planner.md`, `implementer.md`, `qa.md`, `reviewer.md`, plus `product-docs.md` when operator behavior changes; use `.ai/workflows/feature-workflow.md`.
- Security change: `security-auditor.md`, `qa.md`, `.ai/security/threat-model.md`, and `.ai/workflows/security-workflow.md`.
- Performance change: `performance-engineer.md`, `qa.md`, and `.ai/workflows/performance-workflow.md`.
- Broker/accounting change: `finance-ops.md`, `data.md`, `qa.md`, then `reviewer.md`.
- Docs/product explanation change: `product-docs.md`, `operator-ux.md`, then `qa.md`.
- PR/release/setup change: `release-manager.md`, `qa.md`, then `reviewer.md`; use `.ai/workflows/release-pr-workflow.md`.
- Research/provider/sidecar change: `researcher.md`, `data.md`, `security-auditor.md`, then `qa.md`.
- Broad cross-module change: `repo-architect.md`, `planner.md`, `implementer.md`, then `reviewer.md`.
- Static quality cleanup: `code-quality.md`, `implementer.md`, then `qa.md`.
- Browser surface check: `browser-qa.md`, `operator-ux.md`, then `qa.md`.
- Long validation: `test-long-runner.md`, then `reviewer.md`.

External agents may be used for parallel investigation only when the task is
large enough to justify delegation. Their output is advisory evidence; repo
contracts, tests, and operator-facing truth remain authoritative.

## RuFlo Advisory Command Map

Use `.ai/skills/ruflo-codex.md` and `.ai/playbooks/ruflo-advisory-checks.md`
when system-level RuFlo is available. Preferred examples:

```bash
ruflo route task "describe the current task"
ruflo hooks route -t "describe the current task"
ruflo hooks pre-command -- "pnpm run check"
ruflo analyze diff --risk
ruflo analyze complexity agentic_trader tests scripts
ruflo security secrets
ruflo performance bottleneck
```

Do not run init, daemon, agent-spawn, swarm-start, workflow-run, memory-store,
or cleanup commands unless the user explicitly asks for that operation.

## Hand-Off Rules

- Planner output should be file-level and bounded enough for an implementer to act.
- Implementer output should list changed files, validation run, and assumptions.
- Reviewer output should lead with blockers and safety regressions before praise.
- QA output should include commands, expected behavior, actual behavior, and evidence.
- QA output should use Computer Use for visual CLI/Rich/Ink inspection when available, then fall back to pexpect, tmux, asciinema, and text artifacts when it is not.
- Operator UX output should include viewport, operator lens, evidence, and the smallest simplification or repair recommendation that would improve V1 usability.
- Data output should keep raw provider payloads behind canonical contracts.
- Product docs output should translate internal contracts into operator workflows, concepts, and feature deep dives before contributor implementation notes.
- Finance ops output should reconcile broker/account claims against adapter payloads, persisted records, dashboard/observer truth, and evidence bundles.

## Release / Version Handoff

- Treat `pyproject.toml` as the canonical stable application version source.
- On stable release work, verify semantic-release version stamping keeps
  `pyproject.toml`, `agentic_trader/__init__.py`, root `package.json`,
  `webgui/package.json`, `docs/package.json`, `tui/package.json`, and
  `sidecars/research_flow/pyproject.toml` aligned through the configured release
  automation.
- On non-main feature or V1 branch pushes that carry product-impacting code,
  operator-surface, docs, sidecar, or workflow changes, bump the tracked app
  patch version consistently before pushing: `pyproject.toml`,
  `agentic_trader/__init__.py`, root `package.json`, `webgui/package.json`,
  `docs/package.json`, `tui/package.json`, `sidecars/research_flow/pyproject.toml`,
  and the matching lockfile metadata. Still run `pnpm run version:plan` so the
  branch artifact identity is visible.
- Do not edit `CHANGELOG.md` on feature branches unless the task is explicitly a
  release/changelog task; changelog generation remains release-flow owned.
- Before pushing release, CI, binary, or package-metadata changes, run or record
  why you skipped `pnpm run version:plan` and `pnpm run release:preview`.
- If a version file must be changed manually, document the reason in
  `.ai/decisions.md` and make sure all product package manifests agree before
  pushing.

## Non-Negotiables

- Paper remains the default execution backend.
- Live trading remains blocked unless intentionally implemented behind explicit gates.
- Strict runtime gating must not be weakened.
- Operator chat and instruction flows must not become hidden execution paths.
- Storage changes should be additive and replay/audit friendly.
- CLI, Rich, Ink, observer API, and storage should expose the same underlying truth.
- `webgui` and `docs` should preserve the current shadcn/Tailwind baseline unless an explicit design-system decision changes it.
- Docs should not describe project `.ai` memory as if it were the product's trading memory; operator-facing pages must distinguish decision history, review evidence, and contributor notes.
