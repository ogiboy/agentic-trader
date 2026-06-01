"""Terminal UI text catalog for one locale."""

from __future__ import annotations

from agentic_trader.i18n.ui_text.factory import build_ui_text_catalog
from agentic_trader.i18n.ui_text.locales.tr.help import TR_HELP_COPY
from agentic_trader.i18n.ui_text.locales.tr.labels import TR_LABELS_COPY
from agentic_trader.i18n.ui_text.locales.tr.messages import TR_MESSAGES_COPY
from agentic_trader.i18n.ui_text.locales.tr.shell import TR_SHELL_COPY
from agentic_trader.i18n.ui_text.locales.tr.titles import TR_TITLES_COPY
from agentic_trader.i18n.ui_text.types import UITextCatalog

TR_TEXT_VALUES: dict[str, str] = {
    **TR_HELP_COPY,
    **TR_LABELS_COPY,
    **TR_MESSAGES_COPY,
    **TR_TITLES_COPY,
    **TR_SHELL_COPY,
}
TR_TEXT: UITextCatalog = build_ui_text_catalog("tr", TR_TEXT_VALUES)

__all__ = ("TR_TEXT", "TR_TEXT_VALUES")
