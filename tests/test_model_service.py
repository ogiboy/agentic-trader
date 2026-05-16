import signal
from pathlib import Path
from typing import Any

import pytest

from agentic_trader.config import Settings
from agentic_trader.system import model_service


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
        lambda _host, port: port != 11434,
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
        captured["command"] = command
        captured["stdout"] = stdout
        captured["stderr"] = stderr
        captured["env"] = env
        captured["start_new_session"] = start_new_session
        return FakeProcess()

    monkeypatch.setenv("AGENTIC_TRADER_ALPACA_SECRET_KEY", "secret-value")
    monkeypatch.setattr(model_service.shutil, "which", lambda _: "/opt/homebrew/bin/ollama")
    monkeypatch.setattr(model_service, "_external_ollama_serve_pids", lambda _path: [])
    monkeypatch.setattr(model_service, "_is_port_available", lambda _host, _port: True)
    monkeypatch.setattr(model_service.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(
        model_service,
        "_fetch_ollama_tags",
        lambda api_root, timeout_seconds=2.0: (
            True,
            ["qwen3:8b"],
            f"{api_root} reachable",
        ),
    )
    monkeypatch.setattr(
        model_service,
        "is_process_alive",
        lambda pid: pid == FakeProcess.pid,
    )
    monkeypatch.setattr(model_service, "_process_matches_state", lambda _state: True)

    status = model_service.start_model_service(settings)

    assert status.app_owned is True
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
        _ = timeout_seconds
        captured_urls.append(api_root)
        return True, ["qwen3:8b"], f"{api_root} reachable"

    monkeypatch.setattr(model_service.shutil, "which", lambda _: "/opt/homebrew/bin/ollama")
    monkeypatch.setattr(model_service, "_external_ollama_serve_pids", lambda _path: [])
    monkeypatch.setattr(model_service, "_is_port_available", lambda _host, port: port != 11434)
    monkeypatch.setattr(model_service.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(model_service, "is_process_alive", lambda pid: pid == FakeProcess.pid)
    monkeypatch.setattr(model_service, "_process_matches_state", fake_process_matches_state)
    monkeypatch.setattr(model_service, "_fetch_ollama_tags", fake_fetch)
    monkeypatch.setattr(model_service.time, "sleep", lambda _seconds: None)

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
        lambda _pid: "/opt/homebrew/bin/ollama serve",
    )
    monkeypatch.setattr(model_service, "_listen_port_owner_pid", lambda _host, _port: 12345)

    assert model_service._process_matches_state(state) is True

    monkeypatch.setattr(model_service, "_listen_port_owner_pid", lambda _host, _port: 54321)

    assert model_service._process_matches_state(state) is False


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

    monkeypatch.setattr(model_service, "_process_command_line", lambda _pid: None)
    monkeypatch.setattr(model_service, "_listen_port_owner_pid", lambda _host, _port: 12345)

    assert model_service._process_matches_state(state) is True


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
    model_service._write_state(settings, state)
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
        captured["command"] = command
        captured["env"] = env

        class Completed:
            returncode = 0
            stdout = "ok"
            stderr = ""

        _ = (text, capture_output, timeout, check)
        return Completed()

    monkeypatch.setenv("AGENTIC_TRADER_FMP_API_KEY", "secret-value")
    monkeypatch.setattr(model_service.shutil, "which", lambda _: "/opt/homebrew/bin/ollama")
    monkeypatch.setattr(model_service, "is_process_alive", lambda pid: pid == 12345)
    monkeypatch.setattr(model_service, "_process_matches_state", lambda _state: True)
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
    model_service._write_state(settings, state)
    killed: list[int] = []

    monkeypatch.setattr(model_service, "is_process_alive", lambda pid: pid == 77777)
    monkeypatch.setattr(model_service, "_process_matches_state", lambda _state: False)
    monkeypatch.setattr(model_service, "_external_ollama_serve_pids", lambda _path: [])
    monkeypatch.setattr(model_service.os, "kill", lambda pid, _signal: killed.append(pid))
    monkeypatch.setattr(
        model_service,
        "_fetch_ollama_tags",
        lambda api_root, timeout_seconds=2.0: (False, [], f"{api_root} unavailable"),
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
    model_service._write_state(settings, state)
    alive = True
    sent_signals: list[int] = []

    def fake_kill(_pid: int, sent_signal: int) -> None:
        nonlocal alive
        sent_signals.append(sent_signal)
        if sent_signal == signal.SIGKILL:
            alive = False

    wait_results = iter([False, True])

    monkeypatch.setattr(model_service, "is_process_alive", lambda pid: alive and pid == 88888)
    monkeypatch.setattr(model_service, "_process_matches_state", lambda _state: alive)
    monkeypatch.setattr(model_service, "_external_ollama_serve_pids", lambda _path: [])
    monkeypatch.setattr(model_service.os, "kill", fake_kill)
    monkeypatch.setattr(
        model_service,
        "_wait_for_pid_exit",
        lambda _pid, timeout_seconds: next(wait_results),
    )
    monkeypatch.setattr(
        model_service,
        "_fetch_ollama_tags",
        lambda api_root, timeout_seconds=2.0: (False, [], f"{api_root} unavailable"),
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
    model_service._write_state(settings, state)

    monkeypatch.setattr(model_service, "is_process_alive", lambda pid: pid == 99999)
    monkeypatch.setattr(model_service, "_process_matches_state", lambda _state: True)
    monkeypatch.setattr(model_service, "_external_ollama_serve_pids", lambda _path: [])
    monkeypatch.setattr(
        model_service.os,
        "kill",
        lambda _pid, _signal: (_ for _ in ()).throw(PermissionError("denied")),
    )
    monkeypatch.setattr(
        model_service,
        "_fetch_ollama_tags",
        lambda api_root, timeout_seconds=2.0: (True, ["qwen3:8b"], f"{api_root} reachable"),
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

    assert model_service._process_command_line(12345) == "ollama serve"
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
    model_service._write_state(settings, state)

    monkeypatch.setattr(model_service, "is_process_alive", lambda pid: pid == 22222)
    monkeypatch.setattr(model_service, "_process_matches_state", lambda _state: True)
    monkeypatch.setattr(
        model_service,
        "_fetch_ollama_tags",
        lambda api_root, timeout_seconds=2.0: (
            True,
            ["qwen3:8b"],
            f"{api_root} reachable",
        ),
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
    model_service._write_state(settings, state)

    monkeypatch.setattr(model_service, "is_process_alive", lambda pid: pid == 22223)
    monkeypatch.setattr(model_service, "_process_matches_state", lambda _state: True)
    monkeypatch.setattr(
        model_service,
        "_fetch_ollama_tags",
        lambda api_root, timeout_seconds=2.0: (
            True,
            ["qwen3:8b"],
            f"{api_root} reachable",
        ),
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
        lambda api_root, timeout_seconds=2.0: (
            True,
            ["qwen3:8b"],
            f"{api_root} reachable",
        ),
    )
    monkeypatch.setattr(
        model_service.httpx,
        "post",
        lambda *_args, **_kwargs: FakeResponse(),
    )

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

    monkeypatch.setattr(model_service.shutil, "which", lambda _: "/opt/homebrew/bin/ollama")
    monkeypatch.setattr(
        model_service,
        "_external_ollama_serve_pids",
        lambda _command_path: [111, 222],
    )
    monkeypatch.setattr(
        model_service,
        "_listening_loopback_ports_for_pid",
        lambda pid: {11434} if pid == 111 else {11450},
    )
    monkeypatch.setattr(
        model_service,
        "_fetch_ollama_tags",
        lambda api_root, timeout_seconds=2.0: (
            True,
            ["qwen3:8b"],
            "Ollama is reachable.",
        ),
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
                "n127.0.0.1:11434\n"
            )
        return Completed(0)

    monkeypatch.setattr(model_service.subprocess, "run", fake_run)

    assert model_service._external_ollama_serve_pids("/opt/homebrew/bin/ollama") == [
        111,
        444,
    ]


def test_stop_model_service_cleans_orphan_app_managed_ports_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    killed: list[int] = []

    monkeypatch.setattr(model_service.shutil, "which", lambda _: "/opt/homebrew/bin/ollama")
    monkeypatch.setattr(
        model_service,
        "_external_ollama_serve_pids",
        lambda _command_path: [111, 222],
    )
    monkeypatch.setattr(
        model_service,
        "_listening_loopback_ports_for_pid",
        lambda pid: {11435} if pid == 111 else {11434},
    )
    monkeypatch.setattr(model_service, "is_process_alive", lambda pid: pid not in killed)

    def fake_kill(pid: int, sent_signal: int) -> None:
        if sent_signal == signal.SIGTERM:
            killed.append(pid)

    monkeypatch.setattr(model_service.os, "kill", fake_kill)
    monkeypatch.setattr(model_service, "_wait_for_pid_exit", lambda pid, timeout_seconds: pid in killed)
    monkeypatch.setattr(
        model_service,
        "_fetch_ollama_tags",
        lambda api_root, timeout_seconds=2.0: (
            True,
            ["qwen3:8b"],
            "Ollama is reachable.",
        ),
    )

    model_service.stop_model_service(settings)

    assert killed == [111]


def test_same_loopback_api_root_accepts_localhost_and_127() -> None:
    assert model_service._same_loopback_api_root(
        "http://localhost:11434",
        "http://127.0.0.1:11434",
    ) is True


def test_same_loopback_api_root_accepts_identical_hosts() -> None:
    assert model_service._same_loopback_api_root(
        "http://127.0.0.1:11434",
        "http://127.0.0.1:11434",
    ) is True


def test_same_loopback_api_root_rejects_different_ports() -> None:
    assert model_service._same_loopback_api_root(
        "http://127.0.0.1:11434",
        "http://127.0.0.1:11435",
    ) is False


def test_same_loopback_api_root_rejects_different_schemes() -> None:
    assert model_service._same_loopback_api_root(
        "http://127.0.0.1:11434",
        "https://127.0.0.1:11434",
    ) is False


def test_same_loopback_api_root_rejects_different_paths() -> None:
    assert model_service._same_loopback_api_root(
        "http://127.0.0.1:11434/api",
        "http://127.0.0.1:11434/v2",
    ) is False


def test_same_loopback_api_root_accepts_trailing_slash_equivalence() -> None:
    assert model_service._same_loopback_api_root(
        "http://127.0.0.1:11434/",
        "http://127.0.0.1:11434",
    ) is True


def test_same_loopback_api_root_handles_no_scheme_literal_comparison() -> None:
    assert model_service._same_loopback_api_root(
        "127.0.0.1:11434",
        "127.0.0.1:11434",
    ) is True
    assert model_service._same_loopback_api_root(
        "127.0.0.1:11434",
        "localhost:11434",
    ) is False


def test_same_loopback_api_root_rejects_non_loopback_even_if_same_host() -> None:
    assert model_service._same_loopback_api_root(
        "http://192.168.1.1:11434",
        "http://192.168.1.1:11434",
    ) is True
    assert model_service._same_loopback_api_root(
        "http://192.168.1.1:11434",
        "http://192.168.1.2:11434",
    ) is False
