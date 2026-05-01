"""CrewAI setup detection for the optional research sidecar backend."""

from pathlib import Path
import shutil
import subprocess

from agentic_trader.config import Settings


def default_crewai_flow_dir(settings: Settings) -> Path:
    """Return the tracked sidecar path used for optional CrewAI development."""
    _ = settings
    return Path(__file__).resolve().parents[2] / "sidecars" / "research_flow"


def crewai_setup_status(settings: Settings) -> dict[str, object]:
    """Report optional CrewAI CLI/setup state without importing CrewAI."""
    cli_path = shutil.which("crewai")
    uv_path = shutil.which("uv")
    version: str | None = None
    if cli_path:
        try:
            completed = subprocess.run(
                [cli_path, "--version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            version = (completed.stdout or completed.stderr).strip() or None
        except Exception as exc:
            version = f"version_check_failed: {exc}"

    flow_dir = default_crewai_flow_dir(settings)
    python_version_file = flow_dir / ".python-version"
    return {
        "available": cli_path is not None,
        "cli_path": cli_path,
        "uv_available": uv_path is not None,
        "uv_path": uv_path,
        "version": version,
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
        "notes": [
            "CrewAI stays optional and isolated behind researchd backend boundaries.",
            "The tracked CrewAI Flow sidecar lives in sidecars/research_flow with its own uv environment.",
            "The core runtime calls the Flow sidecar through a subprocess JSON contract only after setup.",
            "Do not import CrewAI from core trading runtime modules.",
        ],
    }
