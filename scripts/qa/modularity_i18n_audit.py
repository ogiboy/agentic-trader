#!/usr/bin/env python3
"""Report project-wide modularity and i18n debt without failing CI by default."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_ROOTS = ("agentic_trader", "webgui/src", "docs", "tui")
CODE_SUFFIXES = {".py", ".ts", ".tsx", ".mjs", ".css", ".mdx"}
SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".sonar",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "runtime",
}
HELPER_NAME_ALLOWLIST = {
    "_object_list",
    "_object_mapping",
    "_object_mapping_list",
    "_utc_now_iso",
    "utc_now_iso",
    "to_payload",
    "from_payload",
    "default_symbols_from_preferences",
}
UI_SURFACE_PATTERNS = (
    "agentic_trader/cli.py",
    "agentic_trader/tui.py",
    "tui/index.mjs",
    "webgui/src/components",
    "webgui/src/app",
    "docs/components",
    "docs/lib",
)
COPY_BOUNDARY_PATTERNS = (
    "/copy/",
    "/content/",
    "/i18n/",
    "ui_text.py",
    "nav-copy.ts",
    "site-metadata.ts",
    ".test.",
)
OPERATOR_COPY_HINT = re.compile(
    r"(?:Panel\(|Table\(|Prompt\.ask|console\.print|add_column|add_row|"
    r"title=|help=|label|Label|title|Title|message|Message|description|"
    r"Error|Warning|Status|Overview|Runtime|Portfolio|Settings)"
)
QUOTED_HUMAN_TEXT = re.compile(r"""["']([^"']*[A-Za-z][^"']*\s[^"']*)["']""")


@dataclass(frozen=True)
class FileMetric:
    path: str
    lines: int
    threshold: int
    category: str

    def as_json(self) -> dict[str, object]:
        return {
            "path": self.path,
            "lines": self.lines,
            "threshold": self.threshold,
            "category": self.category,
        }


@dataclass(frozen=True)
class FunctionMetric:
    path: str
    name: str
    line: int
    lines: int

    def as_json(self) -> dict[str, object]:
        return {
            "path": self.path,
            "name": self.name,
            "line": self.line,
            "lines": self.lines,
        }


@dataclass(frozen=True)
class HelperMetric:
    name: str
    paths: tuple[str, ...]

    def as_json(self) -> dict[str, object]:
        return {"name": self.name, "paths": list(self.paths), "count": len(self.paths)}


@dataclass(frozen=True)
class CopyCandidate:
    path: str
    line: int
    excerpt: str

    def as_json(self) -> dict[str, object]:
        return {"path": self.path, "line": self.line, "excerpt": self.excerpt}


@dataclass(frozen=True)
class LocaleParity:
    english_only: tuple[str, ...]
    turkish_only: tuple[str, ...]

    def as_json(self) -> dict[str, object]:
        return {
            "english_only": list(self.english_only),
            "turkish_only": list(self.turkish_only),
        }


@dataclass(frozen=True)
class AuditReport:
    oversized_files: tuple[FileMetric, ...]
    long_functions: tuple[FunctionMetric, ...]
    repeated_helpers: tuple[HelperMetric, ...]
    copy_candidates: tuple[CopyCandidate, ...]
    docs_locale_parity: LocaleParity
    scanned_files: int

    def as_json(self) -> dict[str, object]:
        return {
            "scanned_files": self.scanned_files,
            "oversized_files": [metric.as_json() for metric in self.oversized_files],
            "long_functions": [metric.as_json() for metric in self.long_functions],
            "repeated_helpers": [metric.as_json() for metric in self.repeated_helpers],
            "copy_candidates": [
                candidate.as_json() for candidate in self.copy_candidates
            ],
            "docs_locale_parity": self.docs_locale_parity.as_json(),
        }


def _relative(path: Path, *, repo_root: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def _iter_scan_files(repo_root: Path, roots: Iterable[str]) -> Iterable[Path]:
    for root_name in roots:
        root = repo_root / root_name
        if root.is_file():
            if root.suffix in CODE_SUFFIXES:
                yield root
            continue
        if not root.exists():
            continue
        for current_root, dirs, files in os.walk(root):
            dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
            current = Path(current_root)
            for file_name in files:
                path = current / file_name
                if path.suffix in CODE_SUFFIXES:
                    yield path


def _line_threshold(path: Path, rel_path: str) -> tuple[str, int]:
    if ".test." in path.name:
        return "test", 700
    if rel_path == "agentic_trader/cli.py":
        return "python-cli-facade", 1800
    if rel_path in {"agentic_trader/tui.py", "tui/index.mjs"}:
        return "terminal-ui-entrypoint", 900
    if path.suffix == ".py":
        return "python-module", 800
    if path.suffix == ".css":
        return "style-module", 450
    if path.suffix in {".ts", ".tsx", ".mjs"}:
        return "frontend-module", 300
    if path.suffix == ".mdx":
        return "docs-page", 280
    return "source-file", 500


def _oversized_files(paths: Sequence[Path], *, repo_root: Path) -> tuple[FileMetric, ...]:
    metrics: list[FileMetric] = []
    for path in paths:
        try:
            line_count = len(path.read_text(encoding="utf-8").splitlines())
        except UnicodeDecodeError:
            continue
        rel_path = _relative(path, repo_root=repo_root)
        category, threshold = _line_threshold(path, rel_path)
        if line_count > threshold:
            metrics.append(
                FileMetric(
                    path=rel_path,
                    lines=line_count,
                    threshold=threshold,
                    category=category,
                )
            )
    return tuple(sorted(metrics, key=lambda metric: metric.lines, reverse=True))


def _python_tree(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return None


def _long_python_functions(
    paths: Sequence[Path], *, repo_root: Path, threshold: int
) -> tuple[FunctionMetric, ...]:
    metrics: list[FunctionMetric] = []
    for path in paths:
        if path.suffix != ".py":
            continue
        tree = _python_tree(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            end_line = node.end_lineno
            if end_line is None:
                continue
            function_lines = end_line - node.lineno + 1
            if function_lines >= threshold:
                metrics.append(
                    FunctionMetric(
                        path=_relative(path, repo_root=repo_root),
                        name=node.name,
                        line=node.lineno,
                        lines=function_lines,
                    )
                )
    return tuple(sorted(metrics, key=lambda metric: metric.lines, reverse=True))


def _repeated_python_helpers(
    paths: Sequence[Path], *, repo_root: Path
) -> tuple[HelperMetric, ...]:
    helper_paths: dict[str, set[str]] = defaultdict(set)
    for path in paths:
        if path.suffix != ".py":
            continue
        tree = _python_tree(path)
        if tree is None:
            continue
        rel_path = _relative(path, repo_root=repo_root)
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            if node.name in HELPER_NAME_ALLOWLIST:
                helper_paths[node.name].add(rel_path)
    metrics = [
        HelperMetric(name=name, paths=tuple(sorted(found_paths)))
        for name, found_paths in helper_paths.items()
        if len(found_paths) >= 3
    ]
    return tuple(sorted(metrics, key=lambda metric: len(metric.paths), reverse=True))


def _is_ui_surface(rel_path: str) -> bool:
    return any(rel_path.startswith(pattern) for pattern in UI_SURFACE_PATTERNS)


def _is_copy_boundary(rel_path: str) -> bool:
    normalized = f"/{rel_path}"
    return any(pattern in normalized for pattern in COPY_BOUNDARY_PATTERNS)


def _copy_candidates(
    paths: Sequence[Path], *, repo_root: Path, limit: int
) -> tuple[CopyCandidate, ...]:
    candidates: list[CopyCandidate] = []
    for path in paths:
        rel_path = _relative(path, repo_root=repo_root)
        if not _is_ui_surface(rel_path) or _is_copy_boundary(rel_path):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for index, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith(("//", "#", "*")):
                continue
            if not OPERATOR_COPY_HINT.search(stripped):
                continue
            if not QUOTED_HUMAN_TEXT.search(stripped):
                continue
            candidates.append(
                CopyCandidate(path=rel_path, line=index, excerpt=stripped[:180])
            )
            if len(candidates) >= limit:
                return tuple(candidates)
    return tuple(candidates)


def _docs_locale_parity(repo_root: Path) -> LocaleParity:
    docs_english_root = repo_root / "docs" / "content" / "docs" / "en"
    docs_turkish_root = repo_root / "docs" / "content" / "docs" / "tr"
    home_english_root = repo_root / "docs" / "lib" / "home" / "content" / "en.ts"
    home_turkish_root = repo_root / "docs" / "lib" / "home" / "content" / "tr.ts"

    def _relative_files(root: Path, suffixes: set[str]) -> set[str]:
        if not root.exists():
            return set()
        return {
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file() and path.suffix in suffixes
        }

    def _single_file(file_path: Path) -> set[str]:
        if not file_path.exists():
            return set()
        return {file_path.name}

    english_files = _relative_files(docs_english_root, {".mdx", ".json"}) | _single_file(home_english_root)
    turkish_files = _relative_files(docs_turkish_root, {".mdx", ".json"}) | _single_file(home_turkish_root)
    return LocaleParity(
        english_only=tuple(sorted(english_files - turkish_files)),
        turkish_only=tuple(sorted(turkish_files - english_files)),
    )


def build_report(
    *,
    repo_root: Path = REPO_ROOT,
    roots: Iterable[str] = SCAN_ROOTS,
    function_threshold: int = 80,
    copy_candidate_limit: int = 80,
) -> AuditReport:
    paths = tuple(_iter_scan_files(repo_root, roots))
    return AuditReport(
        oversized_files=_oversized_files(paths, repo_root=repo_root),
        long_functions=_long_python_functions(
            paths, repo_root=repo_root, threshold=function_threshold
        ),
        repeated_helpers=_repeated_python_helpers(paths, repo_root=repo_root),
        copy_candidates=_copy_candidates(
            paths, repo_root=repo_root, limit=copy_candidate_limit
        ),
        docs_locale_parity=_docs_locale_parity(repo_root),
        scanned_files=len(paths),
    )


def _print_section(title: str, rows: Sequence[str]) -> None:
    print(f"\n{title}")
    if not rows:
        print("  none")
        return
    for row in rows:
        print(f"  {row}")


def print_report(report: AuditReport, *, top: int) -> None:
    print("modularity-i18n-audit: reporting-only")
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
            (
                f"{metric.path}:{metric.line} {metric.name} "
                f"lines={metric.lines}"
            )
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
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the report as JSON.",
    )
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
        help="Opt-in future gate mode. Defaults to reporting-only success.",
    )
    return parser.parse_args(list(argv))


def _has_findings(report: AuditReport) -> bool:
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


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    report = build_report(
        function_threshold=cast(int, args.function_threshold),
        copy_candidate_limit=cast(int, args.copy_candidate_limit),
    )
    if cast(bool, args.json):
        print(json.dumps(report.as_json(), indent=2, sort_keys=True))
    else:
        print_report(report, top=cast(int, args.top))
    return 1 if cast(bool, args.fail_on_findings) and _has_findings(report) else 0


if __name__ == "__main__":
    raise SystemExit(main())
