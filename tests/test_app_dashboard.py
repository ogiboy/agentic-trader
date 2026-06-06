"""Tests for agentic_trader.cli_modules.app_dashboard.

Verifies that every private provider factory returns a callable that delegates
to the correct namespace method, and that the public assembly functions wire
everything together correctly.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agentic_trader.cli_modules.app_dashboard import (
    _calendar_provider,
    _canonical_analysis_provider,
    _finance_ops_provider,
    _journal_provider,
    _market_context_provider,
    _memory_explorer_provider,
    _news_provider,
    _open_read_db_provider,
    _portfolio_provider,
    _preferences_provider,
    _provider_diagnostics_provider,
    _recent_runs_provider,
    _retrieval_inspection_provider,
    _risk_report_provider,
    _run_record_provider,
    _run_replay_provider,
    _runtime_mode_provider,
    _service_supervisor_provider,
    _settings_provider,
    _trade_context_provider,
    _v1_readiness_provider,
    build_dashboard_snapshot_payload,
    build_evidence_bundle,
    build_observer_api_payload,
    dashboard_command_deps,
)
from agentic_trader.cli_modules.dashboard_commands import DashboardCommandDeps


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _ns(**attrs: object) -> SimpleNamespace:
    return SimpleNamespace(**attrs)


# ---------------------------------------------------------------------------
# _settings_provider
# ---------------------------------------------------------------------------


def test_settings_provider_returns_callable() -> None:
    ns = _ns(get_settings=MagicMock())
    provider = _settings_provider(ns)
    assert callable(provider)


def test_settings_provider_delegates_to_namespace() -> None:
    settings = MagicMock()
    ns = _ns(get_settings=MagicMock(return_value=settings))
    provider = _settings_provider(ns)
    result = provider()
    ns.get_settings.assert_called_once_with()
    assert result is settings


# ---------------------------------------------------------------------------
# _open_read_db_provider
# ---------------------------------------------------------------------------


def test_open_read_db_provider_returns_callable() -> None:
    ns = _ns(_open_db=MagicMock())
    provider = _open_read_db_provider(ns)
    assert callable(provider)


def test_open_read_db_provider_opens_with_read_only_true() -> None:
    db = MagicMock()
    ns = _ns(_open_db=MagicMock(return_value=db))
    settings = MagicMock()

    provider = _open_read_db_provider(ns)
    result = provider(settings)

    ns._open_db.assert_called_once_with(settings, read_only=True)
    assert result is db


# ---------------------------------------------------------------------------
# _service_supervisor_provider
# ---------------------------------------------------------------------------


def test_service_supervisor_provider_returns_callable() -> None:
    ns = _ns(_read_text_tail=MagicMock())
    provider = _service_supervisor_provider(ns)
    assert callable(provider)


def test_service_supervisor_provider_passes_read_text_tail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {"state": "ok"}
    mock_impl = MagicMock(return_value=payload)
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard._service_supervisor_payload_impl",
        mock_impl,
    )
    read_text_tail = MagicMock()
    ns = _ns(_read_text_tail=read_text_tail)
    settings = MagicMock()

    provider = _service_supervisor_provider(ns)
    result = provider(settings)

    mock_impl.assert_called_once_with(settings, read_text_tail=read_text_tail)
    assert result is payload


# ---------------------------------------------------------------------------
# _finance_ops_provider
# ---------------------------------------------------------------------------


def test_finance_ops_provider_returns_callable() -> None:
    ns = _ns(_open_db=MagicMock(), get_broker_adapter=MagicMock())
    provider = _finance_ops_provider(ns)
    assert callable(provider)


def test_finance_ops_provider_passes_correct_deps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {"ops": []}
    mock_impl = MagicMock(return_value=payload)
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard._finance_ops_payload_impl",
        mock_impl,
    )
    open_db = MagicMock()
    get_broker_adapter = MagicMock()
    ns = _ns(_open_db=open_db, get_broker_adapter=get_broker_adapter)
    settings = MagicMock()

    provider = _finance_ops_provider(ns)
    result = provider(settings)

    mock_impl.assert_called_once_with(
        settings,
        open_db_provider=open_db,
        broker_adapter_provider=get_broker_adapter,
    )
    assert result is payload


# ---------------------------------------------------------------------------
# _portfolio_provider
# ---------------------------------------------------------------------------


def test_portfolio_provider_returns_callable() -> None:
    ns = _ns(_open_db=MagicMock(), get_broker_adapter=MagicMock())
    provider = _portfolio_provider(ns)
    assert callable(provider)


def test_portfolio_provider_passes_correct_deps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {"portfolio": {}}
    mock_impl = MagicMock(return_value=payload)
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard._finance_portfolio_payload",
        mock_impl,
    )
    open_db = MagicMock()
    get_broker_adapter = MagicMock()
    ns = _ns(_open_db=open_db, get_broker_adapter=get_broker_adapter)
    settings = MagicMock()

    provider = _portfolio_provider(ns)
    result = provider(settings)

    mock_impl.assert_called_once_with(
        settings,
        open_db_provider=open_db,
        broker_adapter_provider=get_broker_adapter,
    )
    assert result is payload


# ---------------------------------------------------------------------------
# _preferences_provider
# ---------------------------------------------------------------------------


def test_preferences_provider_returns_callable() -> None:
    ns = _ns(_open_db=MagicMock())
    provider = _preferences_provider(ns)
    assert callable(provider)


def test_preferences_provider_passes_open_db(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {"risk_profile": "moderate"}
    mock_impl = MagicMock(return_value=payload)
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard._preferences_payload_impl",
        mock_impl,
    )
    open_db = MagicMock()
    ns = _ns(_open_db=open_db)
    settings = MagicMock()

    provider = _preferences_provider(ns)
    result = provider(settings)

    mock_impl.assert_called_once_with(settings, open_db=open_db)
    assert result is payload


# ---------------------------------------------------------------------------
# _recent_runs_provider
# ---------------------------------------------------------------------------


def test_recent_runs_provider_returns_callable() -> None:
    ns = _ns(_open_db=MagicMock())
    provider = _recent_runs_provider(ns)
    assert callable(provider)


def test_recent_runs_provider_passes_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {"runs": []}
    mock_impl = MagicMock(return_value=payload)
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard._recent_runs_payload_impl",
        mock_impl,
    )
    open_db = MagicMock()
    ns = _ns(_open_db=open_db)
    settings = MagicMock()

    provider = _recent_runs_provider(ns)
    result = provider(settings, 7)

    mock_impl.assert_called_once_with(settings, open_db=open_db, limit=7)
    assert result is payload


# ---------------------------------------------------------------------------
# _journal_provider
# ---------------------------------------------------------------------------


def test_journal_provider_returns_callable() -> None:
    ns = _ns(_open_db=MagicMock())
    provider = _journal_provider(ns)
    assert callable(provider)


def test_journal_provider_passes_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {"entries": []}
    mock_impl = MagicMock(return_value=payload)
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard._journal_payload_impl",
        mock_impl,
    )
    open_db = MagicMock()
    ns = _ns(_open_db=open_db)
    settings = MagicMock()

    provider = _journal_provider(ns)
    result = provider(settings, 20)

    mock_impl.assert_called_once_with(settings, open_db=open_db, limit=20)
    assert result is payload


# ---------------------------------------------------------------------------
# _risk_report_provider
# ---------------------------------------------------------------------------


def test_risk_report_provider_returns_callable() -> None:
    ns = _ns(_open_db=MagicMock(), get_broker_adapter=MagicMock())
    provider = _risk_report_provider(ns)
    assert callable(provider)


def test_risk_report_provider_passes_correct_deps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {"risk": {}}
    mock_impl = MagicMock(return_value=payload)
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard._finance_risk_report_payload",
        mock_impl,
    )
    open_db = MagicMock()
    get_broker_adapter = MagicMock()
    ns = _ns(_open_db=open_db, get_broker_adapter=get_broker_adapter)
    settings = MagicMock()

    provider = _risk_report_provider(ns)
    result = provider(settings)

    mock_impl.assert_called_once_with(
        settings,
        open_db_provider=open_db,
        broker_adapter_provider=get_broker_adapter,
    )
    assert result is payload


# ---------------------------------------------------------------------------
# _run_record_provider
# ---------------------------------------------------------------------------


def test_run_record_provider_returns_callable() -> None:
    ns = _ns(_open_db=MagicMock())
    provider = _run_record_provider(ns)
    assert callable(provider)


def test_run_record_provider_passes_open_db(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {"run_id": "abc"}
    mock_impl = MagicMock(return_value=payload)
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard._run_record_payload_impl",
        mock_impl,
    )
    open_db = MagicMock()
    ns = _ns(_open_db=open_db)
    settings = MagicMock()

    provider = _run_record_provider(ns)
    result = provider(settings)

    mock_impl.assert_called_once_with(settings, open_db=open_db)
    assert result is payload


# ---------------------------------------------------------------------------
# _trade_context_provider
# ---------------------------------------------------------------------------


def test_trade_context_provider_returns_callable() -> None:
    ns = _ns(_open_db=MagicMock())
    provider = _trade_context_provider(ns)
    assert callable(provider)


def test_trade_context_provider_passes_open_db(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {"trade_id": "t-1"}
    mock_impl = MagicMock(return_value=payload)
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard._trade_context_payload_impl",
        mock_impl,
    )
    open_db = MagicMock()
    ns = _ns(_open_db=open_db)
    settings = MagicMock()

    provider = _trade_context_provider(ns)
    result = provider(settings)

    mock_impl.assert_called_once_with(settings, open_db=open_db)
    assert result is payload


# ---------------------------------------------------------------------------
# _market_context_provider
# ---------------------------------------------------------------------------


def test_market_context_provider_returns_callable() -> None:
    ns = _ns(_open_db=MagicMock())
    provider = _market_context_provider(ns)
    assert callable(provider)


def test_market_context_provider_passes_open_db(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {"market": "context"}
    mock_impl = MagicMock(return_value=payload)
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard._market_context_payload_impl",
        mock_impl,
    )
    open_db = MagicMock()
    ns = _ns(_open_db=open_db)
    settings = MagicMock()

    provider = _market_context_provider(ns)
    result = provider(settings)

    mock_impl.assert_called_once_with(settings, open_db=open_db)
    assert result is payload


# ---------------------------------------------------------------------------
# _canonical_analysis_provider
# ---------------------------------------------------------------------------


def test_canonical_analysis_provider_returns_callable() -> None:
    ns = _ns(_open_db=MagicMock())
    provider = _canonical_analysis_provider(ns)
    assert callable(provider)


def test_canonical_analysis_provider_passes_open_db(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {"canonical": True}
    mock_impl = MagicMock(return_value=payload)
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard._canonical_analysis_payload_impl",
        mock_impl,
    )
    open_db = MagicMock()
    ns = _ns(_open_db=open_db)
    settings = MagicMock()

    provider = _canonical_analysis_provider(ns)
    result = provider(settings)

    mock_impl.assert_called_once_with(settings, open_db=open_db)
    assert result is payload


# ---------------------------------------------------------------------------
# _run_replay_provider
# ---------------------------------------------------------------------------


def test_run_replay_provider_returns_callable() -> None:
    ns = _ns(_open_db=MagicMock())
    provider = _run_replay_provider(ns)
    assert callable(provider)


def test_run_replay_provider_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"replay": True}
    mock_impl = MagicMock(return_value=payload)
    mock_run_record_impl = MagicMock(return_value={})
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard._run_replay_payload_impl",
        mock_impl,
    )
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard._run_record_payload_impl",
        mock_run_record_impl,
    )
    ns = _ns(_open_db=MagicMock())
    settings = MagicMock()

    provider = _run_replay_provider(ns)
    result = provider(settings)

    mock_impl.assert_called_once()
    assert result is payload


# ---------------------------------------------------------------------------
# _memory_explorer_provider
# ---------------------------------------------------------------------------


def test_memory_explorer_provider_returns_callable() -> None:
    ns = _ns(_open_db=MagicMock())
    provider = _memory_explorer_provider(ns)
    assert callable(provider)


def test_memory_explorer_provider_passes_limit_and_use_latest_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {"memory": []}
    mock_impl = MagicMock(return_value=payload)
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard._memory_explorer_payload_impl",
        mock_impl,
    )
    open_db = MagicMock()
    ns = _ns(_open_db=open_db)
    settings = MagicMock()

    provider = _memory_explorer_provider(ns)
    result = provider(settings, True, 15)

    mock_impl.assert_called_once_with(
        settings,
        open_db=open_db,
        limit=15,
        use_latest_run=True,
    )
    assert result is payload


# ---------------------------------------------------------------------------
# _retrieval_inspection_provider
# ---------------------------------------------------------------------------


def test_retrieval_inspection_provider_returns_callable() -> None:
    ns = _ns(_open_db=MagicMock())
    provider = _retrieval_inspection_provider(ns)
    assert callable(provider)


def test_retrieval_inspection_provider_delegates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {"stages": []}
    mock_impl = MagicMock(return_value=payload)
    mock_run_record_impl = MagicMock(return_value={})
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard._retrieval_inspection_payload_impl",
        mock_impl,
    )
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard._run_record_payload_impl",
        mock_run_record_impl,
    )
    ns = _ns(_open_db=MagicMock())
    settings = MagicMock()

    provider = _retrieval_inspection_provider(ns)
    result = provider(settings)

    mock_impl.assert_called_once()
    assert result is payload


# ---------------------------------------------------------------------------
# _calendar_provider
# ---------------------------------------------------------------------------


def test_calendar_provider_returns_callable() -> None:
    ns = _ns(_open_db=MagicMock())
    provider = _calendar_provider(ns)
    assert callable(provider)


def test_calendar_provider_passes_open_db(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"sessions": []}
    mock_impl = MagicMock(return_value=payload)
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard._calendar_payload_impl",
        mock_impl,
    )
    open_db = MagicMock()
    ns = _ns(_open_db=open_db)
    settings = MagicMock()

    provider = _calendar_provider(ns)
    result = provider(settings)

    mock_impl.assert_called_once_with(settings, open_db=open_db)
    assert result is payload


# ---------------------------------------------------------------------------
# _news_provider
# ---------------------------------------------------------------------------


def test_news_provider_returns_callable() -> None:
    ns = _ns(_open_db=MagicMock())
    provider = _news_provider(ns)
    assert callable(provider)


def test_news_provider_passes_open_db(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"articles": []}
    mock_impl = MagicMock(return_value=payload)
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard._news_payload_impl",
        mock_impl,
    )
    open_db = MagicMock()
    ns = _ns(_open_db=open_db)
    settings = MagicMock()

    provider = _news_provider(ns)
    result = provider(settings)

    mock_impl.assert_called_once_with(settings, open_db=open_db)
    assert result is payload


# ---------------------------------------------------------------------------
# _provider_diagnostics_provider
# ---------------------------------------------------------------------------


def test_provider_diagnostics_provider_returns_callable() -> None:
    ns = _ns(provider_diagnostics_payload=MagicMock())
    provider = _provider_diagnostics_provider(ns)
    assert callable(provider)


def test_provider_diagnostics_provider_delegates_to_namespace() -> None:
    payload = {"ollama": "ok"}
    ns = _ns(provider_diagnostics_payload=MagicMock(return_value=payload))
    settings = MagicMock()

    provider = _provider_diagnostics_provider(ns)
    result = provider(settings)

    ns.provider_diagnostics_payload.assert_called_once_with(settings)
    assert result is payload


# ---------------------------------------------------------------------------
# _v1_readiness_provider
# ---------------------------------------------------------------------------


def test_v1_readiness_provider_returns_callable() -> None:
    ns = _ns(v1_readiness_payload=MagicMock())
    provider = _v1_readiness_provider(ns)
    assert callable(provider)


def test_v1_readiness_provider_delegates_to_namespace() -> None:
    payload = {"ready": True}
    ns = _ns(v1_readiness_payload=MagicMock(return_value=payload))
    settings = MagicMock()

    provider = _v1_readiness_provider(ns)
    result = provider(settings, True)

    ns.v1_readiness_payload.assert_called_once_with(settings, check_provider=True)
    assert result is payload


def test_v1_readiness_provider_check_provider_false() -> None:
    ns = _ns(v1_readiness_payload=MagicMock(return_value={}))
    provider = _v1_readiness_provider(ns)
    provider(MagicMock(), False)

    _, kwargs = ns.v1_readiness_payload.call_args
    assert kwargs["check_provider"] is False


# ---------------------------------------------------------------------------
# _runtime_mode_provider
# ---------------------------------------------------------------------------


def test_runtime_mode_provider_returns_callable() -> None:
    ns = _ns()
    provider = _runtime_mode_provider(ns)
    assert callable(provider)


def test_runtime_mode_provider_calls_transition_plan_with_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = MagicMock()
    mock_transition = MagicMock(return_value=plan)
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard._runtime_mode_transition_plan",
        mock_transition,
    )
    ns = _ns()
    settings = MagicMock()

    provider = _runtime_mode_provider(ns)
    result = provider(settings)

    mock_transition.assert_called_once_with(
        settings, target_mode="operation", check_provider=False
    )
    assert result is plan


# ---------------------------------------------------------------------------
# dashboard_command_deps
# ---------------------------------------------------------------------------


def _full_namespace() -> SimpleNamespace:
    """Build a namespace with all attributes needed by dashboard_command_deps."""
    return _ns(
        get_settings=MagicMock(),
        _emit_json=MagicMock(),
        _format_latest_order=MagicMock(),
        _open_db=MagicMock(),
        _read_text_tail=MagicMock(),
        get_broker_adapter=MagicMock(),
        provider_diagnostics_payload=MagicMock(),
        v1_readiness_payload=MagicMock(),
        read_service_events=MagicMock(),
        read_service_state=MagicMock(),
        build_runtime_status_view=MagicMock(),
    )


def test_dashboard_command_deps_returns_dashboard_command_deps_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Patch heavy impls so we don't need a real DB or network
    for name in [
        "_service_supervisor_payload_impl",
        "_finance_ops_payload_impl",
        "_finance_portfolio_payload",
        "_preferences_payload_impl",
        "_recent_runs_payload_impl",
        "_journal_payload_impl",
        "_finance_risk_report_payload",
        "_run_record_payload_impl",
        "_trade_context_payload_impl",
        "_market_context_payload_impl",
        "_canonical_analysis_payload_impl",
        "_run_replay_payload_impl",
        "_memory_explorer_payload_impl",
        "_retrieval_inspection_payload_impl",
        "_calendar_payload_impl",
        "_news_payload_impl",
        "_runtime_mode_transition_plan",
    ]:
        monkeypatch.setattr(
            f"agentic_trader.cli_modules.app_dashboard.{name}",
            MagicMock(return_value={}),
        )

    ns = _full_namespace()
    deps = dashboard_command_deps(ns)
    assert isinstance(deps, DashboardCommandDeps)


def test_dashboard_command_deps_wires_emit_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_all_impls(monkeypatch)
    emit_json = MagicMock()
    ns = _full_namespace()
    ns._emit_json = emit_json  # type: ignore[assignment]

    deps = dashboard_command_deps(ns)
    assert deps.emit_json is emit_json


def test_dashboard_command_deps_wires_latest_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_all_impls(monkeypatch)
    format_latest_order = MagicMock()
    ns = _full_namespace()
    ns._format_latest_order = format_latest_order  # type: ignore[assignment]

    deps = dashboard_command_deps(ns)
    assert deps.latest_order is format_latest_order


def test_dashboard_command_deps_get_settings_delegates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_all_impls(monkeypatch)
    settings = MagicMock()
    ns = _full_namespace()
    ns.get_settings = MagicMock(return_value=settings)  # type: ignore[assignment]

    deps = dashboard_command_deps(ns)
    result = deps.get_settings()
    assert result is settings


def test_dashboard_command_deps_open_read_db_uses_read_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_all_impls(monkeypatch)
    db = MagicMock()
    open_db = MagicMock(return_value=db)
    ns = _full_namespace()
    ns._open_db = open_db  # type: ignore[assignment]

    deps = dashboard_command_deps(ns)
    result = deps.open_read_db(MagicMock())
    open_db.assert_called_once()
    _, kwargs = open_db.call_args
    assert kwargs.get("read_only") is True
    assert result is db


def test_dashboard_command_deps_read_service_events_wired(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_all_impls(monkeypatch)
    read_service_events = MagicMock()
    ns = _full_namespace()
    ns.read_service_events = read_service_events  # type: ignore[assignment]

    deps = dashboard_command_deps(ns)
    assert deps.read_service_events is read_service_events


def test_dashboard_command_deps_build_runtime_status_view_wired(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_all_impls(monkeypatch)
    build_rsv = MagicMock()
    ns = _full_namespace()
    ns.build_runtime_status_view = build_rsv  # type: ignore[assignment]

    deps = dashboard_command_deps(ns)
    assert deps.build_runtime_status_view is build_rsv


# ---------------------------------------------------------------------------
# build_dashboard_snapshot_payload
# ---------------------------------------------------------------------------


def test_build_dashboard_snapshot_payload_delegates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {"snapshot": True}
    mock_fn = MagicMock(return_value=payload)
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard._build_dashboard_snapshot_payload",
        mock_fn,
    )
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard.dashboard_command_deps",
        MagicMock(return_value=MagicMock()),
    )
    ns = _full_namespace()
    settings = MagicMock()

    result = build_dashboard_snapshot_payload(ns, settings, log_limit=5)

    mock_fn.assert_called_once()
    _, kwargs = mock_fn.call_args
    assert kwargs["log_limit"] == 5
    assert result is payload


def test_build_dashboard_snapshot_payload_check_provider_forwarded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_fn = MagicMock(return_value={})
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard._build_dashboard_snapshot_payload",
        mock_fn,
    )
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard.dashboard_command_deps",
        MagicMock(return_value=MagicMock()),
    )
    ns = _full_namespace()
    build_dashboard_snapshot_payload(ns, MagicMock(), check_provider=True)

    _, kwargs = mock_fn.call_args
    assert kwargs["check_provider"] is True


# ---------------------------------------------------------------------------
# build_evidence_bundle
# ---------------------------------------------------------------------------


def test_build_evidence_bundle_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"bundle": True}
    mock_fn = MagicMock(return_value=payload)
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard._build_dashboard_evidence_bundle",
        mock_fn,
    )
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard.dashboard_command_deps",
        MagicMock(return_value=MagicMock()),
    )
    ns = _full_namespace()
    settings = MagicMock()
    output_dir = Path("/tmp/evidence")

    result = build_evidence_bundle(
        ns, settings, output_dir=output_dir, label="test", log_limit=10
    )

    mock_fn.assert_called_once()
    _, kwargs = mock_fn.call_args
    assert kwargs["output_dir"] is output_dir
    assert kwargs["label"] == "test"
    assert kwargs["log_limit"] == 10
    assert result is payload


def test_build_evidence_bundle_include_latest_smoke_and_check_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_fn = MagicMock(return_value={})
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard._build_dashboard_evidence_bundle",
        mock_fn,
    )
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard.dashboard_command_deps",
        MagicMock(return_value=MagicMock()),
    )
    ns = _full_namespace()
    build_evidence_bundle(
        ns,
        MagicMock(),
        include_latest_smoke=False,
        check_provider=True,
    )

    _, kwargs = mock_fn.call_args
    assert kwargs["include_latest_smoke"] is False
    assert kwargs["check_provider"] is True


# ---------------------------------------------------------------------------
# build_observer_api_payload
# ---------------------------------------------------------------------------


def test_build_observer_api_payload_delegates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = (200, {"api": "data"})
    mock_fn = MagicMock(return_value=payload)
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard._build_observer_api_payload",
        mock_fn,
    )
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard.dashboard_command_deps",
        MagicMock(return_value=MagicMock()),
    )
    ns = _full_namespace()
    settings = MagicMock()

    result = build_observer_api_payload(
        ns, settings, path="/api/v1/status", log_limit=5
    )

    mock_fn.assert_called_once()
    _, kwargs = mock_fn.call_args
    assert kwargs["path"] == "/api/v1/status"
    assert kwargs["log_limit"] == 5
    assert result is payload


def test_build_observer_api_payload_default_log_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_fn = MagicMock(return_value=(200, {}))
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard._build_observer_api_payload",
        mock_fn,
    )
    monkeypatch.setattr(
        "agentic_trader.cli_modules.app_dashboard.dashboard_command_deps",
        MagicMock(return_value=MagicMock()),
    )
    ns = _full_namespace()
    build_observer_api_payload(ns, MagicMock(), path="/api/v1/portfolio")

    _, kwargs = mock_fn.call_args
    assert kwargs["log_limit"] == 14


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _patch_all_impls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch all heavy implementation functions to avoid side effects in tests."""
    for name in [
        "_service_supervisor_payload_impl",
        "_finance_ops_payload_impl",
        "_finance_portfolio_payload",
        "_preferences_payload_impl",
        "_recent_runs_payload_impl",
        "_journal_payload_impl",
        "_finance_risk_report_payload",
        "_run_record_payload_impl",
        "_trade_context_payload_impl",
        "_market_context_payload_impl",
        "_canonical_analysis_payload_impl",
        "_run_replay_payload_impl",
        "_memory_explorer_payload_impl",
        "_retrieval_inspection_payload_impl",
        "_calendar_payload_impl",
        "_news_payload_impl",
        "_runtime_mode_transition_plan",
    ]:
        monkeypatch.setattr(
            f"agentic_trader.cli_modules.app_dashboard.{name}",
            MagicMock(return_value={}),
        )