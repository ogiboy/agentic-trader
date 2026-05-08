import signal
from pathlib import Path
from typing import Any

import pytest

from agentic_trader.config import Settings
from agentic_trader.system import webgui_service


def _settings(tmp_path: Path, **overrides: Any) -> Settings:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        market_data_cache_dir=tmp_path / "market_cache",
        **overrides,
    )
    settings.ensure_directories()
    return settings


def test_choose_webgui_port_rejects_non_loopback() -> None:
    with pytest.raises(ValueError, match="webgui_host_must_be_loopback"):
        webgui_service.choose_webgui_port("0.0.0.0")


def test_choose_webgui_port_skips_occupied_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        webgui_service,
        "_is_port_available",
        lambda _host, port: port != webgui_service.DEFAULT_WEBGUI_PORT,
    )

    assert webgui_service.choose_webgui_port("127.0.0.1") == 3211


def test_start_webgui_service_uses_loopback_and_managed_python(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path)
    captured: dict[str, object] = {}

    class FakeProcess:
        pid = 88881

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

    monkeypatch.setenv("AGENTIC_TRADER_ALPACA_SECRET_KEY", "secret-value")
    monkeypatch.setattr(webgui_service, "_node_command_path", lambda: "/opt/homebrew/bin/node")
    monkeypatch.setattr(
        webgui_service,
        "_next_cli_path",
        lambda: webgui_service.webgui_dir() / "node_modules" / "next" / "dist" / "bin" / "next",
    )
    monkeypatch.setattr(webgui_service, "_webgui_package_available", lambda: True)
    monkeypatch.setattr(webgui_service, "_is_port_available", lambda _host, _port: True)
    monkeypatch.setattr(webgui_service.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(webgui_service, "is_process_alive", lambda pid: pid == FakeProcess.pid)
    monkeypatch.setattr(webgui_service, "_process_matches_state", lambda _state: True)
    monkeypatch.setattr(
        webgui_service,
        "_webgui_reachable",
        lambda url: (True, f"{url} reachable"),
    )

    status = webgui_service.start_webgui_service(settings)

    assert status.app_owned is True
    assert status.service_reachable is True
    assert status.url == "http://127.0.0.1:3210"
    command = captured["command"]
    assert isinstance(command, list)
    assert command[0] == "/opt/homebrew/bin/node"
    assert "next/dist/bin/next" in command[1]
    assert "--hostname" in command
    assert "127.0.0.1" in command
    env = captured["env"]
    assert isinstance(env, dict)
    assert Path(env["AGENTIC_TRADER_PYTHON"]).name.startswith("python")
    assert env["AGENTIC_TRADER_ALPACA_SECRET_KEY"] == "secret-value"
    state = webgui_service._read_state(settings)
    assert state is not None
    assert state.pid == FakeProcess.pid
    assert state.launcher_pid == FakeProcess.pid


def test_start_webgui_service_records_listener_pid_instead_of_launcher_pid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path)

    class FakeProcess:
        pid = 111

    def fake_popen(
        command: list[str],
        *,
        cwd: Path,
        stdout: object,
        stderr: object,
        env: dict[str, str],
        start_new_session: bool,
    ) -> FakeProcess:
        _ = command, cwd, stdout, stderr, env, start_new_session
        return FakeProcess()

    monkeypatch.setattr(webgui_service, "_node_command_path", lambda: "/opt/homebrew/bin/node")
    monkeypatch.setattr(
        webgui_service,
        "_next_cli_path",
        lambda: webgui_service.webgui_dir() / "node_modules" / "next" / "dist" / "bin" / "next",
    )
    monkeypatch.setattr(webgui_service, "_webgui_package_available", lambda: True)
    monkeypatch.setattr(webgui_service, "_is_port_available", lambda _host, _port: True)
    monkeypatch.setattr(webgui_service.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(webgui_service, "_listen_port_owner_pid", lambda _host, _port: 222)
    monkeypatch.setattr(webgui_service, "is_process_alive", lambda pid: pid == 222)
    monkeypatch.setattr(webgui_service, "_process_matches_state", lambda state: state.pid == 222)
    monkeypatch.setattr(webgui_service, "_webgui_reachable", lambda _url: (True, "reachable"))

    status = webgui_service.start_webgui_service(settings)

    state = webgui_service._read_state(settings)
    assert state is not None
    assert state.pid == 222
    assert state.launcher_pid == 111
    assert status.app_owned is True
    assert status.pid == 222


def test_status_marks_reachable_external_listener_not_app_owned(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path)
    state = webgui_service.WebGUIServiceState(
        pid=111,
        launcher_pid=111,
        host="127.0.0.1",
        port=3210,
        url="http://127.0.0.1:3210",
        started_at="2026-01-01T00:00:00+00:00",
        stdout_log_path=str(tmp_path / "out.log"),
        stderr_log_path=str(tmp_path / "err.log"),
        command=["node", "webgui/node_modules/next/dist/bin/next", "dev"],
    )
    webgui_service._write_state(settings, state)

    monkeypatch.setattr(webgui_service, "_node_command_path", lambda: "/opt/homebrew/bin/node")
    monkeypatch.setattr(
        webgui_service,
        "_next_cli_path",
        lambda: webgui_service.webgui_dir() / "node_modules" / "next" / "dist" / "bin" / "next",
    )
    monkeypatch.setattr(webgui_service, "_webgui_package_available", lambda: True)
    monkeypatch.setattr(webgui_service, "is_process_alive", lambda pid: pid == 111)
    monkeypatch.setattr(webgui_service, "_process_matches_state", lambda _state: False)
    monkeypatch.setattr(webgui_service, "_webgui_reachable", lambda _url: (True, "reachable"))

    status = webgui_service.build_webgui_service_status(settings)

    assert status.service_reachable is True
    assert status.app_owned is False
    assert status.pid is None
    assert status.stdout_log_path is None


def test_start_webgui_service_returns_external_status_for_existing_webgui(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path)
    state = webgui_service.WebGUIServiceState(
        pid=111,
        launcher_pid=111,
        host="127.0.0.1",
        port=3211,
        url="http://127.0.0.1:3211",
        started_at="2026-01-01T00:00:00+00:00",
        stdout_log_path=str(tmp_path / "out.log"),
        stderr_log_path=str(tmp_path / "err.log"),
        command=["node", "webgui/node_modules/next/dist/bin/next", "dev"],
    )
    webgui_service._write_state(settings, state)

    monkeypatch.setattr(webgui_service, "_node_command_path", lambda: "/opt/homebrew/bin/node")
    monkeypatch.setattr(
        webgui_service,
        "_next_cli_path",
        lambda: webgui_service.webgui_dir() / "node_modules" / "next" / "dist" / "bin" / "next",
    )
    monkeypatch.setattr(webgui_service, "_webgui_package_available", lambda: True)
    monkeypatch.setattr(webgui_service, "is_process_alive", lambda _pid: False)
    monkeypatch.setattr(
        webgui_service,
        "_listen_port_owner_pid",
        lambda _host, port: 222 if port == webgui_service.DEFAULT_WEBGUI_PORT else None,
    )
    monkeypatch.setattr(webgui_service, "_process_looks_like_webgui", lambda pid: pid == 222)
    monkeypatch.setattr(webgui_service, "_webgui_reachable", lambda _url: (True, "Web GUI is reachable."))

    status = webgui_service.start_webgui_service(settings)

    assert status.service_reachable is True
    assert status.app_owned is False
    assert status.port == webgui_service.DEFAULT_WEBGUI_PORT
    assert "not started by webgui-service" in status.message
    assert not webgui_service.webgui_service_state_path(settings).exists()


def test_status_reports_external_webgui_when_no_state_exists(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path)

    monkeypatch.setattr(webgui_service, "_node_command_path", lambda: "/opt/homebrew/bin/node")
    monkeypatch.setattr(
        webgui_service,
        "_next_cli_path",
        lambda: webgui_service.webgui_dir() / "node_modules" / "next" / "dist" / "bin" / "next",
    )
    monkeypatch.setattr(webgui_service, "_webgui_package_available", lambda: True)
    monkeypatch.setattr(
        webgui_service,
        "_listen_port_owner_pid",
        lambda _host, port: 222 if port == webgui_service.DEFAULT_WEBGUI_PORT else None,
    )
    monkeypatch.setattr(webgui_service, "_process_looks_like_webgui", lambda pid: pid == 222)
    monkeypatch.setattr(webgui_service, "_webgui_reachable", lambda _url: (True, "Web GUI is reachable."))

    status = webgui_service.build_webgui_service_status(settings)

    assert status.service_reachable is True
    assert status.app_owned is False
    assert status.port == webgui_service.DEFAULT_WEBGUI_PORT
    assert "not started by webgui-service" in status.message


def test_stop_webgui_service_does_not_kill_unmatched_reused_pid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path)
    state = webgui_service.WebGUIServiceState(
        pid=88882,
        host="127.0.0.1",
        port=3210,
        url="http://127.0.0.1:3210",
        started_at="2026-01-01T00:00:00+00:00",
        stdout_log_path=str(tmp_path / "out.log"),
        stderr_log_path=str(tmp_path / "err.log"),
        command=["node", "webgui/node_modules/next/dist/bin/next", "dev"],
    )
    webgui_service._write_state(settings, state)
    killed: list[int] = []

    monkeypatch.setattr(webgui_service, "is_process_alive", lambda pid: pid == 88882)
    monkeypatch.setattr(webgui_service, "_process_matches_state", lambda _state: False)
    monkeypatch.setattr(webgui_service.os, "kill", lambda pid, _signal: killed.append(pid))
    monkeypatch.setattr(webgui_service, "_webgui_reachable", lambda _url: (False, "unavailable"))

    status = webgui_service.stop_webgui_service(settings)

    assert killed == []
    assert status.app_owned is False
    assert not webgui_service.webgui_service_state_path(settings).exists()


def test_stop_webgui_service_escalates_when_app_owned_process_survives_sigterm(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path)
    state = webgui_service.WebGUIServiceState(
        pid=88883,
        host="127.0.0.1",
        port=3210,
        url="http://127.0.0.1:3210",
        started_at="2026-01-01T00:00:00+00:00",
        stdout_log_path=str(tmp_path / "out.log"),
        stderr_log_path=str(tmp_path / "err.log"),
        command=["node", "webgui/node_modules/next/dist/bin/next", "dev"],
    )
    webgui_service._write_state(settings, state)
    signals: list[int] = []
    wait_timeouts: list[float] = []

    def fake_wait(_state: webgui_service.WebGUIServiceState, *, timeout: float) -> bool:
        wait_timeouts.append(timeout)
        return False

    monkeypatch.setattr(webgui_service, "is_process_alive", lambda pid: pid == 88883)
    monkeypatch.setattr(webgui_service, "_process_matches_state", lambda _state: True)
    monkeypatch.setattr(webgui_service.os, "kill", lambda _pid, sig: signals.append(sig))
    monkeypatch.setattr(webgui_service, "_wait_for_state_exit", fake_wait)
    monkeypatch.setattr(webgui_service, "_webgui_reachable", lambda _url: (False, "unavailable"))

    status = webgui_service.stop_webgui_service(settings)

    assert signals == [
        signal.SIGTERM,
        getattr(signal, "SIGKILL", signal.SIGTERM),
    ]
    assert wait_timeouts == [5, 1]
    assert status.app_owned is False
    assert not webgui_service.webgui_service_state_path(settings).exists()


def test_stop_webgui_service_kills_verified_listener_pid_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path)
    state = webgui_service.WebGUIServiceState(
        pid=222,
        launcher_pid=111,
        host="127.0.0.1",
        port=3210,
        url="http://127.0.0.1:3210",
        started_at="2026-01-01T00:00:00+00:00",
        stdout_log_path=str(tmp_path / "out.log"),
        stderr_log_path=str(tmp_path / "err.log"),
        command=["node", "webgui/node_modules/next/dist/bin/next", "dev"],
    )
    webgui_service._write_state(settings, state)
    killed: list[int] = []
    alive = {222}

    def fake_kill(pid: int, _signal: int) -> None:
        killed.append(pid)
        alive.discard(pid)

    monkeypatch.setattr(webgui_service, "is_process_alive", lambda pid: pid in alive)
    monkeypatch.setattr(webgui_service, "_process_matches_state", lambda checked: checked.pid == 222)
    monkeypatch.setattr(webgui_service.os, "kill", fake_kill)
    monkeypatch.setattr(webgui_service, "_webgui_reachable", lambda _url: (False, "unavailable"))

    status = webgui_service.stop_webgui_service(settings)

    assert killed == [222]
    assert status.app_owned is False


def test_process_matches_state_uses_lsof_when_ps_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = webgui_service.WebGUIServiceState(
        pid=4242,
        host="127.0.0.1",
        port=3210,
        url="http://127.0.0.1:3210",
        started_at="2026-01-01T00:00:00+00:00",
        stdout_log_path="/tmp/out.log",
        stderr_log_path="/tmp/err.log",
        command=["node", "webgui/node_modules/next/dist/bin/next", "dev"],
    )

    monkeypatch.setattr(webgui_service, "_process_command_line", lambda _pid: None)
    monkeypatch.setattr(
        webgui_service,
        "_listen_port_owner_pid",
        lambda host, port: 4242 if host == "127.0.0.1" and port == 3210 else None,
    )

    assert webgui_service._process_matches_state(state) is True


def test_listen_port_owner_pid_returns_none_when_lsof_is_unavailable_or_ambiguous(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Completed:
        returncode = 0
        stdout = "p111\np222\n"

    def missing_lsof(*_args: object, **_kwargs: object) -> object:
        raise FileNotFoundError

    monkeypatch.setattr(webgui_service.subprocess, "run", missing_lsof)
    assert webgui_service._listen_port_owner_pid("127.0.0.1", 3210) is None

    monkeypatch.setattr(webgui_service.subprocess, "run", lambda *_args, **_kwargs: Completed())
    assert webgui_service._listen_port_owner_pid("127.0.0.1", 3210) is None
