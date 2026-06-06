"""Tests for the refactored agentic_trader/cli.py.

Focuses on the changes introduced in this PR:
- build_dashboard_snapshot_payload now passes sys.modules[__name__] as namespace
- build_evidence_bundle now passes sys.modules[__name__] as namespace
- build_observer_api_payload now passes sys.modules[__name__] as namespace
- resolve_tui_node_commands uses shutil.which
- register_cli_app is called with the module as namespace
- PROJECT_ROOT / ENV_LOCAL_FILE are module-level constants
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import agentic_trader.cli as cli_module
from agentic_trader.cli import (
    ENV_LOCAL_FILE,
    PROJECT_ROOT,
    build_dashboard_snapshot_payload,
    build_evidence_bundle,
    build_observer_api_payload,
    resolve_tui_node_commands,
)


# ---------------------------------------------------------------------------
# PROJECT_ROOT and ENV_LOCAL_FILE constants
# ---------------------------------------------------------------------------


def test_project_root_is_path_instance() -> None:
    assert isinstance(PROJECT_ROOT, Path)


def test_project_root_is_absolute() -> None:
    assert PROJECT_ROOT.is_absolute()


def test_env_local_file_is_path_instance() -> None:
    assert isinstance(ENV_LOCAL_FILE, Path)


def test_env_local_file_is_under_project_root() -> None:
    assert ENV_LOCAL_FILE.parent == PROJECT_ROOT


def test_env_local_file_named_env_local() -> None:
    assert ENV_LOCAL_FILE.name == ".env.local"


# ---------------------------------------------------------------------------
# resolve_tui_node_commands
# ---------------------------------------------------------------------------


def test_resolve_tui_node_commands_delegates_to_impl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = MagicMock()
    mock_impl = MagicMock(return_value=result)
    monkeypatch.setattr(cli_module, "_resolve_tui_node_commands", mock_impl)

    tui_dir = Path("/fake/tui")
    outcome = resolve_tui_node_commands(tui_dir)

    mock_impl.assert_called_once()
    args, kwargs = mock_impl.call_args
    assert args[0] == tui_dir
    assert callable(kwargs.get("which"))
    assert outcome is result


def test_resolve_tui_node_commands_uses_shutil_which(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The impl should be called with shutil.which as the `which` argument."""
    import shutil

    calls: list[dict] = []

    def capture_impl(tui_dir: Path, *, which: object) -> None:
        calls.append({"tui_dir": tui_dir, "which": which})
        return None

    monkeypatch.setattr(cli_module, "_resolve_tui_node_commands", capture_impl)

    tui_dir = Path("/some/path")
    resolve_tui_node_commands(tui_dir)

    assert len(calls) == 1
    assert calls[0]["which"] is shutil.which
    assert calls[0]["tui_dir"] == tui_dir


def test_resolve_tui_node_commands_returns_none_when_impl_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cli_module, "_resolve_tui_node_commands", MagicMock(return_value=None)
    )
    result = resolve_tui_node_commands(Path("/no/tui"))
    assert result is None


def test_resolve_tui_node_commands_passes_tui_dir_to_impl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_impl = MagicMock(return_value=None)
    monkeypatch.setattr(cli_module, "_resolve_tui_node_commands", mock_impl)

    tui_dir = Path("/custom/tui/dir")
    resolve_tui_node_commands(tui_dir)

    args, _ = mock_impl.call_args
    assert args[0] == tui_dir


# ---------------------------------------------------------------------------
# build_dashboard_snapshot_payload
# ---------------------------------------------------------------------------


def test_build_dashboard_snapshot_payload_passes_module_as_namespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[object] = []
    payload = {"snapshot": True}

    def capture(namespace: object, settings: object, **kwargs: object) -> dict:
        captured.append(namespace)
        return payload

    monkeypatch.setattr(cli_module, "_build_dashboard_snapshot_payload", capture)
    settings = MagicMock()

    result = build_dashboard_snapshot_payload(settings)

    assert len(captured) == 1
    assert captured[0] is sys.modules["agentic_trader.cli"]
    assert result is payload


def test_build_dashboard_snapshot_payload_forwards_log_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []

    def capture(namespace: object, settings: object, **kwargs: object) -> dict:
        calls.append(dict(kwargs))
        return {}

    monkeypatch.setattr(cli_module, "_build_dashboard_snapshot_payload", capture)
    build_dashboard_snapshot_payload(MagicMock(), log_limit=42)

    assert calls[0]["log_limit"] == 42


def test_build_dashboard_snapshot_payload_forwards_check_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []

    def capture(namespace: object, settings: object, **kwargs: object) -> dict:
        calls.append(dict(kwargs))
        return {}

    monkeypatch.setattr(cli_module, "_build_dashboard_snapshot_payload", capture)
    build_dashboard_snapshot_payload(MagicMock(), check_provider=True)

    assert calls[0]["check_provider"] is True


def test_build_dashboard_snapshot_payload_default_check_provider_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []

    def capture(namespace: object, settings: object, **kwargs: object) -> dict:
        calls.append(dict(kwargs))
        return {}

    monkeypatch.setattr(cli_module, "_build_dashboard_snapshot_payload", capture)
    build_dashboard_snapshot_payload(MagicMock())

    assert calls[0]["check_provider"] is False


# ---------------------------------------------------------------------------
# build_evidence_bundle
# ---------------------------------------------------------------------------


def test_build_evidence_bundle_passes_module_as_namespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[object] = []
    payload = {"bundle": True}

    def capture(namespace: object, settings: object, **kwargs: object) -> dict:
        captured.append(namespace)
        return payload

    monkeypatch.setattr(cli_module, "_build_evidence_bundle", capture)
    result = build_evidence_bundle(MagicMock())

    assert len(captured) == 1
    assert captured[0] is sys.modules["agentic_trader.cli"]
    assert result is payload


def test_build_evidence_bundle_forwards_output_dir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []

    def capture(namespace: object, settings: object, **kwargs: object) -> dict:
        calls.append(dict(kwargs))
        return {}

    monkeypatch.setattr(cli_module, "_build_evidence_bundle", capture)
    output_dir = Path("/tmp/out")
    build_evidence_bundle(MagicMock(), output_dir=output_dir)

    assert calls[0]["output_dir"] is output_dir


def test_build_evidence_bundle_forwards_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []

    def capture(namespace: object, settings: object, **kwargs: object) -> dict:
        calls.append(dict(kwargs))
        return {}

    monkeypatch.setattr(cli_module, "_build_evidence_bundle", capture)
    build_evidence_bundle(MagicMock(), label="my-label")

    assert calls[0]["label"] == "my-label"


def test_build_evidence_bundle_forwards_log_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []

    def capture(namespace: object, settings: object, **kwargs: object) -> dict:
        calls.append(dict(kwargs))
        return {}

    monkeypatch.setattr(cli_module, "_build_evidence_bundle", capture)
    build_evidence_bundle(MagicMock(), log_limit=5)

    assert calls[0]["log_limit"] == 5


def test_build_evidence_bundle_default_include_latest_smoke_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []

    def capture(namespace: object, settings: object, **kwargs: object) -> dict:
        calls.append(dict(kwargs))
        return {}

    monkeypatch.setattr(cli_module, "_build_evidence_bundle", capture)
    build_evidence_bundle(MagicMock())

    assert calls[0]["include_latest_smoke"] is True


def test_build_evidence_bundle_include_latest_smoke_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []

    def capture(namespace: object, settings: object, **kwargs: object) -> dict:
        calls.append(dict(kwargs))
        return {}

    monkeypatch.setattr(cli_module, "_build_evidence_bundle", capture)
    build_evidence_bundle(MagicMock(), include_latest_smoke=False)

    assert calls[0]["include_latest_smoke"] is False


# ---------------------------------------------------------------------------
# build_observer_api_payload
# ---------------------------------------------------------------------------


def test_build_observer_api_payload_passes_module_as_namespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[object] = []
    result_val = (200, {"api": "data"})

    def capture(namespace: object, settings: object, **kwargs: object) -> tuple:
        captured.append(namespace)
        return result_val

    monkeypatch.setattr(cli_module, "_build_observer_api_payload", capture)
    result = build_observer_api_payload(MagicMock(), path="/api/v1/status")

    assert len(captured) == 1
    assert captured[0] is sys.modules["agentic_trader.cli"]
    assert result is result_val


def test_build_observer_api_payload_forwards_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []

    def capture(namespace: object, settings: object, **kwargs: object) -> tuple:
        calls.append(dict(kwargs))
        return (200, {})

    monkeypatch.setattr(cli_module, "_build_observer_api_payload", capture)
    build_observer_api_payload(MagicMock(), path="/api/v1/portfolio")

    assert calls[0]["path"] == "/api/v1/portfolio"


def test_build_observer_api_payload_forwards_log_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []

    def capture(namespace: object, settings: object, **kwargs: object) -> tuple:
        calls.append(dict(kwargs))
        return (200, {})

    monkeypatch.setattr(cli_module, "_build_observer_api_payload", capture)
    build_observer_api_payload(MagicMock(), path="/api/v1/status", log_limit=7)

    assert calls[0]["log_limit"] == 7


def test_build_observer_api_payload_default_log_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []

    def capture(namespace: object, settings: object, **kwargs: object) -> tuple:
        calls.append(dict(kwargs))
        return (200, {})

    monkeypatch.setattr(cli_module, "_build_observer_api_payload", capture)
    build_observer_api_payload(MagicMock(), path="/api/v1/status")

    assert calls[0]["log_limit"] == 14


# ---------------------------------------------------------------------------
# Module-level registration sanity
# ---------------------------------------------------------------------------


def test_cli_module_has_app_attribute() -> None:
    """The module should expose a 'app' Typer instance after registration."""
    import typer

    assert hasattr(cli_module, "app")
    assert isinstance(cli_module.app, typer.Typer)


def test_cli_module_exports_main() -> None:
    assert hasattr(cli_module, "main")
    assert callable(cli_module.main)


def test_all_list_includes_expected_public_names() -> None:
    """Verify that the __all__ export list contains key symbols added in this PR."""
    for name in [
        "build_runtime_status_view",
        "render_execution_panels",
        "parse_ui_locale",
        "ui_payload",
        "v1_readiness_payload",
    ]:
        assert name in cli_module.__all__, f"{name!r} missing from __all__"