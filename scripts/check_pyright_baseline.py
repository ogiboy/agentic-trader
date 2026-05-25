#!/usr/bin/env python3
"""Run strict Pyright and require a clean diagnostic set."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

STRICT_BASELINE_ERROR_COUNT = 0
DEFAULT_TARGETS = ("agentic_trader", "tests", "scripts", "sidecars/research_flow/src")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Run strict Pyright and fail when any diagnostics are reported.")
    )
    parser.add_argument(
        "--max-errors",
        type=int,
        default=STRICT_BASELINE_ERROR_COUNT,
        help="Maximum accepted strict Pyright error count.",
    )
    parser.add_argument(
        "--pythonpath",
        help="Optional Python interpreter path forwarded to Pyright.",
    )
    parser.add_argument(
        "--top-files",
        type=int,
        default=10,
        help="Number of files to show in the diagnostic summary.",
    )
    parser.add_argument(
        "targets",
        nargs="*",
        default=list(DEFAULT_TARGETS),
        help=(
            "Pyright targets. Defaults to agentic_trader tests scripts "
            "sidecars/research_flow/src."
        ),
    )
    return parser.parse_args()


def _diagnostic_file(entry: dict[str, Any]) -> str:
    file_path = str(entry.get("file") or "<unknown>")
    try:
        return str(Path(file_path).resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return file_path


def main() -> int:
    args = _parse_args()
    pyright = shutil.which("pyright")
    if pyright is None:
        print("pyright executable not found on PATH", file=sys.stderr)
        return 127

    command = [pyright]
    if args.pythonpath:
        command.extend(["--pythonpath", args.pythonpath])
    command.extend([*args.targets, "--outputjson"])

    completed = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        print("Pyright did not return JSON output.", file=sys.stderr)
        if completed.stdout:
            print(completed.stdout, file=sys.stderr)
        if completed.stderr:
            print(completed.stderr, file=sys.stderr)
        return completed.returncode or 1

    summary = payload.get("summary", {})
    error_count = int(summary.get("errorCount") or 0)
    warning_count = int(summary.get("warningCount") or 0)
    information_count = int(summary.get("informationCount") or 0)
    files_analyzed = int(summary.get("filesAnalyzed") or 0)
    elapsed = float(summary.get("timeInSec") or 0.0)

    print(
        "Strict Pyright baseline: "
        f"errors={error_count}/{args.max_errors}, "
        f"warnings={warning_count}, information={information_count}, "
        f"files={files_analyzed}, time={elapsed:.2f}s"
    )

    diagnostics = payload.get("generalDiagnostics", [])
    if diagnostics and args.top_files > 0:
        counts = Counter(_diagnostic_file(entry) for entry in diagnostics)
        print("Top strict Pyright files:")
        for file_path, count in counts.most_common(args.top_files):
            print(f"  {count:4d} {file_path}")

    if error_count > args.max_errors:
        print(
            "Strict Pyright reported errors. Fix diagnostics before publishing.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
