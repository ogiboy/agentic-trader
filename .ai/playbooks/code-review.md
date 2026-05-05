# Code Review Playbook

Use this for local review, CodeRabbit/Sonar follow-up, or pre-PR review.

## Review Order

1. Findings first: bugs, security, safety, data loss, operator confusion.
2. Architecture drift: new runtime path, hidden side effect, duplicate truth.
3. Tests: changed behavior without focused coverage.
4. Operator evidence: CLI/TUI/Web/docs claims match contracts.
5. Maintainability: complexity, duplication, names, boundaries.

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
