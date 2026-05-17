"""Tests for Firecrawl CLI fallback ownership enforcement.

The PR added an ownership gate to FirecrawlNewsResearchProvider._cli_symbol_records:
the host CLI fallback is disabled unless the persisted ownership mode is 'host-owned'.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from agentic_trader.config import Settings
from agentic_trader.researchd import providers as researchd_providers
from agentic_trader.researchd.providers import FirecrawlNewsResearchProvider
from agentic_trader.system.tool_ownership import write_tool_ownership


def _settings(tmp_path: Path, **overrides: Any) -> Settings:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        market_data_cache_dir=tmp_path / "market_cache",
        research_firecrawl_enabled=True,
        **overrides,
    )
    settings.ensure_directories()
    return settings


def _make_provider(settings: Settings) -> FirecrawlNewsResearchProvider:
    return FirecrawlNewsResearchProvider(settings=settings)


def test_firecrawl_cli_fallback_disabled_when_undecided(tmp_path: Path) -> None:
    """CLI fallback is disabled by default (undecided ownership)."""
    settings = _settings(tmp_path)
    provider = _make_provider(settings)

    records, notes = provider._cli_symbol_records(symbol="AAPL", per_symbol_limit=5)

    assert records == []
    assert any("firecrawl_cli_fallback_disabled" in note for note in notes)
    assert any("undecided" in note for note in notes)


def test_firecrawl_cli_fallback_disabled_when_api_key_only(tmp_path: Path) -> None:
    """CLI fallback is disabled when ownership is api-key-only."""
    settings = _settings(tmp_path)
    write_tool_ownership(settings, {"firecrawl": "api-key-only"}, source="test")
    provider = _make_provider(settings)

    records, notes = provider._cli_symbol_records(symbol="TSLA", per_symbol_limit=5)

    assert records == []
    assert any("firecrawl_cli_fallback_disabled" in note for note in notes)
    assert any("api-key-only" in note for note in notes)


def test_firecrawl_cli_fallback_disabled_when_skipped(tmp_path: Path) -> None:
    """CLI fallback is disabled when ownership is skipped."""
    settings = _settings(tmp_path)
    write_tool_ownership(settings, {"firecrawl": "skipped"}, source="test")
    provider = _make_provider(settings)

    records, notes = provider._cli_symbol_records(symbol="NVDA", per_symbol_limit=5)

    assert records == []
    assert any("firecrawl_cli_fallback_disabled" in note for note in notes)
    assert any("skipped" in note for note in notes)


def test_firecrawl_cli_fallback_disabled_when_app_owned(tmp_path: Path) -> None:
    """CLI fallback is disabled even for app-owned mode (only host-owned enables it)."""
    settings = _settings(tmp_path)
    write_tool_ownership(settings, {"firecrawl": "app-owned"}, source="test")
    provider = _make_provider(settings)

    records, notes = provider._cli_symbol_records(symbol="MSFT", per_symbol_limit=5)

    assert records == []
    assert any("firecrawl_cli_fallback_disabled" in note for note in notes)
    assert any("app-owned" in note for note in notes)


def test_firecrawl_cli_fallback_proceeds_when_host_owned_but_cli_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When ownership is host-owned, the CLI path is attempted; missing CLI returns cli_missing."""
    settings = _settings(tmp_path)
    write_tool_ownership(settings, {"firecrawl": "host-owned"}, source="test")

    monkeypatch.setattr(researchd_providers.shutil, "which", lambda _name: None)

    provider = _make_provider(settings)

    records, notes = provider._cli_symbol_records(symbol="GOOG", per_symbol_limit=5)

    assert records == []
    assert any("firecrawl_cli_missing" in note for note in notes)
    assert not any("firecrawl_cli_fallback_disabled" in note for note in notes)


def test_firecrawl_provider_metadata_reflects_ownership_mode(tmp_path: Path) -> None:
    """Provider metadata notes should reflect the current ownership mode."""
    settings = _settings(tmp_path)
    write_tool_ownership(settings, {"firecrawl": "host-owned"}, source="test")
    provider = _make_provider(settings)
    meta = provider.metadata()

    assert "ownership=host-owned" in meta.notes
    assert "host_cli_fallback_enabled" in meta.notes
    assert "host_cli_fallback_disabled" not in meta.notes


def test_firecrawl_provider_metadata_cli_disabled_when_not_host_owned(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    write_tool_ownership(settings, {"firecrawl": "api-key-only"}, source="test")
    provider = _make_provider(settings)
    meta = provider.metadata()

    assert "ownership=api-key-only" in meta.notes
    assert "host_cli_fallback_disabled" in meta.notes
    assert "host_cli_fallback_enabled" not in meta.notes
