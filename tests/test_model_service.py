import signal
from pathlib import Path
from typing import Any

import pytest

from agentic_trader.config import Settings
from agentic_trader.system import model_service
from agentic_trader.system.model_service import same_loopback_api_root
from tests.typing_helpers import (
    constant,
    empty_int_list,
    loopback_ports_for,
    no_sleep,
    ollama_tags_available,
    ollama_tags_reachable,
    ollama_tags_unavailable,
    pid_is,
    pid_not_in,
    port_available_except,
    process_command_line,
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


def test_choose_app_managed_port_rejects_non_loopback() -> None:
    with pytest.raises(ValueError, match="model_service_host_must_be_loopback"):
        model_service.choose_app_managed_port("0.0.0.0", 11434)


def test_choose_app_managed_port_skips_occupied_preferred(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        model_service,
        "_is_port_available",
        port_available_except(11434),
    )

    assert model_service.choose_app_managed_port("127.0.0.1", 11434) == 11435


def test_start_model_service_uses_minimal_env_and_owner_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path)
    captured: dict[str, object] = {}

    class FakeProcess:
        pid = 99991

    def fake_popen(
        command: list[str],
        *,
        stdout: object,
        stderr: object,
        env: dict[str, str],
        start_new_session: bool,
    ) -> FakeProcess:
        """
        Act as a test replacement for subprocess.Popen that records the invocation and returns a FakeProcess.

        Parameters:
            command (list[str]): The command and arguments passed to the process.
            stdout: The stdout stream/redirect passed to Popen.
            stderr: The stderr stream/redirect passed to Popen.
            env (dict[str, str]): Environment variables passed to the process.
            start_new_session (bool): Whether the process is started in a new session.

        Returns:
            FakeProcess: A new FakeProcess instance.

        Notes:
            Invocation details are saved into the surrounding `captured` mapping under the keys
            "command", "stdout", "stderr", "env", and "start_new_session".
        """
        captured["command"] = command
        captured["stdout"] = stdout
        captured["stderr"] = stderr
        captured["env"] = env
        captured["start_new_session"] = start_new_session
        return FakeProcess()

    monkeypatch.setenv("AGENTIC_TRADER_ALPACA_SECRET_KEY", "secret-value")
    monkeypatch.setattr(
        model_service.shutil, "which", constant("/opt/homebrew/bin/ollama")
    )
    monkeypatch.setattr(model_service, "_external_ollama_serve_pids", empty_int_list)
    monkeypatch.setattr(model_service, "_is_port_available", constant(True))
    monkeypatch.setattr(model_service.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(
        model_service,
        "_fetch_ollama_tags",
        ollama_tags_available,
    )
    monkeypatch.setattr(
        model_service,
        "is_process_alive",
        pid_is(FakeProcess.pid),
    )
    monkeypatch.setattr(model_service, "_process_matches_state", constant(True))

    status = model_service.start_model_service(settings)

    assert status.app_owned is True
    assert status.owner == settings.host_id
    assert status.is_owned_by_host(settings.host_id) is True
    assert status.service_reachable is True
    assert status.model_available is True
    assert status.base_url == "http://127.0.0.1:11434"
    assert status.tool_id == "ollama"
    assert status.tool_status_id == "ollama_cli"
    assert "model-service" in status.tool_consumers
    assert "app_managed_repo_config" in status.tool_fallback_order
    assert "app-owned" in status.tool_ownership_modes
    assert "local_tool_id=ollama" in status.notes
    assert captured["command"] == ["/opt/homebrew/bin/ollama", "serve"]
    env = captured["env"]
    assert isinstance(env, dict)
    assert env["OLLAMA_HOST"] == "http://127.0.0.1:11434"
    assert "AGENTIC_TRADER_ALPACA_SECRET_KEY" not in env
    assert model_service.model_service_state_path(settings).exists()


def test_start_model_service_waits_for_app_owned_endpoint_when_host_exists(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path, base_url="http://127.0.0.1:11434/v1")
    captured_urls: list[str] = []

    class FakeProcess:
        pid = 99992

    def fake_popen(
        command: list[str],
        *,
        stdout: object,
        stderr: object,
        env: dict[str, str],
        start_new_session: bool,
    ) -> FakeProcess:
        _ = (command, stdout, stderr, env, start_new_session)
        return FakeProcess()

    process_ready = iter([False, True, True])

    def fake_process_matches_state(_state: model_service.ModelServiceState) -> bool:
        return next(process_ready)

    def fake_fetch(
        api_root: str,
        timeout_seconds: float = 2.0,
    ) -> tuple[bool, list[str], str]:
        """
        Stub implementation used in tests that records the probed API root and returns a deterministic "reachable" response with example model tags.

        Parameters:
            api_root (str): The API root URL being probed; this value is appended to captured_urls.
            timeout_seconds (float): Ignored by this stub (present to match the real function's signature).

        Returns:
            tuple: `(reachable, tags, message)` where `reachable` is `True` if the API root is considered reachable, `tags` is a list of available model tags (e.g., `["qwen3:8b"]`), and `message` is a human-readable status string that includes the probed `api_root`.
        """
        _ = timeout_seconds
        captured_urls.append(api_root)
        return True, ["qwen3:8b"], f"{api_root} reachable"

    monkeypatch.setattr(
        model_service.shutil, "which", constant("/opt/homebrew/bin/ollama")
    )
    monkeypatch.setattr(model_service, "_external_ollama_serve_pids", empty_int_list)
    monkeypatch.setattr(
        model_service, "_is_port_available", port_available_except(11434)
    )
    monkeypatch.setattr(model_service.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(model_service, "is_process_alive", pid_is(FakeProcess.pid))
    monkeypatch.setattr(
        model_service, "_process_matches_state", fake_process_matches_state
    )
    monkeypatch.setattr(model_service, "_fetch_ollama_tags", fake_fetch)
    monkeypatch.setattr(model_service.time, "sleep", no_sleep)

    status = model_service.start_model_service(settings)

    assert status.app_owned is True
    assert status.base_url == "http://127.0.0.1:11435"
    assert captured_urls[0] == "http://127.0.0.1:11435"


def test_model_service_process_match_requires_listening_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = model_service.ModelServiceState(
        pid=12345,
        host="127.0.0.1",
        port=11435,
        base_url="http://127.0.0.1:11435",
        started_at="2026-01-01T00:00:00+00:00",
        stdout_log_path="/tmp/out.log",
        stderr_log_path="/tmp/err.log",
        command=["/opt/homebrew/bin/ollama", "serve"],
    )

    monkeypatch.setattr(
        model_service,
        "_process_command_line",
        process_command_line("/opt/homebrew/bin/ollama serve"),
    )
    monkeypatch.setattr(model_service, "_listen_port_owner_pid", constant(12345))

    assert model_service.model_service_process_matches_state(state) is True

    monkeypatch.setattr(model_service, "_listen_port_owner_pid", constant(54321))

    assert model_service.model_service_process_matches_state(state) is False


def test_model_service_process_match_accepts_port_owner_when_command_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = model_service.ModelServiceState(
        pid=12345,
        host="127.0.0.1",
        port=11435,
        base_url="http://127.0.0.1:11435",
        started_at="2026-01-01T00:00:00+00:00",
        stdout_log_path="/tmp/out.log",
        stderr_log_path="/tmp/err.log",
        command=["/opt/homebrew/bin/ollama", "serve"],
    )

    monkeypatch.setattr(
        model_service, "_process_command_line", process_command_line(None)
    )
    monkeypatch.setattr(model_service, "_listen_port_owner_pid", constant(12345))

    assert model_service.model_service_process_matches_state(state) is True


def test_pull_model_uses_app_owned_host_without_provider_secrets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path)
    state = model_service.ModelServiceState(
        pid=12345,
        host="127.0.0.1",
        port=11435,
        base_url="http://127.0.0.1:11435",
        started_at="2026-01-01T00:00:00+00:00",
        stdout_log_path=str(tmp_path / "out.log"),
        stderr_log_path=str(tmp_path / "err.log"),
        command=["ollama", "serve"],
    )
    model_service.write_model_service_state(settings, state)
    captured: dict[str, object] = {}

    def fake_run(
        command: list[str],
        *,
        text: bool,
        capture_output: bool,
        timeout: int,
        check: bool,
        env: dict[str, str],
    ) -> object:
        """
        Test helper that simulates subprocess.run for command capture.

        Records the invoked `command` and `env` into the external `captured` mapping and returns a fake completed-process object with `returncode`, `stdout`, and `stderr` attributes.

        Returns:
            An object with attributes:
                - `returncode` (int): the process exit code (0).
                - `stdout` (str): simulated standard output ("ok").
                - `stderr` (str): simulated standard error (empty string).
        """
        captured["command"] = command
        captured["env"] = env

        class Completed:
            returncode = 0
            stdout = "ok"
            stderr = ""

        _ = (text, capture_output, timeout, check)
        return Completed()

    monkeypatch.setenv("AGENTIC_TRADER_FMP_API_KEY", "secret-value")
    monkeypatch.setattr(
        model_service.shutil, "which", constant("/opt/homebrew/bin/ollama")
    )
    monkeypatch.setattr(model_service, "is_process_alive", pid_is(12345))
    monkeypatch.setattr(model_service, "_process_matches_state", constant(True))
    monkeypatch.setattr(model_service.subprocess, "run", fake_run)

    payload = model_service.pull_model(settings, "qwen3:8b")

    assert payload["exit_code"] == 0
    assert captured["command"] == ["/opt/homebrew/bin/ollama", "pull", "qwen3:8b"]
    env = captured["env"]
    assert isinstance(env, dict)
    assert env["OLLAMA_HOST"] == "http://127.0.0.1:11435"
    assert "AGENTIC_TRADER_FMP_API_KEY" not in env


def test_stop_model_service_does_not_kill_unmatched_reused_pid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path)
    state = model_service.ModelServiceState(
        pid=77777,
        host="127.0.0.1",
        port=11435,
        base_url="http://127.0.0.1:11435",
        started_at="2026-01-01T00:00:00+00:00",
        stdout_log_path=str(tmp_path / "out.log"),
        stderr_log_path=str(tmp_path / "err.log"),
        command=["/opt/homebrew/bin/ollama", "serve"],
    )
    model_service.write_model_service_state(settings, state)
    killed: list[int] = []

    def record_kill(pid: int, _sent_signal: int) -> None:
        killed.append(pid)

    monkeypatch.setattr(model_service, "is_process_alive", pid_is(77777))
    monkeypatch.setattr(model_service, "_process_matches_state", constant(False))
    monkeypatch.setattr(model_service, "_external_ollama_serve_pids", empty_int_list)
    monkeypatch.setattr(model_service.os, "kill", record_kill)
    monkeypatch.setattr(
        model_service,
        "_fetch_ollama_tags",
        ollama_tags_unavailable,
    )

    status = model_service.stop_model_service(settings)

    assert killed == []
    assert status.app_owned is False
    assert not model_service.model_service_state_path(settings).exists()


def test_stop_model_service_escalates_to_kill_when_sigterm_does_not_stop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path)
    state = model_service.ModelServiceState(
        pid=88888,
        host="127.0.0.1",
        port=11435,
        base_url="http://127.0.0.1:11435",
        started_at="2026-01-01T00:00:00+00:00",
        stdout_log_path=str(tmp_path / "out.log"),
        stderr_log_path=str(tmp_path / "err.log"),
        command=["/opt/homebrew/bin/ollama", "serve"],
    )
    model_service.write_model_service_state(settings, state)
    alive = True
    sent_signals: list[int] = []

    def fake_kill(_pid: int, sent_signal: int) -> None:
        nonlocal alive
        sent_signals.append(sent_signal)
        if sent_signal == signal.SIGKILL:
            alive = False

    wait_results = iter([False, True])

    def is_test_process_alive(pid: int) -> bool:
        return alive and pid == 88888

    def matches_state(_state: model_service.ModelServiceState) -> bool:
        return alive

    def wait_for_pid_exit(_pid: int, *, timeout_seconds: float) -> bool:
        _ = timeout_seconds
        return next(wait_results)

    monkeypatch.setattr(model_service, "is_process_alive", is_test_process_alive)
    monkeypatch.setattr(model_service, "_process_matches_state", matches_state)
    monkeypatch.setattr(model_service, "_external_ollama_serve_pids", empty_int_list)
    monkeypatch.setattr(model_service.os, "kill", fake_kill)
    monkeypatch.setattr(
        model_service,
        "_wait_for_pid_exit",
        wait_for_pid_exit,
    )
    monkeypatch.setattr(
        model_service,
        "_fetch_ollama_tags",
        ollama_tags_unavailable,
    )

    status = model_service.stop_model_service(settings)

    assert sent_signals == [signal.SIGTERM, signal.SIGKILL]
    assert status.app_owned is False
    assert not model_service.model_service_state_path(settings).exists()


def test_stop_model_service_keeps_state_when_process_cannot_be_killed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path)
    state = model_service.ModelServiceState(
        pid=99999,
        host="127.0.0.1",
        port=11435,
        base_url="http://127.0.0.1:11435",
        started_at="2026-01-01T00:00:00+00:00",
        stdout_log_path=str(tmp_path / "out.log"),
        stderr_log_path=str(tmp_path / "err.log"),
        command=["/opt/homebrew/bin/ollama", "serve"],
    )
    model_service.write_model_service_state(settings, state)

    def deny_kill(_pid: int, _sent_signal: int) -> None:
        raise PermissionError("denied")

    monkeypatch.setattr(model_service, "is_process_alive", pid_is(99999))
    monkeypatch.setattr(model_service, "_process_matches_state", constant(True))
    monkeypatch.setattr(model_service, "_external_ollama_serve_pids", empty_int_list)
    monkeypatch.setattr(model_service.os, "kill", deny_kill)
    monkeypatch.setattr(
        model_service,
        "_fetch_ollama_tags",
        ollama_tags_available,
    )

    status = model_service.stop_model_service(settings)

    assert status.app_owned is True
    assert model_service.model_service_state_path(settings).exists()


def test_process_command_line_uses_windows_cim_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_run(
        command: list[str],
        *,
        capture_output: bool,
        text: bool,
        timeout: int,
        check: bool,
    ) -> object:
        captured["command"] = command
        _ = (capture_output, text, timeout, check)

        class Completed:
            returncode = 0
            stdout = "ollama serve\n"

        return Completed()

    monkeypatch.setattr(model_service.sys, "platform", "win32")
    monkeypatch.setattr(model_service.subprocess, "run", fake_run)

    assert model_service.model_service_process_command_line(12345) == "ollama serve"
    command = captured["command"]
    assert isinstance(command, list)
    assert command[:3] == ["powershell", "-NoProfile", "-Command"]
    assert "ProcessId = 12345" in command[3]


def test_model_service_status_marks_app_owned_base_url_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path, base_url="http://127.0.0.1:11434/v1")
    state = model_service.ModelServiceState(
        pid=22222,
        host="127.0.0.1",
        port=11435,
        base_url="http://127.0.0.1:11435",
        started_at="2026-01-01T00:00:00+00:00",
        stdout_log_path=str(tmp_path / "out.log"),
        stderr_log_path=str(tmp_path / "err.log"),
        command=["/opt/homebrew/bin/ollama", "serve"],
    )
    model_service.write_model_service_state(settings, state)

    monkeypatch.setattr(model_service, "is_process_alive", pid_is(22222))
    monkeypatch.setattr(model_service, "_process_matches_state", constant(True))
    monkeypatch.setattr(
        model_service,
        "_fetch_ollama_tags",
        ollama_tags_available,
    )

    status = model_service.build_model_service_status(settings)

    assert status.app_owned is True
    assert status.runtime_base_url_matches_app_service is False
    assert "different base URL" in status.message


def test_model_service_status_accepts_equivalent_loopback_base_url(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path, base_url="http://localhost:11434/v1")
    state = model_service.ModelServiceState(
        pid=22223,
        host="127.0.0.1",
        port=11434,
        base_url="http://127.0.0.1:11434",
        started_at="2026-01-01T00:00:00+00:00",
        stdout_log_path=str(tmp_path / "out.log"),
        stderr_log_path=str(tmp_path / "err.log"),
        command=["/opt/homebrew/bin/ollama", "serve"],
    )
    model_service.write_model_service_state(settings, state)

    monkeypatch.setattr(model_service, "is_process_alive", pid_is(22223))
    monkeypatch.setattr(model_service, "_process_matches_state", constant(True))
    monkeypatch.setattr(
        model_service,
        "_fetch_ollama_tags",
        ollama_tags_available,
    )

    status = model_service.build_model_service_status(settings)

    assert status.runtime_base_url_matches_app_service is True
    assert "different base URL" not in status.message


def test_model_service_status_can_probe_generation_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path)

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json() -> dict[str, str]:
            return {
                "error": (
                    "model failed to load, this may be due to resource "
                    "limitations or an internal error"
                )
            }

    monkeypatch.setattr(
        model_service,
        "_fetch_ollama_tags",
        ollama_tags_available,
    )

    def fake_post(*_args: object, **_kwargs: object) -> FakeResponse:
        return FakeResponse()

    monkeypatch.setattr(model_service.httpx, "post", fake_post)

    status = model_service.build_model_service_status(
        settings,
        include_generation=True,
    )

    assert status.generation_checked is True
    assert status.generation_available is False
    assert "model failed to load" in (status.generation_message or "")
    assert "generation probe failed" in status.message


def test_model_service_status_warns_about_duplicate_external_ollama(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)

    monkeypatch.setattr(
        model_service.shutil, "which", constant("/opt/homebrew/bin/ollama")
    )
    monkeypatch.setattr(
        model_service,
        "_external_ollama_serve_pids",
        constant([111, 222]),
    )
    monkeypatch.setattr(
        model_service,
        "_listening_loopback_ports_for_pid",
        loopback_ports_for({111: {11434}, 222: {11450}}),
    )
    monkeypatch.setattr(
        model_service,
        "_fetch_ollama_tags",
        ollama_tags_reachable,
    )

    status = model_service.build_model_service_status(settings)

    assert status.app_owned is False
    assert "Multiple host/default Ollama serve processes" in status.message
    assert "ollama_process_count=2" in status.notes
    assert "external_ollama_duplicate_processes_detected" in status.notes
    assert "orphan_app_managed_ollama_process_count=1" in status.notes


def test_ollama_pid_detection_falls_back_to_lsof_when_ps_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(
        command: list[str],
        *,
        capture_output: bool,
        text: bool,
        timeout: int,
        check: bool,
    ) -> object:
        """
        Fake subprocess.run used in tests to simulate `ps` and `lsof` invocations.

        Parameters:
            command (list[str]): The command that would be run. Only the command prefix is inspected.
            capture_output (bool): Ignored (kept for signature compatibility).
            text (bool): Ignored (kept for signature compatibility).
            timeout (int): Ignored (kept for signature compatibility).
            check (bool): Ignored (kept for signature compatibility).

        Returns:
            An object with attributes:
              - `returncode` (int): Simulated process exit code.
              - `stdout` (str): Simulated standard output. For `["ps","-ax"]` returns `returncode=1` and empty stdout. For `["lsof","-nP","-iTCP"]` returns `returncode=0` and a multi-line stdout containing pseudo `p<uid>`, `c...`, `f...`, and `n<addr:port>` lines. For any other command returns `returncode=0` and empty stdout.
        """
        _ = (capture_output, text, timeout, check)

        class Completed:
            def __init__(self, returncode: int, stdout: str = "") -> None:
                self.returncode = returncode
                self.stdout = stdout

        if command[:2] == ["ps", "-ax"]:
            return Completed(1)
        if command[:3] == ["lsof", "-nP", "-iTCP"]:
            return Completed(
                0,
                "p111\n"
                "collama\n"
                "f3\n"
                "n127.0.0.1:11435\n"
                "p222\n"
                "cnode\n"
                "f3\n"
                "n127.0.0.1:11436\n"
                "p333\n"
                "collama\n"
                "f3\n"
                "n*:11437\n"
                "p444\n"
                "collama\n"
                "f3\n"
                "n127.0.0.1:11434\n",
            )
        return Completed(0)

    monkeypatch.setattr(model_service.subprocess, "run", fake_run)

    assert model_service.external_ollama_serve_pids("/opt/homebrew/bin/ollama") == [
        111,
        444,
    ]


def test_ollama_pid_detection_ignores_model_runner_child(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(
        command: list[str],
        *,
        capture_output: bool,
        text: bool,
        timeout: int,
        check: bool,
    ) -> object:
        """
        Test helper that simulates subprocess.run responses for `ps -ax` and `lsof -nP -iTCP` calls.

        For `["ps", "-ax"]` it returns a result with stdout containing two process lines:
        - a normal `ollama serve` process (PID 111)
        - an `ollama runner` child process (PID 222) including a `--port 60443` fragment

        For `["lsof", "-nP", "-iTCP"]` it returns stdout representing an lsof-style block that references port `127.0.0.1:60443` tied to PID 222.

        For any other command it returns a successful result with empty stdout.

        Returns:
            An object with attributes `returncode` (int) and `stdout` (str) representing the simulated command result.
        """
        _ = (capture_output, text, timeout, check)

        class Completed:
            def __init__(self, returncode: int, stdout: str = "") -> None:
                """
                Initialize the result with a process return code and captured standard output.

                Parameters:
                    returncode (int): Process exit code; 0 typically indicates success.
                    stdout (str): Captured standard output text (empty string by default).
                """
                self.returncode = returncode
                self.stdout = stdout

        if command[:2] == ["ps", "-ax"]:
            return Completed(
                0,
                "111 /opt/homebrew/bin/ollama serve\n"
                "222 /opt/homebrew/Cellar/ollama/0.24.0/libexec/ollama "
                "runner --ollama-engine --model "
                "/Users/me/.ollama/models/blobs/sha256-abc --port 60443\n",
            )
        if command[:3] == ["lsof", "-nP", "-iTCP"]:
            return Completed(
                0,
                "p222\ncollama\nf3\nn127.0.0.1:60443\n",
            )
        return Completed(0)

    monkeypatch.setattr(model_service.subprocess, "run", fake_run)

    assert model_service.external_ollama_serve_pids("/opt/homebrew/bin/ollama") == [
        111,
    ]


def test_stop_model_service_does_not_kill_unrecorded_managed_ports(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    killed: list[int] = []

    monkeypatch.setattr(
        model_service.shutil, "which", constant("/opt/homebrew/bin/ollama")
    )
    monkeypatch.setattr(
        model_service,
        "_external_ollama_serve_pids",
        constant([111, 222]),
    )
    monkeypatch.setattr(
        model_service,
        "_listening_loopback_ports_for_pid",
        loopback_ports_for({111: {11435}, 222: {11434}}),
    )
    monkeypatch.setattr(model_service, "is_process_alive", pid_not_in(killed))

    def fake_kill(pid: int, sent_signal: int) -> None:
        if sent_signal == signal.SIGTERM:
            killed.append(pid)

    def wait_for_pid_exit(pid: int, *, timeout_seconds: float) -> bool:
        _ = timeout_seconds
        return pid in killed

    monkeypatch.setattr(model_service.os, "kill", fake_kill)
    monkeypatch.setattr(
        model_service,
        "_wait_for_pid_exit",
        wait_for_pid_exit,
    )
    monkeypatch.setattr(
        model_service,
        "_fetch_ollama_tags",
        ollama_tags_reachable,
    )

    status = model_service.stop_model_service(settings)

    assert status.app_owned is False
    assert killed == []


# ---------------------------------------------------------------------------
# _same_loopback_api_root
# ---------------------------------------------------------------------------


def test_same_loopback_api_root_identical_urls() -> None:
    assert (
        same_loopback_api_root(
            "http://127.0.0.1:11434",
            "http://127.0.0.1:11434",
        )
        is True
    )


def test_same_loopback_api_root_localhost_and_127_same_port() -> None:
    assert (
        same_loopback_api_root(
            "http://localhost:11434",
            "http://127.0.0.1:11434",
        )
        is True
    )


def test_same_loopback_api_root_different_ports_returns_false() -> None:
    assert (
        same_loopback_api_root(
            "http://127.0.0.1:11434",
            "http://127.0.0.1:11435",
        )
        is False
    )


def test_same_loopback_api_root_different_scheme_returns_false() -> None:
    assert (
        same_loopback_api_root(
            "http://127.0.0.1:11434",
            "https://127.0.0.1:11434",
        )
        is False
    )


def test_same_loopback_api_root_non_loopback_host_returns_false() -> None:
    assert (
        same_loopback_api_root(
            "http://example.com:11434",
            "http://127.0.0.1:11434",
        )
        is False
    )


def test_same_loopback_api_root_schemeless_strings_use_exact_match() -> None:
    assert same_loopback_api_root("localhost:11434", "localhost:11434") is True
    assert same_loopback_api_root("localhost:11434", "localhost:11435") is False


def test_same_loopback_api_root_path_mismatch_returns_false() -> None:
    assert (
        same_loopback_api_root(
            "http://127.0.0.1:11434/api",
            "http://127.0.0.1:11434/other",
        )
        is False
    )


def test_same_loopback_api_root_trailing_slash_ignored_in_path() -> None:
    assert (
        same_loopback_api_root(
            "http://127.0.0.1:11434/api/",
            "http://127.0.0.1:11434/api",
        )
        is True
    )
