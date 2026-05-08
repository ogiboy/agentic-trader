from pathlib import Path
from typing import Any, cast

from agentic_trader.config import Settings
from agentic_trader.researchd.cycle_runner import run_research_cycle
from agentic_trader.runtime_feed import research_latest_snapshot_path


def _settings(tmp_path: Path, **overrides: Any) -> Settings:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        research_mode="training",
        research_sidecar_enabled=True,
        **overrides,
    )
    settings.ensure_directories()
    return settings


def test_research_cycle_run_persists_bounded_evidence_only_snapshot(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)

    payload = run_research_cycle(
        settings,
        symbols=["aapl", "MSFT"],
        cycles=2,
        cadence_seconds=1,
        persist=True,
        sleep_between_cycles=False,
    )

    assert payload["executed_cycles"] == 2
    execution_policy = cast(dict[str, object], payload["execution_policy"])
    assert execution_policy["broker_access"] is False
    assert execution_policy["proposal_approval"] is False
    assert execution_policy["raw_web_text_in_core_prompt"] is False
    executions = cast(list[dict[str, object]], payload["executions"])
    assert isinstance(executions, list)
    assert executions[0]["watched_symbols"] == ["AAPL", "MSFT"]
    assert executions[0]["persisted_snapshot_id"]
    assert research_latest_snapshot_path(settings).exists()
    assert settings.database_path.exists() is False


def test_research_cycle_run_fails_closed_without_symbols(tmp_path: Path) -> None:
    settings = _settings(tmp_path)

    try:
        run_research_cycle(settings, symbols=[" ", ""], sleep_between_cycles=False)
    except ValueError as exc:
        assert "symbols must contain" in str(exc)
    else:
        raise AssertionError("empty research cycle symbols should fail closed")
