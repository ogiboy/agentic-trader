"""Namespace-key translation helpers for terminal UI text."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final

from agentic_trader.i18n.ui_text.catalog import get_ui_text
from agentic_trader.i18n.ui_text.types import UITextCatalog

CATEGORY_PREFIXES: Final[frozenset[str]] = frozenset(
    {
        "db",
        "help",
        "label",
        "launcher",
        "menu",
        "message",
        "prompt",
        "stage",
        "status",
        "style",
        "title",
        "ui",
    }
)
DOMAIN_DEFAULT_PREFIXES: Final[tuple[str, ...]] = (
    "message",
    "title",
    "label",
    "status",
    "help",
    "prompt",
    "menu",
    "stage",
)


class MissingUITranslationError(KeyError):
    """Raised when a namespace key cannot be resolved in the UI text catalog."""


class UITranslationFormatError(ValueError):
    """Raised when a UI text template cannot be formatted with provided values."""


def _normalize_key_parts(key: str) -> tuple[str, ...]:
    parts = tuple(part.strip().replace("-", "_") for part in key.split("."))
    normalized = tuple(part for part in parts if part)
    if not normalized:
        raise MissingUITranslationError("UI translation key is empty")
    return normalized


def _unique(candidates: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in seen:
            ordered.append(candidate)
            seen.add(candidate)
    return tuple(ordered)


def candidate_field_names(key: str) -> tuple[str, ...]:
    """Return catalog field candidates for a dotted translation key."""

    parts = list(_normalize_key_parts(key))
    if not parts:
        raise MissingUITranslationError("UI translation key is empty")
    direct = "_".join(parts)
    stripped_namespace = "_".join(parts[1:]) if len(parts) > 1 else ""
    candidates: list[str] = [direct, stripped_namespace]
    if parts[-1] in CATEGORY_PREFIXES and len(parts) > 1:
        candidates.append("_".join((parts[-1], *parts[:-1])))
    for prefix in DOMAIN_DEFAULT_PREFIXES:
        candidates.append(f"{prefix}_{direct}")
        if stripped_namespace:
            candidates.append(f"{prefix}_{stripped_namespace}")
    return _unique(candidates)


def resolve_translation_field(key: str, catalog: UITextCatalog | None = None) -> str:
    """Resolve a dotted translation key to a concrete catalog field name."""

    resolved_catalog = catalog or get_ui_text()
    for field_name in candidate_field_names(key):
        if hasattr(resolved_catalog, field_name):
            return field_name
    raise MissingUITranslationError(
        f"Unknown UI translation key {key!r}; tried "
        f"{', '.join(candidate_field_names(key))}"
    )


def t(
    key: str,
    *,
    locale: str | None = None,
    catalog: UITextCatalog | None = None,
    **values: object,
) -> str:
    """Translate a dotted terminal UI key and format it when values are provided."""

    resolved_catalog = catalog or get_ui_text(locale)
    field_name = resolve_translation_field(key, resolved_catalog)
    template = getattr(resolved_catalog, field_name)
    if not isinstance(template, str):
        raise MissingUITranslationError(
            f"UI translation key {key!r} resolved to non-string field {field_name!r}"
        )
    if not values:
        return template
    try:
        return template.format(**values)
    except (IndexError, KeyError, ValueError) as exc:
        raise UITranslationFormatError(
            f"Could not format UI translation key {key!r}"
        ) from exc


translate = t


__all__ = (
    "MissingUITranslationError",
    "UITranslationFormatError",
    "candidate_field_names",
    "resolve_translation_field",
    "t",
    "translate",
)
