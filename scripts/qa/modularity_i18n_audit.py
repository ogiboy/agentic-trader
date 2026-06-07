#!/usr/bin/env python3
"""Audit project-wide modularity and i18n debt for reports and CI gates."""

from __future__ import annotations

import json
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import cast

from scripts.qa.modularity_i18n_modules.cli import (
    parse_args,
    print_report,
    should_fail_gate,
)
from scripts.qa.modularity_i18n_modules.metrics import AuditReport
from scripts.qa.modularity_i18n_modules.scanners import (
    copy_candidates,
    docs_locale_parity,
    iter_scan_files,
    long_python_functions,
    oversized_files,
    repeated_python_helpers,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_ROOTS = (
    "agentic_trader",
    "webgui/src",
    "docs",
    "tui",
    "scripts",
    "tools",
    "sidecars/research_flow",
    ".ai",
)


def build_report(
    *,
    repo_root: Path = REPO_ROOT,
    roots: Iterable[str] = SCAN_ROOTS,
    function_threshold: int = 80,
    copy_candidate_limit: int = 80,
) -> AuditReport:
    """
    Scan the given repository roots and assemble an AuditReport summarizing modularity and i18n findings.

    Performs repository-wide scans and aggregates results into an AuditReport containing:
    - oversized_files: files whose line counts exceed category-specific thresholds
    - long_functions: Python functions whose length meets or exceeds `function_threshold`
    - repeated_helpers: helper function names reused across multiple Python files
    - copy_candidates: UI-located lines that look like hardcoded operator/copy strings (up to `copy_candidate_limit`)
    - docs_locale_parity: files present in English-only or Turkish-only doc trees
    - scanned_files: total number of scanned files

    Parameters:
        repo_root (Path): Root directory of the repository to scan.
        roots (Iterable[str]): Root paths (relative to `repo_root`) to include in the scan.
        function_threshold (int): Minimum number of lines for a Python function to be reported as long.
        copy_candidate_limit (int): Maximum number of copy-candidate results to collect.

    Returns:
        AuditReport: Aggregated audit report with all computed sections and the scanned file count.
    """
    paths = tuple(iter_scan_files(repo_root, roots))
    return AuditReport(
        oversized_files=oversized_files(paths, repo_root=repo_root),
        long_functions=long_python_functions(
            paths, repo_root=repo_root, threshold=function_threshold
        ),
        repeated_helpers=repeated_python_helpers(paths, repo_root=repo_root),
        copy_candidates=copy_candidates(
            paths, repo_root=repo_root, limit=copy_candidate_limit
        ),
        docs_locale_parity=docs_locale_parity(repo_root),
        scanned_files=len(paths),
    )


def main(argv: Sequence[str] | None = None) -> int:
    """
    Run the repository modularity and i18n audit using provided CLI-style arguments and print the report to stdout.

    Prints either pretty JSON (when `--json` is set) or a human-readable text report, and honors the configured function-length and copy-candidate limits parsed from `argv`.

    Parameters:
        argv (Sequence[str] | None): Command-line arguments to parse (omit the program name). If `None`, uses `sys.argv[1:]`.

    Returns:
        int: Exit code — `0` on success; `1` when `--fail-on-findings` is set and the audit produced any findings.
    """
    args = parse_args(sys.argv[1:] if argv is None else argv)
    report = build_report(
        function_threshold=cast(int, args.function_threshold),
        copy_candidate_limit=cast(int, args.copy_candidate_limit),
    )
    if cast(bool, args.json):
        print(json.dumps(report.as_json(), indent=2, sort_keys=True))
    else:
        print_report(
            report,
            top=cast(int, args.top),
            fail_on_findings=cast(bool, args.fail_on_findings),
        )
    return (
        1
        if should_fail_gate(
            report,
            fail_on_findings=cast(bool, args.fail_on_findings),
        )
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
