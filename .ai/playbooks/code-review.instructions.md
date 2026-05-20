# Code Review Playbook

Use this for local review, CodeRabbit/Sonar follow-up, or pre-PR review.

If an external review tool, Sonar server, CodeRabbit comment, RuFlo command, or
line reference is unavailable or stale, say exactly which source could not be
verified and continue from the local diff, tests, and runtime contracts. Do not
copy a bot finding into the review unless the current source still supports it.

## Review Order

1. Findings first: bugs, security, safety, data loss, operator confusion.
2. Architecture drift: new runtime path, hidden side effect, duplicate truth.
3. Tests: changed behavior without focused coverage.
4. Operator evidence: CLI/TUI/Web/docs claims match contracts.
5. Maintainability: complexity, duplication, names, boundaries.

## Sectional External Review Workflow

Use this when the diff is too large for one useful CodeRabbit/Sonar pass, or
when the current PR risks a reviewer file limit.

1. Resolve the intended base and count changed files:

   ```bash
   git diff --name-only <base>...HEAD | sort -u
   ```

2. If the section is over 120 meaningful files, split it before asking an
   external reviewer. Keep each section comfortably under 150 files.
3. Review sections in this order:
   - runtime and safety: `agentic_trader/system/`, `agentic_trader/workflows/`,
     `agentic_trader/runtime_feed.py`, `agentic_trader/observer_api.py`,
     `agentic_trader/cli.py`, and nearest tests
   - trading and persistence: `agentic_trader/engine/`,
     `agentic_trader/execution/`, `agentic_trader/finance/`,
     `agentic_trader/storage/`, and nearest tests
   - providers and sidecars: `agentic_trader/providers/`,
     `agentic_trader/researchd/`, `sidecars/`, `tools/`, and nearest tests
   - operator surfaces: `webgui/src/app/api/`, `webgui/src/lib/`,
     `webgui/src/components/`, `tui/`, `agentic_trader/tui.py`, and nearest
     tests
   - docs, setup, and release: `.ai/`, `docs/`, `dev-docs/`, scripts,
     workflows, package metadata, and lockfiles
4. For CodeRabbit, prefer a real branch/PR per section when the aggregate PR is
   too large. Use `coderabbit review --agent --base <base>` only after checking
   the section branch is under the file budget. Do not rely on path-scoped CLI
   flags unless `coderabbit review --help` in the current install shows them.
5. For Sonar, treat findings as project backlog signals, not as latest-commit
   truth. Verify each issue against the current checkout before fixing or
   accepting it.
6. Record a short section report with: base/head, file count, commands, still
   valid findings, skipped stale findings with reasons, fixes, tests, and
   residual risk.

## Evidence

- Include file and line references.
- Verify external review comments against actual code and local build output.
- Distinguish blockers from polish.
- If no issue is found, state remaining test or runtime risk.

## Agentic Trader Specific Checks

- Paper-first and live-block gates remain intact.
- Research sidecar does not mutate broker, policy, runtime mode, or storage
  contracts outside its file-backed snapshot feed.
- WebGUI remains a thin shell over CLI/runtime contracts.
- Observer API remains read-only.
- Memory and review surfaces explain source/freshness rather than guessing.

## Advisory Commands

```bash
ruflo analyze diff --risk
ruflo analyze code agentic_trader tests scripts
ruflo analyze complexity agentic_trader tests scripts
ruflo analyze imports agentic_trader --external
ruflo analyze circular agentic_trader
```

If an advisory command is missing or exits with an infrastructure error, record
the skipped command and run the focused local checks that exercise the same
surface. Do not suppress a finding just because the advisory tool is down.

For a focused review, add:

```bash
ruff check <changed-files>
pyright <changed-files-or-packages>
uv run python -m pytest -q -p no:cacheprovider <focused-tests>
```

## Review Template

```text
Findings:
- [severity] file:line - issue

Verified:
- source contract:
- tests:
- runtime/operator surface:

Residual risk:
-
```
