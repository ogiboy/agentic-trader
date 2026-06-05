#!/usr/bin/env python3
"""Render GitHub Release notes from CHANGELOG.md."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHANGELOG = ROOT / "CHANGELOG.md"
DEFAULT_REPO_URL = "https://github.com/ogiboy/agentic-trader"


def _display_version(value: str) -> str:
    stripped = value.strip()
    return stripped if stripped.startswith("v") else f"v{stripped}"


def _section_pattern(version: str) -> re.Pattern[str]:
    display = re.escape(_display_version(version))
    plain = re.escape(_display_version(version).removeprefix("v"))
    return re.compile(
        rf"(?ms)^(?P<header>##\s+\[?(?:{display}|{plain})\]?[^\n]*\n)"
        r"(?P<body>.*?)(?=^##\s+|\Z)"
    )


def changelog_body(text: str, version: str) -> str | None:
    match = _section_pattern(version).search(text)
    if match is None:
        return None
    body = match.group("body").strip()
    return body or None


def changelog_url(*, repo_url: str, ref: str) -> str:
    return f"{repo_url.rstrip('/')}/blob/{ref}/CHANGELOG.md"


def render_release_notes(
    *,
    version: str,
    changelog_text: str,
    repo_url: str = DEFAULT_REPO_URL,
    run_url: str | None = None,
    stable: bool = False,
    channel: str | None = None,
    branch: str | None = None,
    short_sha: str | None = None,
) -> str:
    tag = _display_version(version)
    link_ref = tag if stable else (short_sha or branch or "main")
    body = changelog_body(changelog_text, tag)
    lines: list[str] = []

    if stable:
        lines.append(f"Stable release build for `{tag}`.")
        lines.append("")
        if body:
            lines.extend(["## Changes", "", body, ""])
        else:
            lines.extend(
                [
                    "## Changes",
                    "",
                    "No changelog entries were found for this release tag.",
                    "",
                ]
            )
    else:
        lines.append(f"Automated {channel or 'preview'} preview build for `{branch or tag}`.")
        lines.append("")
        if channel:
            lines.append(f"- Channel: `{channel}`")
        if short_sha:
            lines.append(f"- Commit: `{short_sha}`")
        if branch:
            lines.append(f"- Branch: `{branch}`")
        lines.append("")
        lines.append(
            "This prerelease is intended for branch testing. Stable releases are "
            "produced from `main`."
        )
        lines.append("")

    lines.append(f"Full changelog: {changelog_url(repo_url=repo_url, ref=link_ref)}")
    if run_url:
        lines.append(f"Workflow run: {run_url}")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--repo-url", default=DEFAULT_REPO_URL)
    parser.add_argument("--run-url")
    parser.add_argument("--stable", action="store_true")
    parser.add_argument("--channel")
    parser.add_argument("--branch")
    parser.add_argument("--short-sha")
    args = parser.parse_args()

    notes = render_release_notes(
        version=args.version,
        changelog_text=CHANGELOG.read_text(encoding="utf-8"),
        repo_url=args.repo_url,
        run_url=args.run_url,
        stable=args.stable,
        channel=args.channel,
        branch=args.branch,
        short_sha=args.short_sha,
    )
    Path(args.output).write_text(notes, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
