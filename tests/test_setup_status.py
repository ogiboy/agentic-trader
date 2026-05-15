import json
from pathlib import Path
from typing import Any

import pytest

from agentic_trader.config import Settings
from agentic_trader.system import setup


def _settings(tmp_path: Path, **overrides: Any) -> Settings:
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
    tool_paths = {
        "uv": "/opt/homebrew/bin/uv",
        "pnpm": "/opt/homebrew/bin/pnpm",
        "node": "/opt/homebrew/bin/node",
        "ollama": "/opt/homebrew/bin/ollama",
    }

    monkeypatch.setattr(setup.shutil, "which", lambda command: tool_paths.get(command))
    monkeypatch.setattr(setup, "_command_version", lambda command, args=None: f"{command}-version")
    monkeypatch.setattr(
        setup,
        "crewai_setup_status",
        lambda _: {
            "environment_exists": False,
            "flow_dir": str(tmp_path / "sidecars" / "research_flow"),
            "version": None,
            "notes": ["optional"],
        },
    )
    monkeypatch.setattr(
        setup,
        "build_model_service_status",
        lambda _: type(
            "Status",
            (),
            {
                "model_dump": lambda self, mode="json": {
                    "provider": "ollama",
                    "service_reachable": False,
                }
            },
        )(),
    )
    monkeypatch.setattr(
        setup,
        "build_camofox_service_status",
        lambda _: type(
            "Status",
            (),
            {
                "model_dump": lambda self, mode="json": {
                    "service_reachable": False,
                    "message": "not running",
                }
            },
        )(),
    )
    monkeypatch.setattr(
        setup,
        "build_webgui_service_status",
        lambda _: type(
            "Status",
            (),
            {
                "model_dump": lambda self, mode="json": {
                    "service_reachable": False,
                    "message": "not running",
                }
            },
        )(),
    )

    status = setup.build_setup_status(settings)

    assert status.core_ready is True
    assert status.optional_ready is True
    tool_ids = {tool.tool_id: tool for tool in status.tools}
    assert tool_ids["uv"].required_for_core is True
    assert tool_ids["firecrawl_cli"].available is False
    assert tool_ids["research_flow_sidecar"].status == "needs_setup"
    assert "make bootstrap" in status.recommended_commands


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

    monkeypatch.setattr(setup.httpx, "get", lambda *_args, **_kwargs: Response())

    tool = setup._camofox_tool(settings)

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

    monkeypatch.setattr(setup.httpx, "get", lambda *_args, **_kwargs: Response())

    tool = setup._camofox_tool(settings)

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

    tool = setup._camofox_tool(settings)

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

    monkeypatch.setattr(setup, "_repo_root", lambda: repo_root)
    monkeypatch.setattr(setup.shutil, "which", lambda command: str(stale) if command == "agentic-trader" else None)
    monkeypatch.setattr(setup, "_command_version", lambda _command, _args=None: "help")

    tool = setup._agentic_trader_entrypoint()

    assert tool.available is True
    assert tool.status == "path_drift"
    assert any("expected_repo_entrypoint" in note for note in tool.notes)
