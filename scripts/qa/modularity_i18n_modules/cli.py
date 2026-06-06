from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import Any


def _print_section(title: str, rows: Sequence[str]) -> None:
    print(f"\n{title}")
    if not rows:
        print("  none")
        return
    for row in rows:
        print(f"  {row}")


def print_report(report: Any, *, top: int, fail_on_findings: bool = False) -> None:
    gate_mode = "fail-on-findings" if fail_on_findings else "reporting-only"
    print(f"modularity-i18n-audit: gate={gate_mode}")
    print(f"scanned_files={report.scanned_files}")

    _print_section(
        "Oversized files",
        [
            (
                f"{metric.path}: lines={metric.lines} "
                f"threshold={metric.threshold} category={metric.category}"
            )
            for metric in report.oversized_files[:top]
        ],
    )
    _print_section(
        "Long Python functions",
        [
            f"{metric.path}:{metric.line} {metric.name} lines={metric.lines}"
            for metric in report.long_functions[:top]
        ],
    )
    _print_section(
        "Repeated helper patterns",
        [
            f"{metric.name}: count={len(metric.paths)} paths={', '.join(metric.paths)}"
            for metric in report.repeated_helpers[:top]
        ],
    )
    _print_section(
        "Hardcoded operator-copy candidates",
        [
            f"{candidate.path}:{candidate.line}: {candidate.excerpt}"
            for candidate in report.copy_candidates[:top]
        ],
    )
    parity = report.docs_locale_parity
    _print_section(
        "Docs locale parity",
        [
            *[f"en-only: {path}" for path in parity.english_only],
            *[f"tr-only: {path}" for path in parity.turkish_only],
        ],
    )


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    if list(argv[:1]) == ["--"]:
        argv = argv[1:]
    parser = argparse.ArgumentParser(
        description=(
            "Report oversized modules, long functions, repeated helpers, docs "
            "locale parity, and hardcoded UI copy candidates."
        )
    )
    parser.add_argument("--json", action="store_true", help="Emit the report as JSON.")
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Number of rows to print per text section.",
    )
    parser.add_argument(
        "--function-threshold",
        type=int,
        default=80,
        help="Minimum Python function length to report.",
    )
    parser.add_argument(
        "--copy-candidate-limit",
        type=int,
        default=80,
        help="Maximum hardcoded-copy candidates to collect.",
    )
    parser.add_argument(
        "--fail-on-findings",
        action="store_true",
        help="Fail when the audit reports any modularity or i18n findings.",
    )
    return parser.parse_args(list(argv))


def _has_findings(report: Any) -> bool:
    parity = report.docs_locale_parity
    return any(
        (
            report.oversized_files,
            report.long_functions,
            report.repeated_helpers,
            report.copy_candidates,
            parity.english_only,
            parity.turkish_only,
        )
    )


def should_fail_gate(report: Any, *, fail_on_findings: bool) -> bool:
    return fail_on_findings and _has_findings(report)
