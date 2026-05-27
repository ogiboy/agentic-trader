import signal
from pathlib import Path
from typing import Any, cast

import pytest

from agentic_trader.config import Settings
from agentic_trader.system import webgui_service
from tests.typing_helpers import (
    constant,
    listen_owner_for,
    pid_in,
    pid_is,
    port_available_except,
    process_command_line,
    process_command_line_for,
    process_cwd_for,
    reachable_message,
    state_pid_is,
    state_pid_is_alive,
    unreachable_message,
)


def _settings(tmp_path: Path, **overrides: Any) -> Settings:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        market_data_cache_dir=tmp_path / "market_cache",
        **overrides,
    )
    settings.ensure_directories()
    return settings


def _next_cli_path() -> Path:
    return (
        webgui_service.webgui_dir() / "node_modules" / "next" / "dist" / "bin" / "next"
    )


def test_choose_webgui_port_rejects_non_loopback() -> None:
    with pytest.raises(ValueError, match="webgui_host_must_be_loopback"):
        webgui_service.choose_webgui_port("0.0.0.0")


def test_choose_webgui_port_skips_occupied_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        webgui_service,
        "_is_port_available",
        port_available_except(webgui_service.DEFAULT_WEBGUI_PORT),
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
        """
        Test double for subprocess.Popen that records invocation arguments and returns a fake process.

        Records the provided `command`, `cwd`, `stdout`, `stderr`, `env`, and `start_new_session` into the surrounding `captured` mapping and returns a new `FakeProcess` instance.

        Parameters:
            command (list[str]): The command that would have been executed.
            cwd (Path): The working directory passed to the process.
            stdout: The stdout argument passed to the process.
            stderr: The stderr argument passed to the process.
            env (dict[str, str]): Environment variables passed to the process.
            start_new_session (bool): Whether the process was requested to start a new session.

        Returns:
            FakeProcess: A test double representing the spawned process.
        """
        captured["command"] = command
        captured["cwd"] = cwd
        captured["stdout"] = stdout
        captured["stderr"] = stderr
        captured["env"] = env
        captured["start_new_session"] = start_new_session
        return FakeProcess()

    monkeypatch.setenv("AGENTIC_TRADER_ALPACA_SECRET_KEY", "secret-value")
    monkeypatch.setattr(
        webgui_service, "_node_command_path", constant("/opt/homebrew/bin/node")
    )
    monkeypatch.setattr(webgui_service, "_next_cli_path", _next_cli_path)
    monkeypatch.setattr(webgui_service, "_webgui_package_available", constant(True))
    monkeypatch.setattr(webgui_service, "_is_port_available", constant(True))
    monkeypatch.setattr(webgui_service.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(webgui_service, "is_process_alive", pid_is(FakeProcess.pid))
    monkeypatch.setattr(webgui_service, "_process_matches_state", constant(True))
    monkeypatch.setattr(
        webgui_service,
        "_webgui_reachable",
        reachable_message("{url} reachable"),
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
    env = cast("dict[str, str]", captured["env"])
    assert Path(env["AGENTIC_TRADER_PYTHON"]).name.startswith("python")
    assert env["AGENTIC_TRADER_WEBGUI_LOOPBACK_ONLY"] == "1"
    assert env["AGENTIC_TRADER_ALPACA_SECRET_KEY"] == "secret-value"
    state = webgui_service.read_webgui_service_state(settings)
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
        """
        Test helper that mimics subprocess.Popen by returning a new FakeProcess.

        All provided arguments are accepted for compatibility with Popen but ignored.

        Parameters:
            command (list[str]): The command that would be executed (ignored).
            cwd (Path): Working directory for the process (ignored).
            stdout: Stdout target (ignored).
            stderr: Stderr target (ignored).
            env (dict[str, str]): Environment variables (ignored).
            start_new_session (bool): Whether to start a new session (ignored).

        Returns:
            FakeProcess: A newly created fake process instance.
        """
        _ = command, cwd, stdout, stderr, env, start_new_session
        return FakeProcess()

    monkeypatch.setattr(
        webgui_service, "_node_command_path", constant("/opt/homebrew/bin/node")
    )
    monkeypatch.setattr(webgui_service, "_next_cli_path", _next_cli_path)
    monkeypatch.setattr(webgui_service, "_webgui_package_available", constant(True))
    monkeypatch.setattr(webgui_service, "_is_port_available", constant(True))
    monkeypatch.setattr(webgui_service.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(webgui_service, "_listen_port_owner_pid", constant(222))
    monkeypatch.setattr(webgui_service, "is_process_alive", pid_is(222))
    monkeypatch.setattr(webgui_service, "_process_matches_state", state_pid_is(222))
    monkeypatch.setattr(
        webgui_service, "_webgui_reachable", reachable_message("reachable")
    )

    status = webgui_service.start_webgui_service(settings)

    state = webgui_service.read_webgui_service_state(settings)
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
    webgui_service.write_webgui_service_state(settings, state)

    monkeypatch.setattr(
        webgui_service, "_node_command_path", constant("/opt/homebrew/bin/node")
    )
    monkeypatch.setattr(webgui_service, "_next_cli_path", _next_cli_path)
    monkeypatch.setattr(webgui_service, "_webgui_package_available", constant(True))
    monkeypatch.setattr(webgui_service, "is_process_alive", pid_is(111))
    monkeypatch.setattr(webgui_service, "_process_matches_state", constant(False))
    monkeypatch.setattr(
        webgui_service, "_webgui_reachable", reachable_message("reachable")
    )

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
    webgui_service.write_webgui_service_state(settings, state)

    monkeypatch.setattr(
        webgui_service, "_node_command_path", constant("/opt/homebrew/bin/node")
    )
    monkeypatch.setattr(webgui_service, "_next_cli_path", _next_cli_path)
    monkeypatch.setattr(webgui_service, "_webgui_package_available", constant(True))
    monkeypatch.setattr(webgui_service, "is_process_alive", constant(False))
    monkeypatch.setattr(
        webgui_service,
        "_listen_port_owner_pid",
        listen_owner_for({webgui_service.DEFAULT_WEBGUI_PORT: 222}),
    )
    monkeypatch.setattr(webgui_service, "_process_looks_like_webgui", pid_is(222))
    monkeypatch.setattr(
        webgui_service,
        "_webgui_reachable",
        reachable_message("Web GUI is reachable."),
    )

    status = webgui_service.start_webgui_service(settings)

    assert status.service_reachable is True
    assert status.app_owned is False
    assert status.port == webgui_service.DEFAULT_WEBGUI_PORT
    assert "not started by webgui-service" in status.message
    assert not webgui_service.webgui_service_state_path(settings).exists()


def test_status_reports_external_webgui_when_no_state_exists(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """
    Verifies that the service reports an externally-run Web GUI as external when no persisted state file exists.

    Simulates an external process owning the default WebGUI port and appearing to be a WebGUI, and verifies that:
    - the service is reported reachable,
    - the service is not marked as app-owned,
    - the reported port is the default WebGUI port,
    - the status message indicates the WebGUI was not started by webgui-service.
    """
    settings = _settings(tmp_path)

    monkeypatch.setattr(
        webgui_service, "_node_command_path", constant("/opt/homebrew/bin/node")
    )
    monkeypatch.setattr(webgui_service, "_next_cli_path", _next_cli_path)
    monkeypatch.setattr(webgui_service, "_webgui_package_available", constant(True))
    monkeypatch.setattr(
        webgui_service,
        "_listen_port_owner_pid",
        listen_owner_for({webgui_service.DEFAULT_WEBGUI_PORT: 222}),
    )
    monkeypatch.setattr(webgui_service, "_process_looks_like_webgui", pid_is(222))
    monkeypatch.setattr(
        webgui_service,
        "_webgui_reachable",
        reachable_message("Web GUI is reachable."),
    )

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
    webgui_service.write_webgui_service_state(settings, state)
    killed: list[int] = []

    def record_kill(pid: int, _sent_signal: int) -> None:
        killed.append(pid)

    monkeypatch.setattr(webgui_service, "is_process_alive", pid_is(88882))
    monkeypatch.setattr(webgui_service, "_process_matches_state", constant(False))
    monkeypatch.setattr(webgui_service.os, "kill", record_kill)
    monkeypatch.setattr(
        webgui_service, "_webgui_reachable", unreachable_message("unavailable")
    )

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
    webgui_service.write_webgui_service_state(settings, state)
    signals: list[tuple[int, int]] = []
    wait_timeouts: list[float] = []

    def fake_wait(_state: webgui_service.WebGUIServiceState, *, timeout: float) -> bool:
        """
        Simulate waiting for a WebGUI service state to exit while recording the timeout value.

        Parameters:
            _state (WebGUIServiceState): State object to check (unused by this fake).
            timeout (float): Timeout duration that will be recorded.

        Returns:
            bool: `False` indicating the state did not exit within the given timeout.
        """
        wait_timeouts.append(timeout)
        return False

    def getpgid(pid: int) -> int:
        return pid + 10

    def record_group_signal(pgid: int, sig: int) -> None:
        signals.append((pgid, sig))

    monkeypatch.setattr(webgui_service, "is_process_alive", pid_is(88883))
    monkeypatch.setattr(webgui_service, "_process_matches_state", constant(True))
    monkeypatch.setattr(webgui_service.os, "getpgid", getpgid)
    monkeypatch.setattr(webgui_service.os, "killpg", record_group_signal)
    monkeypatch.setattr(webgui_service, "_wait_for_state_exit", fake_wait)
    monkeypatch.setattr(
        webgui_service, "_webgui_reachable", unreachable_message("unavailable")
    )

    status = webgui_service.stop_webgui_service(settings)

    assert signals == [
        (88893, signal.SIGTERM),
        (88893, getattr(signal, "SIGKILL", signal.SIGTERM)),
    ]
    assert wait_timeouts == [5, 1]
    assert "state preserved" in status.message
    assert webgui_service.webgui_service_state_path(settings).exists()


def test_stop_webgui_service_falls_back_to_verified_launcher_and_listener_pids(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """
    Verifies that stopping the WebGUI service falls back to terminating a verified launcher and listener PID pair when direct state-based termination is not sufficient.

    Asserts that the process group receives a SIGTERM, that the verified listener PID is terminated and then the launcher PID is terminated (both with SIGTERM), that the returned status indicates the service is not app-owned, and that the persisted service state file is removed.
    """
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
    webgui_service.write_webgui_service_state(settings, state)
    alive = {111, 222}
    group_signals: list[tuple[int, int]] = []
    pid_signals: list[tuple[int, int]] = []

    def fake_kill(pid: int, sent_signal: int) -> None:
        """
        Record a simulated signal sent to a process and mark that process as no longer alive.

        Parameters:
            pid (int): Process ID receiving the signal.
            sent_signal (int): Signal number sent to the process.
        """
        pid_signals.append((pid, sent_signal))
        alive.discard(pid)

    def record_group_signal(pgid: int, sig: int) -> None:
        group_signals.append((pgid, sig))

    monkeypatch.setattr(webgui_service, "is_process_alive", pid_in(alive))
    monkeypatch.setattr(
        webgui_service,
        "_process_matches_state",
        state_pid_is_alive(222, alive),
    )
    monkeypatch.setattr(
        webgui_service,
        "_process_command_line",
        process_command_line_for(
            {
                111: (
                    "node webgui/node_modules/next/dist/bin/next dev "
                    "--hostname 127.0.0.1 -p 3210"
                ),
                222: "next-server (v16.2.6)",
            }
        ),
    )
    monkeypatch.setattr(webgui_service.os, "getpgid", constant(333))
    monkeypatch.setattr(webgui_service.os, "killpg", record_group_signal)
    monkeypatch.setattr(webgui_service.os, "kill", fake_kill)
    monkeypatch.setattr(
        webgui_service, "_webgui_reachable", unreachable_message("unavailable")
    )

    status = webgui_service.stop_webgui_service(settings)

    assert group_signals == [(333, signal.SIGTERM)]
    assert pid_signals == [(222, signal.SIGTERM), (111, signal.SIGTERM)]
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
    webgui_service.write_webgui_service_state(settings, state)
    killed: list[tuple[int, int]] = []
    alive = {222}

    def fake_killpg(pgid: int, sig: int) -> None:
        """
        Record a simulated process-group termination and mark the test listener PID as dead.

        Parameters:
            pgid (int): The process group ID that would be signaled.
            sig (int): The signal number sent to the process group.
        """
        killed.append((pgid, sig))
        alive.discard(222)

    monkeypatch.setattr(webgui_service, "is_process_alive", pid_in(alive))
    monkeypatch.setattr(webgui_service, "_process_matches_state", state_pid_is(222))
    monkeypatch.setattr(webgui_service.os, "getpgid", constant(333))
    monkeypatch.setattr(webgui_service.os, "killpg", fake_killpg)
    monkeypatch.setattr(
        webgui_service, "_webgui_reachable", unreachable_message("unavailable")
    )

    status = webgui_service.stop_webgui_service(settings)

    assert killed == [(333, signal.SIGTERM)]
    assert status.app_owned is False


def test_stop_webgui_service_kills_next_server_listener_verified_by_cwd(
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
    webgui_service.write_webgui_service_state(settings, state)
    alive = {222}
    killed_groups: list[tuple[int, int]] = []
    killed_pids: list[tuple[int, int]] = []

    def fake_killpg(pgid: int, sig: int) -> None:
        """
        Record a process-group kill signal for test inspection.

        Appends the tuple (pgid, sig) to the outer-scope `killed_groups` list so tests can assert which signals would have been sent.

        Parameters:
            pgid (int): The process group ID targeted.
            sig (int): The signal number sent to the process group.
        """
        killed_groups.append((pgid, sig))

    def fake_kill(pid: int, sig: int) -> None:
        """
        Simulate sending a signal to a process by recording the (pid, sig) pair and removing the pid from the alive set.

        Parameters:
            pid (int): Process ID to signal.
            sig (int): Signal number to record.
        """
        killed_pids.append((pid, sig))
        alive.discard(pid)

    monkeypatch.setattr(webgui_service, "is_process_alive", pid_in(alive))
    monkeypatch.setattr(
        webgui_service,
        "_process_command_line",
        process_command_line_for({222: "next-server (v16.2.6)"}),
    )
    monkeypatch.setattr(
        webgui_service,
        "_process_cwd",
        process_cwd_for({222: webgui_service.webgui_dir().resolve()}),
    )
    monkeypatch.setattr(
        webgui_service,
        "_listen_port_owner_pid",
        listen_owner_for({3210: 222}),
    )
    monkeypatch.setattr(webgui_service.os, "getpgid", constant(333))
    monkeypatch.setattr(webgui_service.os, "killpg", fake_killpg)
    monkeypatch.setattr(webgui_service.os, "kill", fake_kill)
    monkeypatch.setattr(
        webgui_service, "_webgui_reachable", unreachable_message("unavailable")
    )

    status = webgui_service.stop_webgui_service(settings)

    assert killed_groups == [(333, signal.SIGTERM)]
    assert killed_pids == [(222, signal.SIGTERM)]
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

    monkeypatch.setattr(
        webgui_service, "_process_command_line", process_command_line(None)
    )
    monkeypatch.setattr(
        webgui_service,
        "_listen_port_owner_pid",
        listen_owner_for({3210: 4242}),
    )

    assert webgui_service.webgui_process_matches_state(state) is True


def test_listen_port_owner_pid_returns_none_when_lsof_is_unavailable_or_ambiguous(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Completed:
        returncode = 0
        stdout = "p111\np222\n"

    def missing_lsof(*_args: object, **_kwargs: object) -> object:
        raise FileNotFoundError

    monkeypatch.setattr(webgui_service.subprocess, "run", missing_lsof)
    assert webgui_service.webgui_listen_port_owner_pid("127.0.0.1", 3210) is None

    def fake_run(*_args: object, **_kwargs: object) -> Completed:
        return Completed()

    monkeypatch.setattr(webgui_service.subprocess, "run", fake_run)
    assert webgui_service.webgui_listen_port_owner_pid("127.0.0.1", 3210) is None
