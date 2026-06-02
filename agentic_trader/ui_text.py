"""Shared operator-facing text catalog facade.

New terminal UI code should import ``get_ui_text`` or ``UITextCatalog`` and
receive locale-aware copy from ``agentic_trader.i18n.ui_text``. The uppercase
constants remain for older CLI/TUI call sites while those surfaces migrate to
catalog injection.
"""

from __future__ import annotations

from agentic_trader.i18n.ui_text.catalog import (
    EN_TEXT,
    SUPPORTED_UI_LOCALES,
    TR_TEXT,
    UI_LOCALE_ENV,
    UI_TEXT,
    UILocale,
    UITextCatalog,
    get_ui_text,
    normalize_locale,
)
from agentic_trader.i18n.ui_text.legacy import LEGACY_EXPORTS

_PUBLIC_API = (
    EN_TEXT,
    SUPPORTED_UI_LOCALES,
    TR_TEXT,
    UITextCatalog,
    UILocale,
    UI_TEXT,
    UI_LOCALE_ENV,
    get_ui_text,
    normalize_locale,
)
_PUBLIC_API_NAMES = (
    "EN_TEXT",
    "SUPPORTED_UI_LOCALES",
    "TR_TEXT",
    "UITextCatalog",
    "UILocale",
    "UI_TEXT",
    "UI_LOCALE_ENV",
    "get_ui_text",
    "normalize_locale",
)

globals().update(LEGACY_EXPORTS)
LABEL_MATCHES: str = LEGACY_EXPORTS["LABEL_MATCHES"]
LABEL_MODEL_SERVICE: str = LEGACY_EXPORTS["LABEL_MODEL_SERVICE"]
