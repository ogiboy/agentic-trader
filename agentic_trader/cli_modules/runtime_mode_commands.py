from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

import typer
from rich.panel import Panel
from rich.table import Table

from agentic_trader.cli_modules.common import console
from agentic_trader.config import Settings
from agentic_trader.schemas import RuntimeMode, RuntimeModeTransitionPlan
from agentic_trader.ui_text import t


class RuntimeModePlanProvider(Protocol):
    def __call__(
        self,
        settings: Settings,
        *,
        target_mode: RuntimeMode,
        check_provider: bool,
    ) -> RuntimeModeTransitionPlan: ...


@dataclass(frozen=True)
class RuntimeModeCommandDeps:
    get_settings: Callable[[], Settings]
    emit_json: Callable[[object], None]
    transition_plan: RuntimeModePlanProvider


def register_runtime_mode_commands(
    app: typer.Typer,
    deps: RuntimeModeCommandDeps,
) -> None:
    @app.command("runtime-mode-checklist")
    def runtime_mode_checklist(
        target_mode: RuntimeMode = typer.Argument(
            ...,
            help=runtime_mode_text("target.help"),
        ),
        check_provider: bool = typer.Option(
            True,
            "--provider-check/--skip-provider-check",
            help=runtime_mode_text("provider.check.help"),
        ),
        json_output: bool = typer.Option(False, "--json", help=t("help.json")),
    ) -> None:
        """Show the approved checklist for a Training/Operation mode transition."""
        settings = deps.get_settings()
        plan = deps.transition_plan(
            settings,
            target_mode=target_mode,
            check_provider=check_provider,
        )
        if json_output:
            deps.emit_json(plan.model_dump(mode="json"))
            return
        render_runtime_mode_transition_plan(plan, locale=settings.ui_locale)


def render_runtime_mode_transition_plan(
    plan: RuntimeModeTransitionPlan,
    *,
    locale: str | None = None,
) -> None:
    table = Table(title=runtime_mode_text("transition.checklist.title", locale=locale))
    table.add_column(t("label.check", locale=locale))
    table.add_column(t("label.passed", locale=locale))
    table.add_column(t("label.blocking", locale=locale))
    table.add_column(t("label.details", locale=locale))
    for check in plan.checks:
        table.add_row(
            check.name,
            t("label.yes", locale=locale)
            if check.passed
            else t("label.no", locale=locale),
            t("label.yes", locale=locale)
            if check.blocking
            else t("label.no", locale=locale),
            check.details,
        )
    console.print(
        Panel(
            (
                f"{t('label.current', locale=locale)}: {plan.current_mode}\n"
                f"{t('label.target', locale=locale)}: {plan.target_mode}\n"
                f"{t('label.allowed', locale=locale)}: {plan.allowed}\n\n"
                f"{plan.summary}"
            ),
            title=runtime_mode_text("title", locale=locale),
            border_style="green" if plan.allowed else "yellow",
        )
    )
    console.print(table)


def runtime_mode_text(
    key: str, *, locale: str | None = None, **values: object
) -> str:
    return t(f"runtime.mode.{key}", locale=locale, catalog=None, **values)


__all__ = (
    "RuntimeModeCommandDeps",
    "register_runtime_mode_commands",
    "render_runtime_mode_transition_plan",
    "runtime_mode_text",
)
