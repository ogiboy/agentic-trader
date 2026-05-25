"""CrewAI setup detection for the optional research sidecar backend."""

import shutil
import subprocess
from pathlib import Path

from agentic_trader.config import Settings
from agentic_trader.security import redact_sensitive_text


def default_crewai_flow_dir(settings: Settings) -> Path:
    """Return the tracked sidecar path used for optional CrewAI development."""
    _ = settings
    return Path(__file__).resolve().parents[2] / "sidecars" / "research_flow"


def crewai_setup_status(settings: Settings) -> dict[str, object]:
    """Report optional CrewAI CLI/setup state without importing CrewAI."""
    cli_path = shutil.which("crewai")
    uv_path = shutil.which("uv")
    version: str | None = None
    version_status = "missing" if cli_path is None else "not_checked"
    version_error: str | None = None
    if cli_path:
        try:
            completed = subprocess.run(
                [cli_path, "--version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            output = (completed.stdout or completed.stderr).strip()
            first_line = next(
                (line.strip() for line in output.splitlines() if line.strip()),
                "",
            )
            if completed.returncode == 0:
                version = redact_sensitive_text(first_line, max_length=160) or None
                version_status = "ok"
            else:
                version_status = "failed"
                if "Traceback" in output:
                    version_error = "crewai --version failed before returning a version"
                else:
                    version_error = (
                        redact_sensitive_text(first_line, max_length=200)
                        or "crewai --version returned a non-zero exit code"
                    )
        except Exception as exc:
            version_status = "failed"
            version_error = redact_sensitive_text(str(exc), max_length=200)

    flow_dir = default_crewai_flow_dir(settings)
    python_version_file = flow_dir / ".python-version"
    notes = [
        "CrewAI stays optional and isolated behind researchd backend boundaries.",
        "The tracked CrewAI Flow sidecar lives in sidecars/research_flow with its own uv environment.",
        "The core runtime calls the Flow sidecar through a subprocess JSON contract only after setup.",
        "Do not import CrewAI from core trading runtime modules.",
    ]
    if version_error:
        notes.append(
            f"crewai_cli_version_check_failed: {version_error}; run pnpm run setup:research-flow"
        )
    return {
        "available": cli_path is not None,
        "cli_path": cli_path,
        "uv_available": uv_path is not None,
        "uv_path": uv_path,
        "version": version,
        "version_status": version_status,
        "version_error": version_error,
        "flow_dir": str(flow_dir),
        "flow_scaffold_exists": (flow_dir / "pyproject.toml").exists(),
        "environment_exists": (flow_dir / ".venv").exists(),
        "python_version": (
            python_version_file.read_text(encoding="utf-8").strip()
            if python_version_file.exists()
            else None
        ),
        "lockfile_exists": (flow_dir / "uv.lock").exists(),
        "core_dependency": False,
        "recommended_commands": [
            "pnpm run setup:research-flow",
            "pnpm run check:research-flow",
            "AGENTIC_TRADER_ALLOW_CREWAI_NOOP=1 pnpm run run:research-flow",
        ],
        "notes": notes,
    }
