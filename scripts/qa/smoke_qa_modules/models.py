from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    details: str
    artifact: str | None = None


@dataclass(frozen=True)
class SmokeContext:
    artifacts_dir: Path
