import pytest

import agentic_trader
from agentic_trader import ui_text


def test_translation_facade_new_control_room_keys_english() -> None:
    """New title and message keys added in this PR resolve correctly in English."""
    assert ui_text.t("title.control.room", locale="en") == "Agentic Trader Control Room"
    assert ui_text.t("title.live.monitor", locale="en") == "Agentic Trader Live Monitor"
    assert (
        ui_text.t("message.control.room.compact.subtitle", locale="en")
        == "Strict LLM gate, portfolio state, runtime controls."
    )
    full_subtitle = ui_text.t("message.control.room.full.subtitle", locale="en")
    assert full_subtitle.startswith("Strict LLM gate")
    assert "saved preferences" in full_subtitle
    assert "launch controls" in full_subtitle
    assert (
        ui_text.t("message.control.room.closed", locale="en")
        == "Control room closed cleanly."
    )


def test_translation_facade_new_control_room_keys_turkish() -> None:
    """New title and message keys added in this PR resolve correctly in Turkish."""
    assert (
        ui_text.t("title.control.room", locale="tr") == "Agentic Trader Kontrol Odası"
    )
    assert ui_text.t("title.live.monitor", locale="tr") == "Agentic Trader Live Monitor"
    compact = ui_text.t("message.control.room.compact.subtitle", locale="tr")
    assert compact.startswith("Strict LLM kapısı")
    full = ui_text.t("message.control.room.full.subtitle", locale="tr")
    assert full.startswith("Strict LLM kapısı")
    assert "kayıtlı tercihler" in full
    closed = ui_text.t("message.control.room.closed", locale="tr")
    assert closed == "Control room temiz kapandı."
    assert "ı" in closed


@pytest.mark.parametrize(
    ("key", "locale", "expected"),
    (
        ("label.intervention", "tr", "Müdahale"),
        ("label.regions", "tr", "Bölgeler"),
        ("label.sectors", "tr", "Sektörler"),
    ),
)
def test_translation_facade_turkish_label_unicode_corrections(
    key: str, locale: str, expected: str
) -> None:
    """Turkish label corrections from this PR include expected diacritics."""
    assert ui_text.t(key, locale=locale) == expected


def test_catalog_turkish_label_corrections_via_get_ui_text() -> None:
    catalog = ui_text.get_ui_text("tr")

    assert catalog.label_intervention == "Müdahale"
    assert catalog.label_regions == "Bölgeler"
    assert catalog.label_sectors == "Sektörler"


def test_message_text_fields_catalog_has_new_control_room_attributes() -> None:
    catalog = ui_text.get_ui_text("en")
    tr_catalog = ui_text.get_ui_text("tr")

    assert catalog.message_control_room_compact_subtitle
    assert catalog.message_control_room_full_subtitle
    assert tr_catalog.message_control_room_compact_subtitle
    assert tr_catalog.message_control_room_full_subtitle


def test_title_text_fields_catalog_has_new_title_attributes() -> None:
    for locale in ("en", "tr"):
        catalog = ui_text.get_ui_text(locale)
        assert catalog.title_control_room
        assert catalog.title_live_monitor


def test_control_room_full_subtitle_does_not_contain_format_placeholders() -> None:
    en = ui_text.get_ui_text("en")
    tr = ui_text.get_ui_text("tr")

    assert "{" not in en.message_control_room_full_subtitle
    assert "{" not in en.message_control_room_compact_subtitle
    assert "{" not in tr.message_control_room_full_subtitle
    assert "{" not in tr.message_control_room_compact_subtitle


def test_package_version_bumped_to_0_16_0() -> None:
    """Package __version__ was bumped to 0.16.0 in this PR."""
    assert agentic_trader.__version__ == "0.16.1"
