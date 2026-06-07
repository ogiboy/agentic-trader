from __future__ import annotations

import ast
import os
import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from pathlib import Path

from scripts.qa.modularity_i18n_modules.metrics import (
    CopyCandidate,
    FileMetric,
    FunctionMetric,
    HelperMetric,
    LocaleParity,
)

CODE_SUFFIXES = {".py", ".ts", ".tsx", ".mjs", ".js", ".css", ".md", ".mdx"}
SKIP_DIRS = {
    ".agents",
    ".claude",
    ".claude-flow",
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


def _relative(path: Path, *, repo_root: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def iter_scan_files(repo_root: Path, roots: Iterable[str]) -> Iterable[Path]:
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


def oversized_files(paths: Sequence[Path], *, repo_root: Path) -> tuple[FileMetric, ...]:
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


def long_python_functions(
    paths: Sequence[Path], *, repo_root: Path, threshold: int
) -> tuple[FunctionMetric, ...]:
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


def repeated_python_helpers(
    paths: Sequence[Path], *, repo_root: Path
) -> tuple[HelperMetric, ...]:
    helper_paths: defaultdict[str, set[str]] = defaultdict(set)
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


def copy_candidates(
    paths: Sequence[Path], *, repo_root: Path, limit: int
) -> tuple[CopyCandidate, ...]:
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


def docs_locale_parity(repo_root: Path) -> LocaleParity:
    docs_english_root = repo_root / "docs" / "content" / "docs" / "en"
    docs_turkish_root = repo_root / "docs" / "content" / "docs" / "tr"
    home_english_root = repo_root / "docs" / "lib" / "home" / "content" / "en.ts"
    home_turkish_root = repo_root / "docs" / "lib" / "home" / "content" / "tr.ts"

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
    return {"home.ts"}
