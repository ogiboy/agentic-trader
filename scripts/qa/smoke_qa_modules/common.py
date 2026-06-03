from __future__ import annotations

import json
from pathlib import Path

from scripts.qa.smoke_qa_modules.models import CheckResult, SmokeContext

TRACEBACK_MARKERS = ("Traceback (most recent call last):", "KeyboardInterrupt")
OPERATOR_NOISE_MARKERS = (
    "LLM structured validation failed on attempt",
    "LLM structured request issue on attempt",
    "LLM text request issue on attempt",
    "Failed download:",
)
RENDER_SECONDS = 3.0
EXIT_WAIT_SECONDS = 2.0
TUI_READY_PATTERNS = (
    r"Agentic Trader",
    r"AGENTIC TRADER",
    r"CONTROL ROOM",
    r"Main Menu",
    r"Select action",
    r"Overview",
)
PROMPT_SELECT_ACTION = "Select action"
PROMPT_PRESS_ENTER = "Press Enter to continue"


def artifact_path(context: SmokeContext, name: str) -> Path:
    context.artifacts_dir.mkdir(parents=True, exist_ok=True)
    return context.artifacts_dir / f"{name}.log"


def coverage_path(context: SmokeContext) -> Path:
    return context.artifacts_dir / "coverage.xml"


def command_display(command: list[str]) -> str:
    return " ".join(command)


def write_artifact(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", errors="replace")


def output_has_traceback(output: str) -> bool:
    return any(marker in output for marker in TRACEBACK_MARKERS)


def operator_noise_marker(output: str) -> str | None:
    for marker in OPERATOR_NOISE_MARKERS:
        if marker in output:
            return marker
    return None


def redact_sensitive_text(text: str, sensitive_values: tuple[str, ...]) -> str:
    redacted = text
    for value in sensitive_values:
        if value:
            redacted = redacted.replace(value, "<redacted>")
    return redacted


def json_stdout_error(stdout: str) -> str | None:
    try:
        json.loads(stdout)
    except json.JSONDecodeError as exc:
        return str(exc)
    return None


def skip_result(context: SmokeContext, name: str, details: str) -> CheckResult:
    artifact = artifact_path(context, name)
    write_artifact(artifact, f"SKIPPED: {details}\n")
    return CheckResult(
        name=name,
        passed=True,
        details=f"skipped; {details}",
        artifact=str(artifact),
    )
