import json
from pathlib import Path
from typing import Any, Callable, cast

import pytest

from agentic_trader.config import Settings
from agentic_trader.researchd import crewai_setup
from agentic_trader.system import setup
from agentic_trader.system.tool_ownership import write_tool_ownership

JsonObject = dict[str, object]


class _Status:
    def __init__(self, payload: JsonObject) -> None:
        self._payload = payload

    def model_dump(self, mode: str = "json") -> JsonObject:
        return self._payload


def _which_from(tool_paths: dict[str, str]) -> Callable[[str], str | None]:
    def fake_which(command: str) -> str | None:
        return tool_paths.get(command)

    return fake_which


def _bin_which(command: str) -> str | None:
    return f"/bin/{command}"


def _version_for(command: str, args: list[str] | None = None) -> str:
    return f"{command}-version"


def _crewai_status(payload: JsonObject) -> Callable[[Settings], JsonObject]:
    def fake_crewai_status(_settings: Settings) -> JsonObject:
        return payload

    return fake_crewai_status


def _service_status(payload: JsonObject) -> Callable[[Settings], _Status]:
    def fake_service_status(_settings: Settings) -> _Status:
        return _Status(payload)

    return fake_service_status


def _settings(tmp_path: Path, **overrides: Any) -> Settings:
    """
    Construct a Settings object rooted at the provided temporary path and create its required directories.

    Parameters:
        tmp_path (Path): Base directory for runtime files and storage (used for runtime_dir, database_path, and market_data_cache_dir).
        **overrides: Additional Settings attributes to override the defaults (for example, alternate paths or credentials).

    Returns:
        Settings: A Settings configured with runtime_dir set to `tmp_path`, database_path set to `tmp_path / "agentic_trader.duckdb"`, and market_data_cache_dir set to `tmp_path / "market_cache"`.
    """
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        market_data_cache_dir=tmp_path / "market_cache",
        **overrides,
    )
    settings.ensure_directories()
    return settings


def test_build_setup_status_classifies_core_and_optional_tools(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path)
    write_tool_ownership(
        settings, {"ollama": "host-owned", "firecrawl": "api-key-only"}, source="test"
    )
    tool_paths = {
        "uv": "/opt/homebrew/bin/uv",
        "pnpm": "/opt/homebrew/bin/pnpm",
        "node": "/opt/homebrew/bin/node",
        "ollama": "/opt/homebrew/bin/ollama",
    }

    monkeypatch.setattr(setup.shutil, "which", _which_from(tool_paths))
    monkeypatch.setattr(setup, "_command_version", _version_for)
    monkeypatch.setattr(
        setup,
        "crewai_setup_status",
        _crewai_status(
            {
                "available": False,
                "environment_exists": False,
                "flow_dir": str(tmp_path / "sidecars" / "research_flow"),
                "version": None,
                "notes": ["optional"],
            }
        ),
    )
    monkeypatch.setattr(
        setup,
        "build_model_service_status",
        _service_status({"provider": "ollama", "service_reachable": False}),
    )
    monkeypatch.setattr(
        setup,
        "build_camofox_service_status",
        _service_status({"service_reachable": False, "message": "not running"}),
    )
    monkeypatch.setattr(
        setup,
        "build_webgui_service_status",
        _service_status({"service_reachable": False, "message": "not running"}),
    )

    status = setup.build_setup_status(settings)

    assert status.core_ready is True
    assert status.optional_ready is False
    tool_ids = {tool.tool_id: tool for tool in status.tools}
    assert tool_ids["uv"].required_for_core is True
    assert tool_ids["firecrawl_cli"].available is False
    assert tool_ids["firecrawl_cli"].ownership_mode == "api-key-only"
    assert tool_ids["ollama_cli"].ownership_mode == "host-owned"
    assert status.tool_ownership is not None
    assert status.tool_ownership.decisions_by_tool["ollama"].mode == "host-owned"
    assert tool_ids["research_flow_sidecar"].status == "needs_setup"
    assert "make bootstrap" in status.recommended_commands


def test_setup_status_requires_reachable_owned_runtime(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path)
    write_tool_ownership(
        settings, {"ollama": "app-owned", "camofox": "app-owned"}, source="test"
    )

    monkeypatch.setattr(setup.shutil, "which", _bin_which)
    monkeypatch.setattr(setup, "_command_version", _version_for)
    monkeypatch.setattr(
        setup,
        "crewai_setup_status",
        _crewai_status(
            {
                "available": True,
                "environment_exists": True,
                "flow_dir": str(tmp_path / "sidecars" / "research_flow"),
                "version": "0.1.0",
                "notes": [],
            }
        ),
    )
    monkeypatch.setattr(
        setup,
        "build_model_service_status",
        _service_status(
            {"provider": "ollama", "service_reachable": True, "model_available": True}
        ),
    )
    monkeypatch.setattr(
        setup,
        "build_camofox_service_status",
        _service_status({"service_reachable": False, "message": "not running"}),
    )
    monkeypatch.setattr(
        setup,
        "build_webgui_service_status",
        _service_status({"service_reachable": True, "message": "ready"}),
    )

    status = setup.build_setup_status(settings)

    assert status.optional_ready is False
    assert status.model_service["service_reachable"] is True
    assert status.camofox_service["service_reachable"] is False


def test_crewai_setup_status_summarizes_failed_sidecar_version(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path)
    flow_dir = tmp_path / "sidecars" / "research_flow"
    flow_dir.mkdir(parents=True)
    (flow_dir / ".venv").mkdir()
    (flow_dir / "pyproject.toml").write_text(
        "[project]\nname = 'research-flow'\n",
        encoding="utf-8",
    )

    def fake_flow_dir(_settings: Settings) -> Path:
        return flow_dir

    monkeypatch.setattr(
        crewai_setup,
        "default_crewai_flow_dir",
        fake_flow_dir,
    )

    def fake_which(command: str) -> str | None:
        return "/bin/uv" if command == "uv" else None

    class Completed:
        returncode = 1
        stdout = ""
        stderr = "Traceback (most recent call last):\nPermissionError: denied\n"

    def fake_run(*_args: object, **_kwargs: object) -> Completed:
        return Completed()

    monkeypatch.setattr(crewai_setup.shutil, "which", fake_which)
    monkeypatch.setattr(crewai_setup.subprocess, "run", fake_run)

    payload = crewai_setup.crewai_setup_status(settings)

    assert payload["version"] is None
    assert payload["version_status"] == "failed"
    assert "Traceback" not in json.dumps(payload)
    notes = payload.get("notes")
    assert isinstance(notes, list)
    note_values = cast(list[object], notes)
    assert "crewai_sidecar_version_check_failed" in " ".join(
        str(note) for note in note_values
    )


def test_camofox_tool_reports_package_and_health(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CAMOFOX_ACCESS_KEY", "local-key")
    camofox_root = tmp_path / "tools" / "camofox-browser"
    camofox_root.mkdir(parents=True)
    (camofox_root / "server.js").write_text("console.log('ok')", encoding="utf-8")
    (camofox_root / "package.json").write_text(
        json.dumps({"name": "camofox-browser", "version": "1.2.3"}),
        encoding="utf-8",
    )
    settings = _settings(tmp_path, research_camofox_tool_dir=camofox_root)

    class Response:
        status_code = 200

    def fake_get(url: str, **kwargs: object) -> Response:
        return Response()

    monkeypatch.setattr(setup.httpx, "get", fake_get)

    tool = setup.build_camofox_tool_status(settings)

    assert tool.available is True
    assert tool.status == "healthy"
    assert tool.version == "1.2.3"
    assert "health_endpoint_reachable" in tool.notes


def test_camofox_tool_marks_reachable_helper_without_access_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("CAMOFOX_ACCESS_KEY", raising=False)
    monkeypatch.delenv("CAMOFOX_API_KEY", raising=False)
    camofox_root = tmp_path / "tools" / "camofox-browser"
    camofox_root.mkdir(parents=True)
    (camofox_root / "server.js").write_text("console.log('ok')", encoding="utf-8")
    (camofox_root / "package.json").write_text(
        json.dumps({"name": "camofox-browser", "version": "1.2.3"}),
        encoding="utf-8",
    )
    settings = _settings(
        tmp_path,
        research_camofox_tool_dir=camofox_root,
        camofox_access_key=None,
        camofox_api_key=None,
    )

    class Response:
        status_code = 200

    def fake_get(url: str, **kwargs: object) -> Response:
        return Response()

    monkeypatch.setattr(setup.httpx, "get", fake_get)

    tool = setup.build_camofox_tool_status(settings)

    assert tool.available is True
    assert tool.status == "healthy_unkeyed"
    assert "health_endpoint_reachable" in tool.notes
    assert "access_key_not_configured_start_with_wrapper" in tool.notes


def test_camofox_tool_skips_non_loopback_health_probe(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    camofox_root = tmp_path / "tools" / "camofox-browser"
    camofox_root.mkdir(parents=True)
    (camofox_root / "server.js").write_text("console.log('ok')", encoding="utf-8")
    (camofox_root / "package.json").write_text(
        json.dumps({"name": "camofox-browser", "version": "1.2.3"}),
        encoding="utf-8",
    )
    settings = _settings(
        tmp_path,
        research_camofox_tool_dir=camofox_root,
        research_camofox_base_url="http://0.0.0.0:9377",
    )
    called = False

    def fake_get(*_args: object, **_kwargs: object) -> object:
        nonlocal called
        called = True
        raise AssertionError("non-loopback Camofox setup probe should not fetch")

    monkeypatch.setattr(setup.httpx, "get", fake_get)

    tool = setup.build_camofox_tool_status(settings)

    assert called is False
    assert tool.available is True
    assert tool.status == "unsafe_base_url"
    assert "health_probe_skipped_non_loopback_base_url" in tool.notes


def test_agentic_trader_entrypoint_reports_path_drift(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo_root = tmp_path / "repo"
    expected = repo_root / ".venv" / "bin" / "agentic-trader"
    stale = tmp_path / "global" / "agentic-trader"
    expected.parent.mkdir(parents=True)
    stale.parent.mkdir(parents=True)
    expected.write_text("#!/bin/sh\n", encoding="utf-8")
    stale.write_text("#!/bin/sh\n", encoding="utf-8")

    def fake_repo_root() -> Path:
        return repo_root

    def fake_entrypoint_which(command: str) -> str | None:
        return str(stale) if command == "agentic-trader" else None

    def fake_entrypoint_version(command: str, args: list[str] | None = None) -> str:
        return "help"

    monkeypatch.setattr(setup, "_repo_root", fake_repo_root)
    monkeypatch.setattr(
        setup.shutil,
        "which",
        fake_entrypoint_which,
    )
    monkeypatch.setattr(setup, "_command_version", fake_entrypoint_version)

    tool = setup.build_agentic_trader_entrypoint_status()

    assert tool.available is True
    assert tool.status == "path_drift"
    assert any("expected_repo_entrypoint" in note for note in tool.notes)
