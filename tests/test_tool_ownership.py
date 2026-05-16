import json
from pathlib import Path
from typing import Any

import pytest

from agentic_trader.config import Settings
from agentic_trader.system.tool_ownership import (
    OWNERSHIP_MODES,
    normalize_ownership_tool,
    ownership_mode_for_tool,
    ownership_note,
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


def test_validate_ownership_mode_accepts_all_valid_modes() -> None:
    for mode in OWNERSHIP_MODES:
        assert validate_ownership_mode(mode) == mode


def test_normalize_ownership_tool_maps_camofox_browser_alias() -> None:
    assert normalize_ownership_tool("camofox-browser") == "camofox"


def test_normalize_ownership_tool_passes_through_known_ids() -> None:
    assert normalize_ownership_tool("ollama") == "ollama"
    assert normalize_ownership_tool("firecrawl") == "firecrawl"
    assert normalize_ownership_tool("camofox") == "camofox"


def test_normalize_ownership_tool_rejects_unknown_id() -> None:
    with pytest.raises(ValueError, match="unknown_tool_ownership_id"):
        normalize_ownership_tool("docker")


def test_ownership_note_returns_non_empty_string_for_all_modes() -> None:
    tools = ("ollama", "firecrawl", "camofox")
    modes = ("undecided", "host-owned", "app-owned", "api-key-only", "skipped")
    for tool in tools:
        for mode in modes:
            note = ownership_note(tool, mode)  # type: ignore[arg-type]
            assert isinstance(note, str) and note.strip()


def test_ownership_note_returns_special_firecrawl_app_owned_note() -> None:
    note = ownership_note("firecrawl", "app-owned")
    assert "host CLI fallback" in note
    assert "host-owned" in note


def test_ownership_note_returns_generic_app_owned_for_non_firecrawl() -> None:
    note = ownership_note("ollama", "app-owned")
    assert "app may manage" in note.lower() or "explicit lifecycle" in note.lower() or "app-owned" in note.lower()


def test_read_tool_ownership_payload_with_malformed_json_returns_defaults(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    state_path = tool_ownership_path(settings)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text("{not valid json", encoding="utf-8")

    payload = read_tool_ownership_payload(settings)

    assert all(decision.mode == "undecided" for decision in payload.decisions)


def test_read_tool_ownership_payload_preserves_updated_at_from_file(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    state_path = tool_ownership_path(settings)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    stored = {
        "schema_version": "tool-ownership/v1",
        "updated_at": "2025-01-15T12:00:00+00:00",
        "decisions": {
            "ollama": {"mode": "app-owned", "source": "cli"},
        },
    }
    state_path.write_text(json.dumps(stored), encoding="utf-8")
    import os
    os.chmod(state_path, 0o600)

    payload = read_tool_ownership_payload(settings)

    assert payload.updated_at == "2025-01-15T12:00:00+00:00"
    assert payload.decisions_by_tool["ollama"].mode == "app-owned"
    assert payload.decisions_by_tool["ollama"].source == "cli"
    assert payload.decisions_by_tool["firecrawl"].mode == "undecided"
    assert payload.decisions_by_tool["camofox"].mode == "undecided"


def test_read_tool_ownership_payload_falls_back_invalid_mode_to_undecided(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    state_path = tool_ownership_path(settings)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    stored = {
        "schema_version": "tool-ownership/v1",
        "updated_at": "2025-01-15T12:00:00+00:00",
        "decisions": {
            "ollama": {"mode": "not-a-valid-mode", "source": "cli"},
        },
    }
    state_path.write_text(json.dumps(stored), encoding="utf-8")
    import os
    os.chmod(state_path, 0o600)

    payload = read_tool_ownership_payload(settings)

    assert payload.decisions_by_tool["ollama"].mode == "undecided"


def test_read_tool_ownership_payload_handles_non_dict_record(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    state_path = tool_ownership_path(settings)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    stored = {
        "schema_version": "tool-ownership/v1",
        "decisions": {
            "ollama": "not-a-dict",
        },
    }
    state_path.write_text(json.dumps(stored), encoding="utf-8")
    import os
    os.chmod(state_path, 0o600)

    payload = read_tool_ownership_payload(settings)

    assert payload.decisions_by_tool["ollama"].mode == "undecided"


def test_write_tool_ownership_preserves_unrelated_decisions_during_partial_update(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    write_tool_ownership(
        settings,
        {"ollama": "host-owned", "firecrawl": "api-key-only"},
        source="initial",
    )

    updated = write_tool_ownership(settings, {"camofox": "app-owned"}, source="update")

    assert updated.decisions_by_tool["ollama"].mode == "host-owned"
    assert updated.decisions_by_tool["firecrawl"].mode == "api-key-only"
    assert updated.decisions_by_tool["camofox"].mode == "app-owned"


def test_write_tool_ownership_records_source_in_file(tmp_path: Path) -> None:
    settings = _settings(tmp_path)

    write_tool_ownership(settings, {"ollama": "app-owned"}, source="webgui")

    raw = json.loads(tool_ownership_path(settings).read_text(encoding="utf-8"))
    assert raw["decisions"]["ollama"]["source"] == "webgui"


def test_write_tool_ownership_undecided_removes_tool_from_file(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    write_tool_ownership(settings, {"ollama": "host-owned"}, source="test")

    write_tool_ownership(settings, {"ollama": "undecided"}, source="test")

    raw = json.loads(tool_ownership_path(settings).read_text(encoding="utf-8"))
    assert "ollama" not in raw["decisions"]


def test_ownership_mode_for_tool_uses_camofox_browser_alias(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    write_tool_ownership(settings, {"camofox": "app-owned"}, source="test")

    assert ownership_mode_for_tool(settings, "camofox-browser") == "app-owned"


def test_ownership_mode_for_tool_returns_undecided_without_file(tmp_path: Path) -> None:
    settings = _settings(tmp_path)

    assert ownership_mode_for_tool(settings, "ollama") == "undecided"
    assert ownership_mode_for_tool(settings, "firecrawl") == "undecided"
    assert ownership_mode_for_tool(settings, "camofox") == "undecided"
