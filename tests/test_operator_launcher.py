from pathlib import Path
from typing import Any

import pytest

from agentic_trader.config import Settings
from agentic_trader.schemas import ServiceStateSnapshot
from agentic_trader.system import operator_launcher
from agentic_trader.system.camofox_service import CamofoxServiceStatus
from agentic_trader.system.model_service import ModelServiceStatus
from agentic_trader.system.setup import SetupStatus, ToolStatus
from agentic_trader.system.webgui_service import WebGUIServiceStatus


def _settings(tmp_path: Path, **overrides: Any) -> Settings:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        market_data_cache_dir=tmp_path / "market_cache",
        **overrides,
    )
    settings.ensure_directories()
    return settings


def _setup_status(tmp_path: Path) -> SetupStatus:
    return SetupStatus(
        platform="Darwin",
        workspace_root=str(tmp_path),
        core_ready=True,
        optional_ready=True,
        tools=[
            ToolStatus(
                tool_id="uv",
                label="uv",
                category="core",
                available=True,
                required_for_core=True,
            )
        ],
        model_service={"service_reachable": True},
        camofox_service={"service_reachable": False},
        webgui_service={"service_reachable": False},
        recommended_commands=["make setup"],
    )


def _model_status() -> ModelServiceStatus:
    return ModelServiceStatus(
        command_available=True,
        configured_base_url="http://127.0.0.1:11434/v1",
        configured_model="qwen3:8b",
        service_reachable=True,
        model_available=True,
        state_path="/tmp/model-service.json",
        message="ready",
    )


def _webgui_status() -> WebGUIServiceStatus:
    return WebGUIServiceStatus(
        command_available=True,
        package_available=True,
        service_reachable=False,
        state_path="/tmp/webgui-service.json",
        message="not running",
    )


def _camofox_status() -> CamofoxServiceStatus:
    return CamofoxServiceStatus(
        command_available=True,
        package_available=True,
        dependency_available=True,
        access_key_configured=True,
        service_reachable=False,
        health_ok=False,
        base_url="http://127.0.0.1:9377",
        state_path="/tmp/camofox-service.json",
        tool_dir="/tmp/tools/camofox-browser",
        message="not running",
    )


def test_build_operator_launcher_status_reports_existing_runtime(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path)
    state = ServiceStateSnapshot(
        service_name="agentic-trader",
        state="running",
        updated_at="2026-01-01T00:00:00+00:00",
        pid=12345,
        runtime_mode="operation",
        symbols=["AAPL"],
        interval="1d",
        lookback="180d",
    )
    monkeypatch.setattr(operator_launcher, "read_service_state", lambda _: state)
    monkeypatch.setattr(operator_launcher, "is_process_alive", lambda pid: pid == 12345)
    monkeypatch.setattr(operator_launcher, "build_setup_status", lambda _: _setup_status(tmp_path))
    monkeypatch.setattr(operator_launcher, "build_model_service_status", lambda _: _model_status())
    monkeypatch.setattr(operator_launcher, "build_camofox_service_status", lambda _: _camofox_status())
    monkeypatch.setattr(operator_launcher, "build_webgui_service_status", lambda _: _webgui_status())

    status = operator_launcher.build_operator_launcher_status(settings)

    assert status.runtime_active is True
    assert status.runtime_symbols == ["AAPL"]
    assert status.default_runtime_plan["symbols"] == ["AAPL", "MSFT"]


def test_start_default_background_runtime_keeps_strict_gate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path)
    captured: dict[str, object] = {}

    monkeypatch.setattr(operator_launcher, "ensure_llm_ready", lambda _: object())

    def fake_start_background_service(**kwargs: object) -> int:
        captured.update(kwargs)
        return 54321

    monkeypatch.setattr(
        operator_launcher,
        "start_background_service",
        fake_start_background_service,
    )

    pid = operator_launcher.start_default_background_runtime(settings)

    assert pid == 54321
    assert captured["symbols"] == ["AAPL", "MSFT"]
    assert captured["continuous"] is True
    assert captured["poll_seconds"] == settings.default_poll_seconds
