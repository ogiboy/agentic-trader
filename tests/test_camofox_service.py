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
