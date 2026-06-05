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


def default_crewai_workspace_root(settings: Settings) -> Path:
    """Return the uv workspace root that owns the CrewAI sidecar environment."""
    _ = settings
    return Path(__file__).resolve().parents[2]


def crewai_workspace_root_for_flow(flow_dir: Path) -> Path:
    """Return the workspace root that owns a tracked or test CrewAI flow path."""
    if flow_dir.parent.name == "sidecars":
        return flow_dir.parent.parent
    return flow_dir.parent


def _crewai_sidecar_version(
    uv_path: str, workspace_root: Path
) -> tuple[str | None, str, str | None]:
    try:
        completed = subprocess.run(
            [
                uv_path,
                "run",
                "--directory",
                str(workspace_root),
                "--locked",
                "--package",
                "research-flow",
                "--no-sync",
                "python",
                "-c",
                "import crewai; print(getattr(crewai, '__version__', 'unknown'))",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception as exc:
        return None, "failed", redact_sensitive_text(str(exc), max_length=200)

    output = (completed.stdout or completed.stderr).strip()
    first_line = next(
        (line.strip() for line in output.splitlines() if line.strip()),
        "",
    )
    if completed.returncode == 0:
        return redact_sensitive_text(first_line, max_length=160) or None, "ok", None
    if "Traceback" in output:
        return None, "failed", "CrewAI sidecar import failed before returning a version"
    return (
        None,
        "failed",
        redact_sensitive_text(first_line, max_length=200)
        or "CrewAI sidecar version check returned a non-zero exit code",
    )


def crewai_setup_status(settings: Settings) -> dict[str, object]:
    """Report optional CrewAI sidecar setup state without importing CrewAI into core runtime."""
    uv_path = shutil.which("uv")
    flow_dir = default_crewai_flow_dir(settings)
    workspace_root = default_crewai_workspace_root(settings)
    flow_scaffold_exists = (flow_dir / "pyproject.toml").exists()
    environment_path = workspace_root / ".venv"
    lockfile_path = workspace_root / "uv.lock"
    environment_exists = environment_path.exists()
    version: str | None = None
    version_status = "missing_uv" if uv_path is None else "not_checked"
    version_error: str | None = None
    if uv_path is not None and flow_scaffold_exists:
        version, version_status, version_error = _crewai_sidecar_version(
            uv_path, workspace_root
        )
        if version_status == "ok" and not environment_exists:
            version_status = "missing_environment"
    elif uv_path is not None and not flow_scaffold_exists:
        version_status = "missing_scaffold"
    elif uv_path is not None and not environment_exists:
        version_status = "missing_environment"

    python_version_file = flow_dir / ".python-version"
    notes = [
        "CrewAI stays isolated behind researchd backend boundaries.",
        "The tracked CrewAI Flow sidecar lives in sidecars/research_flow as the research-flow uv workspace dependency.",
        "The root uv workspace owns the shared lockfile and environment for sidecar setup.",
        "The core runtime controls the Flow sidecar through a subprocess JSON contract only after setup.",
        "Do not import CrewAI from core trading runtime modules.",
    ]
    if version_error:
        notes.append(
            f"crewai_sidecar_version_check_failed: {version_error}; run pnpm run setup:research-flow"
        )
    package_available = environment_exists and version_status == "ok"
    return {
        "available": package_available,
        "cli_path": None,
        "uv_available": uv_path is not None,
        "uv_path": uv_path,
        "version": version,
        "version_source": "workspace_uv",
        "version_status": version_status,
        "version_error": version_error,
        "flow_dir": str(flow_dir),
        "workspace_root": str(workspace_root),
        "flow_scaffold_exists": flow_scaffold_exists,
        "environment_exists": environment_exists,
        "environment_path": str(environment_path),
        "package_available": package_available,
        "python_version": (
            python_version_file.read_text(encoding="utf-8").strip()
            if python_version_file.exists()
            else None
        ),
        "lockfile_exists": lockfile_path.exists(),
        "lockfile_path": str(lockfile_path),
        "core_dependency": False,
        "workspace_dependency": True,
        "runtime_controlled": True,
        "workspace_member": True,
        "recommended_commands": [
            "pnpm run setup:research-flow",
            "pnpm run check:research-flow",
            "AGENTIC_TRADER_ALLOW_CREWAI_NOOP=1 pnpm run run:research-flow",
        ],
        "notes": notes,
    }
