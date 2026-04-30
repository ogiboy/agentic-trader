"""CrewAI setup detection for the optional research sidecar backend."""

from pathlib import Path
import shutil
import subprocess

from agentic_trader.config import Settings


def default_crewai_flow_dir(settings: Settings) -> Path:
    """Return the ignored runtime path used for optional CrewAI scaffolds."""
    return settings.runtime_dir / "researchd" / "research_sidecar_flow"


def crewai_setup_status(settings: Settings) -> dict[str, object]:
    """Report optional CrewAI CLI/setup state without importing CrewAI."""
    cli_path = shutil.which("crewai")
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
    return {
        "available": cli_path is not None,
        "cli_path": cli_path,
        "version": version,
        "flow_dir": str(flow_dir),
        "flow_scaffold_exists": (flow_dir / "pyproject.toml").exists(),
        "core_dependency": False,
        "recommended_commands": [
            "crewai create flow research_sidecar_flow --skip_provider",
            "cd runtime/researchd/research_sidecar_flow",
            "crewai install",
            "crewai run",
        ],
        "notes": [
            "CrewAI stays optional and isolated behind researchd backend boundaries.",
            "Scaffolded CrewAI projects belong under ignored runtime/researchd/ until promoted intentionally.",
            "Do not import CrewAI from core trading runtime modules.",
        ],
    }
