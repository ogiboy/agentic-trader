from pathlib import Path
from typing import Any

import pytest

from agentic_trader.config import Settings
from agentic_trader.system import camofox_service


def _settings(tmp_path: Path, **overrides: Any) -> Settings:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        market_data_cache_dir=tmp_path / "market_cache",
        **overrides,
    )
    settings.ensure_directories()
    return settings


def _tool_dir(tmp_path: Path) -> Path:
    root = tmp_path / "tools" / "camofox-browser"
    (root / "node_modules").mkdir(parents=True)
    (root / "server.js").write_text("console.log('ok')", encoding="utf-8")
    (root / "package.json").write_text('{"name":"camofox","version":"1.0.0"}', encoding="utf-8")
    return root


def _status(*, app_owned: bool = False) -> camofox_service.CamofoxServiceStatus:
    return camofox_service.CamofoxServiceStatus(
        command_available=True,
        command_path="/usr/bin/node",
        package_available=True,
        dependency_available=True,
        dependency_path="/repo/node_modules",
        access_key_configured=True,
        app_owned=app_owned,
        pid=999 if app_owned else None,
        host="127.0.0.1",
        port=9377,
        base_url="http://127.0.0.1:9377",
        service_reachable=True,
        health_ok=True,
        state_path="/tmp/camofox.json",
        tool_dir="/repo/tools/camofox-browser",
        message="ready",
    )


def test_start_camofox_service_uses_loopback_keyed_minimal_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tool_dir = _tool_dir(tmp_path)
    settings = _settings(tmp_path, research_camofox_tool_dir=tool_dir)
    captured: dict[str, object] = {}

    class FakeProcess:
        pid = 24680

    def fake_popen(
        command: list[str],
        *,
        cwd: Path,
        stdout: object,
        stderr: object,
        env: dict[str, str],
        start_new_session: bool,
    ) -> FakeProcess:
        captured["command"] = command
        captured["cwd"] = cwd
        captured["stdout"] = stdout
        captured["stderr"] = stderr
        captured["env"] = env
        captured["start_new_session"] = start_new_session
        return FakeProcess()

    monkeypatch.setenv("CAMOFOX_ACCESS_KEY", "local-key")
    monkeypatch.setenv("AGENTIC_TRADER_ALPACA_SECRET_KEY", "secret-value")
    monkeypatch.setattr(camofox_service, "_node_command_path", lambda: "/opt/homebrew/bin/node")
    monkeypatch.setattr(camofox_service, "_is_port_available", lambda _host, _port: True)
    monkeypatch.setattr(camofox_service.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(camofox_service, "is_process_alive", lambda pid: pid == FakeProcess.pid)
    monkeypatch.setattr(camofox_service, "_process_matches_state", lambda _state: True)
    monkeypatch.setattr(
        camofox_service,
        "_health",
        lambda base_url: (True, True, f"{base_url} reachable"),
    )

    status = camofox_service.start_camofox_service(settings)

    assert status.app_owned is True
    assert status.service_reachable is True
    assert status.health_ok is True
    assert status.tool_id == "camofox-browser"
    assert status.tool_status_id == "camofox_browser"
    assert "camofox-service" in status.tool_consumers
    assert "repo_tools" in status.tool_fallback_order
    assert "app-owned" in status.tool_ownership_modes
    assert "local_tool_id=camofox-browser" in status.notes
    assert captured["command"] == ["/opt/homebrew/bin/node", "server.js"]
    assert captured["cwd"] == tool_dir
    env = captured["env"]
    assert isinstance(env, dict)
    assert env["CAMOFOX_HOST"] == "127.0.0.1"
    assert env["CAMOFOX_PORT"] == "9377"
    assert env["CAMOFOX_BROWSER_PREWARM"] == "false"
    assert env["CAMOFOX_CRASH_REPORT_ENABLED"] == "false"
    assert env["CAMOFOX_ACCESS_KEY"] == "local-key"
    assert "AGENTIC_TRADER_ALPACA_SECRET_KEY" not in env


def test_start_camofox_service_requires_access_key_or_api_key(tmp_path: Path) -> None:
    tool_dir = _tool_dir(tmp_path)
    settings = _settings(
        tmp_path,
        research_camofox_tool_dir=tool_dir,
        camofox_access_key=None,
        camofox_api_key=None,
    )

    with pytest.raises(RuntimeError, match="CAMOFOX_ACCESS_KEY or CAMOFOX_API_KEY"):
        camofox_service.start_camofox_service(settings)


def test_camofox_env_uses_api_key_as_access_token_when_access_key_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(
        tmp_path,
        camofox_access_key=None,
        camofox_api_key="api-key",
    )
    monkeypatch.delenv("CAMOFOX_ACCESS_KEY", raising=False)
    monkeypatch.delenv("CAMOFOX_API_KEY", raising=False)

    env = camofox_service._camofox_env(settings, host="127.0.0.1", port=9377)

    assert env["CAMOFOX_API_KEY"] == "api-key"
    assert env["CAMOFOX_ACCESS_KEY"] == "api-key"


def test_start_camofox_service_rejects_non_loopback(tmp_path: Path) -> None:
    tool_dir = _tool_dir(tmp_path)
    settings = _settings(
        tmp_path,
        research_camofox_tool_dir=tool_dir,
        research_camofox_base_url="http://0.0.0.0:9377",
    )

    with pytest.raises(RuntimeError, match="loopback"):
        camofox_service.start_camofox_service(settings)


def test_camofox_process_match_accepts_expected_cwd(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tool_dir = _tool_dir(tmp_path)
    state = camofox_service.CamofoxServiceState(
        pid=24680,
        host="127.0.0.1",
        port=9377,
        base_url="http://127.0.0.1:9377",
        started_at="2026-01-01T00:00:00+00:00",
        stdout_log_path=str(tmp_path / "out.log"),
        stderr_log_path=str(tmp_path / "err.log"),
        command=["/opt/homebrew/bin/node", "server.js"],
        tool_dir=str(tool_dir),
    )

    monkeypatch.setattr(
        camofox_service,
        "_process_command_line",
        lambda _pid: "/opt/homebrew/bin/node server.js",
    )
    monkeypatch.setattr(camofox_service, "_process_cwd", lambda _pid: tool_dir.resolve())

    assert camofox_service._process_matches_state(state) is True


def test_camofox_status_does_not_probe_non_loopback_url(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tool_dir = _tool_dir(tmp_path)
    settings = _settings(
        tmp_path,
        research_camofox_tool_dir=tool_dir,
        research_camofox_base_url="http://0.0.0.0:9377",
    )

    def fake_health(_base_url: str) -> tuple[bool, bool, str]:
        raise AssertionError("non-loopback Camofox status must not probe")

    monkeypatch.setattr(camofox_service, "_node_command_path", lambda: "/opt/homebrew/bin/node")
    monkeypatch.setattr(camofox_service, "_health", fake_health)

    status = camofox_service.build_camofox_service_status(settings)

    assert status.service_reachable is False
    assert status.health_ok is False
    assert status.message == "Camofox base URL must remain loopback."


def test_stop_camofox_service_keeps_state_when_process_cannot_be_killed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tool_dir = _tool_dir(tmp_path)
    settings = _settings(tmp_path, research_camofox_tool_dir=tool_dir)
    state = camofox_service.CamofoxServiceState(
        pid=99991,
        host="127.0.0.1",
        port=9377,
        base_url="http://127.0.0.1:9377",
        started_at="2026-01-01T00:00:00+00:00",
        stdout_log_path=str(tmp_path / "out.log"),
        stderr_log_path=str(tmp_path / "err.log"),
        command=["node", "server.js"],
        tool_dir=str(tool_dir),
    )
    camofox_service._write_state(settings, state)

    monkeypatch.setattr(camofox_service, "is_process_alive", lambda pid: pid == 99991)
    monkeypatch.setattr(camofox_service, "_process_matches_state", lambda _state: True)
    monkeypatch.setattr(
        camofox_service.os,
        "kill",
        lambda _pid, _signal: (_ for _ in ()).throw(PermissionError("denied")),
    )
    monkeypatch.setattr(camofox_service, "_node_command_path", lambda: "/opt/homebrew/bin/node")
    monkeypatch.setattr(camofox_service, "_health", lambda _base_url: (True, True, "reachable"))

    status = camofox_service.stop_camofox_service(settings)

    assert status.app_owned is True
    assert status.message == "Unable to stop app-owned Camofox: denied"
    assert camofox_service.camofox_service_state_path(settings).exists()


def test_camofox_status_marks_browser_launch_failure_from_logs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tool_dir = _tool_dir(tmp_path)
    settings = _settings(tmp_path, research_camofox_tool_dir=tool_dir)
    stdout_path = tmp_path / "camofox.out.log"
    stderr_path = tmp_path / "camofox.err.log"
    stdout_path.write_text(
        '{"level":"warn","msg":"camoufox launch attempt failed"}\n',
        encoding="utf-8",
    )
    stderr_path.write_text("", encoding="utf-8")
    state = camofox_service.CamofoxServiceState(
        pid=24681,
        host="127.0.0.1",
        port=9377,
        base_url="http://127.0.0.1:9377",
        started_at="2026-01-01T00:00:00+00:00",
        stdout_log_path=str(stdout_path),
        stderr_log_path=str(stderr_path),
        command=["node", "server.js"],
        tool_dir=str(tool_dir),
    )
    camofox_service._write_state(settings, state)

    monkeypatch.setattr(camofox_service, "_node_command_path", lambda: "/opt/homebrew/bin/node")
    monkeypatch.setattr(camofox_service, "is_process_alive", lambda pid: pid == 24681)
    monkeypatch.setattr(camofox_service, "_process_matches_state", lambda _state: True)
    monkeypatch.setattr(camofox_service, "_health", lambda _base_url: (True, True, "reachable"))

    status = camofox_service.build_camofox_service_status(settings)

    assert status.service_reachable is True
    assert status.health_ok is False
    assert status.message == "Camofox server is reachable, but browser launch is failing."


def test_camofox_health_allows_on_demand_browser_launch(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "ok": True,
                "browserConnected": False,
                "browserRunning": False,
            }

    monkeypatch.setattr(camofox_service.httpx, "get", lambda *_args, **_kwargs: FakeResponse())

    reachable, health_ok, message = camofox_service._health("http://127.0.0.1:9377")

    assert reachable is True
    assert health_ok is True
    assert message == "Camofox server is reachable; browser launches on demand."


def test_camofox_helper_paths_are_defensive(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tool_dir = _tool_dir(tmp_path)
    settings = _settings(
        tmp_path,
        research_camofox_tool_dir=tool_dir,
        research_camofox_base_url="http://localhost:9378",
        camofox_access_key="configured-access",
    )
    state_path = camofox_service.camofox_service_state_path(settings)
    state_path.parent.mkdir(parents=True)
    state_path.write_text("{not-json", encoding="utf-8")
    assert camofox_service._read_state(settings) is None
    camofox_service._remove_state(settings)
    camofox_service._remove_state(settings)
    assert not state_path.exists()

    stdout_path = tmp_path / "out.log"
    stderr_path = tmp_path / "err.log"
    stdout_path.write_text("camoufox launch attempt failed\n", encoding="utf-8")
    stderr_path.write_text("CAMOFOX_ACCESS_KEY=secret-value\n", encoding="utf-8")
    state = camofox_service.CamofoxServiceState(
        pid=1,
        host="127.0.0.1",
        port=9377,
        base_url="http://127.0.0.1:9377",
        started_at="2026-01-01T00:00:00+00:00",
        stdout_log_path=str(stdout_path),
        stderr_log_path=str(stderr_path),
        command=["node", "server.js"],
        tool_dir=str(tool_dir),
    )
    assert camofox_service._tail_contains_browser_launch_failure(state) is True
    assert "secret-value" not in camofox_service._tail_text(str(stderr_path))[0]
    assert camofox_service._tail_text(None) == []
    assert camofox_service._tail_contains_browser_launch_failure(None) is False

    assert camofox_service._configured_host_port(settings) == ("localhost", 9378)
    assert camofox_service._configured_base_url(settings) == "http://localhost:9378"

    monkeypatch.setenv("CAMOFOX_COOKIES_DIR", "/tmp/cookies")
    monkeypatch.setenv("PROXY_HOST", "127.0.0.1")
    monkeypatch.setenv("CAMOFOX_CRASH_REPORT_ENABLED", "true")
    env = camofox_service._camofox_env(settings, host="127.0.0.1", port=9390)
    assert env["CAMOFOX_ACCESS_KEY"] == "configured-access"
    assert env["CAMOFOX_COOKIES_DIR"] == "/tmp/cookies"
    assert env["PROXY_HOST"] == "127.0.0.1"
    assert env["CAMOFOX_CRASH_REPORT_ENABLED"] == "true"
    assert env["CAMOFOX_PORT"] == "9390"

    monkeypatch.setattr(camofox_service, "_is_port_available", lambda _host, port: port == 9379)
    assert camofox_service.choose_camofox_port("127.0.0.1", 9377) == 9379
    with pytest.raises(ValueError, match="loopback"):
        camofox_service.choose_camofox_port("0.0.0.0")
    monkeypatch.setattr(camofox_service, "_is_port_available", lambda *_args: False)
    with pytest.raises(RuntimeError, match="no_free"):
        camofox_service.choose_camofox_port("127.0.0.1")


def test_camofox_runtime_command_and_probe_messages(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tool_dir = _tool_dir(tmp_path)
    monkeypatch.setattr(camofox_service, "_node_command_path", lambda: None)
    with pytest.raises(RuntimeError, match="node"):
        camofox_service._runtime_command(tool_dir)

    monkeypatch.setattr(camofox_service, "_node_command_path", lambda: "/usr/bin/node")
    (tool_dir / "server.js").unlink()
    with pytest.raises(RuntimeError, match="missing"):
        camofox_service._runtime_command(tool_dir)
    (tool_dir / "server.js").write_text("console.log('ok')", encoding="utf-8")
    for child in (tool_dir / "node_modules").iterdir():
        child.unlink()
    (tool_dir / "node_modules").rmdir()
    with pytest.raises(RuntimeError, match="dependencies"):
        camofox_service._runtime_command(tool_dir)
    (tool_dir / "node_modules").mkdir()
    assert camofox_service._runtime_command(tool_dir) == ["/usr/bin/node", "server.js"]

    assert camofox_service._camofox_blocking_status_message(
        probe_host="0.0.0.0",
        package_available=True,
        command_path="/usr/bin/node",
        dependency_available=True,
    ) == "Camofox base URL must remain loopback."
    assert camofox_service._camofox_blocking_status_message(
        probe_host="127.0.0.1",
        package_available=False,
        command_path="/usr/bin/node",
        dependency_available=True,
    ) == "Camofox browser helper is missing."
    assert camofox_service._camofox_blocking_status_message(
        probe_host="127.0.0.1",
        package_available=True,
        command_path=None,
        dependency_available=True,
    ) == "node is not installed or not on PATH."
    assert camofox_service._camofox_blocking_status_message(
        probe_host="127.0.0.1",
        package_available=True,
        command_path="/usr/bin/node",
        dependency_available=False,
    ) == (
        "Camofox dependencies are missing. Run "
        "`pnpm --dir tools/camofox-browser install --ignore-workspace --ignore-scripts`."
    )
    assert camofox_service._camofox_blocking_status_message(
        probe_host="127.0.0.1",
        package_available=True,
        command_path="/usr/bin/node",
        dependency_available=True,
    ) is None

    state = camofox_service.CamofoxServiceState(
        pid=123,
        host="127.0.0.1",
        port=9377,
        base_url="http://127.0.0.1:9377",
        started_at="2026-01-01T00:00:00+00:00",
        stdout_log_path=str(tmp_path / "out.log"),
        stderr_log_path=str(tmp_path / "err.log"),
        command=["node", "server.js"],
        tool_dir=str(tool_dir),
    )
    monkeypatch.setattr(camofox_service, "_health", lambda _url: (True, True, "ok"))
    assert camofox_service._camofox_probe_status(
        base_url=state.base_url, state=state, app_state=state
    ) == (True, True, "App-owned Camofox is running.")
    monkeypatch.setattr(
        camofox_service,
        "_tail_contains_browser_launch_failure",
        lambda _state: True,
    )
    assert camofox_service._camofox_probe_status(
        base_url=state.base_url, state=state, app_state=state
    ) == (
        True,
        False,
        "Camofox server is reachable, but browser launch is failing.",
    )
    assert camofox_service._camofox_probe_status(
        base_url=state.base_url, state=state, app_state=None
    )[2].startswith("Recorded Camofox state is stale")


def test_camofox_process_and_stop_helpers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tool_dir = _tool_dir(tmp_path)
    state = camofox_service.CamofoxServiceState(
        pid=456,
        host="127.0.0.1",
        port=9377,
        base_url="http://127.0.0.1:9377",
        started_at="2026-01-01T00:00:00+00:00",
        stdout_log_path=str(tmp_path / "out.log"),
        stderr_log_path=str(tmp_path / "err.log"),
        command=["node", "server.js"],
        tool_dir=str(tool_dir),
    )

    class Completed:
        def __init__(self, returncode: int, stdout: str) -> None:
            self.returncode = returncode
            self.stdout = stdout

    def fake_run(command: list[str], **_kwargs: object) -> Completed:
        if command[:3] == ["ps", "-p", "456"]:
            return Completed(0, "/usr/bin/node server.js\n")
        if "-d" in command:
            return Completed(0, f"n{tool_dir.resolve()}\n")
        if any(str(item).startswith("-iTCP@127.0.0.1:9377") for item in command):
            return Completed(0, "p456\n")
        raise AssertionError(command)

    monkeypatch.setattr(camofox_service.subprocess, "run", fake_run)
    assert camofox_service._process_command_line(456) == "/usr/bin/node server.js"
    assert camofox_service._process_cwd(456) == tool_dir.resolve()
    assert camofox_service._listen_port_owner_pid("localhost", 9377) == 456
    assert camofox_service._process_matches_state(state) is True
    monkeypatch.setattr(camofox_service, "is_process_alive", lambda pid: pid == 456)
    assert camofox_service._state_process_alive(state) is True
    monkeypatch.setattr(camofox_service, "_state_process_alive", lambda _state: False)
    assert camofox_service._wait_for_state_exit(state, timeout=0.01) is True

    kill_calls: list[int] = []
    monkeypatch.setattr(camofox_service.os, "kill", lambda pid, _signal: kill_calls.append(pid))
    stopped, error = camofox_service._stop_camofox_state_process(state)
    assert stopped is True
    assert error is None
    assert kill_calls == [456]


def test_camofox_start_and_stop_short_circuit_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tool_dir = _tool_dir(tmp_path)
    settings = _settings(
        tmp_path,
        research_camofox_tool_dir=tool_dir,
        camofox_access_key="local-key",
    )
    state = camofox_service.CamofoxServiceState(
        pid=999,
        host="127.0.0.1",
        port=9377,
        base_url="http://127.0.0.1:9377",
        started_at="2026-01-01T00:00:00+00:00",
        stdout_log_path=str(tmp_path / "out.log"),
        stderr_log_path=str(tmp_path / "err.log"),
        command=["node", "server.js"],
        tool_dir=str(tool_dir),
    )
    status = _status(app_owned=True)

    monkeypatch.setattr(camofox_service, "_runtime_command", lambda _tool_dir: ["node", "server.js"])
    monkeypatch.setattr(camofox_service, "_read_state", lambda _settings: state)
    monkeypatch.setattr(camofox_service, "_state_process_alive", lambda _state: True)
    monkeypatch.setattr(camofox_service, "build_camofox_service_status", lambda _settings: status)
    assert camofox_service.start_camofox_service(settings) == status

    removed: list[str] = []
    monkeypatch.setattr(camofox_service, "_state_process_alive", lambda _state: False)
    monkeypatch.setattr(camofox_service, "_remove_state", lambda _settings: removed.append("state"))
    assert camofox_service.stop_camofox_service(settings) == status
    assert removed == ["state"]

    monkeypatch.setattr(camofox_service, "_read_state", lambda _settings: None)
    assert camofox_service.stop_camofox_service(settings) == status
