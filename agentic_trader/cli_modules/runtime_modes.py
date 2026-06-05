from __future__ import annotations

from typing import Protocol

from agentic_trader.config import Settings
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import (
    RuntimeMode,
    RuntimeModeTransitionCheck,
    RuntimeModeTransitionPlan,
)
from agentic_trader.ui_text import t


def runtime_mode_transition_plan(
    settings: Settings, *, target_mode: RuntimeMode, check_provider: bool
) -> RuntimeModeTransitionPlan:
    locale = settings.ui_locale
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
            locale=locale,
            checks=add_check,
            check_provider=check_provider,
        )
    else:
        add_training_mode_checks(add_check, locale=locale)

    allowed = all(check.passed for check in checks if check.blocking)
    summary = (
        runtime_mode_text(
            "transition.allowed",
            locale=locale,
            current_mode=settings.runtime_mode,
            target_mode=target_mode,
        )
        if allowed
        else runtime_mode_text(
            "transition.blocked",
            locale=locale,
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
    locale: str | None,
    checks: AddCheck,
    check_provider: bool,
) -> None:
    checks(
        "strict_llm_enabled",
        settings.strict_llm,
        runtime_mode_text("strict.llm.required", locale=locale),
    )
    if check_provider:
        add_provider_checks(settings=settings, locale=locale, checks=checks)
    else:
        checks(
            "provider_reachable",
            False,
            runtime_mode_text("provider.check.skipped", locale=locale),
        )
    checks(
        "non_live_execution_backend",
        settings.execution_backend in {"paper", "simulated_real"},
        runtime_mode_text(
            "configured.backend",
            locale=locale,
            backend=settings.execution_backend,
        ),
    )
    checks(
        "live_execution_disabled",
        not settings.live_execution_enabled,
        runtime_mode_text("live.execution.disabled.required", locale=locale),
    )
    checks(
        "kill_switch_clear",
        not settings.execution_kill_switch_active,
        runtime_mode_text("kill.switch.clear.required", locale=locale),
    )


def add_provider_checks(
    *, settings: Settings, locale: str | None, checks: AddCheck
) -> None:
    health = LocalLLM(settings).health_check(include_generation=True)
    checks("provider_reachable", health.service_reachable, health.message)
    checks(
        "model_available",
        health.model_available,
        runtime_mode_text(
            "configured.model",
            locale=locale,
            model_name=health.model_name,
        ),
    )
    checks(
        "model_generation_ready",
        health.generation_available is not False,
        health.generation_message or health.message,
    )


def add_training_mode_checks(checks: AddCheck, *, locale: str | None) -> None:
    checks(
        "diagnostic_scope",
        True,
        runtime_mode_text("training.diagnostic.scope", locale=locale),
    )
    checks(
        "runtime_no_hidden_trades",
        True,
        runtime_mode_text("training.no.hidden.trades", locale=locale),
    )
    checks(
        "operator_confirmation_required",
        True,
        runtime_mode_text(
            "training.operator.confirmation.required",
            locale=locale,
        ),
    )


def runtime_mode_text(
    key: str, *, locale: str | None = None, **values: object
) -> str:
    return t(f"runtime.mode.{key}", locale=locale, catalog=None, **values)


class AddCheck(Protocol):
    def __call__(
        self, name: str, passed: bool, details: str, *, blocking: bool = True
    ) -> None: ...
