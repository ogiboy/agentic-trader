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
    """
    Check whether the changelog text contains a top-level header for the given version.

    Matches headings that start with "##", optionally wrapped in square brackets, and accepts the version with or without a leading "v".

    Parameters:
        text (str): Full changelog contents to search.
        version (str): Version identifier to look for; may include or omit a leading "v".

    Returns:
        bool: `True` if a matching version header is present, `False` otherwise.
    """
    display = re.escape(_display_version(version))
    plain = re.escape(_display_version(version).removeprefix("v"))
    return (
        re.search(rf"^##\s+\[?(?:{display}|{plain})\]?", text, re.MULTILINE) is not None
    )


def _commit_category(subject: str) -> str | None:
    """
    Map a git commit subject line to a changelog category or indicate it should be excluded.

    Parameters:
        subject (str): The commit subject line (the first line of a commit message).

    Returns:
        str | None: The matched category name from CATEGORIES, `"Other Changes"` when the subject is a conventional commit type not in CATEGORIES or not matching conventional commit format, or `None` to indicate the commit should be excluded (for `chore(release):` and merge commits).
    """
    match = re.match(r"(?P<type>[a-z]+)(?:\([^)]+\))?!?:\s+(?P<title>.+)", subject)
    if match:
        return CATEGORIES.get(match.group("type"), "Other Changes")
    if subject.startswith("chore(release):"):
        return None
    if subject.startswith("Merge "):
        return None
    return "Other Changes"


def collect_commit_entries(*, since: str | None = None) -> dict[str, list[str]]:
    """
    Collects commit subjects from git history and groups them into changelog categories.

    Parameters:
        since (str | None): A git revision (commit, tag, or ref) used as the start of the log range. If provided the range is "<since>..HEAD"; if omitted the log is taken starting at "HEAD".

    Returns:
        dict[str, list[str]]: Mapping from changelog category title to a list of entries. Each entry is a formatted bullet string: "- <subject> (<short_hash>)".
    """
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


def render_section(*, version: str, date: str, entries: dict[str, list[str]]) -> str:
    """
    Render a changelog section for the given version and date from categorized entries.

    Parameters:
        version (str): Version label (will be normalized to start with `v`).
        date (str): Release date as an ISO-formatted string (YYYY-MM-DD).
        entries (dict[str, list[str]]): Mapping of subsection titles to lists of bullet lines; use an empty dict to generate a Maintenance baseline entry.

    Returns:
        section (str): The formatted changelog section text ready to insert into CHANGELOG.md. If `entries` is empty, the section contains a `Maintenance` subsection with a baseline note; otherwise it contains subsections in the configured category order and an `Other Changes` subsection when present.
    """
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
