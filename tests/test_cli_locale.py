"""Tests for CLI locale helper functions added in the modularity/i18n track."""

from __future__ import annotations

from pathlib import Path

import pytest
import typer

import agentic_trader.cli as cli_module
from agentic_trader.cli import (
    UI_LOCALE_ENV,
    parse_ui_locale,
    ui_payload,
    upsert_env_local_value,
)
from agentic_trader.ui_text import SUPPORTED_UI_LOCALES


# ---------------------------------------------------------------------------
# parse_ui_locale
# ---------------------------------------------------------------------------


def test_parse_ui_locale_returns_none_for_none_input() -> None:
    assert parse_ui_locale(None) is None


def test_parse_ui_locale_accepts_english() -> None:
    assert parse_ui_locale("en") == "en"


def test_parse_ui_locale_accepts_turkish() -> None:
    assert parse_ui_locale("tr") == "tr"


def test_parse_ui_locale_normalizes_to_lowercase() -> None:
    assert parse_ui_locale("EN") == "en"
    assert parse_ui_locale("TR") == "tr"


def test_parse_ui_locale_strips_surrounding_whitespace() -> None:
    assert parse_ui_locale("  en  ") == "en"
    assert parse_ui_locale("\ttr\n") == "tr"


def test_parse_ui_locale_raises_bad_parameter_for_unsupported_locale() -> None:
    with pytest.raises(typer.BadParameter, match="Locale must be one of"):
        parse_ui_locale("de")


def test_parse_ui_locale_raises_bad_parameter_for_unknown_locale() -> None:
    with pytest.raises(typer.BadParameter, match="Locale must be one of"):
        parse_ui_locale("fr-FR")


def test_parse_ui_locale_error_message_lists_supported_locales() -> None:
    try:
        parse_ui_locale("xx")
    except typer.BadParameter as exc:
        for locale in SUPPORTED_UI_LOCALES:
            assert locale in str(exc)
    else:
        raise AssertionError("expected BadParameter for unknown locale")


def test_parse_ui_locale_raises_for_empty_string() -> None:
    # Empty string after strip is not in SUPPORTED_UI_LOCALES
    with pytest.raises(typer.BadParameter):
        parse_ui_locale("")


def test_parse_ui_locale_accepts_all_supported_locales() -> None:
    for locale in SUPPORTED_UI_LOCALES:
        result = parse_ui_locale(locale)
        assert result == locale


# ---------------------------------------------------------------------------
# ui_payload
# ---------------------------------------------------------------------------


def test_ui_payload_contains_locale_key() -> None:
    payload = ui_payload("en")

    assert payload["locale"] == "en"


def test_ui_payload_contains_supported_locales_list() -> None:
    payload = ui_payload("en")

    assert isinstance(payload["supported_locales"], list)
    assert set(payload["supported_locales"]) == set(SUPPORTED_UI_LOCALES)  # type: ignore[arg-type]


def test_ui_payload_contains_env_key() -> None:
    payload = ui_payload("en")

    assert payload["env"] == UI_LOCALE_ENV


def test_ui_payload_env_key_is_correct_env_var_name() -> None:
    payload = ui_payload("tr")

    assert payload["env"] == "AGENTIC_TRADER_UI_LOCALE"


def test_ui_payload_reflects_passed_locale() -> None:
    en_payload = ui_payload("en")
    tr_payload = ui_payload("tr")

    assert en_payload["locale"] == "en"
    assert tr_payload["locale"] == "tr"


def test_ui_payload_supported_locales_includes_en_and_tr() -> None:
    payload = ui_payload("en")
    locales = payload["supported_locales"]

    assert "en" in locales  # type: ignore[operator]
    assert "tr" in locales  # type: ignore[operator]


# ---------------------------------------------------------------------------
# UI_LOCALE_ENV constant
# ---------------------------------------------------------------------------


def test_ui_locale_env_constant_value() -> None:
    assert UI_LOCALE_ENV == "AGENTIC_TRADER_UI_LOCALE"


# ---------------------------------------------------------------------------
# upsert_env_local_value
# ---------------------------------------------------------------------------


def test_upsert_env_local_value_creates_file_if_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env.local"
    monkeypatch.setattr(cli_module, "ENV_LOCAL_FILE", env_file)

    upsert_env_local_value("AGENTIC_TRADER_UI_LOCALE", "tr")

    assert env_file.exists()
    content = env_file.read_text(encoding="utf-8")
    assert "AGENTIC_TRADER_UI_LOCALE" in content
    assert "tr" in content


def test_upsert_env_local_value_writes_without_quotes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env.local"
    monkeypatch.setattr(cli_module, "ENV_LOCAL_FILE", env_file)

    upsert_env_local_value("SOME_KEY", "some_value")

    content = env_file.read_text(encoding="utf-8")
    # quote_mode="never" means the value is stored without surrounding quotes
    assert '"some_value"' not in content
    assert "'some_value'" not in content
    assert "some_value" in content


def test_upsert_env_local_value_updates_existing_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env.local"
    env_file.write_text("AGENTIC_TRADER_UI_LOCALE=en\n", encoding="utf-8")
    monkeypatch.setattr(cli_module, "ENV_LOCAL_FILE", env_file)

    upsert_env_local_value("AGENTIC_TRADER_UI_LOCALE", "tr")

    content = env_file.read_text(encoding="utf-8")
    assert "tr" in content
    # Should not have duplicate entries with the old value appearing as a key
    lines_with_key = [
        line for line in content.splitlines() if line.startswith("AGENTIC_TRADER_UI_LOCALE=")
    ]
    assert len(lines_with_key) == 1
    assert lines_with_key[0] == "AGENTIC_TRADER_UI_LOCALE=tr"


def test_upsert_env_local_value_preserves_other_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env.local"
    env_file.write_text("EXISTING_KEY=existing_value\n", encoding="utf-8")
    monkeypatch.setattr(cli_module, "ENV_LOCAL_FILE", env_file)

    upsert_env_local_value("NEW_KEY", "new_value")

    content = env_file.read_text(encoding="utf-8")
    assert "EXISTING_KEY=existing_value" in content
    assert "new_value" in content
