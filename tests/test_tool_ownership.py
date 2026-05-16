from pathlib import Path
from typing import Any

import pytest

from agentic_trader.config import Settings
from agentic_trader.system.tool_ownership import (
    ownership_mode_for_tool,
    read_tool_ownership_payload,
    tool_ownership_path,
    validate_ownership_mode,
    write_tool_ownership,
)


def _settings(tmp_path: Path, **overrides: Any) -> Settings:
    settings = Settings(
        runtime_dir=tmp_path,
        database_path=tmp_path / "agentic_trader.duckdb",
        market_data_cache_dir=tmp_path / "market_cache",
        **overrides,
    )
    settings.ensure_directories()
    return settings


def test_tool_ownership_defaults_to_undecided_without_state(tmp_path: Path) -> None:
    settings = _settings(tmp_path)

    payload = read_tool_ownership_payload(settings)

    assert payload.schema_version == "tool-ownership/v1"
    assert [decision.tool for decision in payload.decisions] == [
        "ollama",
        "firecrawl",
        "camofox",
    ]
    assert all(decision.mode == "undecided" for decision in payload.decisions)
    assert ownership_mode_for_tool(settings, "camofox-browser") == "undecided"


def test_write_tool_ownership_persists_owner_only_decisions(tmp_path: Path) -> None:
    settings = _settings(tmp_path)

    payload = write_tool_ownership(
        settings,
        {"ollama": "host-owned", "firecrawl": "api-key-only", "camofox": "app-owned"},
        source="test",
    )

    assert payload.decisions_by_tool["ollama"].mode == "host-owned"
    assert payload.decisions_by_tool["firecrawl"].mode == "api-key-only"
    assert payload.decisions_by_tool["camofox"].mode == "app-owned"
    path = tool_ownership_path(settings)
    assert path.exists()
    assert path.stat().st_mode & 0o777 == 0o600
    assert "secret" not in path.read_text(encoding="utf-8").lower()


def test_write_tool_ownership_can_clear_to_undecided(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    write_tool_ownership(settings, {"ollama": "app-owned"}, source="test")

    payload = write_tool_ownership(settings, {"ollama": "undecided"}, source="test")

    assert payload.decisions_by_tool["ollama"].mode == "undecided"


def test_validate_ownership_mode_rejects_unknown_value() -> None:
    with pytest.raises(ValueError, match="ownership mode"):
        validate_ownership_mode("mine")
