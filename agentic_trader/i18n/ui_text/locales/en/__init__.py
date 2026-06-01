"""Terminal UI text catalog for one locale."""

from __future__ import annotations

from agentic_trader.i18n.ui_text.factory import build_ui_text_catalog
from agentic_trader.i18n.ui_text.locales.en.help import EN_HELP_COPY
from agentic_trader.i18n.ui_text.locales.en.labels import EN_LABELS_COPY
from agentic_trader.i18n.ui_text.locales.en.messages import EN_MESSAGES_COPY
from agentic_trader.i18n.ui_text.locales.en.shell import EN_SHELL_COPY
from agentic_trader.i18n.ui_text.locales.en.titles import EN_TITLES_COPY
from agentic_trader.i18n.ui_text.types import UITextCatalog

EN_TEXT_VALUES: dict[str, str] = {
    **EN_HELP_COPY,
    **EN_LABELS_COPY,
    **EN_MESSAGES_COPY,
    **EN_TITLES_COPY,
    **EN_SHELL_COPY,
}
EN_TEXT: UITextCatalog = build_ui_text_catalog("en", EN_TEXT_VALUES)

__all__ = ("EN_TEXT", "EN_TEXT_VALUES")
