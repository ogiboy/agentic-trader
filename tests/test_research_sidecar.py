from dataclasses import replace
from datetime import UTC, datetime, timedelta
import json
import subprocess

import pytest

from agentic_trader.config import Settings
from agentic_trader.researchd.orchestrator import CrewAiResearchBackend, ResearchSidecar
from agentic_trader.researchd.persistence import persist_research_result
from agentic_trader.researchd.providers import (
    SecEdgarSubmissionsProvider,
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


def test_crewai_backend_uses_subprocess_contract_without_core_imports(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("AGENTIC_TRADER_ALPACA_SECRET_KEY", "broker-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "model-secret")
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
        captured["broker_secret"] = env.get("AGENTIC_TRADER_ALPACA_SECRET_KEY")
        captured["model_secret"] = env.get("OPENAI_API_KEY")
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
    assert captured["broker_secret"] is None
    assert captured["model_secret"] == "model-secret"
    request = captured["request"]
    assert isinstance(request, dict)
    assert request["symbols"] == ["AAPL"]
    provider_outputs = request["provider_outputs"]
    assert isinstance(provider_outputs, list)
    assert provider_outputs[0]["metadata"]["provider_id"] == "sec_edgar_research"


def test_crewai_backend_redacts_non_json_process_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "secret-openai")
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

    def fake_runner(
        command: list[str],
        stdin_payload: str,
        cwd,
        env: dict[str, str],
        timeout_seconds: float,
    ) -> subprocess.CompletedProcess[str]:
        _ = (stdin_payload, cwd, env, timeout_seconds)
        return subprocess.CompletedProcess(
            command,
            0,
            "OPENAI_API_KEY=secret-openai",
            "Authorization: Bearer abc.def",
        )

    backend = CrewAiResearchBackend(
        flow_dir=flow_dir,
        uv_path="uv",
        command_runner=fake_runner,
    )

    result = ResearchSidecar(settings, backend=backend).collect_once()

    assert result.state.status == "failed"
    assert result.state.last_error is not None
    assert "secret-openai" not in result.state.last_error
    assert "abc.def" not in result.state.last_error
    assert "<redacted>" in result.state.last_error


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
        assert timeout_seconds == pytest.approx(30.0)
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
    assert record.source_attributions[0].confidence == pytest.approx(0.95)
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
