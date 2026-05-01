#!/usr/bin/env python3
"""Create the first stable changelog section when a baseline tag is needed."""

from __future__ import annotations

import argparse
import re
import subprocess
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CHANGELOG = ROOT / "CHANGELOG.md"
CATEGORIES = {
    "feat": "Features",
    "fix": "Fixes",
    "perf": "Performance",
    "docs": "Documentation",
    "ci": "CI",
    "build": "Build",
    "test": "Tests",
    "refactor": "Refactors",
    "chore": "Maintenance",
}


def _run_git(args: list[str]) -> str:
    return subprocess.check_output(  # noqa: S603
        ["git", *args],
        cwd=ROOT,
        stderr=subprocess.DEVNULL,
        text=True,
    ).strip()


def _display_version(value: str) -> str:
    stripped = value.strip()
    return stripped if stripped.startswith("v") else f"v{stripped}"


def changelog_has_version(text: str, version: str) -> bool:
    display = re.escape(_display_version(version))
    plain = re.escape(_display_version(version).removeprefix("v"))
    return re.search(rf"^##\s+\[?(?:{display}|{plain})\]?", text, re.MULTILINE) is not None


def _commit_category(subject: str) -> str | None:
    match = re.match(r"(?P<type>[a-z]+)(?:\([^)]+\))?!?:\s+(?P<title>.+)", subject)
    if match:
        return CATEGORIES.get(match.group("type"), "Other Changes")
    if subject.startswith("chore(release):"):
        return None
    if subject.startswith("Merge "):
        return None
    return "Other Changes"


def collect_commit_entries(*, since: str | None = None) -> dict[str, list[str]]:
    range_arg = f"{since}..HEAD" if since else "HEAD"
    raw = _run_git(["log", "--reverse", "--format=%H%x1f%s", range_arg])
    entries: dict[str, list[str]] = defaultdict(list)
    for line in raw.splitlines():
        if not line.strip():
            continue
        commit_hash, subject = line.split("\x1f", 1)
        category = _commit_category(subject)
        if category is None:
            continue
        entries[category].append(f"- {subject} ({commit_hash[:7]})")
    return dict(entries)


def render_section(
    *, version: str, date: str, entries: dict[str, list[str]]
) -> str:
    lines = [f"## {_display_version(version)} - {date}", ""]
    if not entries:
        lines.extend(["### Maintenance", "", "- Baseline release tag."])
        return "\n".join(lines)

    for category in CATEGORIES.values():
        items = entries.get(category)
        if not items:
            continue
        lines.extend([f"### {category}", "", *items, ""])
    other = entries.get("Other Changes")
    if other:
        lines.extend(["### Other Changes", "", *other, ""])
    return "\n".join(lines).rstrip()


def insert_section(text: str, section: str, *, version: str) -> str:
    if changelog_has_version(text, version):
        return text
    match = re.search(r"\n##\s+", text)
    if match:
        index = match.start() + 1
        return f"{text[:index]}{section}\n\n{text[index:]}"
    return f"{text.rstrip()}\n\n{section}\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a baseline changelog section for a stable tag."
    )
    parser.add_argument("--version", required=True)
    parser.add_argument("--since")
    parser.add_argument(
        "--date",
        default=datetime.now(tz=UTC).date().isoformat(),
        help="Release date to write in YYYY-MM-DD format.",
    )
    args = parser.parse_args()

    text = CHANGELOG.read_text(encoding="utf-8")
    if changelog_has_version(text, args.version):
        return 0
    entries = collect_commit_entries(since=args.since)
    section = render_section(version=args.version, date=args.date, entries=entries)
    CHANGELOG.write_text(
        insert_section(text, section, version=args.version),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
