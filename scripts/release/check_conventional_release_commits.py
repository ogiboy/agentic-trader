#!/usr/bin/env python3
"""Validate release-range commit subjects before semantic-release runs."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STABLE_TAG_PATTERN = re.compile(r"^v\d+\.\d+\.\d+$")
CONVENTIONAL_SUBJECT_PATTERN = re.compile(
    r"^(feat|fix|perf|docs|build|ci|chore|refactor|test|style)"
    r"(?:\([^)]+\))?!?:\s+\S.+"
)
RELEASE_SUBJECT_PATTERN = re.compile(r"^chore\(release\):")
LEGACY_NONCONVENTIONAL_SUBJECTS = {
    "e0604a96dd8b8c7d2fb9d7e62a65babf70e25162": "Harden release changelog coverage",
    "6a8bdbd60423a543eceeab1e292aacf0fd8d718b": "📝 Add docstrings to `refactor/modularity-i18n-completion-v2`",
    "000ed4f4d37efad3c6dc125da83a4fa43af1b0ad": "📝 CodeRabbit Chat: Add generated unit tests",
}


def _run_git(args: list[str]) -> str:
    return subprocess.check_output(  # noqa: S603
        ["git", *args],
        cwd=ROOT,
        stderr=subprocess.DEVNULL,
        text=True,
    ).strip()


def _latest_stable_tag() -> str | None:
    raw_tags = _run_git(["tag", "--merged", "HEAD", "--sort=-v:refname"])
    for tag in raw_tags.splitlines():
        if STABLE_TAG_PATTERN.match(tag):
            return tag
    return None


def _release_range(tag: str | None) -> str:
    return f"{tag}..HEAD" if tag else "HEAD"


def main() -> int:
    latest_tag = _latest_stable_tag()
    raw_commits = _run_git(
        ["log", "--format=%H%x1f%P%x1f%s", _release_range(latest_tag)]
    )
    invalid: list[str] = []
    for line in raw_commits.splitlines():
        commit_hash, parents, subject = line.split("\x1f", 2)
        if RELEASE_SUBJECT_PATTERN.match(subject) or len(parents.split()) > 1:
            continue
        if LEGACY_NONCONVENTIONAL_SUBJECTS.get(commit_hash) == subject:
            continue
        if not CONVENTIONAL_SUBJECT_PATTERN.match(subject):
            invalid.append(f"{commit_hash[:7]} {subject}")

    if not invalid:
        return 0

    since = latest_tag or "repository start"
    print(
        f"Release commits since {since} must use conventional commit subjects.",
        file=sys.stderr,
    )
    print(
        "Use feat:, fix:, docs:, chore:, ci:, build:, perf:, refactor:, test:, or style:.",
        file=sys.stderr,
    )
    for entry in invalid:
        print(f"- {entry}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
