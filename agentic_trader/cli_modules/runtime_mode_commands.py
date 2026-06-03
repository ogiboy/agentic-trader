# pyright: reportUnusedFunction=false
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
from agentic_trader.ui_text import (
    HELP_JSON,
    HELP_RUNTIME_MODE_PROVIDER_CHECK,
    HELP_RUNTIME_MODE_TARGET,
    UITextCatalog,
    get_ui_text,
)


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
        target_mode: RuntimeMode = typer.Argument(..., help=HELP_RUNTIME_MODE_TARGET),
        check_provider: bool = typer.Option(
            True,
            "--provider-check/--skip-provider-check",
            help=HELP_RUNTIME_MODE_PROVIDER_CHECK,
        ),
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    ) -> None:
        """Show the approved checklist for a Training/Operation mode transition."""
        settings = deps.get_settings()
        copy = get_ui_text(settings.ui_locale)
        plan = deps.transition_plan(
            settings,
            target_mode=target_mode,
            check_provider=check_provider,
        )
        if json_output:
            deps.emit_json(plan.model_dump(mode="json"))
            return
        render_runtime_mode_transition_plan(plan, copy=copy)


def render_runtime_mode_transition_plan(
    plan: RuntimeModeTransitionPlan,
    *,
    copy: UITextCatalog | None = None,
) -> None:
    resolved_copy = copy or get_ui_text()
    table = Table(title=resolved_copy.title_runtime_mode_transition_checklist)
    table.add_column(resolved_copy.label_check)
    table.add_column(resolved_copy.label_passed)
    table.add_column(resolved_copy.label_blocking)
    table.add_column(resolved_copy.label_details)
    for check in plan.checks:
        table.add_row(
            check.name,
            resolved_copy.label_yes if check.passed else resolved_copy.label_no,
            resolved_copy.label_yes if check.blocking else resolved_copy.label_no,
            check.details,
        )
    console.print(
        Panel(
            (
                f"{resolved_copy.label_current}: {plan.current_mode}\n"
                f"{resolved_copy.label_target}: {plan.target_mode}\n"
                f"{resolved_copy.label_allowed}: {plan.allowed}\n\n{plan.summary}"
            ),
            title=resolved_copy.title_runtime_mode,
            border_style="green" if plan.allowed else "yellow",
        )
    )
    console.print(table)


__all__ = (
    "RuntimeModeCommandDeps",
    "register_runtime_mode_commands",
    "render_runtime_mode_transition_plan",
)
