# Helper Intent Registry

This directory records helper intentions that are safe for Agentic Trader. It
does not contain executable advisory scripts. Add real scripts only when they
are repo-owned, reviewed, tested, and documented in root setup/check flows.

## Accepted Helper Ideas

| Helper Intent | Repo-Native Form |
| --- | --- |
| Checkpoint before mutation | Run `git status --short --branch`, inspect dirty files, and avoid reverting user changes. |
| Setup validation | Use `.ai/playbooks/setup-validation.md` and root pnpm/uv scripts. |
| Security scan | Use `.ai/playbooks/security-scan.md`, Sonar/CodeRabbit findings, focused negative tests, and redaction checks. |
| Performance benchmark | Use `.ai/workflows/performance-workflow.md` with measured setup/check/build/runtime timings. |
| Diff-risk advisory | Use RuFlo MCP diff-risk/file-risk tools when available, then verify locally. |
| GitHub safety | Use `.ai/workflows/release-pr-workflow.md` for base, version, PR, and release checks. |
| Browser QA | Use `.ai/playbooks/browser-qa.md` and the Browser/Computer tools when available. |

## Rejected Helper Ideas

- auto-commit
- auto-merge
- generated pre/post hooks
- repo-local advisory daemon managers
- generated status lines
- hidden memory writers
- background security/performance workers that mutate repo files
- dependency auto-upgrade helpers without explicit review

## Script Standards If A Real Helper Is Added

- idempotent
- shell-safe, no `shell=True` style string interpolation
- bounded runtime and output
- no secrets in stdout/stderr
- clear exit codes
- covered by focused tests or documented manual QA
- wired through root scripts only when the command is stable
