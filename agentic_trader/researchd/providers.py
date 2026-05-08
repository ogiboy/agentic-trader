"""Providers for the optional research sidecar.

Providers expose source readiness and missing-data truth. Real network-backed
providers must stay opt-in, source-attributed, and free of fabricated events.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlparse
import shutil
import subprocess
from typing import Any, Callable, Protocol, cast, runtime_checkable

import httpx

from agentic_trader.config import Settings
from agentic_trader.providers.base import metadata, source_attribution, utc_now_iso
from agentic_trader.security import is_loopback_host, redact_sensitive_text
from agentic_trader.schemas import (
    DataProviderKind,
    DataSourceRole,
    DataSourceAttribution,
    MacroEvent,
    ProviderMetadata,
    RawEvidenceRecord,
    ResearchProviderHealth,
    SocialSignal,
    EvidenceInferenceBreakdown,
)
from agentic_trader.system.camofox_service import (
    CamofoxServiceStatus,
    build_camofox_service_status,
)


SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_COMPANY_FACTS_URL_TEMPLATE = (
    "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
)
SEC_SUBMISSIONS_URL_TEMPLATE = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_ARCHIVES_URL_TEMPLATE = (
    "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{primary_document}"
)
SEC_RESEARCH_FORMS = frozenset(
    {
        "10-K",
        "10-K/A",
        "10-Q",
        "10-Q/A",
        "8-K",
        "8-K/A",
        "20-F",
        "20-F/A",
        "40-F",
        "40-F/A",
        "6-K",
        "6-K/A",
    }
)
SEC_COMPANY_FACT_CONCEPTS = (
    (
        "revenue",
        "Revenue",
        (
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "SalesRevenueNet",
        ),
    ),
    ("net_income", "Net income", ("NetIncomeLoss",)),
    ("assets", "Assets", ("Assets",)),
    ("liabilities", "Liabilities", ("Liabilities",)),
    (
        "operating_cash_flow",
        "Operating cash flow",
        ("NetCashProvidedByUsedInOperatingActivities",),
    ),
    (
        "cash",
        "Cash and equivalents",
        ("CashAndCashEquivalentsAtCarryingValue",),
    ),
)
JsonFetcher = Callable[[str, Mapping[str, str], float], dict[str, Any]]
FirecrawlSdkSearcher = Callable[[str, int, float], object]
CamofoxServiceStatusBuilder = Callable[[Settings], CamofoxServiceStatus]


class CommandRunner(Protocol):
    """Subprocess runner for optional CLI providers with explicit env."""

    def __call__(
        self,
        command: list[str],
        timeout_seconds: float,
        env: Mapping[str, str],
    ) -> subprocess.CompletedProcess[str]:
        ...


MINIMAL_COMMAND_ENV_KEYS = (
    "PATH",
    "HOME",
    "TMPDIR",
    "USER",
    "LOGNAME",
    "SHELL",
    "USERPROFILE",
    "APPDATA",
    "LOCALAPPDATA",
    "SYSTEMROOT",
    "WINDIR",
)
HealthFetcher = Callable[[str, float], dict[str, Any]]


@dataclass(frozen=True)
class ResearchProviderOutput:
    """Normalized output shape returned by sidecar research providers."""

    metadata: ProviderMetadata
    raw_evidence: list[RawEvidenceRecord] = field(default_factory=list)
    macro_events: list[MacroEvent] = field(default_factory=list)
    social_signals: list[SocialSignal] = field(default_factory=list)
    missing_reasons: list[str] = field(default_factory=list)


@runtime_checkable
class ResearchEvidenceProvider(Protocol):
    """Provider contract for sidecar evidence collection."""

    def metadata(self) -> ProviderMetadata:
        """Return provider identity and operational metadata."""
        ...

    def collect(self, *, symbols: list[str], limit: int) -> ResearchProviderOutput:
        """Collect normalized research evidence or explicit missing-source state."""
        ...


class ScaffoldResearchProvider:
    """A provider placeholder that reports missing ingestion without fake data."""

    def __init__(
        self,
        *,
        provider_id: str,
        name: str,
        provider_type: DataProviderKind,
        role: DataSourceRole,
        priority: int,
        notes: list[str],
        enabled: bool = True,
        requires_network: bool = False,
    ) -> None:
        self._metadata = metadata(
            provider_id=provider_id,
            name=name,
            provider_type=provider_type,
            role=role,
            priority=priority,
            enabled=enabled,
            requires_network=requires_network,
            notes=[*notes, "ingestion_pending"],
        )

    def metadata(self) -> ProviderMetadata:
        return self._metadata

    def collect(self, *, symbols: list[str], limit: int) -> ResearchProviderOutput:
        _ = (symbols, limit)
        return ResearchProviderOutput(
            metadata=self._metadata,
            missing_reasons=["ingestion_pending"],
        )


@dataclass(frozen=True)
class _SecTickerMatch:
    symbol: str
    cik: str
    entity_name: str


class SecEdgarSubmissionsProvider:
    """Opt-in SEC EDGAR submissions provider for normalized filing evidence."""

    def __init__(
        self,
        *,
        settings: Settings,
        fetcher: JsonFetcher | None = None,
    ) -> None:
        self._enabled = settings.research_sec_edgar_enabled
        self._user_agent = (settings.research_sec_edgar_user_agent or "").strip()
        self._timeout = min(max(settings.request_timeout_seconds, 1.0), 30.0)
        self._fetcher = fetcher or _fetch_json
        configuration_note = _sec_configuration_note(
            enabled=self._enabled,
            user_agent=self._user_agent,
        )
        self._metadata = metadata(
            provider_id="sec_edgar_research",
            name="SEC EDGAR Research",
            provider_type="disclosure",
            role="primary",
            priority=10,
            enabled=self._enabled,
            requires_network=self._enabled,
            notes=[
                "sec_10k_10q_8k_source",
                "official_disclosure_source",
                "sec_submissions_api",
                configuration_note,
            ],
        )

    def metadata(self) -> ProviderMetadata:
        return self._metadata

    def collect(self, *, symbols: list[str], limit: int) -> ResearchProviderOutput:
        if not self._enabled:
            return ResearchProviderOutput(
                metadata=self._metadata,
                missing_reasons=["provider_disabled"],
            )
        if not self._user_agent:
            return ResearchProviderOutput(
                metadata=self._metadata,
                missing_reasons=["sec_user_agent_missing"],
            )

        watched_symbols = [_normalize_symbol(symbol) for symbol in symbols]
        watched_symbols = [symbol for symbol in watched_symbols if symbol]
        if not watched_symbols:
            return ResearchProviderOutput(
                metadata=self._metadata,
                missing_reasons=["watchlist_missing"],
            )

        safe_limit = max(1, limit)
        headers = {
            "Accept": "application/json",
            "User-Agent": self._user_agent,
        }
        missing_reasons: list[str] = []
        try:
            ticker_payload = self._fetcher(
                SEC_COMPANY_TICKERS_URL,
                headers,
                self._timeout,
            )
        except (httpx.HTTPError, ValueError, TypeError, TimeoutError) as exc:
            return ResearchProviderOutput(
                metadata=self._metadata,
                missing_reasons=["sec_ticker_lookup_failed", _safe_error_note(exc)],
            )

        ticker_index = _sec_ticker_index(ticker_payload)
        records: list[RawEvidenceRecord] = []
        for symbol in watched_symbols:
            match = ticker_index.get(symbol)
            if match is None:
                missing_reasons.append(f"sec_cik_missing:{symbol}")
                continue
            if len(records) < safe_limit:
                try:
                    facts_payload = self._fetcher(
                        SEC_COMPANY_FACTS_URL_TEMPLATE.format(cik=match.cik),
                        headers,
                        self._timeout,
                    )
                except (httpx.HTTPError, ValueError, TypeError, TimeoutError) as exc:
                    missing_reasons.extend(
                        [
                            f"sec_companyfacts_fetch_failed:{symbol}",
                            _safe_error_note(exc),
                        ]
                    )
                else:
                    facts_record = _record_from_company_facts(
                        provider=self._metadata,
                        symbol=symbol,
                        match=match,
                        payload=facts_payload,
                    )
                    if facts_record is None:
                        missing_reasons.append(f"sec_companyfacts_missing:{symbol}")
                    else:
                        records.append(facts_record)
            if len(records) >= safe_limit:
                break
            try:
                submissions_payload = self._fetcher(
                    SEC_SUBMISSIONS_URL_TEMPLATE.format(cik=match.cik),
                    headers,
                    self._timeout,
                )
            except (httpx.HTTPError, ValueError, TypeError, TimeoutError) as exc:
                missing_reasons.extend(
                    [
                        f"sec_submissions_fetch_failed:{symbol}",
                        _safe_error_note(exc),
                    ]
                )
                continue

            symbol_records = _records_from_submissions(
                provider=self._metadata,
                symbol=symbol,
                match=match,
                payload=submissions_payload,
                limit=safe_limit - len(records),
            )
            if not symbol_records:
                missing_reasons.append(f"sec_target_filings_missing:{symbol}")
            records.extend(symbol_records)
            if len(records) >= safe_limit:
                break

        return ResearchProviderOutput(
            metadata=self._metadata,
            raw_evidence=records,
            missing_reasons=list(dict.fromkeys(missing_reasons)),
        )


class FirecrawlNewsResearchProvider:
    """Opt-in Firecrawl news search provider with sanitized evidence output."""

    def __init__(
        self,
        *,
        settings: Settings,
        command_runner: CommandRunner | None = None,
        sdk_searcher: FirecrawlSdkSearcher | None = None,
    ) -> None:
        self._enabled = settings.research_firecrawl_enabled
        self._api_key = settings.firecrawl_api_key
        self._cli = settings.research_firecrawl_cli
        self._country = settings.research_firecrawl_country.upper()
        self._timeout = min(
            max(settings.research_firecrawl_timeout_seconds, 1.0), 300.0
        )
        self._runner = command_runner or _run_command
        self._sdk_searcher = sdk_searcher
        self._prefer_sdk = command_runner is None
        self._metadata = metadata(
            provider_id="firecrawl_news_research",
            name="Firecrawl News Research",
            provider_type="news",
            role="fallback",
            priority=35,
            enabled=self._enabled,
            requires_network=self._enabled,
            notes=[
                "firecrawl_sdk_optional",
                "firecrawl_cli_optional",
                "news_search_provider",
                "raw_web_text_not_injected",
                "enabled" if self._enabled else "provider_disabled",
            ],
        )

    def metadata(self) -> ProviderMetadata:
        return self._metadata

    def collect(self, *, symbols: list[str], limit: int) -> ResearchProviderOutput:
        if not self._enabled:
            return ResearchProviderOutput(
                metadata=self._metadata,
                missing_reasons=["provider_disabled"],
            )
        watched_symbols = [_normalize_symbol(symbol) for symbol in symbols]
        watched_symbols = [symbol for symbol in watched_symbols if symbol]
        if not watched_symbols:
            return ResearchProviderOutput(
                metadata=self._metadata,
                missing_reasons=["watchlist_missing"],
            )

        records: list[RawEvidenceRecord] = []
        missing_reasons: list[str] = []
        per_symbol_limit = max(1, min(limit, 10))
        for symbol in watched_symbols:
            query = f"{symbol} stock news this week"
            if self._prefer_sdk:
                try:
                    sdk_payload = _firecrawl_sdk_search_payload(
                        query=query,
                        limit=per_symbol_limit,
                        timeout_seconds=self._timeout,
                        api_key=self._api_key,
                        sdk_searcher=self._sdk_searcher,
                    )
                except Exception as exc:
                    missing_reasons.append(
                        f"firecrawl_sdk_failed:{symbol}:{type(exc).__name__}"
                    )
                    sdk_payload = None
                if sdk_payload is not None:
                    symbol_records = _records_from_firecrawl_payload(
                        provider=self._metadata,
                        symbol=symbol,
                        payload=sdk_payload,
                        limit=per_symbol_limit,
                    )
                    if not symbol_records:
                        missing_reasons.append(f"firecrawl_no_news:{symbol}")
                    records.extend(symbol_records)
                    if len(records) >= limit:
                        break
                    continue

            cli_path = _resolve_cli(self._cli)
            if cli_path is None:
                missing_reasons.append("firecrawl_cli_missing")
                continue
            command = [
                cli_path,
                "search",
                query,
                "--sources",
                "news",
                "--country",
                self._country,
                "--limit",
                str(per_symbol_limit),
                "--json",
            ]
            try:
                completed = self._runner(
                    command,
                    self._timeout,
                    _minimal_firecrawl_env(self._api_key),
                )
            except (OSError, subprocess.SubprocessError, TimeoutError) as exc:
                missing_reasons.append(
                    f"firecrawl_command_failed:{symbol}:{type(exc).__name__}"
                )
                continue
            if completed.returncode != 0:
                missing_reasons.append(
                    f"firecrawl_nonzero_exit:{symbol}:"
                    f"{redact_sensitive_text(completed.stderr, max_length=120)}"
                )
                continue
            try:
                payload = json.loads(completed.stdout)
            except json.JSONDecodeError:
                missing_reasons.append(f"firecrawl_json_parse_failed:{symbol}")
                continue
            symbol_records = _records_from_firecrawl_payload(
                provider=self._metadata,
                symbol=symbol,
                payload=payload,
                limit=per_symbol_limit,
            )
            if not symbol_records:
                missing_reasons.append(f"firecrawl_no_news:{symbol}")
            records.extend(symbol_records)
            if len(records) >= limit:
                break

        return ResearchProviderOutput(
            metadata=self._metadata,
            raw_evidence=records[:limit],
            missing_reasons=list(dict.fromkeys(missing_reasons)),
        )


class CamofoxBrowserResearchProvider:
    """Opt-in local Camofox health provider for browser-backed research readiness."""

    def __init__(
        self,
        *,
        settings: Settings,
        health_fetcher: HealthFetcher | None = None,
        service_status_builder: CamofoxServiceStatusBuilder | None = None,
    ) -> None:
        self._settings = settings
        self._enabled = settings.research_camofox_enabled
        self._base_url = settings.research_camofox_base_url.rstrip("/")
        parsed_base_url = urlparse(self._base_url)
        self._loopback_only = parsed_base_url.scheme in {"http", "https"} and is_loopback_host(
            parsed_base_url.hostname or ""
        )
        self._timeout = min(max(settings.request_timeout_seconds, 1.0), 10.0)
        self._fetcher = health_fetcher or _fetch_camofox_health
        self._service_status_builder = service_status_builder or build_camofox_service_status
        self._metadata = metadata(
            provider_id="camofox_browser_research",
            name="Camofox Browser Research",
            provider_type="news",
            role="fallback",
            priority=36,
            enabled=self._enabled,
            requires_network=self._enabled,
            notes=[
                "camofox_local_browser_optional",
                "loopback_required",
                "browser_health_only",
                "raw_web_text_not_injected",
                "enabled" if self._enabled else "provider_disabled",
            ],
        )

    def metadata(self) -> ProviderMetadata:
        return self._metadata

    def collect(self, *, symbols: list[str], limit: int) -> ResearchProviderOutput:
        _ = (symbols, limit)
        if not self._enabled:
            return ResearchProviderOutput(
                metadata=self._metadata,
                missing_reasons=["provider_disabled"],
            )
        if not self._loopback_only:
            return ResearchProviderOutput(
                metadata=self._metadata,
                missing_reasons=["camofox_base_url_must_be_loopback"],
            )
        service_status = self._service_status_builder(self._settings)
        if (
            service_status.app_owned
            and service_status.base_url.rstrip("/") == self._base_url
            and not service_status.health_ok
        ):
            return ResearchProviderOutput(
                metadata=self._metadata,
                missing_reasons=["camofox_browser_launch_failed"],
            )
        try:
            payload = self._fetcher(f"{self._base_url}/health", self._timeout)
        except (httpx.HTTPError, ValueError, TypeError, TimeoutError) as exc:
            return ResearchProviderOutput(
                metadata=self._metadata,
                missing_reasons=["camofox_health_failed", _safe_error_note(exc)],
            )
        fetched_at = utc_now_iso()
        ok = bool(payload.get("ok"))
        record = RawEvidenceRecord(
            record_id=f"camofox-health:{_stable_hash(self._base_url)}",
            source_kind="provider_status",
            source_name=self._metadata.provider_id,
            title="Camofox browser research health",
            url=f"{self._base_url}/health",
            observed_at=fetched_at,
            last_verified_at=fetched_at,
            normalized_summary=(
                "Camofox local browser health is "
                f"{'ok' if ok else 'not ok'}; "
                f"engine={payload.get('engine', 'unknown')}; "
                f"browserConnected={payload.get('browserConnected', 'unknown')}; "
                f"browserRunning={payload.get('browserRunning', 'unknown')}."
            ),
            source_payload_ref=f"camofox-health://{_stable_hash(self._base_url)}",
            source_attributions=[
                source_attribution(
                    source_name=self._metadata.provider_id,
                    provider_type=self._metadata.provider_type,
                    source_role=self._metadata.role if ok else "missing",
                    fetched_at=fetched_at,
                    freshness="fresh" if ok else "unknown",
                    confidence=0.8 if ok else 0.2,
                    completeness=1.0 if ok else 0.4,
                    notes=[
                        "local_browser_health",
                        "raw_web_text_not_injected",
                    ],
                )
            ],
            evidence_vs_inference=EvidenceInferenceBreakdown(
                evidence=[
                    "Health endpoint returned a structured browser status payload."
                ],
                inference=[
                    "Browser-backed research can be attempted only when the provider remains enabled and healthy."
                ],
                uncertainty=[
                    "Health status does not prove a specific finance site can be fetched."
                ],
            ),
            missing_fields=[] if ok else ["healthy_browser"],
        )
        missing = [] if ok else ["camofox_unhealthy"]
        return ResearchProviderOutput(
            metadata=self._metadata,
            raw_evidence=[record],
            missing_reasons=missing,
        )


def default_research_providers(settings: Settings) -> list[ResearchEvidenceProvider]:
    """Return the local-first research source ladder for the sidecar."""
    social_configured = bool(settings.research_symbols)
    return [
        SecEdgarSubmissionsProvider(settings=settings),
        ScaffoldResearchProvider(
            provider_id="kap_research",
            name="KAP Research",
            provider_type="disclosure",
            role="primary",
            priority=20,
            notes=["turkey_public_disclosure_platform"],
        ),
        ScaffoldResearchProvider(
            provider_id="macro_research",
            name="Macro Research",
            provider_type="macro",
            role="primary",
            priority=30,
            notes=["fred_cbtr_evds_gdelt_future_sources"],
        ),
        FirecrawlNewsResearchProvider(settings=settings),
        CamofoxBrowserResearchProvider(settings=settings),
        ScaffoldResearchProvider(
            provider_id="news_event_research",
            name="News And Event Research",
            provider_type="news",
            role="fallback",
            priority=40,
            notes=["news_event_timeline_source"],
        ),
        ScaffoldResearchProvider(
            provider_id="social_watchlist_research",
            name="Social Watchlist Research",
            provider_type="social",
            role="fallback",
            priority=50,
            enabled=social_configured,
            requires_network=social_configured,
            notes=[
                "watchlist_only",
                "configured" if social_configured else "watchlist_missing",
            ],
        ),
    ]


def provider_health_from_output(output: ResearchProviderOutput) -> ResearchProviderHealth:
    """Convert provider output into an operator-safe health summary."""
    meta = output.metadata
    has_payload = bool(output.raw_evidence or output.macro_events or output.social_signals)
    freshness = "fresh" if has_payload else "missing"
    source_role = meta.role if has_payload else "missing"
    fetched_at = utc_now_iso() if has_payload else None
    notes = list(dict.fromkeys([*meta.notes, *output.missing_reasons]))
    return ResearchProviderHealth(
        provider_id=meta.provider_id,
        name=meta.name,
        provider_type=meta.provider_type,
        enabled=meta.enabled,
        requires_network=meta.requires_network,
        source_role=source_role,
        freshness=freshness,
        last_successful_update_at=fetched_at,
        message=_provider_health_message(has_payload=has_payload, notes=notes),
        notes=notes,
    )


def missing_attribution(provider: ProviderMetadata):
    """Build a missing-source attribution for future provider output objects."""
    return source_attribution(
        source_name=provider.provider_id,
        provider_type=provider.provider_type,
        source_role="missing",
        fetched_at=utc_now_iso(),
        freshness="missing",
        notes=[*provider.notes, "no_research_payload_returned"],
    )


def source_attributions_from_output(
    output: ResearchProviderOutput,
) -> list[DataSourceAttribution]:
    """Return provider attributions that truthfully represent payload freshness."""
    attributions: list[DataSourceAttribution] = []
    for record in [
        *output.raw_evidence,
        *output.macro_events,
        *output.social_signals,
    ]:
        attributions.extend(record.source_attributions)
    if not attributions and (
        output.raw_evidence or output.macro_events or output.social_signals
    ):
        completeness = 1.0 if not output.missing_reasons else 0.7
        attributions.append(
            source_attribution(
                source_name=output.metadata.provider_id,
                provider_type=output.metadata.provider_type,
                source_role=output.metadata.role,
                fetched_at=utc_now_iso(),
                freshness="fresh",
                confidence=0.8,
                completeness=completeness,
                notes=[*output.metadata.notes, *output.missing_reasons],
            )
        )
    if not attributions:
        attributions.append(missing_attribution(output.metadata))
    return _unique_attributions(attributions)


def _fetch_json(
    url: str,
    headers: Mapping[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    response = httpx.get(url, headers=dict(headers), timeout=timeout_seconds)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("json_payload_not_object")
    return payload


def _run_command(
    command: list[str], timeout_seconds: float, env: Mapping[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
        env=dict(env),
    )


def _minimal_firecrawl_env(api_key: str | None = None) -> dict[str, str]:
    env = {
        key: os.environ[key]
        for key in MINIMAL_COMMAND_ENV_KEYS
        if key in os.environ
    }
    resolved_api_key = api_key or os.environ.get("FIRECRAWL_API_KEY")
    if resolved_api_key:
        env["FIRECRAWL_API_KEY"] = resolved_api_key
    return env


def _firecrawl_sdk_search_payload(
    *,
    query: str,
    limit: int,
    timeout_seconds: float,
    api_key: str | None = None,
    sdk_searcher: FirecrawlSdkSearcher | None = None,
) -> object | None:
    resolved_api_key = (api_key or os.environ.get("FIRECRAWL_API_KEY", "")).strip()
    if not resolved_api_key and sdk_searcher is None:
        return None
    if sdk_searcher is not None:
        return _firecrawl_sdk_payload(sdk_searcher(query, limit, timeout_seconds))
    try:
        from firecrawl import Firecrawl
    except ImportError:
        return None
    client = Firecrawl(api_key=resolved_api_key, timeout=timeout_seconds)
    return _firecrawl_sdk_payload(
        client.search(
            query,
            sources=["news"],
            limit=limit,
            timeout=max(1, int(timeout_seconds)),
        )
    )


def _firecrawl_sdk_payload(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _firecrawl_sdk_payload(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_firecrawl_sdk_payload(item) for item in value]
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return _firecrawl_sdk_payload(cast(Callable[[], object], model_dump)())
    if hasattr(value, "data"):
        return {"data": _firecrawl_sdk_payload(getattr(value, "data"))}
    if hasattr(value, "__dict__"):
        return {
            key: _firecrawl_sdk_payload(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    return value


def _resolve_cli(raw_cli: str) -> str | None:
    raw_cli = raw_cli.strip()
    if not raw_cli:
        return None
    candidate_path = Path(raw_cli).expanduser()
    if (
        candidate_path.is_absolute()
        or candidate_path.parent != Path(".")
        or "\\" in raw_cli
    ):
        return str(candidate_path) if candidate_path.exists() else None
    return shutil.which(raw_cli)


def _fetch_camofox_health(url: str, timeout_seconds: float) -> dict[str, Any]:
    response = httpx.get(url, timeout=timeout_seconds)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("camofox_health_payload_not_object")
    return payload


def _normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def _safe_error_note(exc: BaseException) -> str:
    return f"provider_error:{type(exc).__name__}"


def _records_from_firecrawl_payload(
    *,
    provider: ProviderMetadata,
    symbol: str,
    payload: object,
    limit: int,
) -> list[RawEvidenceRecord]:
    records: list[RawEvidenceRecord] = []
    fetched_at = utc_now_iso()
    for item in _firecrawl_results(payload):
        record = _record_from_firecrawl_item(
            provider=provider,
            symbol=symbol,
            item=item,
            fetched_at=fetched_at,
            index=len(records),
        )
        if record is None:
            continue
        records.append(record)
        if len(records) >= limit:
            break
    return records


def _firecrawl_results(payload: object) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("data", "results", "items", "web", "news"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = _firecrawl_results(value)
            if nested:
                return nested
    value = payload.get("success")
    if isinstance(value, dict):
        return _firecrawl_results(value)
    return []


def _record_from_firecrawl_item(
    *,
    provider: ProviderMetadata,
    symbol: str,
    item: dict[str, Any],
    fetched_at: str,
    index: int,
) -> RawEvidenceRecord | None:
    title = _first_text(item, "title", "name")
    url = _first_text(item, "url", "link")
    if not title and not url:
        return None
    source = _first_text(item, "source", "provider", "site") or _domain(url)
    published_at = _first_text(
        item,
        "published_at",
        "publishedAt",
        "publishedDate",
        "date",
    )
    summary = _sanitized_summary(_first_text(item, "description", "snippet", "summary"))
    record_hash = _stable_hash(f"{symbol}:{url}:{title}:{index}")
    evidence = [
        f"title={title or 'unknown'}",
        f"url={url or 'unknown'}",
        f"source={source or 'unknown'}",
    ]
    if published_at:
        evidence.append(f"published_at={published_at}")
    return RawEvidenceRecord(
        record_id=f"firecrawl-news:{symbol}:{record_hash}",
        source_kind="news",
        source_name=provider.provider_id,
        title=title or f"{symbol} Firecrawl news result",
        symbol=symbol,
        url=url or None,
        normalized_summary=summary,
        source_payload_ref=f"firecrawl-search://{record_hash}",
        observed_at=published_at or fetched_at,
        last_verified_at=fetched_at,
        source_attributions=[
            source_attribution(
                source_name=provider.provider_id,
                provider_type=provider.provider_type,
                source_role=provider.role,
                fetched_at=fetched_at,
                freshness="fresh" if published_at else "unknown",
                confidence=0.65,
                completeness=0.8 if summary else 0.6,
                notes=[
                    "firecrawl_search",
                    "news_source",
                    "raw_web_text_not_injected",
                    f"result_source={source or 'unknown'}",
                ],
            )
        ],
        evidence_vs_inference=EvidenceInferenceBreakdown(
            evidence=evidence,
            inference=[
                "Ticker-specific news query suggests company-specific relevance; downstream synthesis must verify materiality."
            ],
            uncertainty=[
                "Search snippets may omit context, and publication timestamps can be missing or provider-normalized."
            ],
        ),
        missing_fields=[] if summary else ["summary"],
    )


def _first_text(item: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _sanitized_summary(value: str) -> str:
    text = redact_sensitive_text(" ".join(value.split()))
    if len(text) > 500:
        return f"{text[:500]}...<truncated>"
    return text


def _domain(url: str) -> str:
    if not url:
        return ""
    return urlparse(url).netloc.lower()


def _stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _sec_configuration_note(*, enabled: bool, user_agent: str) -> str:
    if not enabled:
        return "sec_provider_disabled"
    if user_agent:
        return "sec_user_agent_configured"
    return "sec_user_agent_missing"


def _sec_ticker_index(payload: dict[str, Any]) -> dict[str, _SecTickerMatch]:
    index: dict[str, _SecTickerMatch] = {}
    for value in payload.values():
        if not isinstance(value, dict):
            continue
        ticker = str(value.get("ticker") or "").strip().upper()
        cik_value = value.get("cik_str")
        entity_name = str(value.get("title") or ticker).strip()
        if not ticker or cik_value is None:
            continue
        cik = str(cik_value).zfill(10)
        index[ticker] = _SecTickerMatch(
            symbol=ticker,
            cik=cik,
            entity_name=entity_name,
        )
    return index


def _records_from_submissions(
    *,
    provider: ProviderMetadata,
    symbol: str,
    match: _SecTickerMatch,
    payload: dict[str, Any],
    limit: int,
) -> list[RawEvidenceRecord]:
    if limit <= 0:
        return []
    recent = _recent_filings(payload)
    if not isinstance(recent, dict):
        return []

    accessions = _list_value(recent.get("accessionNumber"))
    forms = _list_value(recent.get("form"))
    filing_dates = _list_value(recent.get("filingDate"))
    report_dates = _list_value(recent.get("reportDate"))
    primary_documents = _list_value(recent.get("primaryDocument"))
    primary_descriptions = _list_value(recent.get("primaryDocDescription"))
    fetched_at = utc_now_iso()
    entity_name = str(payload.get("name") or match.entity_name).strip()
    records: list[RawEvidenceRecord] = []

    for index, accession_value in enumerate(accessions):
        record = _record_from_submission_row(
            provider=provider,
            symbol=symbol,
            match=match,
            accession_value=accession_value,
            forms=forms,
            filing_dates=filing_dates,
            report_dates=report_dates,
            primary_documents=primary_documents,
            primary_descriptions=primary_descriptions,
            index=index,
            fetched_at=fetched_at,
            entity_name=entity_name,
        )
        if record is None:
            continue
        records.append(record)
        if len(records) >= limit:
            break

    return records


def _record_from_company_facts(
    *,
    provider: ProviderMetadata,
    symbol: str,
    match: _SecTickerMatch,
    payload: dict[str, Any],
) -> RawEvidenceRecord | None:
    us_gaap = _us_gaap_facts(payload)
    if not us_gaap:
        return None

    fetched_at = utc_now_iso()
    entity_name = str(payload.get("entityName") or match.entity_name).strip()
    evidence: list[str] = []
    concept_notes: list[str] = []
    missing_fields: list[str] = []
    observed_candidates: list[str] = []

    for metric_id, label, concepts in SEC_COMPANY_FACT_CONCEPTS:
        fact = _latest_company_fact(us_gaap, concepts=concepts)
        if fact is None:
            missing_fields.append(f"company_fact:{metric_id}")
            continue
        concept, unit, item = fact
        value = item.get("val")
        end = _string_value(item.get("end"))
        filed = _string_value(item.get("filed"))
        form = _string_value(item.get("form"))
        period = _company_fact_period(item)
        if filed:
            observed_candidates.append(filed)
        elif end:
            observed_candidates.append(end)
        evidence.append(
            (
                f"{label}: {_format_fact_value(value, unit)} "
                f"for {period} ending {end or 'unknown'} "
                f"filed {filed or 'unknown'} via {form or 'unknown form'}."
            )
        )
        concept_notes.append(f"{metric_id}={concept}")

    if not evidence:
        return None

    observed_at = max(observed_candidates) if observed_candidates else fetched_at
    completeness = len(evidence) / len(SEC_COMPANY_FACT_CONCEPTS)
    url = SEC_COMPANY_FACTS_URL_TEMPLATE.format(cik=match.cik)
    return RawEvidenceRecord(
        record_id=f"sec-companyfacts:{symbol}:{match.cik}",
        source_kind="disclosure",
        source_name=provider.provider_id,
        title=f"{symbol} SEC company facts summary",
        symbol=symbol,
        entity_name=entity_name,
        region="US",
        url=url,
        observed_at=observed_at,
        last_verified_at=fetched_at,
        normalized_summary=(
            f"SEC company facts reports {len(evidence)} compact XBRL metric(s) "
            f"for {entity_name}: {'; '.join(evidence)}"
        ),
        source_payload_ref=f"sec-companyfacts://CIK{match.cik}",
        source_attributions=[
            source_attribution(
                source_name=provider.provider_id,
                provider_type=provider.provider_type,
                source_role=provider.role,
                fetched_at=fetched_at,
                freshness="fresh",
                confidence=0.95,
                completeness=completeness,
                notes=[
                    "sec_companyfacts_api",
                    f"cik={match.cik}",
                    *concept_notes,
                ],
            )
        ],
        evidence_vs_inference=EvidenceInferenceBreakdown(
            evidence=evidence,
            inference=[],
            uncertainty=[
                "SEC company facts aggregate normalized XBRL facts; filing text was not downloaded or parsed in this pass.",
                "Company-specific extension taxonomy concepts are not included in this compact V1 summary.",
            ],
        ),
        missing_fields=missing_fields,
    )


def _recent_filings(payload: dict[str, Any]) -> dict[str, Any] | None:
    filings = payload.get("filings")
    if not isinstance(filings, dict):
        return None
    recent = filings.get("recent")
    return recent if isinstance(recent, dict) else None


def _record_from_submission_row(
    *,
    provider: ProviderMetadata,
    symbol: str,
    match: _SecTickerMatch,
    accession_value: object,
    forms: list[object],
    filing_dates: list[object],
    report_dates: list[object],
    primary_documents: list[object],
    primary_descriptions: list[object],
    index: int,
    fetched_at: str,
    entity_name: str,
) -> RawEvidenceRecord | None:
    accession = _string_value(accession_value)
    form = _string_at(forms, index)
    if not accession or form not in SEC_RESEARCH_FORMS:
        return None

    filing_date = _string_at(filing_dates, index)
    report_date = _string_at(report_dates, index)
    primary_document = _string_at(primary_documents, index)
    primary_description = _string_at(primary_descriptions, index)
    observed_at = filing_date or fetched_at
    missing_fields = _sec_missing_fields(
        cik=match.cik,
        accession=accession,
        report_date=report_date,
        primary_document=primary_document,
    )
    url = _sec_archive_url(
        cik=match.cik,
        accession=accession,
        primary_document=primary_document,
    )
    filing_label = filing_date or "unknown date"

    return RawEvidenceRecord(
        record_id=f"sec:{symbol}:{accession}",
        source_kind="disclosure",
        source_name=provider.provider_id,
        title=f"{symbol} {form} filed {filing_label}",
        symbol=symbol,
        entity_name=entity_name,
        region="US",
        url=url,
        observed_at=observed_at,
        last_verified_at=fetched_at,
        normalized_summary=(
            f"SEC EDGAR submissions API reports {entity_name} filed "
            f"{form} accession {accession} on {filing_label}"
            f" for report date {report_date or 'unknown'}."
        ),
        source_payload_ref=f"sec-submissions://CIK{match.cik}/{accession}",
        source_attributions=[
            source_attribution(
                source_name=provider.provider_id,
                provider_type=provider.provider_type,
                source_role=provider.role,
                fetched_at=fetched_at,
                freshness="fresh",
                confidence=0.95,
                completeness=0.85 if not missing_fields else 0.7,
                notes=[
                    "sec_submissions_api",
                    f"cik={match.cik}",
                    f"form={form}",
                    _primary_document_note(primary_description),
                ],
            )
        ],
        evidence_vs_inference=EvidenceInferenceBreakdown(
            evidence=[
                f"SEC ticker mapping associates {symbol} with CIK {match.cik}.",
                (
                    f"SEC submissions metadata lists accession {accession} "
                    f"as form {form} filed on {filing_label}."
                ),
            ],
            inference=[],
            uncertainty=[
                "Filing text and XBRL facts were not downloaded or parsed in this pass."
            ],
        ),
        missing_fields=missing_fields,
    )


def _sec_missing_fields(
    *,
    cik: str,
    accession: str,
    report_date: str,
    primary_document: str,
) -> list[str]:
    missing_fields = []
    if not report_date:
        missing_fields.append("report_date")
    if not primary_document:
        missing_fields.append("primary_document")
    if _sec_archive_url(
        cik=cik,
        accession=accession,
        primary_document=primary_document,
    ) is None:
        missing_fields.append("url")
    return missing_fields


def _primary_document_note(primary_description: str) -> str:
    if primary_description:
        return f"primary_doc_description={primary_description}"
    return "primary_doc_description_missing"


def _list_value(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _us_gaap_facts(payload: dict[str, Any]) -> dict[str, Any] | None:
    facts = payload.get("facts")
    if not isinstance(facts, dict):
        return None
    us_gaap = facts.get("us-gaap")
    return us_gaap if isinstance(us_gaap, dict) else None


def _latest_company_fact(
    us_gaap: dict[str, Any],
    *,
    concepts: tuple[str, ...],
) -> tuple[str, str, dict[str, Any]] | None:
    candidates: list[tuple[tuple[str, str, str], str, str, dict[str, Any]]] = []
    for concept in concepts:
        concept_payload = us_gaap.get(concept)
        if not isinstance(concept_payload, dict):
            continue
        units = concept_payload.get("units")
        if not isinstance(units, dict):
            continue
        for unit, values in units.items():
            if unit != "USD" or not isinstance(values, list):
                continue
            for item in values:
                if not isinstance(item, dict) or item.get("val") is None:
                    continue
                candidates.append((_company_fact_sort_key(item), concept, unit, item))
    if not candidates:
        return None
    _, concept, unit, item = max(candidates, key=lambda candidate: candidate[0])
    return concept, unit, item


def _company_fact_sort_key(item: dict[str, Any]) -> tuple[str, str, str]:
    return (
        _string_value(item.get("filed")),
        _string_value(item.get("end")),
        _string_value(item.get("accn")),
    )


def _company_fact_period(item: dict[str, Any]) -> str:
    fy = _string_value(item.get("fy"))
    fp = _string_value(item.get("fp"))
    if fy and fp:
        return f"{fy} {fp}"
    return fy or fp or "unknown period"


def _format_fact_value(value: object, unit: str) -> str:
    if isinstance(value, bool):
        return f"{value} {unit}".strip()
    if isinstance(value, int):
        return f"{value:,} {unit}".strip()
    if isinstance(value, float):
        if value.is_integer():
            return f"{int(value):,} {unit}".strip()
        return f"{value:,.2f} {unit}".strip()
    return f"{_string_value(value) or 'unknown'} {unit}".strip()


def _string_value(value: object) -> str:
    return str(value).strip() if value is not None else ""


def _string_at(values: list[object], index: int) -> str:
    if index >= len(values):
        return ""
    return _string_value(values[index])


def _sec_archive_url(
    *,
    cik: str,
    accession: str,
    primary_document: str,
) -> str | None:
    if not accession or not primary_document:
        return None
    compact_accession = accession.replace("-", "")
    cik_for_archive = str(int(cik))
    return SEC_ARCHIVES_URL_TEMPLATE.format(
        cik=cik_for_archive,
        accession=compact_accession,
        primary_document=primary_document,
    )


def _provider_health_message(*, has_payload: bool, notes: list[str]) -> str:
    if has_payload:
        return "Provider returned normalized research evidence."
    if "provider_disabled" in notes:
        return "Provider is disabled by configuration."
    if "sec_user_agent_missing" in notes:
        return "Provider is configured but missing the required SEC User-Agent."
    if any(note.startswith("provider_error:") for note in notes):
        return "Provider failed to return normalized research evidence."
    if "ingestion_pending" in notes:
        return "Provider scaffold is visible, but ingestion is not implemented yet."
    return "Provider returned no normalized research evidence."


def _unique_attributions(
    attributions: list[DataSourceAttribution],
) -> list[DataSourceAttribution]:
    seen: set[tuple[str, str, str, str | None]] = set()
    unique: list[DataSourceAttribution] = []
    for attribution in attributions:
        key = (
            attribution.source_name,
            attribution.provider_type,
            attribution.source_role,
            attribution.fetched_at,
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(attribution)
    return unique
