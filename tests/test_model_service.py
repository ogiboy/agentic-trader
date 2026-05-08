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
    assert "local_tool_id=ollama" in status.notes
    assert captured["command"] == ["/opt/homebrew/bin/ollama", "serve"]
    env = captured["env"]
    assert isinstance(env, dict)
    assert env["OLLAMA_HOST"] == "http://127.0.0.1:11434"
    assert "AGENTIC_TRADER_ALPACA_SECRET_KEY" not in env
    assert model_service.model_service_state_path(settings).exists()


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
    monkeypatch.setattr(model_service.os, "kill", fake_kill)
    monkeypatch.setattr(
        model_service,
        "_wait_for_state_process_exit",
        lambda _state, timeout_seconds: next(wait_results),
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
