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
    ownership_tool_for_local_tool,
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


def test_normalize_ownership_tool_maps_camofox_browser_alias() -> None:
    assert normalize_ownership_tool("camofox-browser") == "camofox"


def test_normalize_ownership_tool_maps_standard_ids() -> None:
    assert normalize_ownership_tool("ollama") == "ollama"
    assert normalize_ownership_tool("firecrawl") == "firecrawl"
    assert normalize_ownership_tool("camofox") == "camofox"


def test_normalize_ownership_tool_rejects_unknown_id() -> None:
    with pytest.raises(ValueError, match="unknown_tool_ownership_id"):
        normalize_ownership_tool("docker")


def test_ownership_note_returns_distinct_text_for_each_mode() -> None:
    notes = {mode: ownership_note("ollama", mode) for mode in OWNERSHIP_MODES}

    assert len(set(notes.values())) == len(OWNERSHIP_MODES)
    assert "undecided" in notes["undecided"].lower() or "no ownership" in notes["undecided"].lower()
    assert "host-managed" in notes["host-owned"].lower() or "host" in notes["host-owned"].lower()
    assert "app" in notes["app-owned"].lower()
    assert "api" in notes["api-key-only"].lower() or "key" in notes["api-key-only"].lower()
    assert "disabled" in notes["skipped"].lower() or "skip" in notes["skipped"].lower()


def test_ownership_note_has_special_text_for_firecrawl_app_owned() -> None:
    note = ownership_note("firecrawl", "app-owned")

    assert "Firecrawl" in note
    assert "host-owned" in note
    assert "host CLI fallback" in note


def test_ownership_note_for_firecrawl_non_app_owned_uses_generic_text() -> None:
    note_host = ownership_note("firecrawl", "host-owned")
    note_generic = ownership_note("ollama", "host-owned")

    assert note_host == note_generic


def test_ownership_tool_for_local_tool_maps_registry_ids() -> None:
    assert ownership_tool_for_local_tool("ollama") == "ollama"
    assert ownership_tool_for_local_tool("firecrawl") == "firecrawl"
    assert ownership_tool_for_local_tool("camofox") == "camofox"
    assert ownership_tool_for_local_tool("camofox-browser") == "camofox"


def test_write_tool_ownership_merges_partial_updates(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    write_tool_ownership(
        settings,
        {"ollama": "app-owned", "firecrawl": "api-key-only"},
        source="first",
    )

    payload = write_tool_ownership(settings, {"camofox": "skipped"}, source="second")

    assert payload.decisions_by_tool["ollama"].mode == "app-owned"
    assert payload.decisions_by_tool["firecrawl"].mode == "api-key-only"
    assert payload.decisions_by_tool["camofox"].mode == "skipped"


def test_write_tool_ownership_records_source_and_timestamp(tmp_path: Path) -> None:
    settings = _settings(tmp_path)

    payload = write_tool_ownership(settings, {"ollama": "host-owned"}, source="operator-ui")

    decision = payload.decisions_by_tool["ollama"]
    assert decision.source == "operator-ui"
    assert decision.updated_at is not None


def test_read_tool_ownership_handles_malformed_json(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    path = tool_ownership_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not-valid-json", encoding="utf-8")

    payload = read_tool_ownership_payload(settings)

    assert all(d.mode == "undecided" for d in payload.decisions)


def test_read_tool_ownership_handles_non_dict_toplevel_json(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    path = tool_ownership_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(["list", "not", "dict"]), encoding="utf-8")

    payload = read_tool_ownership_payload(settings)

    assert all(d.mode == "undecided" for d in payload.decisions)


def test_read_tool_ownership_ignores_unknown_modes_in_file(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    path = tool_ownership_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({
            "schema_version": "tool-ownership/v1",
            "decisions": {
                "ollama": {"mode": "completely-unknown-mode", "source": "test"},
            },
        }),
        encoding="utf-8",
    )

    payload = read_tool_ownership_payload(settings)

    assert payload.decisions_by_tool["ollama"].mode == "undecided"


def test_read_tool_ownership_preserves_known_modes_from_file(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    write_tool_ownership(
        settings,
        {"ollama": "host-owned", "camofox": "skipped"},
        source="file-test",
    )

    payload = read_tool_ownership_payload(settings)

    assert payload.decisions_by_tool["ollama"].mode == "host-owned"
    assert payload.decisions_by_tool["camofox"].mode == "skipped"
    assert payload.decisions_by_tool["firecrawl"].mode == "undecided"
    assert payload.updated_at is not None


def test_read_tool_ownership_state_path_reflects_settings(tmp_path: Path) -> None:
    settings = _settings(tmp_path)

    payload = read_tool_ownership_payload(settings)

    assert str(tmp_path) in payload.state_path
    assert "tool-ownership.json" in payload.state_path


def test_validate_ownership_mode_accepts_all_valid_modes() -> None:
    for mode in OWNERSHIP_MODES:
        assert validate_ownership_mode(mode) == mode


def test_ownership_mode_for_tool_uses_camofox_browser_alias(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    write_tool_ownership(settings, {"camofox": "app-owned"}, source="test")

    assert ownership_mode_for_tool(settings, "camofox-browser") == "app-owned"
    assert ownership_mode_for_tool(settings, "camofox") == "app-owned"


def test_write_tool_ownership_does_not_store_undecided_in_file(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    write_tool_ownership(settings, {"ollama": "app-owned"}, source="test")

    write_tool_ownership(settings, {"ollama": "undecided"}, source="test")

    raw = json.loads(tool_ownership_path(settings).read_text(encoding="utf-8"))
    assert "ollama" not in raw.get("decisions", {})
