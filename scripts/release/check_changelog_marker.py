#!/usr/bin/env python3
"""Validate the semantic-release changelog insertion marker."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHANGELOG = ROOT / "CHANGELOG.md"
MARKER = "<!-- version list -->"


def main() -> int:
    text = CHANGELOG.read_text(encoding="utf-8")
    count = text.count(MARKER)
    if count == 1:
        return 0

    qualifier = "missing" if count == 0 else f"present {count} times"
    print(
        f"{CHANGELOG.relative_to(ROOT)} must contain {MARKER!r} exactly once; "
        f"it is {qualifier}.",
        file=sys.stderr,
    )
    print(
        "python-semantic-release update mode uses this marker to prepend release notes.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
