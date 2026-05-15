# Agent Role Pack

This folder defines role-specific working agreements for AI collaborators on
Agentic Trader. These agents are development roles only. They are not runtime
agents and must not be wired into the trading system as an external
orchestration framework.

## Shared Contract

Every role must follow the repository root `AGENTS.instructions.md` first. The
existing runtime remains the source of truth.

Required reading before role work:

Core files:

- `README.md`
- `ROADMAP.md`
- `AGENTS.instructions.md`

Project memory and workflow files:

- `.ai/profile.instructions.md`
- `.ai/rules.instructions.md`
- `.ai/architecture.instructions.md`
- `.ai/current-state.instructions.md`
- `.ai/memory.instructions.md`
- `.ai/tasks.instructions.md`
- `.ai/decisions.instructions.md`
- `.ai/workflows/README.instructions.md`
- `.ai/workflows/external-tooling-policy.instructions.md`

If any required file is missing or inaccessible, report the exact path and
continue with the available files while recording the missing dependency in the
handoff or final answer.

If a role-specific instruction conflicts with the root `AGENTS.instructions.md`,
the root contract wins. If two role files conflict, preserve runtime safety,
paper-first execution, source attribution, and operator-visible truth before
speed, convenience, or broad refactoring.

For runtime, CLI, TUI, daemon, broker, memory, or operator-facing changes,
also read the QA documents under `.ai/qa/`.

For `webgui/` or `docs/` work, also read the local app guidance:

- `webgui/AGENTS.instructions.md`
- `docs/AGENTS.instructions.md`

## Role Map

- `planner.agent.md`: shapes scoped implementation plans and separates V1 from later work.
- `implementer.agent.md`: applies approved plans with small, tested, reviewable changes.
- `reviewer.agent.md`: reviews diffs for safety, architecture drift, and operator truth.
- `qa.agent.md`: validates the operator experience and records reproducible evidence.
- `operator-ux.agent.md`: reviews CLI/Rich/Ink UX, visual design, resize behavior, and finance/accounting readability.
- `data.agent.md`: protects provider, canonical data, freshness, and attribution boundaries.
- `product-docs.agent.md`: keeps docs useful to operators first, with contributor notes only where they help.
- `finance-ops.agent.md`: reviews broker, account, portfolio, PnL, exposure, and audit truth through a trading-desk lens.
- `market-strategist.agent.md`: reviews strategy hypotheses, scanner presets, proposal-readiness, and backtest/sweep evidence through a market-structure lens.
- `researcher.agent.md`: grounds codebase, provider, sidecar, and documentation research in source contracts.
- `security-auditor.agent.md`: reviews threat models, route/auth/origin, secrets, artifacts, and sidecar/provider poisoning.
- `release-manager.agent.md`: protects branch, PR, version, changelog, CI, and release-preview hygiene.
- `performance-engineer.agent.md`: measures setup/check/build/runtime bottlenecks without hidden auto-optimization.
- `repo-architect.agent.md`: maps module ownership and architecture boundaries before cross-module changes.
- `code-quality.agent.md`: reviews complexity, static analysis findings, duplicated logic, and small maintainability repairs.
- `browser-qa.agent.md`: verifies WebGUI/docs browser behavior against runtime contracts.
- `test-long-runner.agent.md`: coordinates expensive checks, smoke runs, coverage, and evidence summaries.

## Workflow Map

The concrete workflow agreements live under `.ai/workflows/` and `.ai/playbooks/`.
Use those files instead of generated assistant init files.

Use these role pairings when routing is helpful:

- Bug fix: `planner.agent.md`, `implementer.agent.md`, `qa.agent.md`, then `reviewer.agent.md`; use `.ai/workflows/feature-workflow.instructions.md`.
- Feature/API change: `planner.agent.md`, `implementer.agent.md`, `qa.agent.md`, `reviewer.agent.md`, plus `product-docs.agent.md` when operator behavior changes; use `.ai/workflows/feature-workflow.instructions.md`.
- Security change: `security-auditor.agent.md`, `qa.agent.md`, `.ai/security/threat-model.instructions.md`, and `.ai/workflows/security-workflow.instructions.md`.
- Performance change: `performance-engineer.agent.md`, `qa.agent.md`, and `.ai/workflows/performance-workflow.instructions.md`.
- Broker/accounting change: `finance-ops.agent.md`, `data.agent.md`, `qa.agent.md`, then `reviewer.agent.md`.
- Strategy, scanner, or proposal-enrichment change: `market-strategist.agent.md`, `finance-ops.agent.md`, `data.agent.md`, `qa.agent.md`, then `reviewer.agent.md`; use `.ai/playbooks/strategy-research-and-sweeps.instructions.md`.
- Docs/product explanation change: `product-docs.agent.md`, `operator-ux.agent.md`, then `qa.agent.md`.
- PR/release/setup change: `release-manager.agent.md`, `qa.agent.md`, then `reviewer.agent.md`; use `.ai/workflows/release-pr-workflow.instructions.md`.
- Research/provider/sidecar change: `researcher.agent.md`, `data.agent.md`, `security-auditor.agent.md`, then `qa.agent.md`; use `.ai/playbooks/news-intelligence.instructions.md` when news, event, browser, Firecrawl, or Camofox evidence is involved.
- Broad cross-module change: `repo-architect.agent.md`, `planner.agent.md`, `implementer.agent.md`, then `reviewer.agent.md`.
- Static quality cleanup: `code-quality.agent.md`, `implementer.agent.md`, then `qa.agent.md`.
- Browser surface check: `browser-qa.agent.md`, `operator-ux.agent.md`, then `qa.agent.md`.
- Long validation: `test-long-runner.agent.md`, then `reviewer.agent.md`.

If a task does not fit the listed workflows, route it through
`planner.agent.md` for initial scoping and ask the repository owner when the
owner contract or V1 boundary remains unclear.

If a referenced role, workflow, playbook, external agent, MCP tool, or browser
tool is unavailable, continue with the closest local source inspection only when
the owner contract is still clear. Otherwise stop at a plan and name the missing
input.

Use external agents for parallel investigation only when the user explicitly
allows delegation and the task has independent questions or disjoint write
scopes. Treat their output as advisory evidence; repo contracts, tests, and
operator-facing truth remain authoritative.

## RuFlo Advisory Command Map

Use `.ai/skills/ruflo-codex.instructions.md` and `.ai/playbooks/ruflo-advisory-checks.instructions.md`
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
or cleanup commands unless the current user message names that command family
and asks you to run it.

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
- Market strategist output should turn ideas into data requirements, entry/exit/invalidation, risk/sizing assumptions, backtest checks, and proposal-readiness notes without granting execution authority.

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
  `.ai/decisions.instructions.md` and make sure all product package manifests agree before
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
