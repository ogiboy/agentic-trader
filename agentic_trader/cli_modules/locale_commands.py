# pyright: reportUnusedFunction=false
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import typer
from rich.table import Table

from agentic_trader.cli_modules.common import console
from agentic_trader.config import Settings
from agentic_trader.ui_text import (
    HELP_JSON,
    HELP_LOCALE_PERSIST,
    LABEL_ENVIRONMENT,
    LABEL_FIELD,
    LABEL_LOCALE,
    LABEL_PERSISTED,
    LABEL_SUPPORTED,
    LABEL_VALUE,
    STYLE_KEY_COLUMN,
    SUPPORTED_UI_LOCALES,
    TITLE_UI_LOCALE,
    UI_LIST_SEPARATOR,
    UI_LOCALE_ENV,
    UILocale,
)


def parse_ui_locale(locale: str | None) -> UILocale | None:
    if locale is None:
        return None
    normalized = locale.strip().lower()
    if normalized in SUPPORTED_UI_LOCALES:
        return normalized
    allowed = ", ".join(SUPPORTED_UI_LOCALES)
    raise typer.BadParameter(f"Locale must be one of: {allowed}.")


def ui_payload(locale: str) -> dict[str, object]:
    return {
        "locale": locale,
        "supported_locales": list(SUPPORTED_UI_LOCALES),
        "env": UI_LOCALE_ENV,
    }


PersistLocale = Callable[[str, str], None]
SettingsProvider = Callable[[], Settings]
EmitJson = Callable[[object], None]
EnvFileProvider = Callable[[], Path]


def register_locale_command(
    app: typer.Typer,
    *,
    settings_provider: SettingsProvider,
    fresh_settings_provider: SettingsProvider,
    persist_locale: PersistLocale,
    env_file_provider: EnvFileProvider,
    emit_json: EmitJson,
) -> None:
    @app.command("locale")
    def locale_command(
        set_locale: str | None = typer.Option(
            None,
            "--set",
            help=HELP_LOCALE_PERSIST,
        ),
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    ) -> None:
        """Show or persist the terminal UI locale."""
        settings = settings_provider()
        persisted = False
        selected_locale = parse_ui_locale(set_locale)
        if selected_locale is not None:
            persist_locale(UI_LOCALE_ENV, selected_locale)
            settings = fresh_settings_provider()
            persisted = True

        payload = {
            **ui_payload(settings.ui_locale),
            "persisted": persisted,
            "env_file": str(env_file_provider().name),
        }
        if json_output:
            emit_json(payload)
            return
        _render_locale_payload(payload, persisted=persisted)


def _render_locale_payload(payload: dict[str, object], *, persisted: bool) -> None:
    table = Table(title=TITLE_UI_LOCALE)
    table.add_column(LABEL_FIELD, style=STYLE_KEY_COLUMN)
    table.add_column(LABEL_VALUE)
    table.add_row(LABEL_LOCALE, str(payload["locale"]))
    table.add_row(LABEL_SUPPORTED, UI_LIST_SEPARATOR.join(SUPPORTED_UI_LOCALES))
    table.add_row(LABEL_ENVIRONMENT, UI_LOCALE_ENV)
    table.add_row(LABEL_PERSISTED, str(persisted))
    console.print(table)
