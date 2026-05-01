"""Operator-facing diagnostics for V1 readiness and provider visibility."""

from __future__ import annotations

from collections.abc import Iterable

from agentic_trader.config import Settings
from agentic_trader.engine.broker import (
    alpaca_credentials_ready,
    alpaca_uses_paper_endpoint,
    broker_runtime_payload,
)
from agentic_trader.llm.client import LocalLLM
from agentic_trader.providers.aggregation import ProviderSet, default_provider_set
from agentic_trader.schemas import ProviderMetadata


def _provider_metadata(provider_set: ProviderSet) -> Iterable[ProviderMetadata]:
    yield from (provider.metadata() for provider in provider_set.market)
    yield from (provider.metadata() for provider in provider_set.fundamental)
    yield from (provider.metadata() for provider in provider_set.news)
    yield from (provider.metadata() for provider in provider_set.disclosures)
    yield from (provider.metadata() for provider in provider_set.macro)


def _provider_payload(meta: ProviderMetadata) -> dict[str, object]:
    api_key_ready = None
    if "api_key_configured" in meta.notes:
        api_key_ready = True
    elif "api_key_missing" in meta.notes:
        api_key_ready = False
    return {
        "provider_id": meta.provider_id,
        "name": meta.name,
        "provider_type": meta.provider_type,
        "role": meta.role,
        "priority": meta.priority,
        "enabled": meta.enabled,
        "requires_network": meta.requires_network,
        "api_key_ready": api_key_ready,
        "freshness": "unknown" if meta.enabled else "missing",
        "completeness": "unknown" if meta.enabled else "missing",
        "notes": meta.notes,
    }


def provider_diagnostics_payload(settings: Settings) -> dict[str, object]:
    """Build a network-free snapshot of configured provider/source readiness."""

    provider_rows = [
        _provider_payload(meta) for meta in _provider_metadata(default_provider_set(settings))
    ]
    warnings: list[str] = []
    if any(row["provider_id"] == "yahoo_market" for row in provider_rows):
        warnings.append(
            "Yahoo/yfinance is the bootstrap market-data fallback, not the target "
            "source of truth for V1 financial intelligence."
        )
    if not settings.finnhub_api_key and not settings.fmp_api_key:
        warnings.append(
            "No optional fundamental API key is configured; fundamental providers "
            "will surface missing evidence instead of fabricating data."
        )
    if settings.news_mode == "off":
        warnings.append("Optional news/event ingestion is disabled.")

    return {
        "llm": {
            "provider": settings.llm_provider,
            "base_url": settings.base_url,
            "default_model": settings.model_name,
            "routing": settings.model_routing(),
        },
        "market_data": {
            "mode": settings.market_data_mode,
            "selected_provider": "yahoo_market",
            "selected_role": "fallback",
            "fallback_warning": "Yahoo/yfinance is degraded fallback evidence.",
        },
        "news": {
            "mode": settings.news_mode,
            "headline_limit": settings.news_headline_limit,
            "enabled": settings.news_mode != "off",
        },
        "configured_keys": {
            "finnhub": bool(settings.finnhub_api_key),
            "fmp": bool(settings.fmp_api_key),
            "polygon_or_massive": bool(settings.polygon_api_key or settings.massive_api_key),
            "alpaca": alpaca_credentials_ready(settings),
        },
        "alpaca": {
            "paper_endpoint": settings.alpaca_base_url,
            "paper_endpoint_ready": alpaca_uses_paper_endpoint(settings),
            "data_feed": settings.alpaca_data_feed,
            "paper_trading_enabled": settings.alpaca_paper_trading_enabled,
            "credentials_configured": alpaca_credentials_ready(settings),
        },
        "providers": provider_rows,
        "warnings": warnings,
    }


def _check(
    name: str, passed: bool, details: str, *, blocking: bool = True
) -> dict[str, object]:
    return {
        "name": name,
        "passed": passed,
        "details": details,
        "blocking": blocking,
    }


def _allowed(checks: list[dict[str, object]]) -> bool:
    return all(
        bool(check["passed"]) for check in checks if bool(check.get("blocking", True))
    )


def v1_readiness_payload(
    settings: Settings, *, check_provider: bool = False
) -> dict[str, object]:
    """Build a V1 paper-operation and Alpaca-readiness checklist."""

    broker_payload = broker_runtime_payload(settings)
    paper_checks = [
        _check(
            "runtime_mode_operation",
            settings.runtime_mode == "operation",
            f"runtime_mode={settings.runtime_mode}",
        ),
        _check(
            "strict_llm_enabled",
            settings.strict_llm,
            f"strict_llm={settings.strict_llm}",
        ),
        _check(
            "paper_first_backend",
            settings.execution_backend == "paper",
            f"execution_backend={settings.execution_backend}",
        ),
        _check(
            "live_execution_disabled",
            not settings.live_execution_enabled,
            f"live_execution_enabled={settings.live_execution_enabled}",
        ),
        _check(
            "kill_switch_inactive",
            not settings.execution_kill_switch_active,
            f"execution_kill_switch_active={settings.execution_kill_switch_active}",
        ),
        _check(
            "broker_health_visible",
            isinstance(broker_payload.get("healthcheck"), dict),
            str(broker_payload.get("message", "")),
        ),
    ]

    provider_health: dict[str, object] | None = None
    if check_provider:
        health = LocalLLM(settings).health_check()
        provider_health = health.model_dump(mode="json")
        paper_checks.append(
            _check(
                "llm_provider_ready",
                health.service_reachable and (health.model_available or not settings.strict_llm),
                health.message,
            )
        )
    else:
        paper_checks.append(
            _check(
                "llm_provider_ready",
                False,
                "Provider/model readiness was not checked; rerun with --provider-check.",
            )
        )
    alpaca_checks = [
        _check(
            "credentials_configured",
            alpaca_credentials_ready(settings),
            "Alpaca paper API key and secret are configured."
            if alpaca_credentials_ready(settings)
            else "Alpaca paper credentials are missing.",
        ),
        _check(
            "paper_endpoint",
            alpaca_uses_paper_endpoint(settings),
            f"alpaca_base_url={settings.alpaca_base_url}",
        ),
        _check(
            "iex_feed_default",
            settings.alpaca_data_feed.lower() == "iex",
            f"alpaca_data_feed={settings.alpaca_data_feed}",
            blocking=False,
        ),
        _check(
            "explicit_external_paper_enablement",
            settings.alpaca_paper_trading_enabled,
            "Set AGENTIC_TRADER_ALPACA_PAPER_TRADING_ENABLED=true before external paper orders.",
        ),
        _check(
            "live_execution_blocked",
            not settings.live_execution_enabled,
            "Live execution is disabled; V1 external broker work is paper-only.",
        ),
        _check(
            "us_equities_scope",
            True,
            "V1 Alpaca readiness is intentionally scoped to simple US equity symbols.",
        ),
    ]

    return {
        "runtime_mode": settings.runtime_mode,
        "execution_backend": settings.execution_backend,
        "paper_operations": {
            "allowed": _allowed(paper_checks),
            "checks": paper_checks,
        },
        "alpaca_paper": {
            "ready": _allowed(alpaca_checks),
            "checks": alpaca_checks,
        },
        "broker": broker_payload,
        "provider_health": provider_health,
        "summary": (
            "V1 paper operation checks passed; live execution remains blocked."
            if _allowed(paper_checks)
            else "V1 paper operation checks are not all passing."
        ),
    }
