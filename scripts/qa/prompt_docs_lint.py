#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPT_DOC_SUFFIXES = (".instructions.md", ".agent.md", ".prompt.md")
SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".sonar",
    ".venv",
    "__pycache__",
    "node_modules",
    "runtime",
}
GENERATED_TOOL_STATE_NAMES = {
    ".claude",
    ".claude-flow",
    ".swarm",
    ".mcp.json",
    "CLAUDE.md",
}

ERROR_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("undefined double-brace placeholder", re.compile(r"\{\{[A-Z][A-Z0-9_]*\}\}")),
    ("template filler text", re.compile(r"\bReplace this line\b")),
    ("unfinished TODO/TBD marker", re.compile(r"\b(?:TODO|TBD)\b")),
    (
        "legacy .ai markdown reference",
        re.compile(
            r"\.ai/[^\s`),\]]+(?<!\.instructions)(?<!\.agent)(?<!\.prompt)\.md\b"
        ),
    ),
    ("legacy AGENTS.md reference", re.compile(r"(?<![\w./-])AGENTS\.md\b")),
)

SOFT_COVERAGE_TERMS = re.compile(
    r"\b("
    r"missing|unavailable|fallback|fail|failure|blocked|skip|skipped|record|"
    r"report|degraded|stale|incomplete|conflict|priority"
    r")\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Finding:
    severity: str
    path: Path
    line: int
    message: str
    excerpt: str

    def format(self) -> str:
        rel = self.path.relative_to(REPO_ROOT)
        return f"{self.severity}: {rel}:{self.line}: {self.message}: {self.excerpt}"


def _iter_prompt_docs(roots: Iterable[Path]) -> Iterable[Path]:
    for root in roots:
        if root.is_file():
            if root.name.endswith(PROMPT_DOC_SUFFIXES):
                yield root
            continue
        if not root.exists():
            continue
        for current_root, dirs, files in os.walk(root):
            dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
            current = Path(current_root)
            for file_name in files:
                path = current / file_name
                if path.name.endswith(PROMPT_DOC_SUFFIXES):
                    yield path


def _line_findings(path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    for index, line in enumerate(text.splitlines(), start=1):
        for message, pattern in ERROR_PATTERNS:
            if pattern.search(line):
                findings.append(
                    Finding("error", path, index, message, line.strip()[:180])
                )
    return findings


def _coverage_findings(path: Path, text: str) -> list[Finding]:
    if SOFT_COVERAGE_TERMS.search(text):
        return []
    return [
        Finding(
            "warning",
            path,
            1,
            "no explicit missing/unavailable/fallback/conflict behavior detected",
            "add a short failure-mode note if this file is task-like guidance",
        )
    ]


def _generated_state_findings() -> list[Finding]:
    findings: list[Finding] = []
    for current_root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
        current = Path(current_root)
        if "example" in current.relative_to(REPO_ROOT).parts:
            continue
        for name in list(dirs) + files:
            if name in GENERATED_TOOL_STATE_NAMES:
                findings.append(
                    Finding(
                        "error",
                        current / name,
                        1,
                        "generated assistant/tool state must not live in repo state",
                        name,
                    )
                )
    return findings


def lint(
    paths: Iterable[Path], *, strict_coverage: bool
) -> tuple[list[Finding], list[Finding]]:
    errors: list[Finding] = []
    warnings: list[Finding] = []
    seen: set[Path] = set()
    for path in sorted(set(_iter_prompt_docs(paths))):
        if path in seen:
            continue
        seen.add(path)
        text = path.read_text(encoding="utf-8")
        errors.extend(_line_findings(path, text))
        coverage = _coverage_findings(path, text)
        if strict_coverage:
            errors.extend(coverage)
        else:
            warnings.extend(coverage)
    errors.extend(_generated_state_findings())
    return errors, warnings


def parse_args(argv: list[str]) -> argparse.Namespace:
    if argv[:1] == ["--"]:
        argv = argv[1:]
    parser = argparse.ArgumentParser(
        description="Lint Agentic Trader prompt, agent, and instruction markdown files."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[REPO_ROOT],
        help="Files or directories to scan. Defaults to repo prompt/instruction roots.",
    )
    parser.add_argument(
        "--strict-coverage",
        action="store_true",
        help="Treat soft semantic coverage warnings as errors.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    roots = [path if path.is_absolute() else REPO_ROOT / path for path in args.paths]
    errors, warnings = lint(roots, strict_coverage=args.strict_coverage)
    scanned = len(set(_iter_prompt_docs(roots)))

    for finding in warnings:
        print(finding.format())
    for finding in errors:
        print(finding.format())

    print(
        f"prompt-docs-lint: scanned={scanned} errors={len(errors)} warnings={len(warnings)}"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
