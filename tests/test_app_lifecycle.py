import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCTOR_SCRIPT = ROOT / "scripts" / "app-doctor.mjs"
SETUP_SCRIPT = ROOT / "scripts" / "app-setup.mjs"
SERVICES_SCRIPT = ROOT / "scripts" / "app-services.mjs"
UPDATE_SCRIPT = ROOT / "scripts" / "app-update.mjs"
UNINSTALL_SCRIPT = ROOT / "scripts" / "app-uninstall.mjs"
UP_SCRIPT = ROOT / "scripts" / "app-up.mjs"


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


def _fake_update_toolchain(tmp_path: Path, exit_code: int = 0) -> tuple[Path, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log_path = tmp_path / "update.log"
    for name in ("pnpm", "uv"):
        script = bin_dir / name
        script.write_text(
            "#!/usr/bin/env sh\n"
            "printf '%s|%s|%s\\n' \"$(basename \"$0\")\" \"$PWD\" \"$*\" >> \"$UPDATE_LOG\"\n"
            f"exit {exit_code}\n",
            encoding="utf-8",
        )
        script.chmod(0o755)
    return bin_dir, log_path


def _fake_app_up_toolchain(tmp_path: Path, exit_code: int = 0) -> tuple[Path, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log_path = tmp_path / "app-up.log"
    script = bin_dir / "pnpm"
    script.write_text(
        "#!/usr/bin/env sh\n"
        "printf '%s|%s\\n' \"$PWD\" \"$*\" >> \"$APP_UP_LOG\"\n"
        "case \"$*\" in\n"
        "  *app:doctor*) printf '{\"action\":\"doctor\",\"mutated\":false}\\n' ;;\n"
        "  *app:start*) printf '{\"action\":\"start\",\"mutated\":true}\\n' ;;\n"
        "  *app:setup*) printf '{\"action\":\"setup\",\"mutated\":true}\\n' ;;\n"
        "  *) printf '{\"ok\":true}\\n' ;;\n"
        "esac\n"
        f"exit {exit_code}\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return bin_dir, log_path


def _fake_service_cli(tmp_path: Path, exit_code: int = 0) -> tuple[Path, Path]:
    log_path = tmp_path / "agentic-trader.log"
    script = tmp_path / "agentic-trader"
    script.write_text(
        "#!/usr/bin/env sh\n"
        "if [ -n \"$AGENTIC_TRADER_CLI_LOG\" ]; then\n"
        "  printf '%s\\n' \"$*\" >> \"$AGENTIC_TRADER_CLI_LOG\"\n"
        "fi\n"
        "case \"$*\" in\n"
        "  *' start '*) printf '{\"app_owned\":true,\"service_reachable\":true,\"args\":\"%s\"}\\n' \"$*\" ;;\n"
        "  *' stop '*)\n"
        "    if [ \"$STOP_STILL_APP_OWNED\" = \"1\" ]; then\n"
        "      printf '{\"app_owned\":true,\"service_reachable\":true,\"message\":\"still running\",\"args\":\"%s\"}\\n' \"$*\"\n"
        "    else\n"
        "      printf '{\"app_owned\":false,\"service_reachable\":false,\"args\":\"%s\"}\\n' \"$*\"\n"
        "    fi\n"
        "    ;;\n"
        "  *) printf '{\"ok\":true,\"args\":\"%s\"}\\n' \"$*\" ;;\n"
        "esac\n"
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


def _run_services(
    mode: str,
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env is not None:
        merged_env.update(env)
    return subprocess.run(
        ["node", str(SERVICES_SCRIPT), mode, *args],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=merged_env,
    )


def _run_update(
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env is not None:
        merged_env.update(env)
    return subprocess.run(
        ["node", str(UPDATE_SCRIPT), *args],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=merged_env,
    )


def _run_uninstall(
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env is not None:
        merged_env.update(env)
    return subprocess.run(
        ["node", str(UNINSTALL_SCRIPT), *args],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=merged_env,
    )


def _run_up(
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env is not None:
        merged_env.update(env)
    return subprocess.run(
        ["node", str(UP_SCRIPT), *args],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=merged_env,
    )


def _fake_app_root(tmp_path: Path) -> Path:
    app_root = tmp_path / "app"
    app_root.mkdir()
    (app_root / "package.json").write_text('{"name":"agentic-trader"}\n', encoding="utf-8")
    (app_root / "pyproject.toml").write_text('[project]\nname = "agentic-trader"\n', encoding="utf-8")
    return app_root


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


def test_app_start_dry_run_defers_services_by_default() -> None:
    result = _run_services("start", "--json", "--dry-run")
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert payload["action"] == "start"
    assert payload["dry_run"] is True
    assert payload["mutated"] is False
    assert payload["selected_services"] == []
    commands = [" ".join(step["command"]) for step in payload["steps"]]
    assert (
        "agentic-trader webgui-service start --no-open-browser --json"
        in commands
    )
    assert all(step["status"] == "deferred" for step in payload["steps"])
    assert any(
        "No dependency install" in note
        for note in payload["safety_notes"]
    )


def test_app_start_webgui_yes_starts_only_webgui_without_browser(
    tmp_path: Path,
) -> None:
    fake_cli, log_path = _fake_service_cli(tmp_path)
    result = _run_services(
        "start",
        "--json",
        "--webgui",
        "--yes",
        env={
            "AGENTIC_TRADER_CLI": str(fake_cli),
            "AGENTIC_TRADER_CLI_LOG": str(log_path),
        },
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert payload["dry_run"] is False
    assert payload["mutated"] is True
    assert payload["selected_services"] == ["webgui-service"]
    assert log_path.read_text(encoding="utf-8").splitlines() == [
        "webgui-service start --no-open-browser --json"
    ]
    assert all(
        step["status"] == "deferred"
        for step in payload["steps"]
        if not step["selected"]
    )


def test_app_start_rejects_yes_without_service_selection() -> None:
    result = _run_services("start", "--json", "--yes")

    assert result.returncode == 2
    assert "Select at least one service" in result.stderr


def test_app_start_rejects_browser_open_without_webgui_selection() -> None:
    result = _run_services("start", "--json", "--model-service", "--open-browser")

    assert result.returncode == 2
    assert "--open-browser requires selecting --webgui or --all" in result.stderr


def test_app_stop_all_yes_stops_only_app_owned_service_surfaces(
    tmp_path: Path,
) -> None:
    fake_cli, log_path = _fake_service_cli(tmp_path)
    result = _run_services(
        "stop",
        "--json",
        "--all",
        "--yes",
        env={
            "AGENTIC_TRADER_CLI": str(fake_cli),
            "AGENTIC_TRADER_CLI_LOG": str(log_path),
        },
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert payload["dry_run"] is False
    assert payload["mutated"] is True
    assert payload["selected_services"] == [
        "model-service",
        "camofox-service",
        "webgui-service",
    ]
    assert log_path.read_text(encoding="utf-8").splitlines() == [
        "webgui-service stop --json",
        "camofox-service stop --json",
        "model-service stop --json",
    ]
    commands = [" ".join(step["command"]) for step in payload["steps"]]
    assert not any("setup" in command for command in commands)
    assert not any("pull" in command for command in commands)


def test_app_stop_fails_when_service_payload_remains_app_owned(
    tmp_path: Path,
) -> None:
    fake_cli, _log_path = _fake_service_cli(tmp_path)
    result = _run_services(
        "stop",
        "--json",
        "--webgui",
        "--yes",
        env={
            "AGENTIC_TRADER_CLI": str(fake_cli),
            "STOP_STILL_APP_OWNED": "1",
        },
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 1
    assert payload["steps"][0]["status"] == "failed"
    assert payload["steps"][0]["payload"]["message"] == "still running"


def test_app_update_dry_run_plans_all_owner_lanes() -> None:
    result = _run_update("--json", "--dry-run")
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert payload["action"] == "update"
    assert payload["dry_run"] is True
    assert payload["mutated"] is False
    assert payload["selected_scopes"] == []
    commands = [" ".join(step["command"]) for step in payload["steps"]]
    assert "pnpm update --recursive --latest" in commands
    assert "uv sync --locked --all-extras --group dev" in commands
    assert "pnpm --dir tools/camofox-browser --ignore-workspace update" in commands
    assert "pnpm run check" in commands
    assert "pnpm run app:doctor -- --json" in commands
    assert not any("fetch:camofox" in command for command in commands)
    assert not any("model-service pull" in command for command in commands)
    assert not any("webgui-service start" in command for command in commands)


def test_app_update_rejects_yes_without_scope() -> None:
    result = _run_update("--json", "--yes")

    assert result.returncode == 2
    assert "Select at least one update scope" in result.stderr


def test_app_update_core_yes_runs_only_core_owner_steps(tmp_path: Path) -> None:
    bin_dir, log_path = _fake_update_toolchain(tmp_path)
    result = _run_update(
        "--json",
        "--core",
        "--yes",
        env={
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "UPDATE_LOG": str(log_path),
        },
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert payload["dry_run"] is False
    assert payload["mutated"] is True
    assert payload["selected_scopes"] == ["core"]
    log_lines = log_path.read_text(encoding="utf-8").splitlines()
    assert log_lines == [
        f"pnpm|{ROOT}|update --recursive --latest",
        f"uv|{ROOT}|lock --upgrade",
        f"uv|{ROOT}|sync --locked --all-extras --group dev",
    ]
    assert all(
        step["status"] == "passed"
        for step in payload["steps"]
        if step["scope"] == "core"
    )
    assert all(
        step["status"] == "deferred"
        for step in payload["steps"]
        if step["scope"] != "core"
    )


def test_app_update_stops_selected_lane_after_failure(tmp_path: Path) -> None:
    bin_dir, log_path = _fake_update_toolchain(tmp_path, exit_code=7)
    result = _run_update(
        "--json",
        "--core",
        "--yes",
        env={
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "UPDATE_LOG": str(log_path),
        },
    )
    payload = json.loads(result.stdout)
    core_steps = [step for step in payload["steps"] if step["scope"] == "core"]

    assert result.returncode == 1
    assert payload["mutated"] is True
    assert log_path.read_text(encoding="utf-8").splitlines() == [
        f"pnpm|{ROOT}|update --recursive --latest",
    ]
    assert [step["status"] for step in core_steps] == [
        "failed",
        "skipped",
        "skipped",
    ]


def test_app_up_dry_run_plans_guided_first_run_without_mutation() -> None:
    result = _run_up("--json", "--dry-run")
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert payload["action"] == "up"
    assert payload["dry_run"] is True
    assert payload["mutated"] is False
    assert payload["selected_scopes"] == []
    assert [decision["mode"] for decision in payload["ownership_decisions"]] == [
        "undecided",
        "undecided",
        "undecided",
    ]
    commands = [" ".join(step["command"]) for step in payload["steps"]]
    assert "pnpm run app:setup -- --json --core --yes" in commands
    assert "pnpm run setup:research-flow" in commands
    assert "pnpm run setup:camofox" in commands
    assert "pnpm run fetch:camofox" in commands
    assert "pnpm run app:start -- --json --webgui --yes" in commands
    assert "pnpm run app:doctor -- --json" in commands
    assert not any("model-service pull" in command for command in commands)
    assert any(
        "No trading daemon" in note
        for note in payload["safety_notes"]
    )


def test_app_up_rejects_yes_without_scope() -> None:
    result = _run_up("--json", "--yes")

    assert result.returncode == 2
    assert "Select at least one app:up scope" in result.stderr


def test_app_up_blocks_app_owned_steps_without_owner_decision() -> None:
    result = _run_up("--json", "--model-service", "--yes")
    payload = json.loads(result.stdout)

    assert result.returncode == 1
    blocked = [step for step in payload["steps"] if step["status"] == "blocked"]
    assert blocked[0]["id"] == "model-service-start"
    assert "--ollama-owner=app-owned" in blocked[0]["reason"]
    assert payload["mutated"] is False


def test_app_up_all_yes_runs_safe_first_run_scopes(tmp_path: Path) -> None:
    bin_dir, log_path = _fake_app_up_toolchain(tmp_path)
    result = _run_up(
        "--json",
        "--all",
        "--yes",
        env={
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "APP_UP_LOG": str(log_path),
        },
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert payload["dry_run"] is False
    assert payload["mutated"] is True
    assert payload["selected_scopes"] == ["core", "sidecar", "webgui", "status"]
    assert log_path.read_text(encoding="utf-8").splitlines() == [
        f"{ROOT}|run app:setup -- --json --core --yes",
        f"{ROOT}|run setup:research-flow",
        f"{ROOT}|run app:start -- --json --webgui --yes",
        f"{ROOT}|run app:doctor -- --json",
    ]
    assert all(
        step["status"] == "deferred"
        for step in payload["steps"]
        if step["scope"] in {"camofox-deps", "camofox-browser", "model-service", "camofox-service"}
    )


def test_app_up_owner_scoped_model_service_runs_only_when_app_owned(
    tmp_path: Path,
) -> None:
    bin_dir, log_path = _fake_app_up_toolchain(tmp_path)
    result = _run_up(
        "--json",
        "--model-service",
        "--ollama-owner=app-owned",
        "--yes",
        env={
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "APP_UP_LOG": str(log_path),
        },
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert payload["selected_scopes"] == ["model-service"]
    assert log_path.read_text(encoding="utf-8").splitlines() == [
        f"{ROOT}|run app:start -- --json --model-service --yes"
    ]
    assert payload["steps"][4]["status"] == "passed"


def test_app_uninstall_dry_run_plans_safe_scopes() -> None:
    result = _run_uninstall("--json", "--dry-run")
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert payload["action"] == "uninstall"
    assert payload["dry_run"] is True
    assert payload["mutated"] is False
    assert payload["selected_scopes"] == []
    relative_paths = {target["relative_path"] for target in payload["targets"]}
    assert ".venv" in relative_paths
    assert "node_modules" in relative_paths
    assert "runtime/webgui_service" in relative_paths
    assert "runtime/agentic_trader.duckdb" not in relative_paths
    assert ".env" not in relative_paths
    assert any(
        "User secrets" in note
        for note in payload["safety_notes"]
    )


def test_app_uninstall_rejects_yes_without_scope() -> None:
    result = _run_uninstall("--json", "--yes")

    assert result.returncode == 2
    assert "Select at least one uninstall scope" in result.stderr


def test_app_uninstall_deps_yes_removes_only_dependency_dirs(tmp_path: Path) -> None:
    app_root = _fake_app_root(tmp_path)
    for relative_path in (
        ".venv",
        "node_modules",
        "webgui/node_modules",
        "docs/node_modules",
        "tui/node_modules",
        "sidecars/research_flow/.venv",
        "tools/camofox-browser/node_modules",
        ".pnpm-store",
    ):
        (app_root / relative_path).mkdir(parents=True)
    (app_root / ".env.local").write_text("SECRET=value\n", encoding="utf-8")
    service_log = app_root / "runtime/webgui_service/webgui.out.log"
    service_log.parent.mkdir(parents=True)
    service_log.write_text("kept\n", encoding="utf-8")

    result = _run_uninstall(
        "--json",
        "--deps",
        "--yes",
        env={"AGENTIC_TRADER_APP_UNINSTALL_ROOT": str(app_root)},
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert payload["dry_run"] is False
    assert payload["mutated"] is True
    assert payload["selected_scopes"] == ["deps"]
    assert not (app_root / ".venv").exists()
    assert not (app_root / "node_modules").exists()
    assert not (app_root / "webgui/node_modules").exists()
    assert (app_root / ".env.local").exists()
    assert service_log.exists()
    assert all(
        target["status"] in {"removed", "missing", "deferred"}
        for target in payload["targets"]
    )


def test_app_uninstall_service_state_blocks_recorded_state(tmp_path: Path) -> None:
    app_root = _fake_app_root(tmp_path)
    service_dir = app_root / "runtime/webgui_service"
    service_dir.mkdir(parents=True)
    state_file = service_dir / "webgui_service.json"
    state_file.write_text('{"pid": 12345}\n', encoding="utf-8")
    (service_dir / "webgui.out.log").write_text("still tracked\n", encoding="utf-8")

    result = _run_uninstall(
        "--json",
        "--service-state",
        "--yes",
        env={"AGENTIC_TRADER_APP_UNINSTALL_ROOT": str(app_root)},
    )
    payload = json.loads(result.stdout)
    blocked_targets = [
        target
        for target in payload["targets"]
        if target["status"] == "blocked"
    ]

    assert result.returncode == 1
    assert payload["mutated"] is False
    assert blocked_targets[0]["relative_path"] == "runtime/webgui_service"
    assert "webgui_service.json" in blocked_targets[0]["reason"]
    assert state_file.exists()


def test_app_uninstall_artifacts_yes_removes_discovered_python_caches(
    tmp_path: Path,
) -> None:
    app_root = _fake_app_root(tmp_path)
    pycache_dir = app_root / "agentic_trader/__pycache__"
    pycache_dir.mkdir(parents=True)
    (pycache_dir / "module.pyc").write_bytes(b"cache")
    ignored_env = app_root / ".env.local"
    ignored_env.write_text("SECRET=value\n", encoding="utf-8")

    result = _run_uninstall(
        "--json",
        "--artifacts",
        "--yes",
        env={"AGENTIC_TRADER_APP_UNINSTALL_ROOT": str(app_root)},
    )
    payload = json.loads(result.stdout)
    aggregate_targets = [
        target
        for target in payload["targets"]
        if target["id"] == "python-bytecode-caches"
    ]

    assert result.returncode == 0
    assert aggregate_targets[0]["status"] == "removed"
    assert aggregate_targets[0]["removed_paths"] == [
        "agentic_trader/__pycache__"
    ]
    assert not pycache_dir.exists()
    assert ignored_env.exists()
