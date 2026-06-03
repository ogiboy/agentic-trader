"""Typed terminal UI text catalog shared by CLI and TUI surfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from agentic_trader.i18n.ui_text.type_fields.core import CoreTextFields
from agentic_trader.i18n.ui_text.type_fields.db import DatabaseTextFields
from agentic_trader.i18n.ui_text.type_fields.help import HelpTextFields
from agentic_trader.i18n.ui_text.type_fields.label import LabelTextFields
from agentic_trader.i18n.ui_text.type_fields.launcher import LauncherTextFields
from agentic_trader.i18n.ui_text.type_fields.menu import MenuTextFields
from agentic_trader.i18n.ui_text.type_fields.message import MessageTextFields
from agentic_trader.i18n.ui_text.type_fields.prompt import PromptTextFields
from agentic_trader.i18n.ui_text.type_fields.stage import StageTextFields
from agentic_trader.i18n.ui_text.type_fields.status import StatusTextFields
from agentic_trader.i18n.ui_text.type_fields.style import StyleTextFields
from agentic_trader.i18n.ui_text.type_fields.title import TitleTextFields

UILocale = Literal["en", "tr"]
SUPPORTED_UI_LOCALES: tuple[UILocale, ...] = ("en", "tr")


@dataclass(frozen=True)
class UITextCatalog(
    TitleTextFields,
    StyleTextFields,
    StatusTextFields,
    StageTextFields,
    PromptTextFields,
    MessageTextFields,
    MenuTextFields,
    LauncherTextFields,
    LabelTextFields,
    HelpTextFields,
    DatabaseTextFields,
    CoreTextFields,
):
    """Operator-facing copy shared by terminal and Python UI surfaces."""


__all__ = ("SUPPORTED_UI_LOCALES", "UITextCatalog", "UILocale")
