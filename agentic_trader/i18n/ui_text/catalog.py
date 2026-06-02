"""Locale selection for terminal UI text catalogs."""

from __future__ import annotations

import os

from agentic_trader.i18n.ui_text.locales.en import EN_TEXT
from agentic_trader.i18n.ui_text.locales.tr import TR_TEXT
from agentic_trader.i18n.ui_text.types import (
    SUPPORTED_UI_LOCALES,
    UILocale,
    UITextCatalog,
)

UI_LOCALE_ENV = "AGENTIC_TRADER_UI_LOCALE"
UI_TEXT: dict[UILocale, UITextCatalog] = {
    "en": EN_TEXT,
    "tr": TR_TEXT,
}


def normalize_locale(locale: str | None) -> UILocale:
    """Normalize a locale-ish value to one of the supported UI locales."""

    if not locale:
        return "en"
    normalized = locale.lower()
    if normalized == "tr" or normalized.startswith("tr-"):
        return "tr"
    return "en"


def get_ui_text(locale: str | None = None) -> UITextCatalog:
    """Return the shared UI copy catalog for the requested locale."""

    requested_locale = locale if locale is not None else os.environ.get(UI_LOCALE_ENV)
    return UI_TEXT[normalize_locale(requested_locale)]


__all__ = (
    "EN_TEXT",
    "SUPPORTED_UI_LOCALES",
    "TR_TEXT",
    "UI_LOCALE_ENV",
    "UITextCatalog",
    "UILocale",
    "UI_TEXT",
    "get_ui_text",
    "normalize_locale",
)
