from dataclasses import replace
from datetime import UTC, datetime, timedelta

from agentic_trader.config import Settings
from agentic_trader.researchd.orchestrator import ResearchSidecar
from agentic_trader.researchd.persistence import persist_research_result
from agentic_trader.researchd.providers import (
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


def test_crewai_backend_is_isolated_and_non_runtime(tmp_path) -> None:
    settings = _settings(
        tmp_path,
        research_mode="training",
        research_sidecar_enabled=True,
        research_sidecar_backend="crewai",
        research_symbols="AAPL",
    )

    result = ResearchSidecar(settings).collect_once()

    assert result.state.backend == "crewai"
    assert result.state.status == "failed"
    assert "not implemented" in str(result.state.last_error)
    assert result.world_state is None
    assert result.raw_evidence == []


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
    assert health.source_role == "missing"
    assert health.freshness == "missing"
    assert "ingestion_pending" in health.notes
    assert "Provider scaffold is visible" in health.message


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
