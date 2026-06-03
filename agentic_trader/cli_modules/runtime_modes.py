from __future__ import annotations

from typing import Protocol

from agentic_trader.config import Settings
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import (
    RuntimeMode,
    RuntimeModeTransitionCheck,
    RuntimeModeTransitionPlan,
)
from agentic_trader.ui_text import UITextCatalog, get_ui_text


def runtime_mode_transition_plan(
    settings: Settings, *, target_mode: RuntimeMode, check_provider: bool
) -> RuntimeModeTransitionPlan:
    copy = get_ui_text(settings.ui_locale)
    checks: list[RuntimeModeTransitionCheck] = []

    def add_check(
        name: str, passed: bool, details: str, *, blocking: bool = True
    ) -> None:
        checks.append(
            RuntimeModeTransitionCheck(
                name=name,
                passed=passed,
                details=details,
                blocking=blocking,
            )
        )

    if target_mode == "operation":
        add_operation_mode_checks(
            settings=settings,
            copy=copy,
            checks=add_check,
            check_provider=check_provider,
        )
    else:
        add_training_mode_checks(add_check, copy=copy)

    allowed = all(check.passed for check in checks if check.blocking)
    summary = (
        copy.message_runtime_mode_transition_allowed.format(
            current_mode=settings.runtime_mode,
            target_mode=target_mode,
        )
        if allowed
        else copy.message_runtime_mode_transition_blocked.format(
            current_mode=settings.runtime_mode,
            target_mode=target_mode,
        )
    )
    return RuntimeModeTransitionPlan(
        current_mode=settings.runtime_mode,
        target_mode=target_mode,
        allowed=allowed,
        checks=checks,
        summary=summary,
    )


def add_operation_mode_checks(
    *,
    settings: Settings,
    copy: UITextCatalog,
    checks: AddCheck,
    check_provider: bool,
) -> None:
    checks(
        "strict_llm_enabled",
        settings.strict_llm,
        copy.message_runtime_mode_strict_llm_required,
    )
    if check_provider:
        add_provider_checks(settings=settings, copy=copy, checks=checks)
    else:
        checks(
            "provider_reachable",
            False,
            copy.message_runtime_mode_provider_check_skipped,
        )
    checks(
        "non_live_execution_backend",
        settings.execution_backend in {"paper", "simulated_real"},
        copy.message_runtime_mode_configured_backend.format(
            backend=settings.execution_backend
        ),
    )
    checks(
        "live_execution_disabled",
        not settings.live_execution_enabled,
        copy.message_runtime_mode_live_execution_disabled_required,
    )
    checks(
        "kill_switch_clear",
        not settings.execution_kill_switch_active,
        copy.message_runtime_mode_kill_switch_clear_required,
    )


def add_provider_checks(
    *, settings: Settings, copy: UITextCatalog, checks: AddCheck
) -> None:
    health = LocalLLM(settings).health_check(include_generation=True)
    checks("provider_reachable", health.service_reachable, health.message)
    checks(
        "model_available",
        health.model_available,
        copy.message_runtime_mode_configured_model.format(model_name=health.model_name),
    )
    checks(
        "model_generation_ready",
        health.generation_available is not False,
        health.generation_message or health.message,
    )


def add_training_mode_checks(checks: AddCheck, *, copy: UITextCatalog) -> None:
    checks(
        "diagnostic_scope",
        True,
        copy.message_runtime_mode_training_diagnostic_scope,
    )
    checks(
        "runtime_no_hidden_trades",
        True,
        copy.message_runtime_mode_training_no_hidden_trades,
    )
    checks(
        "operator_confirmation_required",
        True,
        copy.message_runtime_mode_training_operator_confirmation_required,
    )


class AddCheck(Protocol):
    def __call__(
        self, name: str, passed: bool, details: str, *, blocking: bool = True
    ) -> None: ...
