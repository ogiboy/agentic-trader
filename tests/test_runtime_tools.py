from pathlib import Path
from typing import Any

from agentic_trader.config import Settings
from agentic_trader.system import runtime_tools
from agentic_trader.system.camofox_service import CamofoxServiceStatus
from agentic_trader.system.model_service import ModelServiceStatus


def _settings(tmp_path: Path, **overrides: Any) -> Settings:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        market_data_cache_dir=tmp_path / "market_cache",
        **overrides,
    )
    settings.ensure_directories()
    return settings


def _model_status(*, reachable: bool, model_available: bool, app_owned: bool = False) -> ModelServiceStatus:
    return ModelServiceStatus(
        command_available=True,
        configured_base_url="http://127.0.0.1:11434/v1",
        configured_model="qwen3:8b",
        service_reachable=reachable,
        model_available=model_available,
        app_owned=app_owned,
        base_url="http://127.0.0.1:11435" if app_owned else "http://127.0.0.1:11434",
        state_path="/tmp/model-service.json",
        message="ready" if reachable and model_available else "missing",
    )


def _camofox_status(*, reachable: bool, app_owned: bool = False) -> CamofoxServiceStatus:
    return CamofoxServiceStatus(
        command_available=True,
        package_available=True,
        dependency_available=True,
        access_key_configured=True,
        service_reachable=reachable,
        health_ok=reachable,
        app_owned=app_owned,
        base_url="http://127.0.0.1:9380" if app_owned else "http://127.0.0.1:9377",
        state_path="/tmp/camofox-service.json",
        tool_dir="/tmp/tools/camofox-browser",
        message="ready" if reachable else "missing",
    )


def test_ensure_model_service_starts_and_repoints_base_url(
    monkeypatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path)
    monkeypatch.setattr(
        runtime_tools,
        "build_model_service_status",
        lambda _settings: _model_status(reachable=False, model_available=False),
    )
    monkeypatch.setattr(
        runtime_tools,
        "start_model_service",
        lambda _settings: _model_status(reachable=True, model_available=True, app_owned=True),
    )

    status = runtime_tools.ensure_model_service_if_configured(settings)

    assert status.app_owned is True
    assert settings.base_url == "http://127.0.0.1:11435/v1"


def test_ensure_camofox_service_starts_when_research_provider_enabled(
    monkeypatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path, research_camofox_enabled=True)
    monkeypatch.setattr(
        runtime_tools,
        "build_camofox_service_status",
        lambda _settings: _camofox_status(reachable=False),
    )
    monkeypatch.setattr(
        runtime_tools,
        "start_camofox_service",
        lambda _settings: _camofox_status(reachable=True, app_owned=True),
    )

    status = runtime_tools.ensure_camofox_service_if_configured(settings)

    assert status is not None
    assert status.app_owned is True
    assert settings.research_camofox_base_url == "http://127.0.0.1:9380"


def test_ensure_camofox_service_skips_when_provider_disabled(tmp_path: Path) -> None:
    settings = _settings(tmp_path, research_camofox_enabled=False)

    assert runtime_tools.ensure_camofox_service_if_configured(settings) is None
