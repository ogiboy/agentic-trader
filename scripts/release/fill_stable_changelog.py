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
    """
    Execute a git command in the repository root and return its stdout.
    
    Parameters:
        args (list[str]): Arguments to pass to the `git` command (e.g., `["log", "--oneline"]`).
    
    Returns:
        str: The command's standard output with surrounding whitespace removed.
    """
    return subprocess.check_output(  # noqa: S603
        ["git", *args],
        cwd=ROOT,
        stderr=subprocess.DEVNULL,
        text=True,
    ).strip()


def _display_version(value: str) -> str:
    """
    Normalize a version string to ensure it begins with a leading "v".
    
    Parameters:
        value (str): The version identifier to normalize; may include surrounding whitespace.
    
    Returns:
        str: The input trimmed of whitespace and prefixed with "v" if it did not already start with one.
    """
    stripped = value.strip()
    return stripped if stripped.startswith("v") else f"v{stripped}"


def _stable_version_tuple(value: str) -> tuple[int, int, int] | None:
    """
    Parse a version or tag string and return its major, minor, and patch components when it matches a stable `vMAJOR.MINOR.PATCH` form.
    
    Parameters:
        value (str): A version or git tag string (e.g., "v1.2.3" or "1.2.3").
    
    Returns:
        tuple[int, int, int]: `(major, minor, patch)` as integers if `value` matches a stable tag; `None` otherwise.
    """
    match = STABLE_TAG_PATTERN.match(_display_version(value))
    if not match:
        return None
    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
    )


def latest_previous_stable_tag(version: str) -> str | None:
    """
    Finds the most recent stable tag that is strictly earlier than the provided stable version.
    
    Parameters:
        version (str): Target stable version tag in the form `vMAJOR.MINOR.PATCH` or `MAJOR.MINOR.PATCH`.
    
    Returns:
        str | None: The tag string of the latest prior stable version, or `None` if no earlier stable tag is found.
    
    Raises:
        ValueError: If `version` is not a stable tag in `vMAJOR.MINOR.PATCH` format.
    """
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
    """
    Builds a compiled regex that locates the changelog section for the given stable version.
    
    The returned pattern matches a level-2 changelog header line for `version` (accepting either a `v`-prefixed form or the plain numeric form, and either plain or bracketed header text) and captures:
    - `header`: the header line including its trailing newline,
    - `body`: the section body up to the next `##` header or end of file.
    
    Parameters:
        version (str): Version identifier to locate (may include or omit a leading `v`).
    
    Returns:
        re.Pattern[str]: A compiled regex with multiline and dotall modes that captures the section `header` and `body`.
    """
    display = re.escape(_display_version(version))
    plain = re.escape(_display_version(version).removeprefix("v"))
    return re.compile(
        rf"(?ms)^(?P<header>##\s+\[?(?:{display}|{plain})\]?[^\n]*\n)"
        r"(?P<body>.*?)(?=^##\s+|\Z)"
    )


def section_has_release_items(body: str) -> bool:
    """
    Determine whether a changelog section body contains at least one release bullet item.
    
    Parameters:
        body (str): The changelog section text to inspect.
    
    Returns:
        True if the body contains at least one markdown bullet line beginning with `-` followed by non-whitespace, False otherwise.
    """
    return re.search(r"(?m)^-\s+\S", body) is not None


def _entry_title(subject: str) -> str:
    """
    Format a commit subject into a changelog entry title.
    
    If the subject matches the conventional-commit pattern, return the subject's `title` component with its first character capitalized; otherwise return the original subject unchanged.
    
    Parameters:
        subject (str): The commit subject line, possibly following conventional-commit syntax.
    
    Returns:
        str: The formatted title for a changelog entry.
    """
    match = CONVENTIONAL_PATTERN.match(subject)
    if not match:
        return subject
    title = match.group("title").strip()
    return title[:1].upper() + title[1:]


def _commit_category(subject: str) -> str | None:
    """
    Map a git commit subject to its changelog category or indicate it should be ignored.
    
    Parameters:
        subject (str): The commit subject line (first line of the commit message).
    
    Returns:
        str | None: The changelog category name for the commit (e.g., "Features", "Bug Fixes", "Other Changes"), or
        `None` when the commit should be skipped (release chores or merge commits).
    """
    if subject.startswith("chore(release):") or subject.startswith("Merge "):
        return None
    match = CONVENTIONAL_PATTERN.match(subject)
    if not match:
        return "Other Changes"
    return CATEGORIES.get(match.group("type"), "Other Changes")


def _format_entry(commit_hash: str, subject: str) -> str:
    """
    Format a single changelog bullet for a commit, including a capitalized title and a linked short commit hash.
    
    Returns:
        str: Markdown-formatted bullet item like "- Title\n  ([`abcdef0`](<commit_url>))".
    """
    short_hash = commit_hash[:7]
    return (
        f"- {_entry_title(subject)}\n"
        f"  ([`{short_hash}`]({COMMIT_URL_BASE}/{commit_hash}))"
    )


def collect_commit_entries(
    *, since: str | None, until: str = "HEAD"
) -> dict[str, list[str]]:
    """
    Collect changelog entries from git history within a commit range.
    
    Builds a mapping of changelog category names to lists of formatted markdown entries extracted
    from commits in the specified git range. The range is `"<since>..<until>"` when `since`
    is provided, otherwise `until` (defaults to `HEAD`).
    
    Parameters:
        since (str | None): Start identifier (inclusive) for the git range; when `None`, search
            from repository start up to `until`.
        until (str): End identifier for the git range (defaults to `"HEAD"`).
    
    Returns:
        dict[str, list[str]]: A dictionary where each key is a changelog category name (e.g.,
        "Features", "Bug Fixes", "Other Changes") and each value is a list of formatted
        markdown bullet lines for commits in that category. Merge commits and commits that are
        explicitly ignored by the categorization rules are excluded.
    """
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
    """
    Render the markdown body for a changelog release from categorized entry lists.
    
    Takes a mapping of category names to lists of already-formatted changelog entry lines and emits a markdown string composed of ordered `### <Category>` sections (following the order of CATEGORIES.values()). Categories with no entries are omitted; entries under "Other Changes" are appended last. Leading/trailing blank lines are normalized and the final string is trimmed of trailing whitespace.
    
    Parameters:
        entries (dict[str, list[str]]): Mapping from category name to a list of markdown-formatted entry lines (each typically starting with "- ").
    
    Returns:
        str: The rendered markdown body for the release section.
    
    Raises:
        ValueError: If `entries` is empty.
    """
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
    """
    Fill the changelog section for a given stable version with rendered release entries if the section is empty.
    
    Parameters:
    	text (str): Full contents of CHANGELOG.md.
    	entries (dict[str, list[str]]): Mapping of category names to lists of formatted changelog bullet lines to insert.
    	version (str): Target stable version identifier (e.g., "v1.2.3" or "1.2.3") whose section should be filled.
    
    Returns:
    	Updated CHANGELOG.md text with the target section body replaced by the rendered entries if it was empty; otherwise returns the original text unchanged.
    
    Raises:
    	ValueError: If no section header for the specified version exists in the provided text.
    """
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
    """
    Backfill an empty stable release section in CHANGELOG.md using conventional commits.
    
    Parses CLI arguments:
    - --version (required): target stable version whose changelog section will be filled.
    - --since (optional): git ref to start the commit range; when omitted, the previous stable tag before --version is used.
    - --until (optional): git ref to end the commit range; defaults to the provided --version.
    
    Reads CHANGELOG.md, collects conventional-commit entries from the specified git range, replaces the target version's changelog section if it is empty with rendered release entries, and writes the updated file.
    
    Returns:
        int: Exit status code `0` on success.
    """
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
