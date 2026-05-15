import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCTOR_SCRIPT = ROOT / "scripts" / "app-doctor.mjs"
SETUP_SCRIPT = ROOT / "scripts" / "app-setup.mjs"


def _fake_cli(tmp_path: Path, exit_code: int = 0) -> Path:
    script = tmp_path / "agentic-trader"
    script.write_text(
        "#!/usr/bin/env sh\n"
        "case \"$*\" in\n"
        "  *setup-status*) printf '{\"core_ready\":true}\\n' ;;\n"
        "  *model-service*) printf '{\"service_reachable\":false}\\n' ;;\n"
        "  *camofox-service*) printf '{\"service_reachable\":false}\\n' ;;\n"
        "  *webgui-service*) printf '{\"service_reachable\":false}\\n' ;;\n"
        "  *provider-diagnostics*) printf '{\"provider\":\"ollama\"}\\n' ;;\n"
        "  *v1-readiness*) printf '{\"ready\":false}\\n' ;;\n"
        "  *) printf '{\"ok\":true}\\n' ;;\n"
        "esac\n"
        f"exit {exit_code}\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


def _run_doctor(
    tmp_path: Path,
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env is not None:
        merged_env.update(env)
    return subprocess.run(
        ["node", str(DOCTOR_SCRIPT), *args],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=merged_env,
    )


def _fake_pnpm(tmp_path: Path, exit_code: int = 0) -> tuple[Path, Path]:
    log_path = tmp_path / "pnpm.log"
    script = tmp_path / "pnpm"
    script.write_text(
        "#!/usr/bin/env sh\n"
        "printf '%s\\n' \"$*\" >> \"$PNPM_LOG\"\n"
        f"exit {exit_code}\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script, log_path


def _run_setup(
    tmp_path: Path,
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env is not None:
        merged_env.update(env)
    return subprocess.run(
        ["node", str(SETUP_SCRIPT), *args],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=merged_env,
    )


def test_app_doctor_is_read_only_status_surface(tmp_path: Path) -> None:
    fake_cli = _fake_cli(tmp_path)
    result = _run_doctor(
        tmp_path,
        "--json",
        env={"AGENTIC_TRADER_CLI": str(fake_cli)},
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert payload["action"] == "doctor"
    assert payload["mutated"] is False
    commands = [" ".join(step["command"]) for step in payload["steps"]]
    assert any("agentic-trader setup-status --json" in command for command in commands)
    assert any("agentic-trader model-service status --json" in command for command in commands)
    assert any("agentic-trader webgui-service status --json" in command for command in commands)
    assert any("agentic-trader provider-diagnostics --json" in command for command in commands)
    assert any("agentic-trader v1-readiness --json" in command for command in commands)
    assert all(step["mutates"] is False for step in payload["steps"])


def test_app_doctor_does_not_run_provider_generation_probe(tmp_path: Path) -> None:
    fake_cli = _fake_cli(tmp_path)
    result = _run_doctor(
        tmp_path,
        "--json",
        env={"AGENTIC_TRADER_CLI": str(fake_cli)},
    )
    payload = json.loads(result.stdout)

    commands = [" ".join(step["command"]) for step in payload["steps"]]
    assert not any("--provider-check" in command for command in commands)
    assert not any("--probe-generation" in command for command in commands)
    assert not any("webgui-service start" in command for command in commands)
    assert not any("model-service start" in command for command in commands)
    assert any(
        "never starts a trading daemon" in note
        for note in payload["safety_notes"]
    )


def test_app_doctor_reports_missing_cli_without_uv_sync(tmp_path: Path) -> None:
    result = _run_doctor(
        tmp_path,
        "--json",
        env={"AGENTIC_TRADER_CLI": ""},
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 1
    assert payload["mutated"] is False
    assert payload["cli_path"] is None
    assert payload["steps"] == []


def test_app_setup_dry_run_plans_core_and_defers_optional_tools(
    tmp_path: Path,
) -> None:
    result = _run_setup(tmp_path, "--json", "--dry-run")
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert payload["action"] == "setup"
    assert payload["dry_run"] is True
    assert payload["mutated"] is False
    commands = [" ".join(step["command"]) for step in payload["steps"]]
    assert "pnpm run setup:node" in commands
    assert "pnpm run install:python" in commands
    assert "pnpm run fetch:camofox" in commands
    assert "agentic-trader model-service start" in commands
    assert any(
        step["id"] == "camofox-browser" and step["status"] == "deferred"
        for step in payload["steps"]
    )
    assert any(
        "No trading daemon" in note
        for note in payload["safety_notes"]
    )


def test_app_setup_core_without_yes_stays_dry_run(tmp_path: Path) -> None:
    fake_pnpm, log_path = _fake_pnpm(tmp_path)
    result = _run_setup(
        tmp_path,
        "--json",
        "--core",
        env={
            "PATH": f"{fake_pnpm.parent}{os.pathsep}{os.environ['PATH']}",
            "PNPM_LOG": str(log_path),
        },
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert payload["mode"] == "core"
    assert payload["dry_run"] is True
    assert payload["mutated"] is False
    assert not log_path.exists()
    assert all(
        step["status"] in {"planned", "deferred"}
        for step in payload["steps"]
    )


def test_app_setup_core_yes_runs_only_core_repair(tmp_path: Path) -> None:
    fake_pnpm, log_path = _fake_pnpm(tmp_path)
    result = _run_setup(
        tmp_path,
        "--json",
        "--core",
        "--yes",
        env={
            "PATH": f"{fake_pnpm.parent}{os.pathsep}{os.environ['PATH']}",
            "PNPM_LOG": str(log_path),
        },
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert payload["mode"] == "core"
    assert payload["dry_run"] is False
    assert payload["mutated"] is True
    assert log_path.read_text(encoding="utf-8").splitlines() == [
        "run setup:node",
        "run install:python",
    ]
    assert all(
        step["status"] == "passed"
        for step in payload["steps"]
        if step["category"] == "core"
    )
    assert all(
        step["status"] == "deferred"
        for step in payload["steps"]
        if step["category"] == "deferred"
    )
