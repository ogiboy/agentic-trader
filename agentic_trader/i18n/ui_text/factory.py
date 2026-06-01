"""Validated construction helpers for terminal UI text catalogs."""

from __future__ import annotations

from dataclasses import fields
from typing import Any, Mapping, cast

from agentic_trader.i18n.ui_text.types import UITextCatalog

TEXT_CATALOG_FIELDS: tuple[str, ...] = tuple(
    field.name for field in fields(UITextCatalog)
)
TEXT_CATALOG_FIELD_SET: frozenset[str] = frozenset(TEXT_CATALOG_FIELDS)


def build_ui_text_catalog(locale: str, values: Mapping[str, str]) -> UITextCatalog:
    """Build a typed catalog and fail fast when a locale drifts."""

    value_keys = frozenset(values)
    missing = sorted(TEXT_CATALOG_FIELD_SET - value_keys)
    extra = sorted(value_keys - TEXT_CATALOG_FIELD_SET)
    if missing or extra:
        details: list[str] = []
        if missing:
            details.append(f"missing={missing}")
        if extra:
            details.append(f"extra={extra}")
        raise ValueError(f"{locale} UI text catalog mismatch: {'; '.join(details)}")
    return UITextCatalog(**cast("dict[str, Any]", dict(values)))
