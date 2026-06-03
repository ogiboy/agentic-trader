"""Legacy constant exports for CLI/TUI modules during catalog migration."""

from __future__ import annotations

from typing import cast

from agentic_trader.i18n.ui_text.legacy_fields.db import DB_EXPORT_FIELDS
from agentic_trader.i18n.ui_text.legacy_fields.help import HELP_EXPORT_FIELDS
from agentic_trader.i18n.ui_text.legacy_fields.label import LABEL_EXPORT_FIELDS
from agentic_trader.i18n.ui_text.legacy_fields.launcher import LAUNCHER_EXPORT_FIELDS
from agentic_trader.i18n.ui_text.legacy_fields.menu import MENU_EXPORT_FIELDS
from agentic_trader.i18n.ui_text.legacy_fields.message import MESSAGE_EXPORT_FIELDS
from agentic_trader.i18n.ui_text.legacy_fields.prompt import PROMPT_EXPORT_FIELDS
from agentic_trader.i18n.ui_text.legacy_fields.stage import STAGE_EXPORT_FIELDS
from agentic_trader.i18n.ui_text.legacy_fields.status import STATUS_EXPORT_FIELDS
from agentic_trader.i18n.ui_text.legacy_fields.style import STYLE_EXPORT_FIELDS
from agentic_trader.i18n.ui_text.legacy_fields.title import TITLE_EXPORT_FIELDS
from agentic_trader.i18n.ui_text.legacy_fields.ui import UI_EXPORT_FIELDS
from agentic_trader.i18n.ui_text.locales.en import EN_TEXT

LEGACY_EXPORT_FIELDS: dict[str, str] = {
    **DB_EXPORT_FIELDS,
    **HELP_EXPORT_FIELDS,
    **LABEL_EXPORT_FIELDS,
    **LAUNCHER_EXPORT_FIELDS,
    **MENU_EXPORT_FIELDS,
    **MESSAGE_EXPORT_FIELDS,
    **PROMPT_EXPORT_FIELDS,
    **STAGE_EXPORT_FIELDS,
    **STATUS_EXPORT_FIELDS,
    **STYLE_EXPORT_FIELDS,
    **TITLE_EXPORT_FIELDS,
    **UI_EXPORT_FIELDS,
}
LEGACY_EXPORTS: dict[str, str] = {
    public_name: cast(str, getattr(EN_TEXT, field_name))
    for public_name, field_name in LEGACY_EXPORT_FIELDS.items()
}

__all__ = ("LEGACY_EXPORT_FIELDS", "LEGACY_EXPORTS")
