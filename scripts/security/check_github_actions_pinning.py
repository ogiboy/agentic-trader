"""Fail when GitHub Actions workflow steps use mutable action refs."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

WORKFLOW_DIR = Path(".github/workflows")
USES_PATTERN = re.compile(r"^\s*uses:\s*([^@\s]+)@([^\s#]+)")
PINNED_SHA_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")


def tracked_workflows() -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", str(WORKFLOW_DIR)],
        text=True,
    )
    return [
        Path(line)
        for line in output.splitlines()
        if line.endswith((".yml", ".yaml"))
    ]


def main() -> int:
    failures: list[str] = []
    for workflow in tracked_workflows():
        for line_number, line in enumerate(workflow.read_text().splitlines(), 1):
            match = USES_PATTERN.match(line)
            if match is None:
                continue
            action, ref = match.groups()
            if action.startswith("./") or PINNED_SHA_PATTERN.fullmatch(ref):
                continue
            failures.append(f"{workflow}:{line_number}: {action}@{ref}")
    if failures:
        print("Mutable GitHub Action refs found. Pin actions to commit SHA:")
        print("\n".join(failures))
        return 1
    print("All GitHub Action refs are pinned to commit SHAs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
