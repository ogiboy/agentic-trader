from __future__ import annotations

from typing import Protocol

from agentic_trader.config import Settings
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import (
    RuntimeMode,
    RuntimeModeTransitionCheck,
    RuntimeModeTransitionPlan,
)
from agentic_trader.ui_text import (
    MESSAGE_RUNTIME_MODE_TRANSITION_ALLOWED,
    MESSAGE_RUNTIME_MODE_TRANSITION_BLOCKED,
)


def runtime_mode_transition_plan(
    settings: Settings, *, target_mode: RuntimeMode, check_provider: bool
) -> RuntimeModeTransitionPlan:
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
            checks=add_check,
            check_provider=check_provider,
        )
    else:
        add_training_mode_checks(add_check)

    allowed = all(check.passed for check in checks if check.blocking)
    summary = (
        MESSAGE_RUNTIME_MODE_TRANSITION_ALLOWED.format(
            current_mode=settings.runtime_mode,
            target_mode=target_mode,
        )
        if allowed
        else MESSAGE_RUNTIME_MODE_TRANSITION_BLOCKED.format(
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
    checks: AddCheck,
    check_provider: bool,
) -> None:
    checks(
        "strict_llm_enabled",
        settings.strict_llm,
        "Operation mode requires AGENTIC_TRADER_STRICT_LLM=true.",
    )
    if check_provider:
        add_provider_checks(settings=settings, checks=checks)
    else:
        checks(
            "provider_reachable",
            False,
            "Provider check skipped; run doctor before Operation mode.",
        )
    checks(
        "non_live_execution_backend",
        settings.execution_backend in {"paper", "simulated_real"},
        f"Configured backend: {settings.execution_backend}",
    )
    checks(
        "live_execution_disabled",
        not settings.live_execution_enabled,
        "Live execution must remain disabled until a real adapter and approvals exist.",
    )
    checks(
        "kill_switch_clear",
        not settings.execution_kill_switch_active,
        "Execution kill switch must be clear for production-like paper operation.",
    )


def add_provider_checks(*, settings: Settings, checks: AddCheck) -> None:
    health = LocalLLM(settings).health_check(include_generation=True)
    checks("provider_reachable", health.service_reachable, health.message)
    checks(
        "model_available",
        health.model_available,
        f"Configured model: {health.model_name}",
    )
    checks(
        "model_generation_ready",
        health.generation_available is not False,
        health.generation_message or health.message,
    )


def add_training_mode_checks(checks: AddCheck) -> None:
    checks(
        "diagnostic_scope",
        True,
        "Training mode is limited to replay, walk-forward, ablation, and diagnostic evaluation flows.",
    )
    checks(
        "runtime_no_hidden_trades",
        True,
        "`run`, `launch`, and service orchestration remain strict and do not silently trade with fallback outputs.",
    )
    checks(
        "operator_confirmation_required",
        True,
        "Mode changes must be applied through explicit configuration, not chat side effects.",
    )


class AddCheck(Protocol):
    def __call__(
        self, name: str, passed: bool, details: str, *, blocking: bool = True
    ) -> None: ...
