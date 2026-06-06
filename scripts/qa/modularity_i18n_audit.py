#!/usr/bin/env python3
"""Audit project-wide modularity and i18n debt for reports and CI gates."""

from __future__ import annotations

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

from scripts.qa.modularity_i18n_modules.cli import (
    parse_args,
    print_report,
    should_fail_gate,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_ROOTS = (
    "agentic_trader", "webgui/src", "docs", "tui", "scripts", "tools",
    "sidecars/research_flow", ".ai",
)
CODE_SUFFIXES = {".py", ".ts", ".tsx", ".mjs", ".js", ".css", ".md", ".mdx"}
SKIP_DIRS = {
    ".agents", ".claude", ".claude-flow",
    ".git",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".sonar",
    ".venv",
    "__pycache__",
    "artifacts",
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
    "copy.ts",
    "copy.mjs",
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
COMMENT_PREFIXES = ("//", "#", "*")
STYLE_TOKEN = re.compile(r"^[A-Za-z0-9_@*/:.[\]()#%<>=!+-]+$")
STYLE_TOKEN_MARKERS = ("-", "/", ":", "[", "]", "*", "@")


@dataclass(frozen=True)
class FileMetric:
    path: str
    lines: int
    threshold: int
    category: str

    def as_json(self) -> dict[str, object]:
        """
        Serialize the file metric into a JSON-serializable dictionary.

        Returns:
            A dict with keys:
              - `path`: file path as a string
              - `lines`: number of lines in the file (int)
              - `threshold`: configured line threshold for this file (int)
              - `category`: category name used to choose the threshold (str)
        """
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
        """
        Serialize the function metric into a JSON-serializable dictionary.

        Returns:
            dict[str, object]: Dictionary with keys "path" (file path of the function),
            "name" (function name), "line" (starting line number), and "lines"
            (number of lines in the function).
        """
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
        """
        Serialize the helper metric to a JSON-serializable dictionary.

        Returns:
            A dictionary with keys:
            - `name`: the helper function's name (str).
            - `paths`: a list of file path strings where the helper appears.
            - `count`: the number of distinct paths (int).
        """
        return {"name": self.name, "paths": list(self.paths), "count": len(self.paths)}


@dataclass(frozen=True)
class CopyCandidate:
    path: str
    line: int
    excerpt: str

    def as_json(self) -> dict[str, object]:
        """
        Serialize the copy candidate into a JSON-serializable dictionary.

        Returns:
            dict[str, object]: Dictionary with keys "path" (file path), "line" (1-based line number), and "excerpt" (text excerpt).
        """
        return {"path": self.path, "line": self.line, "excerpt": self.excerpt}


@dataclass(frozen=True)
class LocaleParity:
    english_only: tuple[str, ...]
    turkish_only: tuple[str, ...]

    def as_json(self) -> dict[str, object]:
        """
        Convert the locale parity data into a JSON-serializable dictionary.

        Returns:
            dict[str, object]: A mapping with keys "english_only" and "turkish_only", each containing a list of file names present only in that locale.
        """
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
        """
        Serialize the audit report into a JSON-serializable dictionary.

        The returned dictionary contains the following keys:
        - "scanned_files": total number of files scanned (int).
        - "oversized_files": list of oversized file metrics as dictionaries.
        - "long_functions": list of long Python function metrics as dictionaries.
        - "repeated_helpers": list of repeated helper metrics as dictionaries.
        - "copy_candidates": list of hardcoded copy candidate entries as dictionaries.
        - "docs_locale_parity": documentation locale parity information as a dictionary.

        Returns:
            dict[str, object]: A mapping suitable for JSON serialization representing the report.
        """
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
    """
    Return the POSIX-style path of `path` relative to `repo_root`.

    Parameters:
        path (Path): The path to relativize.
        repo_root (Path): The repository root to use as the base for the relative path.

    Returns:
        rel_path (str): POSIX-style relative path from `repo_root` to `path`.
    """
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def _iter_scan_files(repo_root: Path, roots: Iterable[str]) -> Iterable[Path]:
    """
    Yield all file paths under the given repository roots that match configured code suffixes.

    Parameters:
        repo_root (Path): Base repository directory used to resolve each root name.
        roots (Iterable[str]): Iterable of file or directory names (relative to repo_root) to scan.

    Returns:
        Iterable[Path]: Paths to files that should be scanned; each path is under `repo_root` and has a suffix present in `CODE_SUFFIXES`. Missing roots are ignored and directories listed in `SKIP_DIRS` are excluded.
    """
    for root_name in roots:
        yield from _iter_matching_files(repo_root / root_name, suffixes=CODE_SUFFIXES)


def _iter_matching_files(root: Path, *, suffixes: set[str]) -> Iterable[Path]:
    if root.is_file():
        if root.suffix in suffixes:
            yield root
        return
    if not root.exists():
        return
    for current_root, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
        current = Path(current_root)
        for file_name in files:
            path = current / file_name
            if path.suffix in suffixes:
                yield path


def _line_threshold(path: Path, rel_path: str) -> tuple[str, int]:
    """
    Selects a category label and line-count threshold for a file based on its path.

    Parameters:
        path (Path): File system path to the file.
        rel_path (str): Repository-relative POSIX-style path for the file.

    Returns:
        tuple[str, int]: A pair (category, threshold) where `category` is a short label
        describing the file type and `threshold` is the line-count limit for that category.
    """
    if ".test." in path.name:
        return "test", 700
    if rel_path == "tools/camofox-browser/server.js":
        return "tool-entrypoint", 450
    if rel_path == "scripts/qa/modularity_i18n_audit.py":
        return "qa-audit-entrypoint", 700
    if rel_path.startswith("scripts/qa/") and path.parent.name == "qa":
        return "qa-entrypoint", 650
    if rel_path.startswith("scripts/") and not rel_path.startswith("scripts/lib/"):
        if path.suffix in {".js", ".mjs"}:
            return "lifecycle-entrypoint", 280
    if "/copy/" in f"/{rel_path}" or rel_path in {"tui/copy.mjs", "tui/src/copy.mjs"}:
        return "copy-catalog", 450
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
    if path.suffix == ".js":
        return "javascript-module", 450
    if path.suffix == ".mdx":
        return "docs-page", 280
    return "source-file", 500


def _oversized_files(
    paths: Sequence[Path], *, repo_root: Path
) -> tuple[FileMetric, ...]:
    """
    Collect metrics for files whose line counts exceed category-specific thresholds.

    Files that cannot be decoded as UTF-8 are ignored; each returned FileMetric records the file's repository-relative path, its line count, the threshold used, and the category. The results are sorted by `lines` in descending order.

    Returns:
        tuple[FileMetric, ...]: Metrics for files with line counts greater than their threshold, sorted by descending line count.
    """
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
    """
    Parse the Python source at the given path into an AST; return None if parsing or decoding fails.

    Returns:
        ast.Module or None: The parsed AST for the file, or `None` if the file could not be decoded as UTF-8 or contains a syntax error.
    """
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return None


def _long_python_functions(
    paths: Sequence[Path], *, repo_root: Path, threshold: int
) -> tuple[FunctionMetric, ...]:
    """
    Find Python functions whose body length is greater than or equal to the given threshold.

    Parameters:
        paths (Sequence[Path]): Files to inspect; only files with a `.py` suffix are considered.
        repo_root (Path): Repository root used to compute relative paths stored in each metric.
        threshold (int): Minimum number of lines a function must have to be reported.

    Returns:
        tuple[FunctionMetric, ...]: Function metrics for functions meeting the threshold, sorted by `lines` descending.
    """
    metrics: list[FunctionMetric] = []
    for path in paths:
        metrics.extend(
            _long_function_metrics_for_path(
                path,
                repo_root=repo_root,
                threshold=threshold,
            )
        )
    return tuple(sorted(metrics, key=lambda metric: metric.lines, reverse=True))


def _long_function_metrics_for_path(
    path: Path, *, repo_root: Path, threshold: int
) -> tuple[FunctionMetric, ...]:
    if path.suffix != ".py":
        return ()
    tree = _python_tree(path)
    if tree is None:
        return ()
    rel_path = _relative(path, repo_root=repo_root)
    return tuple(
        metric
        for node in ast.walk(tree)
        if (metric := _long_function_metric(node, rel_path, threshold)) is not None
    )


def _long_function_metric(
    node: ast.AST, rel_path: str, threshold: int
) -> FunctionMetric | None:
    if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        return None
    end_line = node.end_lineno
    if end_line is None:
        return None
    function_lines = end_line - node.lineno + 1
    if function_lines < threshold:
        return None
    return FunctionMetric(
        path=rel_path,
        name=node.name,
        line=node.lineno,
        lines=function_lines,
    )


def _repeated_python_helpers(
    paths: Sequence[Path], *, repo_root: Path
) -> tuple[HelperMetric, ...]:
    """
    Identify helper functions from the allowlist that appear in at least three distinct Python files.

    Scans the provided paths for Python files, records occurrences of function definitions whose names are in HELPER_NAME_ALLOWLIST, and returns metrics for helpers found in three or more distinct files. Reported file paths are relative to `repo_root`.

    Parameters:
        repo_root (Path): Base path used to compute relative file paths for reported metrics.

    Returns:
        tuple[HelperMetric, ...]: Metrics for each repeated helper, sorted by descending number of distinct file paths.
    """
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
    """
    Determine whether a repository-relative path is considered a UI surface.

    Parameters:
        rel_path (str): Path relative to the repository root.

    Returns:
        True if `rel_path` begins with any prefix in `UI_SURFACE_PATTERNS`, False otherwise.
    """
    return any(rel_path.startswith(pattern) for pattern in UI_SURFACE_PATTERNS)


def _is_copy_boundary(rel_path: str) -> bool:
    """
    Determine whether a repository-relative path falls under any configured copy boundary.

    Parameters:
        rel_path (str): Path relative to the repository root (POSIX-style, without a leading slash).

    Returns:
        True if the path contains any substring from COPY_BOUNDARY_PATTERNS, False otherwise.
    """
    normalized = f"/{rel_path}"
    return any(pattern in normalized for pattern in COPY_BOUNDARY_PATTERNS)


def _copy_candidates(
    paths: Sequence[Path], *, repo_root: Path, limit: int
) -> tuple[CopyCandidate, ...]:
    """
    Collect UI-facing hardcoded text candidates from the given file paths.

    Scans files under configured UI surface paths (relative to repo_root), skipping files that match copy boundary patterns or fail UTF-8 decoding. Lines that are blank or start with comment markers are ignored; a line is recorded as a candidate when it matches both the operator-copy hint pattern and the quoted-human-text pattern. Scanning stops early once the number of collected candidates reaches `limit`.

    Parameters:
        paths (Sequence[Path]): Files to scan.
        repo_root (Path): Repository root used to compute relative file paths.
        limit (int): Maximum number of candidates to collect.

    Returns:
        tuple[CopyCandidate, ...]: Collected copy candidates in discovery order, up to `limit`.
    """
    candidates: list[CopyCandidate] = []
    for path in paths:
        for candidate in _copy_candidates_for_path(path, repo_root=repo_root):
            candidates.append(candidate)
            if len(candidates) >= limit:
                return tuple(candidates)
    return tuple(candidates)


def _copy_candidates_for_path(
    path: Path, *, repo_root: Path
) -> tuple[CopyCandidate, ...]:
    rel_path = _relative(path, repo_root=repo_root)
    if not _is_ui_surface(rel_path) or _is_copy_boundary(rel_path):
        return ()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return ()
    return tuple(
        candidate
        for index, line in enumerate(lines, start=1)
        if (candidate := _copy_candidate(rel_path, index, line)) is not None
    )


def _copy_candidate(rel_path: str, line_number: int, line: str) -> CopyCandidate | None:
    stripped = line.strip()
    if not stripped or stripped.startswith(COMMENT_PREFIXES):
        return None
    if "typeof " in stripped:
        return None
    if not OPERATOR_COPY_HINT.search(stripped):
        return None
    quoted_values = QUOTED_HUMAN_TEXT.findall(stripped)
    if not quoted_values:
        return None
    if all(_looks_like_style_literal(value) for value in quoted_values):
        return None
    return CopyCandidate(path=rel_path, line=line_number, excerpt=stripped[:180])


def _looks_like_style_literal(value: str) -> bool:
    tokens = value.split()
    if len(tokens) < 2:
        return False
    if not all(STYLE_TOKEN.fullmatch(token) for token in tokens):
        return False
    marked_tokens = sum(
        1 for token in tokens if any(marker in token for marker in STYLE_TOKEN_MARKERS)
    )
    return marked_tokens >= max(1, len(tokens) // 2)


def _docs_locale_parity(repo_root: Path) -> LocaleParity:
    """
    Compute locale parity between English and Turkish docs under the repository.

    Searches the expected documentation directories and returns files that exist only in English or only in Turkish. It considers:
    - docs/content/docs/en and docs/content/docs/tr for `.mdx` and `.json` files (compared by path relative to those roots),
    - docs/lib/home/content/en.ts and docs/lib/home/content/tr.ts as single-file entries.

    Parameters:
        repo_root (Path): Repository root directory to resolve documentation paths against.

    Returns:
        LocaleParity: dataclass with
            english_only: tuple of file paths (POSIX-style, relative to the English doc root) present only in English,
            turkish_only: tuple of file paths present only in Turkish.
    """
    docs_english_root = repo_root / "docs" / "content" / "docs" / "en"
    docs_turkish_root = repo_root / "docs" / "content" / "docs" / "tr"
    home_english_root = repo_root / "docs" / "lib" / "home" / "content" / "en.ts"
    home_turkish_root = repo_root / "docs" / "lib" / "home" / "content" / "tr.ts"

    def _relative_files(root: Path, suffixes: set[str]) -> set[str]:
        """
        Collect relative POSIX paths for files under a directory that have one of the given suffixes.

        Parameters:
            root (Path): Directory to search. If it does not exist, the result is empty.
            suffixes (set[str]): File suffixes to include (for example, {'.mdx', '.json'}).

        Returns:
            set[str]: POSIX-style paths (relative to `root`) of matching files; empty if `root` does not exist.
        """
        if not root.exists():
            return set()
        return {
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file() and path.suffix in suffixes
        }

    def _single_file(file_path: Path) -> set[str]:
        """
        Produce a set containing the file's name if the given path exists.

        Returns:
            A set with the file's basename (e.g., {'README.mdx'}) when `file_path` exists, otherwise an empty set.
        """
        if not file_path.exists():
            return set()
        return {"home.ts"}

    english_files = _relative_files(
        docs_english_root, {".mdx", ".json"}
    ) | _single_file(home_english_root)
    turkish_files = _relative_files(
        docs_turkish_root, {".mdx", ".json"}
    ) | _single_file(home_turkish_root)
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
    return 1 if should_fail_gate(
        report,
        fail_on_findings=cast(bool, args.fail_on_findings),
    ) else 0


if __name__ == "__main__":
    raise SystemExit(main())
