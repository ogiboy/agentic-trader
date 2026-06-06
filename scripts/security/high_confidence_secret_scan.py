"""High-confidence tracked-source secret and live-endpoint scanner."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

EXCLUDED_PREFIXES = (
    ".agents/",
    ".ai/qa/artifacts/",
    ".claude/",
    "docs/out/",
    "webgui/.next/",
)
TEXT_SUFFIXES = {
    ".cfg",
    ".env",
    ".example",
    ".js",
    ".json",
    ".md",
    ".mjs",
    ".py",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{36,}\b")),
    ("OpenAI API key", re.compile(r"\bsk-[A-Za-z0-9]{32,}\b")),
    (
        "JWT",
        re.compile(
            r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"
        ),
    ),
    (
        "private key block",
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ),
    (
        "Alpaca live endpoint",
        re.compile(r"https://api\.alpaca\.markets(?:/|$)"),
    ),
)


def tracked_files() -> list[Path]:
    output = subprocess.check_output(["git", "ls-files"], text=True)
    files: list[Path] = []
    for line in output.splitlines():
        if line.startswith(EXCLUDED_PREFIXES):
            continue
        path = Path(line)
        if path.suffix in TEXT_SUFFIXES or path.name.endswith(".env.example"):
            files.append(path)
    return files


def main() -> int:
    findings: list[str] = []
    for path in tracked_files():
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for label, pattern in SECRET_PATTERNS:
            for match in pattern.finditer(text):
                line_number = text.count("\n", 0, match.start()) + 1
                findings.append(f"{path}:{line_number}: {label}")
    if findings:
        print(
            f"High-confidence secret or live endpoint findings detected: {len(findings)}"
        )
        return 1
    print("No high-confidence tracked-source secrets or live endpoints found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
