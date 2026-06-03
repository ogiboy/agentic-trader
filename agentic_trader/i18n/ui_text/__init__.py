"""Terminal UI i18n catalog modules."""

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
from agentic_trader.i18n.ui_text.translator import (
    MissingUITranslationError,
    UITranslationFormatError,
    candidate_field_names,
    resolve_translation_field,
    t,
    translate,
)

__all__ = (
    "EN_TEXT",
    "SUPPORTED_UI_LOCALES",
    "TR_TEXT",
    "UI_LOCALE_ENV",
    "MissingUITranslationError",
    "UITranslationFormatError",
    "UITextCatalog",
    "UILocale",
    "UI_TEXT",
    "candidate_field_names",
    "get_ui_text",
    "normalize_locale",
    "resolve_translation_field",
    "t",
    "translate",
)
