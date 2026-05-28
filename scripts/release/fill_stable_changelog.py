#!/usr/bin/env python3
"""Backfill an empty stable changelog section from the previous stable tag."""

from __future__ import annotations

import argparse
import re
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHANGELOG = ROOT / "CHANGELOG.md"
COMMIT_URL_BASE = "https://github.com/ogiboy/agentic-trader/commit"
STABLE_TAG_PATTERN = re.compile(r"^v(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$")
CONVENTIONAL_PATTERN = re.compile(
    r"(?P<type>[a-z]+)(?:\((?P<scope>[^)]+)\))?!?:\s+(?P<title>.+)"
)
CATEGORIES = {
    "feat": "Features",
    "fix": "Bug Fixes",
    "perf": "Performance",
    "docs": "Documentation",
    "ci": "Continuous Integration",
    "build": "Build System",
    "test": "Tests",
    "refactor": "Refactors",
    "style": "Styles",
    "chore": "Chores",
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


def _stable_version_tuple(value: str) -> tuple[int, int, int] | None:
    match = STABLE_TAG_PATTERN.match(_display_version(value))
    if not match:
        return None
    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
    )


def latest_previous_stable_tag(version: str) -> str | None:
    target = _stable_version_tuple(version)
    if target is None:
        raise ValueError(f"{version!r} is not a stable vMAJOR.MINOR.PATCH tag")

    best_tag: str | None = None
    best_version: tuple[int, int, int] | None = None
    raw_tags = _run_git(["tag", "--merged", "HEAD", "--sort=-v:refname"])
    for tag in raw_tags.splitlines():
        parsed = _stable_version_tuple(tag)
        if parsed is None or parsed >= target:
            continue
        if best_version is None or parsed > best_version:
            best_tag = tag
            best_version = parsed
    return best_tag


def _section_pattern(version: str) -> re.Pattern[str]:
    display = re.escape(_display_version(version))
    plain = re.escape(_display_version(version).removeprefix("v"))
    return re.compile(
        rf"(?ms)^(?P<header>##\s+\[?(?:{display}|{plain})\]?[^\n]*\n)"
        r"(?P<body>.*?)(?=^##\s+|\Z)"
    )


def section_has_release_items(body: str) -> bool:
    return re.search(r"(?m)^-\s+\S", body) is not None


def _entry_title(subject: str) -> str:
    match = CONVENTIONAL_PATTERN.match(subject)
    if not match:
        return subject
    title = match.group("title").strip()
    return title[:1].upper() + title[1:]


def _commit_category(subject: str) -> str | None:
    if subject.startswith("chore(release):") or subject.startswith("Merge "):
        return None
    match = CONVENTIONAL_PATTERN.match(subject)
    if not match:
        return "Other Changes"
    return CATEGORIES.get(match.group("type"), "Other Changes")


def _format_entry(commit_hash: str, subject: str) -> str:
    short_hash = commit_hash[:7]
    return (
        f"- {_entry_title(subject)}\n"
        f"  ([`{short_hash}`]({COMMIT_URL_BASE}/{commit_hash}))"
    )


def collect_commit_entries(
    *, since: str | None, until: str = "HEAD"
) -> dict[str, list[str]]:
    range_arg = f"{since}..{until}" if since else until
    raw = _run_git(["log", "--reverse", "--no-merges", "--format=%H%x1f%s", range_arg])
    entries: dict[str, list[str]] = defaultdict(list)
    for line in raw.splitlines():
        if not line.strip():
            continue
        commit_hash, subject = line.split("\x1f", 1)
        category = _commit_category(subject)
        if category is None:
            continue
        entries[category].append(_format_entry(commit_hash, subject))
    return dict(entries)


def render_body(entries: dict[str, list[str]]) -> str:
    if not entries:
        raise ValueError("stable changelog backfill found no release entries")

    lines: list[str] = []
    for category in CATEGORIES.values():
        items = entries.get(category)
        if not items:
            continue
        lines.extend([f"### {category}", "", *items, ""])
    other = entries.get("Other Changes")
    if other:
        lines.extend(["### Other Changes", "", *other, ""])
    return "\n".join(lines).rstrip()


def fill_empty_section(
    text: str, *, entries: dict[str, list[str]], version: str
) -> str:
    match = _section_pattern(version).search(text)
    if match is None:
        raise ValueError(f"CHANGELOG.md has no section for {_display_version(version)}")
    if section_has_release_items(match.group("body")):
        return text

    tail = text[match.end("body") :].lstrip("\n")
    return (
        text[: match.start("body")]
        + "\n"
        + render_body(entries)
        + "\n\n"
        + tail
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fill an empty stable changelog section from conventional commits "
            "since the previous stable tag, ignoring prerelease tags."
        )
    )
    parser.add_argument("--version", required=True)
    parser.add_argument("--since")
    parser.add_argument("--until", default=None)
    args = parser.parse_args()

    since = args.since or latest_previous_stable_tag(args.version)
    until = args.until or args.version
    text = CHANGELOG.read_text(encoding="utf-8")
    entries = collect_commit_entries(since=since, until=until)
    CHANGELOG.write_text(
        fill_empty_section(text, entries=entries, version=args.version),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
