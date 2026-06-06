from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import typer
from rich.table import Table

from agentic_trader.cli_modules.common import console
from agentic_trader.config import Settings
from agentic_trader.ui_text import (
    SUPPORTED_UI_LOCALES,
    UI_LOCALE_ENV,
    UILocale,
)
from agentic_trader.ui_text import t as ui_t


def parse_ui_locale(locale: str | None) -> UILocale | None:
    """
    Validate and normalize a UI locale string.
    
    Parameters:
        locale (str | None): Locale input to validate; may be None.
    
    Returns:
        UILocale | None: The normalized locale (trimmed and lowercased) if it is one of the supported locales, or `None` when `locale` is `None`.
    
    Raises:
        typer.BadParameter: If `locale` is provided but not one of the supported locales; the error message lists allowed values.
    """
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
    """
    Register a "locale" CLI subcommand on the given Typer application.
    
    The subcommand displays the current UI locale and supported locales, and can persist a new locale when called with --set <locale>. With --json it emits the assembled locale payload as JSON; otherwise it renders a terminal table. The command relies on the provided provider and emitter callables to read/reload settings, persist the locale, locate the env file, and emit JSON.
    """
    @app.command("locale")
    def locale_command(
        set_locale: str | None = typer.Option(
            None,
            "--set",
            help=ui_t("help.locale_persist"),
        ),
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
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
    """
    Render the UI locale settings payload as a formatted table to the console.
    
    Displays a table with the current locale, the list of supported locales, the
    environment variable used for UI locale, and whether the locale value was
    persisted.
    
    Parameters:
        payload (dict[str, object]): Mapping that must include the key `"locale"` whose
            value is displayed as the current locale. Other keys in the mapping are
            ignored by this renderer.
        persisted (bool): Whether the locale value was persisted; shown in the table.
    """
    table = Table(title=ui_t("title.ui_locale"))
    table.add_column(ui_t("label.field"), style=ui_t("style.key_column"))
    table.add_column(ui_t("label.value"))
    table.add_row(ui_t("label.locale"), str(payload["locale"]))
    table.add_row(
        ui_t("label.supported"), ui_t("list.separator").join(SUPPORTED_UI_LOCALES)
    )
    table.add_row(ui_t("label.environment"), UI_LOCALE_ENV)
    table.add_row(ui_t("label.persisted"), str(persisted))
    console.print(table)
