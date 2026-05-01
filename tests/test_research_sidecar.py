from dataclasses import replace
from datetime import UTC, datetime, timedelta
import json
import subprocess

import httpx
import pytest

from agentic_trader.config import Settings
from agentic_trader.researchd.orchestrator import CrewAiResearchBackend, ResearchSidecar
from agentic_trader.researchd.persistence import persist_research_result
from agentic_trader.researchd.providers import (
    SEC_RESEARCH_FORMS,
    SecEdgarSubmissionsProvider,
    _list_value,
    _normalize_symbol,
    _primary_document_note,
    _provider_health_message,
    _recent_filings,
    _records_from_submissions,
    _safe_error_note,
    _sec_archive_url,
    _sec_configuration_note,
    _sec_missing_fields,
    _sec_ticker_index,
    _string_at,
    _string_value,
    ResearchProviderOutput,
    ScaffoldResearchProvider,
    default_research_providers,
    provider_health_from_output,
)
from agentic_trader.runtime_feed import (
    read_latest_research_snapshot,
    read_research_snapshots,
)
from agentic_trader.researchd.status import build_research_sidecar_state
from agentic_trader.schemas import EvidenceInferenceBreakdown, RawEvidenceRecord


def _settings(tmp_path, **overrides) -> Settings:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        market_data_cache_dir=tmp_path / "market_cache",
        **overrides,
    )
    settings.ensure_directories()
    return settings


def test_research_sidecar_defaults_to_disabled(tmp_path) -> None:
    settings = _settings(tmp_path)

    state = build_research_sidecar_state(settings)

    assert state.mode == "off"
    assert state.enabled is False
    assert state.status == "disabled"
    assert state.backend == "noop"
    assert state.provider_health
    assert state.source_health_summary["missing"] >= 1


def test_enabled_research_sidecar_uses_scaffolds_without_fake_evidence(tmp_path) -> None:
    settings = _settings(
        tmp_path,
        research_mode="training",
        research_sidecar_enabled=True,
        research_symbols="AAPL, MSFT",
    )

    result = ResearchSidecar(settings).collect_once()

    assert result.state.mode == "training"
    assert result.state.enabled is True
    assert result.state.status == "completed"
    assert result.state.watched_symbols == ["AAPL", "MSFT"]
    assert result.world_state is not None
    assert result.world_state.watched_symbols == ["AAPL", "MSFT"]
    assert result.world_state.findings == []
    assert result.raw_evidence == []
    assert result.memory_update["raw_web_text_injected"] is False
    assert result.memory_update["status"] == "not_written"
    assert all(item.freshness == "missing" for item in result.state.provider_health)


def test_crewai_backend_reports_missing_sidecar_environment(tmp_path) -> None:
    settings = _settings(
        tmp_path,
        research_mode="training",
        research_sidecar_enabled=True,
        research_sidecar_backend="crewai",
        research_symbols="AAPL",
    )
    backend = CrewAiResearchBackend(flow_dir=tmp_path / "missing", uv_path="uv")

    result = ResearchSidecar(settings, backend=backend).collect_once()

    assert result.state.backend == "crewai"
    assert result.state.status == "failed"
    assert "missing" in str(result.state.last_error).lower()
    assert result.world_state is None
    assert result.raw_evidence == []
    assert result.memory_update["raw_web_text_injected"] is False


def test_crewai_backend_uses_subprocess_contract_without_core_imports(tmp_path) -> None:
    settings = _settings(
        tmp_path,
        research_mode="training",
        research_sidecar_enabled=True,
        research_sidecar_backend="crewai",
        research_symbols="AAPL",
    )
    flow_dir = tmp_path / "research_flow"
    (flow_dir / ".venv").mkdir(parents=True)
    (flow_dir / "pyproject.toml").write_text("[project]\nname='fake'\n")
    captured: dict[str, object] = {}

    def fake_runner(
        command: list[str],
        stdin_payload: str,
        cwd,
        env: dict[str, str],
        timeout_seconds: float,
    ) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured["cwd"] = str(cwd)
        captured["request"] = json.loads(stdin_payload)
        captured["tracing"] = env.get("CREWAI_TRACING_ENABLED")
        captured["timeout_seconds"] = timeout_seconds
        output = {
            "status": "completed",
            "backend": "crewai",
            "contract_version": "research-flow.v1",
            "generated_at": "2026-01-01T00:00:00+00:00",
            "observed_at": "2026-01-01T00:00:00+00:00",
            "watched_symbols": ["AAPL"],
            "summary": "Contract accepted scaffold provider packets.",
            "planned_tasks": [
                {
                    "task_id": "company-dossier:AAPL",
                    "kind": "company_dossier",
                    "subject": "AAPL",
                    "status": "planned",
                }
            ],
            "findings": [],
            "dossiers": [],
            "macro_events": [],
            "social_signals": [],
            "memory_update": {
                "status": "not_written",
                "planned_tasks": [
                    {
                        "task_id": "company-dossier:AAPL",
                        "kind": "company_dossier",
                        "subject": "AAPL",
                        "status": "planned",
                    }
                ],
                "raw_web_text_injected": False,
                "broker_access": False,
            },
            "raw_web_text_injected": False,
            "broker_access": False,
        }
        return subprocess.CompletedProcess(command, 0, json.dumps(output), "")

    backend = CrewAiResearchBackend(
        flow_dir=flow_dir,
        uv_path="uv",
        command_runner=fake_runner,
    )

    result = ResearchSidecar(settings, backend=backend).collect_once()

    assert result.state.backend == "crewai"
    assert result.state.status == "completed"
    assert result.world_state is not None
    assert result.world_state.summary == "Contract accepted scaffold provider packets."
    assert result.world_state.watched_symbols == ["AAPL"]
    assert result.memory_update["contract_version"] == "research-flow.v1"
    assert result.memory_update["raw_web_text_injected"] is False
    assert result.memory_update["broker_access"] is False
    planned_tasks = result.memory_update["planned_tasks"]
    assert isinstance(planned_tasks, list)
    first_task = planned_tasks[0]
    assert isinstance(first_task, dict)
    assert first_task["kind"] == "company_dossier"
    assert captured["command"] == [
        "uv",
        "run",
        "--locked",
        "--no-sync",
        "research-flow-contract",
    ]
    assert captured["cwd"] == str(flow_dir)
    assert captured["tracing"] == "false"
    request = captured["request"]
    assert isinstance(request, dict)
    assert request["symbols"] == ["AAPL"]
    provider_outputs = request["provider_outputs"]
    assert isinstance(provider_outputs, list)
    assert provider_outputs[0]["metadata"]["provider_id"] == "sec_edgar_research"


def test_research_schema_tracks_staleness_and_uncertainty() -> None:
    now = datetime.now(UTC)
    stale_after = (now - timedelta(minutes=1)).isoformat()
    record = RawEvidenceRecord(
        record_id="raw-1",
        source_kind="news",
        source_name="example_news",
        title="Example event",
        observed_at=(now - timedelta(hours=1)).isoformat(),
        stale_after=stale_after,
        evidence_vs_inference=EvidenceInferenceBreakdown(
            evidence=["Headline was observed from a provider payload."],
            inference=[],
            uncertainty=["Provider payload was not independently verified."],
        ),
        missing_fields=["url"],
    )

    assert record.is_stale(now.isoformat()) is True
    assert record.evidence_vs_inference.evidence
    assert record.evidence_vs_inference.uncertainty
    assert record.missing_fields == ["url"]


def test_research_provider_health_keeps_missing_sources_visible(tmp_path) -> None:
    settings = _settings(tmp_path)
    provider = default_research_providers(settings)[0]

    output = provider.collect(symbols=["AAPL"], limit=5)
    health = provider_health_from_output(output)

    assert health.provider_id == "sec_edgar_research"
    assert health.enabled is False
    assert health.source_role == "missing"
    assert health.freshness == "missing"
    assert "provider_disabled" in health.notes
    assert "Provider is disabled by configuration" in health.message


def test_sec_edgar_provider_requires_explicit_user_agent(tmp_path) -> None:
    settings = _settings(tmp_path, research_sec_edgar_enabled=True)

    def forbidden_fetcher(url, headers, timeout_seconds):
        _ = (url, headers, timeout_seconds)
        raise AssertionError("SEC provider should not fetch without a User-Agent")

    provider = SecEdgarSubmissionsProvider(
        settings=settings,
        fetcher=forbidden_fetcher,
    )

    output = provider.collect(symbols=["AAPL"], limit=5)
    health = provider_health_from_output(output)

    assert output.raw_evidence == []
    assert output.missing_reasons == ["sec_user_agent_missing"]
    assert health.enabled is True
    assert health.requires_network is True
    assert "required SEC User-Agent" in health.message


def test_sec_edgar_provider_normalizes_recent_filings_without_raw_text(tmp_path) -> None:
    settings = _settings(
        tmp_path,
        research_sec_edgar_enabled=True,
        research_sec_edgar_user_agent="Agentic Trader test contact@example.com",
        request_timeout_seconds=999,
    )
    calls: list[str] = []

    def fake_fetcher(url, headers, timeout_seconds):
        calls.append(url)
        assert headers["User-Agent"] == "Agentic Trader test contact@example.com"
        assert headers["Accept"] == "application/json"
        assert timeout_seconds == 30.0
        if url == "https://www.sec.gov/files/company_tickers.json":
            return {
                "0": {
                    "cik_str": 320193,
                    "ticker": "AAPL",
                    "title": "Apple Inc.",
                }
            }
        if url == "https://data.sec.gov/submissions/CIK0000320193.json":
            return {
                "name": "Apple Inc.",
                "filings": {
                    "recent": {
                        "accessionNumber": [
                            "0000320193-24-000100",
                            "0000320193-24-000123",
                        ],
                        "filingDate": ["2024-10-01", "2024-11-01"],
                        "reportDate": ["2024-09-01", "2024-09-28"],
                        "form": ["S-8", "10-K"],
                        "primaryDocument": [
                            "aapl-s8.htm",
                            "aapl-20240928.htm",
                        ],
                        "primaryDocDescription": ["S-8", "10-K"],
                    }
                },
            }
        raise AssertionError(f"unexpected SEC URL: {url}")

    provider = SecEdgarSubmissionsProvider(settings=settings, fetcher=fake_fetcher)

    output = provider.collect(symbols=["aapl", "MISSING"], limit=5)
    health = provider_health_from_output(output)

    assert calls == [
        "https://www.sec.gov/files/company_tickers.json",
        "https://data.sec.gov/submissions/CIK0000320193.json",
    ]
    assert output.missing_reasons == ["sec_cik_missing:MISSING"]
    assert len(output.raw_evidence) == 1
    record = output.raw_evidence[0]
    assert record.record_id == "sec:AAPL:0000320193-24-000123"
    assert record.source_kind == "disclosure"
    assert record.source_name == "sec_edgar_research"
    assert record.title == "AAPL 10-K filed 2024-11-01"
    assert record.symbol == "AAPL"
    assert record.entity_name == "Apple Inc."
    assert record.region == "US"
    assert (
        record.url
        == "https://www.sec.gov/Archives/edgar/data/320193/"
        "000032019324000123/aapl-20240928.htm"
    )
    assert record.source_payload_ref == "sec-submissions://CIK0000320193/0000320193-24-000123"
    assert "Filing text and XBRL facts were not downloaded" in (
        record.evidence_vs_inference.uncertainty[0]
    )
    assert record.evidence_vs_inference.inference == []
    assert record.source_attributions[0].confidence == 0.95
    assert "form=10-K" in record.source_attributions[0].notes
    assert record.missing_fields == []
    assert health.freshness == "fresh"
    assert health.last_successful_update_at is not None
    assert "Provider returned normalized research evidence" in health.message


def test_research_result_persists_to_runtime_feed_without_database(tmp_path) -> None:
    settings = _settings(
        tmp_path,
        research_mode="training",
        research_sidecar_enabled=True,
        research_symbols="AAPL",
    )
    result = ResearchSidecar(settings).collect_once()
    now = datetime.now(UTC).isoformat()
    evidence = RawEvidenceRecord(
        record_id="raw-sidecar-1",
        source_kind="news",
        source_name="example_news",
        title="Example evidence",
        symbol="AAPL",
        observed_at=now,
        normalized_summary="Normalized evidence summary.",
    )
    result = replace(result, raw_evidence=[evidence])

    record = persist_research_result(settings, result)
    latest = read_latest_research_snapshot(settings)
    records = read_research_snapshots(settings)

    assert latest is not None
    assert latest.snapshot_id == record.snapshot_id
    assert latest.mode == "training"
    assert latest.state.status == "completed"
    assert latest.world_state is not None
    assert record.world_state is not None
    assert latest.world_state.snapshot_id == record.world_state.snapshot_id
    assert latest.raw_evidence == [evidence]
    assert latest.memory_update["status"] == "not_written"
    assert records[0].snapshot_id == record.snapshot_id
    assert settings.database_path.exists() is False


# ---------------------------------------------------------------------------
# CrewAiResearchBackend – new subprocess contract error branches
# ---------------------------------------------------------------------------


def test_crewai_backend_fails_when_uv_not_available(tmp_path) -> None:
    """Backend returns failed state immediately if uv is not found."""
    settings = _settings(
        tmp_path,
        research_mode="training",
        research_sidecar_enabled=True,
        research_sidecar_backend="crewai",
        research_symbols="AAPL",
    )
    flow_dir = tmp_path / "research_flow"
    flow_dir.mkdir()
    (flow_dir / "pyproject.toml").write_text("[project]\nname='fake'\n")
    (flow_dir / ".venv").mkdir()

    backend = CrewAiResearchBackend(flow_dir=flow_dir, uv_path=None)
    # Patch shutil.which to always return None so uv_path fallback also fails
    import agentic_trader.researchd.orchestrator as orch_module
    original_which = orch_module.shutil.which

    class _FakeCompleted:
        pass

    # Simulate uv not on PATH by overriding which inside the module
    import shutil as _shutil_real
    saved = _shutil_real.which

    def no_uv(name: str, **kwargs):  # type: ignore[misc]
        return None

    _shutil_real.which = no_uv  # type: ignore[assignment]
    try:
        result = ResearchSidecar(settings, backend=backend).collect_once()
    finally:
        _shutil_real.which = saved

    assert result.state.status == "failed"
    assert "uv is required" in str(result.state.last_error)
    assert result.world_state is None
    assert result.memory_update["raw_web_text_injected"] is False
    assert result.memory_update["broker_access"] is False


def test_crewai_backend_fails_when_pyproject_missing(tmp_path) -> None:
    """Backend returns failed state when pyproject.toml is absent from flow_dir."""
    settings = _settings(
        tmp_path,
        research_mode="training",
        research_sidecar_enabled=True,
        research_sidecar_backend="crewai",
        research_symbols="AAPL",
    )
    flow_dir = tmp_path / "research_flow_no_project"
    flow_dir.mkdir()
    # No pyproject.toml created

    backend = CrewAiResearchBackend(flow_dir=flow_dir, uv_path="uv")
    result = ResearchSidecar(settings, backend=backend).collect_once()

    assert result.state.status == "failed"
    assert "missing" in str(result.state.last_error).lower()
    assert result.world_state is None


def test_crewai_backend_fails_when_venv_missing(tmp_path) -> None:
    """Backend returns failed state when .venv is absent (sidecar not installed)."""
    settings = _settings(
        tmp_path,
        research_mode="training",
        research_sidecar_enabled=True,
        research_sidecar_backend="crewai",
        research_symbols="AAPL",
    )
    flow_dir = tmp_path / "research_flow_no_venv"
    flow_dir.mkdir()
    (flow_dir / "pyproject.toml").write_text("[project]\nname='fake'\n")
    # No .venv created

    backend = CrewAiResearchBackend(flow_dir=flow_dir, uv_path="uv")
    result = ResearchSidecar(settings, backend=backend).collect_once()

    assert result.state.status == "failed"
    assert "not installed" in str(result.state.last_error).lower()
    assert result.world_state is None


def test_crewai_backend_handles_timeout(tmp_path) -> None:
    """Backend returns failed state when subprocess contract times out."""
    settings = _settings(
        tmp_path,
        research_mode="training",
        research_sidecar_enabled=True,
        research_sidecar_backend="crewai",
        research_symbols="AAPL",
    )
    flow_dir = tmp_path / "research_flow"
    (flow_dir / ".venv").mkdir(parents=True)
    (flow_dir / "pyproject.toml").write_text("[project]\nname='fake'\n")

    def timeout_runner(command, stdin_payload, cwd, env, timeout_seconds):
        raise subprocess.TimeoutExpired(command, timeout_seconds)

    backend = CrewAiResearchBackend(
        flow_dir=flow_dir,
        uv_path="uv",
        command_runner=timeout_runner,
    )
    result = ResearchSidecar(settings, backend=backend).collect_once()

    assert result.state.status == "failed"
    assert "timed out" in str(result.state.last_error).lower()
    assert result.world_state is None


def test_crewai_backend_handles_unexpected_subprocess_exception(tmp_path) -> None:
    """Backend returns failed state for unexpected subprocess exceptions."""
    settings = _settings(
        tmp_path,
        research_mode="training",
        research_sidecar_enabled=True,
        research_sidecar_backend="crewai",
        research_symbols="AAPL",
    )
    flow_dir = tmp_path / "research_flow"
    (flow_dir / ".venv").mkdir(parents=True)
    (flow_dir / "pyproject.toml").write_text("[project]\nname='fake'\n")

    def crashing_runner(command, stdin_payload, cwd, env, timeout_seconds):
        raise FileNotFoundError("uv binary not found at path")

    backend = CrewAiResearchBackend(
        flow_dir=flow_dir,
        uv_path="uv",
        command_runner=crashing_runner,
    )
    result = ResearchSidecar(settings, backend=backend).collect_once()

    assert result.state.status == "failed"
    assert "failed to start" in str(result.state.last_error).lower()


def test_crewai_backend_handles_non_json_output(tmp_path) -> None:
    """Backend returns failed state when subprocess emits non-JSON stdout."""
    settings = _settings(
        tmp_path,
        research_mode="training",
        research_sidecar_enabled=True,
        research_sidecar_backend="crewai",
        research_symbols="AAPL",
    )
    flow_dir = tmp_path / "research_flow"
    (flow_dir / ".venv").mkdir(parents=True)
    (flow_dir / "pyproject.toml").write_text("[project]\nname='fake'\n")

    def non_json_runner(command, stdin_payload, cwd, env, timeout_seconds):
        return subprocess.CompletedProcess(command, 0, "not valid json\n", "")

    backend = CrewAiResearchBackend(
        flow_dir=flow_dir,
        uv_path="uv",
        command_runner=non_json_runner,
    )
    result = ResearchSidecar(settings, backend=backend).collect_once()

    assert result.state.status == "failed"
    assert "non-json" in str(result.state.last_error).lower()


def test_crewai_backend_handles_failed_contract_status(tmp_path) -> None:
    """Backend returns failed state when contract JSON has status != completed."""
    settings = _settings(
        tmp_path,
        research_mode="training",
        research_sidecar_enabled=True,
        research_sidecar_backend="crewai",
        research_symbols="AAPL",
    )
    flow_dir = tmp_path / "research_flow"
    (flow_dir / ".venv").mkdir(parents=True)
    (flow_dir / "pyproject.toml").write_text("[project]\nname='fake'\n")

    def failed_status_runner(command, stdin_payload, cwd, env, timeout_seconds):
        payload = {
            "status": "error",
            "errors": ["OPENAI_API_KEY not configured"],
        }
        return subprocess.CompletedProcess(command, 1, json.dumps(payload), "")

    backend = CrewAiResearchBackend(
        flow_dir=flow_dir,
        uv_path="uv",
        command_runner=failed_status_runner,
    )
    result = ResearchSidecar(settings, backend=backend).collect_once()

    assert result.state.status == "failed"
    assert "OPENAI_API_KEY" in str(result.state.last_error)


def test_crewai_backend_handles_failed_status_with_empty_errors(tmp_path) -> None:
    """Backend provides a generic message when errors list is empty in failed status."""
    settings = _settings(
        tmp_path,
        research_mode="training",
        research_sidecar_enabled=True,
        research_sidecar_backend="crewai",
        research_symbols="AAPL",
    )
    flow_dir = tmp_path / "research_flow"
    (flow_dir / ".venv").mkdir(parents=True)
    (flow_dir / "pyproject.toml").write_text("[project]\nname='fake'\n")

    def empty_errors_runner(command, stdin_payload, cwd, env, timeout_seconds):
        payload = {"status": "error", "errors": []}
        return subprocess.CompletedProcess(command, 1, json.dumps(payload), "")

    backend = CrewAiResearchBackend(
        flow_dir=flow_dir,
        uv_path="uv",
        command_runner=empty_errors_runner,
    )
    result = ResearchSidecar(settings, backend=backend).collect_once()

    assert result.state.status == "failed"
    assert "failed status" in str(result.state.last_error).lower()


def test_crewai_backend_result_contains_contract_version(tmp_path) -> None:
    """Successful contract result includes contract_version in memory_update."""
    settings = _settings(
        tmp_path,
        research_mode="training",
        research_sidecar_enabled=True,
        research_sidecar_backend="crewai",
        research_symbols="AAPL",
    )
    flow_dir = tmp_path / "research_flow"
    (flow_dir / ".venv").mkdir(parents=True)
    (flow_dir / "pyproject.toml").write_text("[project]\nname='fake'\n")

    def versioned_runner(command, stdin_payload, cwd, env, timeout_seconds):
        payload = {
            "status": "completed",
            "contract_version": "research-flow.v1",
            "generated_at": "2026-01-01T00:00:00+00:00",
            "observed_at": "2026-01-01T00:00:00+00:00",
            "summary": "ok",
            "findings": [],
            "dossiers": [],
            "macro_events": [],
            "social_signals": [],
            "memory_update": {"status": "not_written"},
        }
        return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")

    backend = CrewAiResearchBackend(
        flow_dir=flow_dir,
        uv_path="uv",
        command_runner=versioned_runner,
    )
    result = ResearchSidecar(settings, backend=backend).collect_once()

    assert result.state.status == "completed"
    assert result.memory_update["contract_version"] == "research-flow.v1"
    assert result.memory_update["raw_web_text_injected"] is False
    assert result.memory_update["broker_access"] is False


def test_crewai_backend_sets_defaults_when_memory_update_not_dict(tmp_path) -> None:
    """Memory update defaults are applied when contract returns a non-dict value."""
    settings = _settings(
        tmp_path,
        research_mode="training",
        research_sidecar_enabled=True,
        research_sidecar_backend="crewai",
        research_symbols="AAPL",
    )
    flow_dir = tmp_path / "research_flow"
    (flow_dir / ".venv").mkdir(parents=True)
    (flow_dir / "pyproject.toml").write_text("[project]\nname='fake'\n")

    def non_dict_memory_runner(command, stdin_payload, cwd, env, timeout_seconds):
        payload = {
            "status": "completed",
            "generated_at": "2026-01-01T00:00:00+00:00",
            "summary": "ok",
            "findings": [],
            "dossiers": [],
            "macro_events": [],
            "social_signals": [],
            "memory_update": "not_a_dict",
        }
        return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")

    backend = CrewAiResearchBackend(
        flow_dir=flow_dir,
        uv_path="uv",
        command_runner=non_dict_memory_runner,
    )
    result = ResearchSidecar(settings, backend=backend).collect_once()

    assert result.state.status == "completed"
    assert result.memory_update["status"] == "not_written"
    assert result.memory_update["raw_web_text_injected"] is False
    assert result.memory_update["broker_access"] is False


def test_crewai_backend_handles_non_list_payload_fields(tmp_path) -> None:
    """Backend handles gracefully when findings/dossiers/events are not lists."""
    settings = _settings(
        tmp_path,
        research_mode="training",
        research_sidecar_enabled=True,
        research_sidecar_backend="crewai",
        research_symbols="AAPL",
    )
    flow_dir = tmp_path / "research_flow"
    (flow_dir / ".venv").mkdir(parents=True)
    (flow_dir / "pyproject.toml").write_text("[project]\nname='fake'\n")

    def malformed_lists_runner(command, stdin_payload, cwd, env, timeout_seconds):
        payload = {
            "status": "completed",
            "generated_at": "2026-01-01T00:00:00+00:00",
            "summary": "ok",
            "findings": "not_a_list",
            "dossiers": 42,
            "macro_events": None,
            "social_signals": False,
            "memory_update": {},
        }
        return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")

    backend = CrewAiResearchBackend(
        flow_dir=flow_dir,
        uv_path="uv",
        command_runner=malformed_lists_runner,
    )
    result = ResearchSidecar(settings, backend=backend).collect_once()

    assert result.state.status == "completed"
    assert result.findings == []
    assert result.dossiers == []
    assert result.macro_events == []
    assert result.social_signals == []


def test_crewai_backend_tracing_disabled_in_env(tmp_path) -> None:
    """Backend sets CREWAI_TRACING_ENABLED=false in the subprocess environment."""
    settings = _settings(
        tmp_path,
        research_mode="training",
        research_sidecar_enabled=True,
        research_sidecar_backend="crewai",
        research_symbols="AAPL",
    )
    flow_dir = tmp_path / "research_flow"
    (flow_dir / ".venv").mkdir(parents=True)
    (flow_dir / "pyproject.toml").write_text("[project]\nname='fake'\n")
    captured_env: dict = {}

    def capture_env_runner(command, stdin_payload, cwd, env, timeout_seconds):
        captured_env.update(env)
        payload = {
            "status": "completed",
            "generated_at": "2026-01-01T00:00:00+00:00",
            "summary": "",
            "findings": [],
            "dossiers": [],
            "macro_events": [],
            "social_signals": [],
            "memory_update": {},
        }
        return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")

    backend = CrewAiResearchBackend(
        flow_dir=flow_dir,
        uv_path="uv",
        command_runner=capture_env_runner,
    )
    ResearchSidecar(settings, backend=backend).collect_once()

    assert captured_env.get("CREWAI_TRACING_ENABLED") == "false"


def test_crewai_contract_payload_from_process_returns_none_for_list_json(
    tmp_path,
) -> None:
    """_contract_payload_from_process returns None when stdout is a JSON list."""
    backend = CrewAiResearchBackend()
    completed = subprocess.CompletedProcess([], 0, '["item1","item2"]', "")

    result = backend._contract_payload_from_process(completed)

    assert result is None


def test_crewai_trim_truncates_long_strings() -> None:
    """_trim truncates strings longer than the default 500 char limit."""
    backend = CrewAiResearchBackend()
    long_string = "x" * 1000

    trimmed = backend._trim(long_string)

    assert len(trimmed) == 500


def test_crewai_trim_strips_newlines() -> None:
    """_trim replaces newlines with spaces."""
    backend = CrewAiResearchBackend()

    trimmed = backend._trim("line1\nline2\nline3")

    assert "\n" not in trimmed
    assert "line1 line2 line3" == trimmed


# ---------------------------------------------------------------------------
# providers.py – helper function edge cases
# ---------------------------------------------------------------------------


def test_normalize_symbol_uppercases_and_strips() -> None:
    assert _normalize_symbol("  aapl  ") == "AAPL"
    assert _normalize_symbol("msft") == "MSFT"
    assert _normalize_symbol("") == ""


def test_safe_error_note_includes_exception_type() -> None:
    exc = ValueError("test")
    note = _safe_error_note(exc)
    assert note == "provider_error:ValueError"


def test_sec_configuration_note_disabled() -> None:
    assert _sec_configuration_note(enabled=False, user_agent="") == "sec_provider_disabled"
    assert _sec_configuration_note(enabled=False, user_agent="agent") == "sec_provider_disabled"


def test_sec_configuration_note_enabled_with_user_agent() -> None:
    assert (
        _sec_configuration_note(enabled=True, user_agent="My App contact@example.com")
        == "sec_user_agent_configured"
    )


def test_sec_configuration_note_enabled_without_user_agent() -> None:
    assert _sec_configuration_note(enabled=True, user_agent="") == "sec_user_agent_missing"


def test_sec_ticker_index_builds_correct_mapping() -> None:
    payload = {
        "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
        "1": {"cik_str": 789019, "ticker": "msft", "title": "Microsoft Corporation"},
    }

    index = _sec_ticker_index(payload)

    assert "AAPL" in index
    assert "MSFT" in index
    assert index["AAPL"].cik == "0000320193"
    assert index["AAPL"].entity_name == "Apple Inc."
    assert index["MSFT"].symbol == "MSFT"


def test_sec_ticker_index_zero_pads_cik() -> None:
    payload = {"0": {"cik_str": 12345, "ticker": "XYZ", "title": "XYZ Corp"}}

    index = _sec_ticker_index(payload)

    assert index["XYZ"].cik == "0000012345"


def test_sec_ticker_index_skips_non_dict_values() -> None:
    payload = {
        "bad": "not_a_dict",
        "0": {"cik_str": 111, "ticker": "OK", "title": "OK Corp"},
    }

    index = _sec_ticker_index(payload)

    assert "OK" in index
    assert len(index) == 1


def test_sec_ticker_index_skips_entries_missing_ticker() -> None:
    payload = {
        "0": {"cik_str": 111, "ticker": "", "title": "Missing Ticker Corp"},
        "1": {"cik_str": 222, "ticker": "VALID", "title": "Valid Corp"},
    }

    index = _sec_ticker_index(payload)

    assert "VALID" in index
    assert len(index) == 1


def test_sec_ticker_index_skips_entries_missing_cik_str() -> None:
    payload = {
        "0": {"cik_str": None, "ticker": "NO_CIK", "title": "No CIK Corp"},
        "1": {"cik_str": 333, "ticker": "HAS_CIK", "title": "Has CIK Corp"},
    }

    index = _sec_ticker_index(payload)

    assert "HAS_CIK" in index
    assert "NO_CIK" not in index


def test_recent_filings_returns_none_for_missing_filings_key() -> None:
    payload = {"name": "Apple Inc."}

    result = _recent_filings(payload)

    assert result is None


def test_recent_filings_returns_none_for_non_dict_filings() -> None:
    payload = {"filings": "not_a_dict"}

    result = _recent_filings(payload)

    assert result is None


def test_recent_filings_returns_none_when_recent_missing() -> None:
    payload = {"filings": {"older": {}}}

    result = _recent_filings(payload)

    assert result is None


def test_recent_filings_returns_recent_dict() -> None:
    recent = {"accessionNumber": ["0001-01-01"]}
    payload = {"filings": {"recent": recent}}

    result = _recent_filings(payload)

    assert result == recent


def test_records_from_submissions_returns_empty_for_zero_limit(tmp_path) -> None:
    """_records_from_submissions returns empty list when limit <= 0."""
    settings = _settings(
        tmp_path,
        research_sec_edgar_enabled=True,
        research_sec_edgar_user_agent="test agent",
    )
    provider = SecEdgarSubmissionsProvider(settings=settings)
    meta = provider.metadata()

    from agentic_trader.researchd.providers import _SecTickerMatch

    match = _SecTickerMatch(symbol="AAPL", cik="0000320193", entity_name="Apple Inc.")
    payload = {
        "name": "Apple Inc.",
        "filings": {
            "recent": {
                "accessionNumber": ["0000320193-24-000123"],
                "form": ["10-K"],
                "filingDate": ["2024-11-01"],
                "reportDate": ["2024-09-28"],
                "primaryDocument": ["aapl-20240928.htm"],
                "primaryDocDescription": ["10-K"],
            }
        },
    }

    records = _records_from_submissions(
        provider=meta,
        symbol="AAPL",
        match=match,
        payload=payload,
        limit=0,
    )

    assert records == []


def test_records_from_submissions_filters_non_research_forms(tmp_path) -> None:
    """Forms not in SEC_RESEARCH_FORMS are skipped."""
    settings = _settings(
        tmp_path,
        research_sec_edgar_enabled=True,
        research_sec_edgar_user_agent="test agent",
    )
    provider = SecEdgarSubmissionsProvider(settings=settings)
    meta = provider.metadata()

    from agentic_trader.researchd.providers import _SecTickerMatch

    match = _SecTickerMatch(symbol="AAPL", cik="0000320193", entity_name="Apple Inc.")
    payload = {
        "name": "Apple Inc.",
        "filings": {
            "recent": {
                "accessionNumber": ["0000320193-24-000001", "0000320193-24-000002"],
                "form": ["S-8", "SC 13G"],  # Neither is in SEC_RESEARCH_FORMS
                "filingDate": ["2024-01-01", "2024-02-01"],
                "reportDate": ["", ""],
                "primaryDocument": ["s8.htm", "sc13g.htm"],
                "primaryDocDescription": ["S-8", "SC 13G"],
            }
        },
    }

    records = _records_from_submissions(
        provider=meta,
        symbol="AAPL",
        match=match,
        payload=payload,
        limit=10,
    )

    assert records == []


def test_records_from_submissions_respects_limit(tmp_path) -> None:
    """_records_from_submissions stops collecting at the given limit."""
    settings = _settings(
        tmp_path,
        research_sec_edgar_enabled=True,
        research_sec_edgar_user_agent="test agent",
    )
    provider = SecEdgarSubmissionsProvider(settings=settings)
    meta = provider.metadata()

    from agentic_trader.researchd.providers import _SecTickerMatch

    match = _SecTickerMatch(symbol="AAPL", cik="0000320193", entity_name="Apple Inc.")
    n = 5
    payload = {
        "name": "Apple Inc.",
        "filings": {
            "recent": {
                "accessionNumber": [f"0000320193-24-{i:06d}" for i in range(n)],
                "form": ["10-K"] * n,
                "filingDate": [f"2024-0{i+1}-01" for i in range(n)],
                "reportDate": [f"2024-0{i+1}-01" for i in range(n)],
                "primaryDocument": [f"doc{i}.htm" for i in range(n)],
                "primaryDocDescription": ["10-K"] * n,
            }
        },
    }

    records = _records_from_submissions(
        provider=meta,
        symbol="AAPL",
        match=match,
        payload=payload,
        limit=2,
    )

    assert len(records) == 2


def test_sec_missing_fields_empty_when_all_present() -> None:
    missing = _sec_missing_fields(
        cik="0000320193",
        accession="0000320193-24-000123",
        report_date="2024-09-28",
        primary_document="aapl-20240928.htm",
    )

    assert missing == []


def test_sec_missing_fields_report_date_missing() -> None:
    missing = _sec_missing_fields(
        cik="0000320193",
        accession="0000320193-24-000123",
        report_date="",
        primary_document="aapl-20240928.htm",
    )

    assert "report_date" in missing


def test_sec_missing_fields_primary_document_missing() -> None:
    missing = _sec_missing_fields(
        cik="0000320193",
        accession="0000320193-24-000123",
        report_date="2024-09-28",
        primary_document="",
    )

    assert "primary_document" in missing
    assert "url" in missing  # URL also missing when primary_document is absent


def test_sec_archive_url_formats_correctly() -> None:
    url = _sec_archive_url(
        cik="0000320193",
        accession="0000320193-24-000123",
        primary_document="aapl-20240928.htm",
    )

    assert url is not None
    assert "000032019324000123" in url  # dashes stripped
    assert "320193" in url  # leading zeros stripped for archive path
    assert "aapl-20240928.htm" in url


def test_sec_archive_url_returns_none_when_accession_missing() -> None:
    url = _sec_archive_url(
        cik="0000320193",
        accession="",
        primary_document="aapl-20240928.htm",
    )

    assert url is None


def test_sec_archive_url_returns_none_when_primary_document_missing() -> None:
    url = _sec_archive_url(
        cik="0000320193",
        accession="0000320193-24-000123",
        primary_document="",
    )

    assert url is None


def test_primary_document_note_with_description() -> None:
    note = _primary_document_note("10-K Annual Report")

    assert "10-K Annual Report" in note


def test_primary_document_note_without_description() -> None:
    note = _primary_document_note("")

    assert "missing" in note.lower()


def test_list_value_with_list() -> None:
    assert _list_value(["a", "b"]) == ["a", "b"]


def test_list_value_with_non_list() -> None:
    assert _list_value("not_a_list") == []
    assert _list_value(None) == []
    assert _list_value(42) == []


def test_string_value_with_string() -> None:
    assert _string_value("  hello  ") == "hello"


def test_string_value_with_none() -> None:
    assert _string_value(None) == ""


def test_string_at_within_bounds() -> None:
    assert _string_at(["a", "b", "c"], 1) == "b"


def test_string_at_out_of_bounds() -> None:
    assert _string_at(["a"], 5) == ""


def test_provider_health_message_with_payload() -> None:
    msg = _provider_health_message(has_payload=True, notes=[])

    assert "normalized research evidence" in msg


def test_provider_health_message_provider_disabled() -> None:
    msg = _provider_health_message(has_payload=False, notes=["provider_disabled"])

    assert "disabled" in msg.lower()


def test_provider_health_message_sec_user_agent_missing() -> None:
    msg = _provider_health_message(
        has_payload=False, notes=["sec_user_agent_missing"]
    )

    assert "user-agent" in msg.lower() or "User-Agent" in msg


def test_provider_health_message_provider_error() -> None:
    msg = _provider_health_message(
        has_payload=False, notes=["provider_error:ValueError"]
    )

    assert "failed" in msg.lower()


def test_provider_health_message_ingestion_pending() -> None:
    msg = _provider_health_message(has_payload=False, notes=["ingestion_pending"])

    assert "scaffold" in msg.lower() or "ingestion" in msg.lower()


def test_provider_health_message_generic_fallback() -> None:
    msg = _provider_health_message(has_payload=False, notes=["unknown_note"])

    assert "no normalized" in msg.lower() or "no" in msg.lower()


# ---------------------------------------------------------------------------
# SecEdgarSubmissionsProvider – additional collection edge cases
# ---------------------------------------------------------------------------


def test_sec_edgar_provider_disabled_state_metadata(tmp_path) -> None:
    """Provider metadata reflects disabled/not-network-required when disabled."""
    settings = _settings(tmp_path)  # research_sec_edgar_enabled defaults to False
    provider = SecEdgarSubmissionsProvider(settings=settings)

    meta = provider.metadata()

    assert meta.enabled is False
    assert meta.requires_network is False
    assert "sec_provider_disabled" in meta.notes


def test_sec_edgar_provider_enabled_state_metadata(tmp_path) -> None:
    """Provider metadata reflects enabled/network-required when enabled."""
    settings = _settings(
        tmp_path,
        research_sec_edgar_enabled=True,
        research_sec_edgar_user_agent="Test App contact@example.com",
    )
    provider = SecEdgarSubmissionsProvider(settings=settings)

    meta = provider.metadata()

    assert meta.enabled is True
    assert meta.requires_network is True
    assert "sec_user_agent_configured" in meta.notes


def test_sec_edgar_provider_collect_disabled_returns_missing_reason(tmp_path) -> None:
    """Disabled provider returns provider_disabled missing reason without fetching."""
    settings = _settings(tmp_path)

    def forbidden_fetcher(url, headers, timeout_seconds):
        raise AssertionError("Should not fetch when disabled")

    provider = SecEdgarSubmissionsProvider(settings=settings, fetcher=forbidden_fetcher)
    output = provider.collect(symbols=["AAPL"], limit=5)

    assert output.raw_evidence == []
    assert "provider_disabled" in output.missing_reasons


def test_sec_edgar_provider_collect_empty_symbols_returns_watchlist_missing(
    tmp_path,
) -> None:
    """Enabled provider returns watchlist_missing when given empty symbol list."""
    settings = _settings(
        tmp_path,
        research_sec_edgar_enabled=True,
        research_sec_edgar_user_agent="Test Agent",
    )

    def forbidden_fetcher(url, headers, timeout_seconds):
        raise AssertionError("Should not fetch without symbols")

    provider = SecEdgarSubmissionsProvider(settings=settings, fetcher=forbidden_fetcher)
    output = provider.collect(symbols=[], limit=5)

    assert "watchlist_missing" in output.missing_reasons


def test_sec_edgar_provider_collect_whitespace_only_symbols(tmp_path) -> None:
    """Whitespace-only symbols are filtered out, triggering watchlist_missing."""
    settings = _settings(
        tmp_path,
        research_sec_edgar_enabled=True,
        research_sec_edgar_user_agent="Test Agent",
    )

    def forbidden_fetcher(url, headers, timeout_seconds):
        raise AssertionError("Should not fetch without valid symbols")

    provider = SecEdgarSubmissionsProvider(settings=settings, fetcher=forbidden_fetcher)
    output = provider.collect(symbols=["  ", "\t", ""], limit=5)

    assert "watchlist_missing" in output.missing_reasons


def test_sec_edgar_provider_ticker_lookup_failure(tmp_path) -> None:
    """Provider returns sec_ticker_lookup_failed when ticker fetch raises HTTPError."""
    settings = _settings(
        tmp_path,
        research_sec_edgar_enabled=True,
        research_sec_edgar_user_agent="Test Agent contact@example.com",
    )

    def failing_fetcher(url, headers, timeout_seconds):
        raise httpx.HTTPError("Connection refused")

    provider = SecEdgarSubmissionsProvider(settings=settings, fetcher=failing_fetcher)
    output = provider.collect(symbols=["AAPL"], limit=5)

    assert output.raw_evidence == []
    assert "sec_ticker_lookup_failed" in output.missing_reasons
    assert any("provider_error:" in r for r in output.missing_reasons)


def test_sec_edgar_provider_cik_not_found_in_index(tmp_path) -> None:
    """Provider records sec_cik_missing when symbol is absent from ticker index."""
    settings = _settings(
        tmp_path,
        research_sec_edgar_enabled=True,
        research_sec_edgar_user_agent="Test Agent contact@example.com",
    )

    def ticker_only_fetcher(url, headers, timeout_seconds):
        return {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}

    provider = SecEdgarSubmissionsProvider(
        settings=settings, fetcher=ticker_only_fetcher
    )
    output = provider.collect(symbols=["UNKNOWN_TICKER"], limit=5)

    assert "sec_cik_missing:UNKNOWN_TICKER" in output.missing_reasons
    assert output.raw_evidence == []


def test_sec_edgar_provider_submissions_fetch_failure(tmp_path) -> None:
    """Provider records sec_submissions_fetch_failed when submissions fetch raises."""
    settings = _settings(
        tmp_path,
        research_sec_edgar_enabled=True,
        research_sec_edgar_user_agent="Test Agent contact@example.com",
    )
    calls: list[str] = []

    def partial_fetcher(url, headers, timeout_seconds):
        calls.append(url)
        if "company_tickers" in url:
            return {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}
        raise httpx.HTTPError("submissions endpoint unavailable")

    provider = SecEdgarSubmissionsProvider(settings=settings, fetcher=partial_fetcher)
    output = provider.collect(symbols=["AAPL"], limit=5)

    assert any("sec_submissions_fetch_failed" in r for r in output.missing_reasons)
    assert any("provider_error:" in r for r in output.missing_reasons)
    assert output.raw_evidence == []


def test_sec_edgar_provider_no_target_filings_for_symbol(tmp_path) -> None:
    """Provider records sec_target_filings_missing when no matching forms found."""
    settings = _settings(
        tmp_path,
        research_sec_edgar_enabled=True,
        research_sec_edgar_user_agent="Test Agent contact@example.com",
    )

    def scaffold_only_fetcher(url, headers, timeout_seconds):
        if "company_tickers" in url:
            return {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}
        return {
            "name": "Apple Inc.",
            "filings": {
                "recent": {
                    "accessionNumber": ["0000320193-24-000001"],
                    "form": ["S-8"],  # Not in SEC_RESEARCH_FORMS
                    "filingDate": ["2024-01-01"],
                    "reportDate": [""],
                    "primaryDocument": ["s8.htm"],
                    "primaryDocDescription": ["S-8"],
                }
            },
        }

    provider = SecEdgarSubmissionsProvider(
        settings=settings, fetcher=scaffold_only_fetcher
    )
    output = provider.collect(symbols=["AAPL"], limit=5)

    assert "sec_target_filings_missing:AAPL" in output.missing_reasons
    assert output.raw_evidence == []


def test_sec_edgar_provider_timeout_clamped(tmp_path) -> None:
    """Provider request timeout is clamped to [1.0, 30.0] regardless of settings."""
    settings_high = _settings(tmp_path, request_timeout_seconds=9999.0)
    settings_low = _settings(tmp_path, request_timeout_seconds=0.0)

    provider_high = SecEdgarSubmissionsProvider(settings=settings_high)
    provider_low = SecEdgarSubmissionsProvider(settings=settings_low)

    # Access private attribute to verify clamping behavior
    assert provider_high._timeout == 30.0
    assert provider_low._timeout == 1.0


def test_sec_research_forms_contains_expected_filing_types() -> None:
    """SEC_RESEARCH_FORMS includes the main annual, quarterly, and current form types."""
    assert "10-K" in SEC_RESEARCH_FORMS
    assert "10-Q" in SEC_RESEARCH_FORMS
    assert "8-K" in SEC_RESEARCH_FORMS
    assert "20-F" in SEC_RESEARCH_FORMS
    # Non-research forms are excluded
    assert "S-8" not in SEC_RESEARCH_FORMS
    assert "SC 13G" not in SEC_RESEARCH_FORMS


# ---------------------------------------------------------------------------
# CLI – research-flow-setup and research-crewai-setup render tests
# ---------------------------------------------------------------------------


def test_research_flow_setup_table_output_includes_new_fields(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Table-format research-flow-setup output includes uv, environment, lockfile fields."""
    from typer.testing import CliRunner
    from agentic_trader.cli import app

    settings = _settings(tmp_path)
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)

    runner = CliRunner()
    result = runner.invoke(app, ["research-flow-setup"])

    assert result.exit_code == 0
    assert "uv Available" in result.output
    assert "Environment Exists" in result.output
    assert "Lockfile Exists" in result.output
    assert "Python Version" in result.output


def test_research_crewai_setup_alias_table_output_matches_flow_setup(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """research-crewai-setup table output matches research-flow-setup output."""
    from typer.testing import CliRunner
    from agentic_trader.cli import app

    settings = _settings(tmp_path)
    monkeypatch.setattr("agentic_trader.cli.get_settings", lambda: settings)

    runner = CliRunner()
    flow_result = runner.invoke(app, ["research-flow-setup"])
    alias_result = runner.invoke(app, ["research-crewai-setup"])

    assert flow_result.exit_code == 0
    assert alias_result.exit_code == 0
    # Both should show the same table title
    assert "Research CrewAI Flow Setup" in flow_result.output
    assert "Research CrewAI Flow Setup" in alias_result.output
