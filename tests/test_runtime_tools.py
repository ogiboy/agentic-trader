from __future__ import annotations

import socket
from pathlib import Path
from typing import Any, cast

import httpx
import pytest

from agentic_trader.config import Settings
from agentic_trader.system import runtime_tools
from agentic_trader.system import model_service
from agentic_trader.system.camofox_service import CamofoxServiceStatus
from agentic_trader.system.model_service import ModelServiceState, ModelServiceStatus
from agentic_trader.system.tool_ownership import write_tool_ownership


def _settings(tmp_path: Path, **overrides: Any) -> Settings:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        market_data_cache_dir=tmp_path / "market_cache",
        **overrides,
    )
    settings.ensure_directories()
    return settings


def _model_status(
    *,
    app_owned: bool = False,
    reachable: bool = True,
    model_available: bool = True,
) -> ModelServiceStatus:
    return ModelServiceStatus(
        command_available=True,
        command_path="/opt/homebrew/bin/ollama",
        configured_base_url="http://127.0.0.1:11434/v1",
        configured_model="qwen3:8b",
        service_reachable=reachable,
        model_available=model_available,
        available_models=["qwen3:8b"] if model_available else [],
        app_owned=app_owned,
        pid=123 if app_owned else None,
        host="127.0.0.1" if app_owned else None,
        port=11435 if app_owned else None,
        base_url="http://127.0.0.1:11435" if app_owned else "http://127.0.0.1:11434",
        stdout_tail=[],
        stderr_tail=[],
        state_path="/tmp/model.json",
        message="model ready" if model_available else "model missing",
    )


def _camofox_status(*, app_owned: bool = False, healthy: bool = True) -> CamofoxServiceStatus:
    return CamofoxServiceStatus(
        command_available=True,
        command_path="/opt/homebrew/bin/node",
        package_available=True,
        dependency_available=True,
        dependency_path="/repo/tools/camofox-browser/node_modules",
        access_key_configured=True,
        service_reachable=healthy,
        health_ok=healthy,
        app_owned=app_owned,
        pid=456 if app_owned else None,
        host="127.0.0.1",
        port=9377,
        base_url="http://127.0.0.1:9377",
        stdout_tail=[],
        stderr_tail=[],
        state_path="/tmp/camofox.json",
        tool_dir="/repo/tools/camofox-browser",
        message="camofox ready" if healthy else "camofox missing",
    )


def test_ensure_model_service_updates_runtime_base_url_for_app_owned_service(
    monkeypatch,
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path, base_url="http://127.0.0.1:11434/v1")

    monkeypatch.setattr(
        runtime_tools,
        "build_model_service_status",
        lambda _settings: _model_status(app_owned=True),
    )

    status = runtime_tools.ensure_model_service_if_configured(settings)

    assert status.app_owned is True
    assert settings.base_url == "http://127.0.0.1:11435/v1"


def test_apply_app_owned_service_settings_uses_recorded_helpers_without_starting(
    monkeypatch,
    tmp_path: Path,
) -> None:
    settings = _settings(
        tmp_path,
        base_url="http://127.0.0.1:11434/v1",
        research_camofox_enabled=True,
    )
    write_tool_ownership(
        settings,
        {"ollama": "app-owned", "camofox": "app-owned"},
        source="test",
    )
    starts: list[str] = []

    monkeypatch.setattr(
        runtime_tools,
        "build_model_service_status",
        lambda _settings: _model_status(app_owned=True),
    )
    monkeypatch.setattr(
        runtime_tools,
        "build_camofox_service_status",
        lambda _settings: _camofox_status(app_owned=True),
    )
    monkeypatch.setattr(
        runtime_tools,
        "start_model_service",
        lambda _settings: starts.append("model") or _model_status(app_owned=True),
    )
    monkeypatch.setattr(
        runtime_tools,
        "start_camofox_service",
        lambda _settings: starts.append("camofox") or _camofox_status(app_owned=True),
    )

    report = runtime_tools.apply_app_owned_service_settings(
        settings,
        include_camofox=True,
    )

    assert starts == []
    assert report.model_service is not None
    assert report.model_service.app_owned is True
    assert settings.base_url == "http://127.0.0.1:11435/v1"
    assert settings.research_camofox_base_url == "http://127.0.0.1:9377"


def test_app_owned_model_service_does_not_override_non_ollama_adapter(
    monkeypatch,
    tmp_path: Path,
) -> None:
    settings = _settings(
        tmp_path,
        llm_provider="openai-compatible",
        base_url="http://127.0.0.1:8080/v1",
    )
    write_tool_ownership(settings, {"ollama": "app-owned"}, source="test")
    starts: list[str] = []
    monkeypatch.setattr(
        runtime_tools,
        "build_model_service_status",
        lambda _settings: _model_status(app_owned=True),
    )
    monkeypatch.setattr(
        runtime_tools,
        "start_model_service",
        lambda _settings: starts.append("model") or _model_status(app_owned=True),
    )

    report = runtime_tools.apply_app_owned_service_settings(settings)
    status = runtime_tools.ensure_model_service_if_configured(settings)

    assert starts == []
    assert settings.base_url == "http://127.0.0.1:8080/v1"
    assert report.model_service is not None
    assert status.app_owned is True


def test_ensure_runtime_tools_starts_configured_degraded_side_tools(
    monkeypatch,
    tmp_path: Path,
) -> None:
    settings = _settings(
        tmp_path,
        research_camofox_enabled=True,
        runtime_auto_start_model_service=True,
        runtime_auto_start_camofox=True,
    )
    write_tool_ownership(
        settings,
        {"ollama": "app-owned", "camofox": "app-owned"},
        source="test",
    )

    monkeypatch.setattr(
        runtime_tools,
        "build_model_service_status",
        lambda _settings: _model_status(reachable=False, model_available=False),
    )
    monkeypatch.setattr(
        runtime_tools,
        "start_model_service",
        lambda _settings: _model_status(app_owned=True),
    )
    monkeypatch.setattr(
        runtime_tools,
        "build_camofox_service_status",
        lambda _settings: _camofox_status(healthy=False),
    )
    monkeypatch.setattr(
        runtime_tools,
        "start_camofox_service",
        lambda _settings: _camofox_status(app_owned=True),
    )

    report = runtime_tools.ensure_runtime_tools(settings, include_camofox=True)

    assert report.model_service is not None
    assert report.model_service.app_owned is True
    assert report.camofox_service is not None
    assert report.camofox_service.app_owned is True
    assert settings.research_camofox_base_url == "http://127.0.0.1:9377"
    assert report.messages == ["model ready", "camofox ready"]


def test_ensure_runtime_tools_does_not_auto_start_host_owned_tools(
    monkeypatch,
    tmp_path: Path,
) -> None:
    settings = _settings(
        tmp_path,
        research_camofox_enabled=True,
        runtime_auto_start_model_service=True,
        runtime_auto_start_camofox=True,
    )
    write_tool_ownership(
        settings,
        {"ollama": "host-owned", "camofox": "host-owned"},
        source="test",
    )
    starts: list[str] = []

    monkeypatch.setattr(
        runtime_tools,
        "build_model_service_status",
        lambda _settings: _model_status(reachable=False, model_available=False),
    )
    monkeypatch.setattr(
        runtime_tools,
        "start_model_service",
        lambda _settings: starts.append("model") or _model_status(app_owned=True),
    )
    monkeypatch.setattr(
        runtime_tools,
        "build_camofox_service_status",
        lambda _settings: _camofox_status(healthy=False),
    )
    monkeypatch.setattr(
        runtime_tools,
        "start_camofox_service",
        lambda _settings: starts.append("camofox") or _camofox_status(app_owned=True),
    )

    report = runtime_tools.ensure_runtime_tools(settings, include_camofox=True)

    assert starts == []
    assert report.model_service is not None
    assert report.model_service.app_owned is False
    assert report.camofox_service is not None
    assert report.camofox_service.app_owned is False


def test_apply_app_owned_service_settings_skips_camofox_when_not_requested(
    monkeypatch,
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    write_tool_ownership(settings, {"ollama": "app-owned", "camofox": "app-owned"}, source="test")
    camofox_calls: list[str] = []

    monkeypatch.setattr(
        runtime_tools,
        "build_model_service_status",
        lambda _settings: _model_status(app_owned=True),
    )
    monkeypatch.setattr(
        runtime_tools,
        "build_camofox_service_status",
        lambda _settings: camofox_calls.append("called") or _camofox_status(app_owned=True),
    )

    report = runtime_tools.apply_app_owned_service_settings(settings, include_camofox=False)

    assert camofox_calls == []
    assert report.camofox_service is None
    assert report.model_service is not None


def test_apply_app_owned_service_settings_skips_base_url_update_when_undecided(
    monkeypatch,
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path, base_url="http://127.0.0.1:11434/v1")

    monkeypatch.setattr(
        runtime_tools,
        "build_model_service_status",
        lambda _settings: _model_status(app_owned=True),
    )

    report = runtime_tools.apply_app_owned_service_settings(settings)

    assert settings.base_url == "http://127.0.0.1:11434/v1"
    assert report.model_service is not None


def test_apply_app_owned_service_settings_skips_camofox_url_when_not_app_owned(
    monkeypatch,
    tmp_path: Path,
) -> None:
    settings = _settings(
        tmp_path,
        research_camofox_base_url="http://127.0.0.1:9377",
    )
    write_tool_ownership(settings, {"camofox": "host-owned"}, source="test")

    monkeypatch.setattr(
        runtime_tools,
        "build_model_service_status",
        lambda _settings: _model_status(),
    )
    monkeypatch.setattr(
        runtime_tools,
        "build_camofox_service_status",
        lambda _settings: _camofox_status(app_owned=False),
    )

    report = runtime_tools.apply_app_owned_service_settings(settings, include_camofox=True)

    assert settings.research_camofox_base_url == "http://127.0.0.1:9377"
    assert report.camofox_service is not None
    assert report.camofox_service.app_owned is False


def test_apply_app_owned_service_settings_report_messages_always_include_model(
    monkeypatch,
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)

    monkeypatch.setattr(
        runtime_tools,
        "build_model_service_status",
        lambda _settings: _model_status(reachable=False, model_available=False),
    )

    report = runtime_tools.apply_app_owned_service_settings(settings)

    assert len(report.messages) == 1
    assert report.messages[0] == "model missing"


def test_model_service_status_helpers_are_defensive(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path, base_url="http://127.0.0.1:11434/v1")
    state_path = model_service.model_service_state_path(settings)
    state_path.parent.mkdir(parents=True)
    state_path.write_text("{not-json", encoding="utf-8")

    assert model_service._read_state(settings) is None
    model_service._remove_state(settings)
    model_service._remove_state(settings)
    assert not state_path.exists()

    log_path = tmp_path / "ollama.log"
    log_path.write_text(
        "\n".join(["first", "AGENTIC_TRADER_ALPACA_SECRET_KEY=secret-value"]),
        encoding="utf-8",
    )
    tail = model_service._tail_text(str(log_path), limit=1)
    assert len(tail) == 1
    assert "secret-value" not in tail[0]
    assert model_service._tail_text(None) == []
    assert model_service._tail_text(str(tmp_path / "missing.log")) == []

    assert model_service._api_root_from_base_url("http://127.0.0.1:11434/v1") == (
        "http://127.0.0.1:11434"
    )
    assert model_service._api_root_from_base_url("http://127.0.0.1:11434/api") == (
        "http://127.0.0.1:11434/api"
    )
    assert model_service._api_root_from_base_url("localhost:11434/v1") == (
        "localhost:11434"
    )

    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setenv("AGENTIC_TRADER_ALPACA_SECRET_KEY", "secret-value")
    env = model_service._minimal_process_env(ollama_host="http://127.0.0.1:11435")
    assert env["OLLAMA_HOST"] == "http://127.0.0.1:11435"
    assert "AGENTIC_TRADER_ALPACA_SECRET_KEY" not in env


def test_model_service_process_and_lsof_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Completed:
        def __init__(self, returncode: int, stdout: str) -> None:
            self.returncode = returncode
            self.stdout = stdout

    calls: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs: object) -> Completed:
        calls.append(command)
        if command[:3] == ["ps", "-p", "111"]:
            return Completed(0, "/opt/homebrew/bin/ollama serve\n")
        if command[:3] == ["ps", "-p", "222"]:
            return Completed(1, "")
        if command[:3] == ["lsof", "-nP", "-iTCP"]:
            return Completed(
                0,
                "\n".join(
                    [
                        "p111",
                        "collama",
                        "n127.0.0.1:11435",
                        "p333",
                        "cnode",
                        "n127.0.0.1:9377",
                    ]
                ),
            )
        if command[:6] == ["lsof", "-nP", "-a", "-p", "111", "-iTCP"]:
            return Completed(0, "n127.0.0.1:11435\nn0.0.0.0:11434\n")
        raise AssertionError(command)

    monkeypatch.setattr(model_service.subprocess, "run", fake_run)

    assert model_service._process_command_line(111) == "/opt/homebrew/bin/ollama serve"
    assert model_service._process_command_line(222) is None
    assert model_service._ollama_listener_pids_from_lsof() == [111]
    assert model_service._listening_loopback_ports_for_pid(111) == {11435}
    assert calls


def test_model_service_low_level_process_helpers_cover_defensive_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Completed:
        def __init__(self, returncode: int, stdout: str) -> None:
            self.returncode = returncode
            self.stdout = stdout

    monkeypatch.setattr(
        model_service.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("ps denied")),
    )
    assert model_service._process_command_line(1234) is None
    assert model_service._external_ollama_serve_pids("/opt/homebrew/bin/ollama") == []
    assert model_service._ollama_listener_pids_from_lsof() == []
    assert model_service._listening_loopback_ports_for_pid(1234) == set()

    def fake_run(command: list[str], **_kwargs: object) -> Completed:
        if command[:4] == ["ps", "-ax", "-o", "pid=,command="]:
            return Completed(
                0,
                "\n".join(
                    [
                        "101 /opt/homebrew/bin/ollama serve",
                        "ignored-line-without-pid",
                        "202 /usr/bin/other process",
                        "303 /tmp/custom-ollama serve --debug",
                    ]
                ),
            )
        if command[:3] == ["lsof", "-nP", "-iTCP"]:
            return Completed(0, "p404\ncollama\nn[::1]:11435\n")
        return Completed(1, "")

    monkeypatch.setattr(model_service.subprocess, "run", fake_run)
    assert model_service._external_ollama_serve_pids("/tmp/custom-ollama") == [
        101,
        303,
        404,
    ]
    assert model_service._ollama_listener_pids_from_lsof() == [404]

    monkeypatch.setattr(model_service.sys, "platform", "win32")
    assert model_service._external_ollama_serve_pids("/tmp/custom-ollama") == []
    assert model_service._ollama_listener_pids_from_lsof() == []


def test_model_service_tail_and_port_owner_edge_cases(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "ollama.err.log"
    log_path.write_text("unreadable", encoding="utf-8")

    def fake_read_text(
        path: Path,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> str:
        del encoding, errors, newline
        if path == log_path:
            raise OSError("permission denied")
        return ""

    monkeypatch.setattr(Path, "read_text", fake_read_text)
    assert model_service._tail_text(str(log_path)) == []

    class Completed:
        def __init__(self, returncode: int, stdout: str) -> None:
            self.returncode = returncode
            self.stdout = stdout

    monkeypatch.setattr(
        model_service.subprocess,
        "run",
        lambda *_args, **_kwargs: Completed(0, "p111\n"),
    )
    assert model_service._listen_port_owner_pid("localhost", 11435) == 111

    monkeypatch.setattr(
        model_service.subprocess,
        "run",
        lambda *_args, **_kwargs: Completed(0, "p111\np222\n"),
    )
    assert model_service._listen_port_owner_pid("127.0.0.1", 11435) is None

    monkeypatch.setattr(
        model_service.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("lsof denied")),
    )
    assert model_service._listen_port_owner_pid("127.0.0.1", 11435) is None


def test_model_service_port_availability_uses_real_loopback_socket() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        busy_port = int(sock.getsockname()[1])
        assert model_service._is_port_available("127.0.0.1", busy_port) is False

    assert model_service._is_port_available("127.0.0.1", busy_port) is True


def test_model_service_process_match_and_wait_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = ModelServiceState(
        pid=777,
        host="127.0.0.1",
        port=11435,
        base_url="http://127.0.0.1:11435",
        started_at="2026-01-01T00:00:00+00:00",
        stdout_log_path="/tmp/out.log",
        stderr_log_path="/tmp/err.log",
        command=["/bin/ollama", "serve"],
    )

    monkeypatch.setattr(model_service, "_listen_port_owner_pid", lambda *_args: 777)
    assert model_service._process_matches_state(state) is True

    monkeypatch.setattr(model_service, "_listen_port_owner_pid", lambda *_args: 778)
    assert model_service._process_matches_state(state) is False

    monkeypatch.setattr(model_service, "_listen_port_owner_pid", lambda *_args: None)
    monkeypatch.setattr(model_service, "_process_command_line", lambda _pid: None)
    assert model_service._process_matches_state(state) is False

    monkeypatch.setattr(
        model_service,
        "_process_command_line",
        lambda _pid: "/usr/local/bin/ollama list",
    )
    assert model_service._process_matches_state(state) is False

    monkeypatch.setattr(
        model_service,
        "_process_command_line",
        lambda _pid: "/usr/local/bin/ollama serve",
    )
    assert model_service._process_matches_state(state) is True

    alive_sequence = iter([True, False])
    monkeypatch.setattr(
        model_service,
        "is_process_alive",
        lambda _pid: next(alive_sequence),
    )
    monkeypatch.setattr(model_service.time, "sleep", lambda _seconds: None)
    assert model_service._wait_for_pid_exit(777, timeout_seconds=1.0) is True

    state_alive_sequence = iter([True, False])
    monkeypatch.setattr(
        model_service,
        "_state_process_alive",
        lambda _state: next(state_alive_sequence),
    )
    assert model_service._wait_for_state_process_exit(state, timeout_seconds=1.0) is True


def test_model_service_messages_and_orphan_detection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active_state = ModelServiceState(
        pid=10,
        host="127.0.0.1",
        port=11435,
        base_url="http://127.0.0.1:11435",
        started_at="2026-01-01T00:00:00+00:00",
        stdout_log_path="/tmp/out.log",
        stderr_log_path="/tmp/err.log",
        command=["ollama", "serve"],
    )
    monkeypatch.setattr(
        model_service,
        "_external_ollama_serve_pids",
        lambda _command_path: [10, 20, 30],
    )
    monkeypatch.setattr(
        model_service,
        "_listening_loopback_ports_for_pid",
        lambda pid: {11435} if pid in {10, 20} else {11434},
    )
    assert model_service._orphan_app_managed_ollama_pids("ollama", active_state) == [
        20
    ]

    assert (
        model_service._model_service_message(
            reachable=False,
            model_available=False,
            generation_checked=False,
            generation_available=None,
            generation_message=None,
            fallback_message="offline",
        )
        == "offline"
    )
    assert "not listed" in model_service._model_service_message(
        reachable=True,
        model_available=False,
        generation_checked=True,
        generation_available=False,
        generation_message=None,
        fallback_message="fallback",
    )
    assert "generation probe failed: refused" in model_service._model_service_message(
        reachable=True,
        model_available=True,
        generation_checked=True,
        generation_available=False,
        generation_message="refused",
        fallback_message="fallback",
    )
    assert "can generate" in model_service._model_service_message(
        reachable=True,
        model_available=True,
        generation_checked=True,
        generation_available=True,
        generation_message="ok",
        fallback_message="fallback",
    )

    assert model_service._generation_probe_status(
        include_generation=False,
        reachable=True,
        model_available=True,
        api_root="http://127.0.0.1:11434",
        model_name="qwen3:8b",
    ) == (None, None)
    assert model_service._generation_probe_status(
        include_generation=True,
        reachable=False,
        model_available=True,
        api_root="http://127.0.0.1:11434",
        model_name="qwen3:8b",
    ) == (False, "Generation probe skipped because Ollama is unreachable.")
    assert model_service._generation_probe_status(
        include_generation=True,
        reachable=True,
        model_available=False,
        api_root="http://127.0.0.1:11434",
        model_name="qwen3:8b",
    ) == (
        False,
        "Generation probe skipped because the configured model is not listed.",
    )

    assert "Generation probe also failed" in model_service._base_url_mismatch_message(
        include_generation=True,
        generation_available=False,
        generation_message="refused",
    )
    assert "Stale app-managed" in model_service._app_owned_model_status_message(
        reachable=True,
        model_available=True,
        include_generation=False,
        generation_available=None,
        generation_message=None,
        fetch_message="ready",
        runtime_base_url_matches_app_service=True,
        orphan_app_managed_pids=[20],
    )
    assert "different base URL" in model_service._app_owned_model_status_message(
        reachable=True,
        model_available=True,
        include_generation=False,
        generation_available=None,
        generation_message=None,
        fetch_message="ready",
        runtime_base_url_matches_app_service=False,
        orphan_app_managed_pids=[],
    )
    assert "Multiple host/default Ollama" in model_service._host_model_status_message(
        status_message="ready",
        reachable=True,
        ollama_serve_pids=[1, 2],
    )
    assert "will not kill it" in model_service._host_model_status_message(
        status_message="ready",
        reachable=True,
        ollama_serve_pids=[1],
    )
    assert model_service._model_status_notes(
        tool_payload={"notes": ["local_tool_id=ollama"]},
        ollama_serve_pids=[1, 2],
        orphan_app_managed_pids=[20],
    ) == [
        "local_tool_id=ollama",
        "ollama_process_count=2",
        "external_ollama_duplicate_processes_detected",
        "orphan_app_managed_ollama_process_count=1",
    ]


def test_model_service_http_probes_and_port_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        def __init__(
            self,
            payload: object,
            *,
            status_code: int = 200,
            raise_error: Exception | None = None,
            json_error: Exception | None = None,
        ) -> None:
            self._payload = payload
            self.status_code = status_code
            self._raise_error = raise_error
            self._json_error = json_error

        def json(self) -> object:
            if self._json_error is not None:
                raise self._json_error
            return self._payload

        def raise_for_status(self) -> None:
            if self._raise_error is not None:
                raise self._raise_error

    def as_httpx_response(response: FakeResponse) -> httpx.Response:
        return cast(httpx.Response, response)

    monkeypatch.setattr(
        model_service.httpx,
        "get",
        lambda *_args, **_kwargs: FakeResponse(
            {"models": [{"name": "z-model"}, {"name": "a-model"}, "ignored"]}
        ),
    )
    assert model_service._fetch_ollama_tags("http://127.0.0.1:11434") == (
        True,
        ["a-model", "z-model"],
        "Ollama is reachable.",
    )

    monkeypatch.setattr(
        model_service.httpx,
        "get",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("down")),
    )
    reachable, models, message = model_service._fetch_ollama_tags(
        "http://127.0.0.1:11434"
    )
    assert reachable is False
    assert models == []
    assert "Unable to reach Ollama" in message

    assert (
        model_service._ollama_error_from_response(
            as_httpx_response(
                FakeResponse({"error": {"message": "load failed"}}, status_code=500)
            )
        )
        == "load failed"
    )
    assert (
        model_service._ollama_error_from_response(
            as_httpx_response(
                FakeResponse({"error": "plain failure"}, status_code=500)
            )
        )
        == "plain failure"
    )
    assert (
        model_service._ollama_error_from_response(
            as_httpx_response(FakeResponse([], status_code=503))
        )
        == "HTTP 503"
    )
    assert (
        model_service._ollama_error_from_response(
            as_httpx_response(
                FakeResponse(
                    {"ok": True},
                    status_code=418,
                    json_error=ValueError("bad json"),
                )
            )
        )
        == "HTTP 418"
    )

    post_payloads: list[dict[str, object]] = []

    def fake_post(_url: str, *, json: dict[str, object], **_kwargs: object) -> FakeResponse:
        post_payloads.append(json)
        return FakeResponse({"response": "OK"})

    monkeypatch.setattr(model_service.httpx, "post", fake_post)
    assert model_service._probe_ollama_generation(
        "http://127.0.0.1:11434", "qwen3:8b"
    ) == (True, "Generation probe succeeded.")
    assert post_payloads[0]["model"] == "qwen3:8b"

    monkeypatch.setattr(
        model_service.httpx,
        "post",
        lambda *_args, **_kwargs: FakeResponse({"response": None}),
    )
    assert model_service._probe_ollama_generation(
        "http://127.0.0.1:11434", "qwen3:8b"
    ) == (False, "Ollama generation response did not include text.")

    monkeypatch.setattr(
        model_service.httpx,
        "post",
        lambda *_args, **_kwargs: FakeResponse({"error": "refused"}),
    )
    assert model_service._probe_ollama_generation(
        "http://127.0.0.1:11434", "qwen3:8b"
    ) == (False, "refused")

    monkeypatch.setattr(
        model_service.httpx,
        "post",
        lambda *_args, **_kwargs: FakeResponse({"error": "load failed"}, status_code=500),
    )
    assert model_service._probe_ollama_generation(
        "http://127.0.0.1:11434", "qwen3:8b"
    ) == (False, "load failed")

    monkeypatch.setattr(
        model_service.httpx,
        "post",
        lambda *_args, **_kwargs: FakeResponse(["not", "a", "dict"]),
    )
    assert model_service._probe_ollama_generation(
        "http://127.0.0.1:11434", "qwen3:8b"
    ) == (False, "Ollama generation response was not a JSON object.")

    monkeypatch.setattr(
        model_service.httpx,
        "post",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("token=secret")),
    )
    ok, probe_message = model_service._probe_ollama_generation(
        "http://127.0.0.1:11434", "qwen3:8b"
    )
    assert ok is False
    assert "token=secret" not in probe_message

    monkeypatch.setattr(
        model_service,
        "_is_port_available",
        lambda _host, port: port == 11436,
    )
    assert model_service.choose_app_managed_port("127.0.0.1", 11435) == 11436
    with pytest.raises(ValueError, match="loopback"):
        model_service.choose_app_managed_port("0.0.0.0", 11435)
    monkeypatch.setattr(model_service, "_is_port_available", lambda *_args: False)
    with pytest.raises(RuntimeError, match="no_free"):
        model_service.choose_app_managed_port("127.0.0.1", 11435)


def test_model_service_lifecycle_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(
        tmp_path,
        model_service_host="127.0.0.1",
        model_service_port=11435,
        model_service_models_dir=tmp_path / "models",
    )
    captured: dict[str, object] = {}

    class FakeProcess:
        pid = 7788

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

    monkeypatch.setattr(model_service.shutil, "which", lambda _name: "/bin/ollama")
    monkeypatch.setattr(model_service, "_is_port_available", lambda *_args: True)
    monkeypatch.setattr(model_service, "_cleanup_orphan_app_managed_ollama_pids", lambda *_args: [])
    monkeypatch.setattr(model_service.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(
        model_service,
        "_state_process_alive",
        lambda state: state is not None and state.pid == FakeProcess.pid,
    )
    monkeypatch.setattr(
        model_service,
        "_fetch_ollama_tags",
        lambda _api_root: (True, ["qwen3:8b"], "ready"),
    )
    monkeypatch.setattr(
        model_service,
        "build_model_service_status",
        lambda _settings: _model_status(app_owned=True),
    )

    status = model_service.start_model_service(settings)

    assert status.app_owned is True
    assert captured["command"] == ["/bin/ollama", "serve"]
    env = captured["env"]
    assert isinstance(env, dict)
    assert env["OLLAMA_HOST"] == "http://127.0.0.1:11435"
    assert env["OLLAMA_MODELS"] == str(tmp_path / "models")
    assert model_service.model_service_state_path(settings).exists()

    with pytest.raises(RuntimeError, match="loopback"):
        model_service.start_model_service(settings, host="0.0.0.0")
    monkeypatch.setattr(model_service.shutil, "which", lambda _name: None)
    with pytest.raises(RuntimeError, match="not installed"):
        model_service.start_model_service(settings)


def test_model_service_stop_and_pull_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    state = ModelServiceState(
        pid=7788,
        host="127.0.0.1",
        port=11435,
        base_url="http://127.0.0.1:11435",
        started_at="2026-01-01T00:00:00+00:00",
        stdout_log_path=str(tmp_path / "out.log"),
        stderr_log_path=str(tmp_path / "err.log"),
        command=["/bin/ollama", "serve"],
    )
    monkeypatch.setattr(model_service.shutil, "which", lambda _name: "/bin/ollama")
    monkeypatch.setattr(
        model_service,
        "build_model_service_status",
        lambda _settings: _model_status(app_owned=False),
    )
    monkeypatch.setattr(
        model_service,
        "_orphan_app_managed_ollama_pids",
        lambda _command_path, _app_state: [],
    )
    monkeypatch.setattr(model_service, "_read_state", lambda _settings: None)
    assert model_service.stop_model_service(settings).message == "model ready"

    removed: list[str] = []
    cleaned: list[object] = []
    monkeypatch.setattr(model_service, "_read_state", lambda _settings: state)
    monkeypatch.setattr(model_service, "_state_process_alive", lambda _state: False)
    monkeypatch.setattr(model_service, "_remove_state", lambda _settings: removed.append("state"))
    monkeypatch.setattr(
        model_service,
        "_cleanup_orphan_app_managed_ollama_pids",
        lambda command_path, active_state: cleaned.append((command_path, active_state)) or [],
    )
    model_service.stop_model_service(settings)
    assert removed == ["state"]
    assert cleaned == [("/bin/ollama", None)]

    stopped: list[int] = []
    monkeypatch.setattr(model_service, "_state_process_alive", lambda _state: True)
    monkeypatch.setattr(model_service, "_stop_pid", lambda pid: stopped.append(pid) or True)
    model_service.stop_model_service(settings)
    assert stopped == [7788]

    class Completed:
        returncode = 0
        stdout = "pulled"
        stderr = "AGENTIC_TRADER_ALPACA_SECRET_KEY=secret-value"

    run_calls: list[dict[str, object]] = []

    def fake_run(command: list[str], **kwargs: object) -> Completed:
        run_calls.append({"command": command, **kwargs})
        return Completed()

    monkeypatch.setattr(model_service.subprocess, "run", fake_run)
    monkeypatch.setattr(model_service, "_state_process_alive", lambda _state: True)
    payload = model_service.pull_model(settings, "qwen3:8b")
    assert payload["exit_code"] == 0
    assert "secret-value" not in str(payload["stderr"])
    assert run_calls[0]["command"] == ["/bin/ollama", "pull", "qwen3:8b"]
    env = run_calls[0]["env"]
    assert isinstance(env, dict)
    assert env["OLLAMA_HOST"] == "http://127.0.0.1:11435"

    monkeypatch.setattr(model_service.shutil, "which", lambda _name: None)
    with pytest.raises(RuntimeError, match="not installed"):
        model_service.pull_model(settings, "qwen3:8b")
