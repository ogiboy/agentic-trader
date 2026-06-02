"""Operator-facing diagnostics for V1 readiness and provider visibility."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, cast

from agentic_trader.config import Settings
from agentic_trader.engine.broker import (
    alpaca_credentials_ready,
    alpaca_uses_paper_endpoint,
    broker_runtime_payload,
)
from agentic_trader.llm.client import LocalLLM
from agentic_trader.providers.aggregation import ProviderSet, default_provider_set
from agentic_trader.schemas import ProviderMetadata

CONTEXT_PACK_REQUIRED_FIELDS = [
    "requested_lookback",
    "expected_bars",
    "analyzed_bars",
    "coverage",
    "as_of",
    "window_start",
    "window_end",
    "data_quality_flags",
    "horizon_returns",
]

REVIEW_EVIDENCE_ARTIFACTS = [
    "dashboard_snapshot",
    "trade_context",
    "run_review",
    "provider_diagnostics",
    "broker_status",
    "v1_readiness",
    "evidence_bundle",
]

Payload = dict[str, Any]
Check = dict[str, Any]


def _payload_from_mapping(value: Mapping[object, object]) -> Payload:

    return {str(key): item for key, item in value.items()}


def _payload_list(value: object) -> list[Payload]:
    if not isinstance(value, list):
        return []
    rows: list[Payload] = []
    for item in cast(list[object], value):
        if isinstance(item, Mapping):
            rows.append(_payload_from_mapping(cast(Mapping[object, object], item)))
    return rows


def _provider_metadata(provider_set: ProviderSet) -> Iterable[ProviderMetadata]:
    yield from (provider.metadata() for provider in provider_set.market)
    yield from (provider.metadata() for provider in provider_set.fundamental)
    yield from (provider.metadata() for provider in provider_set.news)
    yield from (provider.metadata() for provider in provider_set.disclosures)
    yield from (provider.metadata() for provider in provider_set.macro)


def _provider_payload(meta: ProviderMetadata) -> Payload:
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


def provider_diagnostics_payload(settings: Settings) -> Payload:
    """
    Build a network-free snapshot of configured provider and source readiness.

    Returns:
        payload (Payload): Diagnostic snapshot with keys:
            - `llm`: selected LLM provider, base URL, default model, and routing.
            - `market_data`: configured market mode, a selected provider role, and a fallback warning.
            - `news`: news ingestion mode, headline limit, and enabled flag.
            - `configured_keys`: booleans indicating presence of API keys for finnhub, fmp,
              polygon/massive, and Alpaca credential readiness.
            - `alpaca`: Alpaca-related settings and readiness flags (paper endpoint, data feed,
              paper trading enablement, and credentials).
            - `providers`: list of normalized provider records derived from configured providers.
            - `warnings`: list of operator-facing warning messages about optional or degraded settings.
    """

    provider_rows = [
        _provider_payload(meta)
        for meta in _provider_metadata(default_provider_set(settings))
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
            "polygon_or_massive": bool(
                settings.polygon_api_key or settings.massive_api_key
            ),
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


def _check(name: str, passed: bool, details: str, *, blocking: bool = True) -> Check:
    return {
        "name": name,
        "passed": passed,
        "details": details,
        "blocking": blocking,
    }


def _allowed(checks: list[Check]) -> bool:
    return all(
        bool(check["passed"]) for check in checks if bool(check.get("blocking", True))
    )


def _provider_rows(payload: Payload) -> list[Payload]:
    return _payload_list(payload.get("providers", []))


def _source_attribution_visible(provider_rows: list[Payload]) -> bool:
    return all(
        row.get("provider_id") and row.get("provider_type") and row.get("role")
        for row in provider_rows
    )


def _selected_market_provider(provider_payload: Payload) -> object:
    market_data = provider_payload.get("market_data", {})
    market_data_payload = (
        _payload_from_mapping(cast(Mapping[object, object], market_data))
        if isinstance(market_data, Mapping)
        else {}
    )
    return market_data_payload.get("selected_provider") or "unknown"


def _paper_evidence_checks(
    *,
    settings: Settings,
    provider_rows: list[Payload],
    selected_provider: object,
) -> list[Check]:
    source_attribution_visible = _source_attribution_visible(provider_rows)
    return [
        _check(
            "provider_source_ladder_visible",
            bool(provider_rows),
            f"providers={len(provider_rows)} selected_market_provider={selected_provider}",
        ),
        _check(
            "source_attribution_visible",
            bool(provider_rows) and source_attribution_visible,
            "Provider rows expose provider_id, provider_type, role, freshness, completeness, and notes.",
        ),
        _check(
            "context_pack_explainability_visible",
            True,
            "Market Context Pack contract includes "
            + ", ".join(CONTEXT_PACK_REQUIRED_FIELDS)
            + ".",
        ),
        _check(
            "review_evidence_path_visible",
            True,
            "Operator review path includes "
            + ", ".join(REVIEW_EVIDENCE_ARTIFACTS)
            + ".",
        ),
        _check(
            "no_live_until_approved_gate",
            not settings.live_execution_enabled
            and settings.execution_backend != "live",
            (
                "Live execution is blocked until paper evidence, manual approval, "
                "and a real live adapter are intentionally implemented."
            ),
        ),
    ]


def _paper_context_pack_payload() -> Payload:
    return {
        "required_fields": CONTEXT_PACK_REQUIRED_FIELDS,
        "fail_closed_in_operation": True,
        "training_undercoverage_visible": True,
    }


def _paper_live_gate_payload(settings: Settings) -> Payload:
    return {
        "live_execution_enabled": settings.live_execution_enabled,
        "execution_backend": settings.execution_backend,
        "live_blocked": not settings.live_execution_enabled
        and settings.execution_backend != "live",
    }


def _paper_evidence_payload(
    settings: Settings,
    provider_payload: Payload,
) -> Payload:
    """
    Assembles a paper-evidence payload that summarizes provider/source visibility and the gates that block live execution.

    Parameters:
        settings (Settings): Runtime/settings object used to evaluate live execution and backend gating.
        provider_payload (Payload): Provider diagnostics payload (expected to include a `providers` list, `market_data.selected_provider`, and optional `warnings`).

    Returns:
        Payload: A payload containing:
            - ready: `True` if all blocking checks pass, `False` otherwise.
            - checks: List of check records produced for provider/source ladder, source attribution, context pack visibility, review evidence path, and live-execution gate.
            - source_ladder: Dict with `provider_count` (int), `selected_market_provider` (str), and `warnings` (list).
            - context_pack: Dict describing required Market Context Pack fields and fixed visibility flags.
            - review_artifacts: List of operator review artifact paths expected on the review path.
            - no_live_until_approved: Summary of live-execution settings including `live_execution_enabled`, `execution_backend`, and computed `live_blocked`.
    """
    provider_rows = _provider_rows(provider_payload)
    selected_provider = _selected_market_provider(provider_payload)
    checks = _paper_evidence_checks(
        settings=settings,
        provider_rows=provider_rows,
        selected_provider=selected_provider,
    )
    return {
        "ready": _allowed(checks),
        "checks": checks,
        "source_ladder": {
            "provider_count": len(provider_rows),
            "selected_market_provider": selected_provider,
            "warnings": provider_payload.get("warnings", []),
        },
        "context_pack": _paper_context_pack_payload(),
        "review_artifacts": REVIEW_EVIDENCE_ARTIFACTS,
        "no_live_until_approved": _paper_live_gate_payload(settings),
    }


def v1_readiness_payload(
    settings: Settings, *, check_provider: bool = False
) -> Payload:
    """
    Assemble a V1 readiness payload summarizing paper-operation checks and Alpaca paper readiness.

    Builds a diagnostic payload that includes broker and provider diagnostics, paper-operation checks (gate conditions required for V1 paper-only operation), Alpaca-specific readiness checks, and a human-readable summary.

    Parameters:
        settings (Settings): Configuration used to evaluate runtime, execution, broker, provider, and Alpaca readiness.
        check_provider (bool): If True, perform an actual LLM provider health check and populate `provider_health`; if False, `provider_health` will be None and the `llm_provider_ready` check will indicate that provider verification was not performed.

    Returns:
        Payload: A mapping with the following top-level keys:
          - `runtime_mode`: the configured runtime mode string.
          - `execution_backend`: the configured execution backend string.
          - `paper_operations`: object with `allowed` (bool) and `checks` (list of check records) for paper-operation gating.
          - `paper_evidence`: evidence payload used to evaluate source/provider visibility.
          - `alpaca_paper`: object with `ready` (bool) and `checks` (list of Alpaca readiness check records).
          - `broker`: broker runtime payload.
          - `provider_health`: provider health details when `check_provider` is True, otherwise None.
          - `summary`: a short message reflecting whether paper-operation checks passed.
    """

    broker_payload = broker_runtime_payload(settings)
    provider_payload = provider_diagnostics_payload(settings)
    paper_evidence = _paper_evidence_payload(settings, provider_payload)
    paper_checks = _paper_operation_checks(
        settings,
        broker_payload=broker_payload,
        paper_evidence=paper_evidence,
    )
    provider_health, provider_check = _provider_readiness_check(
        settings,
        check_provider=check_provider,
    )
    paper_checks.append(provider_check)
    alpaca_checks = _alpaca_paper_checks(settings)

    return {
        "runtime_mode": settings.runtime_mode,
        "execution_backend": settings.execution_backend,
        "paper_operations": {
            "allowed": _allowed(paper_checks),
            "checks": paper_checks,
        },
        "paper_evidence": paper_evidence,
        "alpaca_paper": {
            "ready": _allowed(alpaca_checks),
            "checks": alpaca_checks,
        },
        "broker": broker_payload,
        "provider_health": provider_health,
        "summary": _v1_readiness_summary(paper_checks),
    }


def _paper_operation_checks(
    settings: Settings,
    *,
    broker_payload: Payload,
    paper_evidence: Payload,
) -> list[Check]:
    checks = [
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
            "paper_or_external_paper_backend",
            settings.execution_backend in {"paper", "alpaca_paper"},
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
    evidence_checks = paper_evidence.get("checks", [])
    checks.extend(_payload_list(evidence_checks))
    return checks


def _provider_readiness_check(
    settings: Settings, *, check_provider: bool
) -> tuple[Payload | None, Check]:
    if check_provider:
        health = LocalLLM(settings).health_check(include_generation=True)
        return (
            health.model_dump(mode="json"),
            _check(
                "llm_provider_ready",
                health.service_reachable
                and (health.model_available or not settings.strict_llm)
                and health.generation_available is not False,
                health.message,
            ),
        )
    return (
        None,
        _check(
            "llm_provider_ready",
            False,
            "Provider/model readiness was not checked; rerun with --provider-check.",
        )
    )


def _alpaca_paper_checks(settings: Settings) -> list[Check]:
    credentials_ready = alpaca_credentials_ready(settings)
    return [
        _check(
            "credentials_configured",
            credentials_ready,
            (
                "Alpaca paper API key and secret are configured."
                if credentials_ready
                else "Alpaca paper credentials are missing."
            ),
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


def _v1_readiness_summary(paper_checks: list[Check]) -> str:
    return (
        "V1 paper operation checks passed; live execution remains blocked."
        if _allowed(paper_checks)
        else "V1 paper operation checks are not all passing."
    )
