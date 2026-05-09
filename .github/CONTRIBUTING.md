# Contributing to Agentic Trader

Thanks for taking the time to improve Agentic Trader. This project is a
local-first, paper-first trading runtime, so contributions are reviewed with
operator safety, auditability, and reproducibility in mind.

## Project Boundaries

Agentic Trader already has its own staged specialist graph, memory layer,
DuckDB storage, broker adapter boundary, CLI/TUI/Web surfaces, and optional
research sidecars. Contributions should extend those contracts rather than
replace them with a new orchestration framework.

Please preserve these invariants:

- live execution remains blocked unless an explicit future decision enables it
- paper trading is the default execution path
- sidecars collect evidence only; they do not submit orders or mutate policy
- operator chat and research tooling never become hidden execution paths
- Web GUI route handlers stay thin wrappers around existing runtime contracts
- secrets stay in ignored local env files and are never committed

## Development Setup

Use the repository root commands:

```bash
make bootstrap-dry-run
make bootstrap
pnpm run setup
```

Python dependencies are managed by `uv`; Node workspaces are managed by `pnpm`.
When adding Python packages, use `uv add <package>` so `pyproject.toml` and
`uv.lock` stay aligned. When upgrading dependencies, use `uv lock --upgrade`
and then restore the dev environment with:

```bash
uv sync --locked --all-extras --group dev
```

Do not use a plain `uv sync` as the normal repair path because it can remove
dev-only tools from the local environment.

## Contribution Flow

1. Read `README.md`, `ROADMAP.md`, and the relevant `.ai/` workflow notes.
2. Inspect the smallest owning module before editing.
3. Prefer focused, additive changes over broad rewrites.
4. Update tests for behavior changes.
5. Update README/docs/`.ai` notes when a command, workflow, operator surface,
   security rule, or future assumption changes.
6. Run focused checks first, then broader checks before opening a PR.

For product-impacting work, include evidence for the user-facing behavior, not
only static checks.

## Required Checks

For most code changes:

```bash
pnpm run check
```

For V1/product-readiness changes, also run or explain the relevant manual QA
scenario from `.ai/qa/qa-scenarios.md`. Examples include:

```bash
agentic-trader setup-status --json
agentic-trader model-service status --probe-generation --json
agentic-trader v1-readiness --provider-check --json
agentic-trader research-status --json
agentic-trader dashboard-snapshot --provider-check
```

If the configured local model cannot generate, strict paper-operation checks
should fail closed. Do not bypass this gate to make a test look green.

## Commit Style

Use Conventional Commits:

- `feat: add proposal queue review state`
- `fix: preserve app-owned model-service state`
- `docs: clarify paper operation setup`
- `test: cover observer loopback rejection`

Release automation reads conventional commits on `main`. Feature branches may
carry version-preview artifacts, but stable release mutation is owned by the
release workflow.

## Pull Requests

A good PR should include:

- what changed
- why it is safe for local-first paper operation
- tests and manual QA evidence
- any known limitations or follow-up issues
- screenshots or terminal evidence for UI/TUI/Web changes when relevant

Do not open PRs to `main` unless the branch plan explicitly says to do so.
Respect staged integration branches such as V1/readiness branches.

## Security-Sensitive Areas

Extra care is required for:

- broker adapters and execution intents/outcomes
- proposal approval and reconciliation
- runtime mode gates
- Web GUI route handlers
- observer API binds and tokens
- subprocess helpers and app-owned services
- research providers, browser fetchers, and sidecar payloads
- runtime logs, evidence bundles, and secret redaction

See `SECURITY.md` for vulnerability reporting and `.ai/qa/qa-checklist.md` for
the pre-push security posture checklist.
