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

## Hand-Off Rules

- Planner output should be file-level and bounded enough for an implementer to act.
- Implementer output should list changed files, validation run, and assumptions.
- Reviewer output should lead with blockers and safety regressions before praise.
- QA output should include commands, expected behavior, actual behavior, and evidence.
- QA output should use Computer Use for visual CLI/Rich/Ink inspection when available, then fall back to pexpect, tmux, asciinema, and text artifacts when it is not.
- Operator UX output should include viewport, operator lens, evidence, and the smallest simplification or repair recommendation that would improve V1 usability.
- Data output should keep raw provider payloads behind canonical contracts.

## Release / Version Handoff

- Treat `pyproject.toml` as the canonical stable application version source.
- On stable release work, verify semantic-release version stamping keeps
  `pyproject.toml`, `agentic_trader/__init__.py`, root `package.json`,
  `webgui/package.json`, `docs/package.json`, `tui/package.json`, and
  `sidecars/research_flow/pyproject.toml` aligned through the configured release
  automation.
- On non-main feature or V1 branch pushes, do not hand-edit stable version files
  or `CHANGELOG.md` just to identify a branch build. Use the SemVer-compatible
  branch artifact identity from `pnpm run version:plan`.
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
