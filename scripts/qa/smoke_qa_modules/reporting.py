from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from scripts.qa.smoke_qa_modules.models import CheckResult, SmokeContext


def write_summary(
    context: SmokeContext,
    results: list[CheckResult],
    *,
    repo_root: Path,
    smoke_python: str,
    resolve_agentic_trader_executable: Callable[[], str | None],
) -> Path:
    summary_path = context.artifacts_dir / "smoke-summary.json"
    payload: dict[str, Any] = {
        "repo_root": str(repo_root),
        "artifacts_dir": str(context.artifacts_dir),
        "python": smoke_python,
        "agentic_trader_path": resolve_agentic_trader_executable(),
        "results": [asdict(result) for result in results],
    }
    summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return summary_path


def status_label(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def dirty_label(value: bool | None) -> str:
    if value is None:
        return "unknown"
    return "yes" if value else "no"


def write_report(
    context: SmokeContext,
    results: list[CheckResult],
    summary_path: Path,
    *,
    repo_root: Path,
    smoke_python: str,
    resolve_agentic_trader_executable: Callable[[], str | None],
    current_git_branch: Callable[[], str | None],
    current_git_commit: Callable[[], str | None],
    git_worktree_dirty: Callable[[], bool | None],
) -> Path:
    report_path = context.artifacts_dir / "qa-report.md"
    failed = [result for result in results if not result.passed]
    branch = current_git_branch() or "detached"
    commit = current_git_commit() or "unknown"
    dirty = git_worktree_dirty()
    agentic_path = resolve_agentic_trader_executable() or "not found"
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")

    lines = [
        "# QA Smoke Report",
        "",
        f"- Generated: {generated_at}",
        f"- Repo: `{repo_root}`",
        f"- Branch: `{branch}`",
        f"- Commit: `{commit}`",
        f"- Worktree dirty: `{dirty_label(dirty)}`",
        f"- Python: `{smoke_python}`",
        f"- Agentic Trader: `{agentic_path}`",
        f"- Summary JSON: `{summary_path}`",
        f"- Result: `{status_label(not failed)}`",
        (
            f"- Checks: `{len(results) - len(failed)} passed / "
            f"{len(failed)} failed / {len(results)} total`"
        ),
        "",
        "## Checks",
        "",
        "| Status | Check | Details | Artifact |",
        "| --- | --- | --- | --- |",
    ]
    for result in results:
        artifact = f"`{result.artifact}`" if result.artifact else "-"
        details = result.details.replace("|", "\\|")
        lines.append(
            f"| {status_label(result.passed)} | `{result.name}` | "
            f"{details} | {artifact} |"
        )

    lines.extend(["", "## Triage"])
    if failed:
        lines.append("")
        for result in failed:
            artifact = f" Artifact: `{result.artifact}`." if result.artifact else ""
            lines.append(f"- `{result.name}` failed: {result.details}.{artifact}")
    else:
        lines.extend(
            [
                "",
                "- No smoke failures were detected.",
                (
                    "- Cross-check any visual/operator claims against the artifacts "
                    "before promoting a run as release evidence."
                ),
            ]
        )

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def claim_artifacts_dir(artifacts_root: Path, run_label: str) -> Path:
    artifacts_root.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, 1000):
        suffix = "" if attempt == 1 else f"-{attempt}"
        candidate = artifacts_root / f"{run_label}{suffix}"
        try:
            candidate.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return candidate
    msg = f"Unable to claim a unique smoke artifact directory for {run_label!r}"
    raise RuntimeError(msg)
