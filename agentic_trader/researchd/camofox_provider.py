"""Camofox browser readiness research provider."""

from urllib.parse import urlparse

import httpx

from agentic_trader.config import Settings
from agentic_trader.providers.base import metadata, source_attribution, utc_now_iso
from agentic_trader.researchd.provider_core import (
    CamofoxServiceStatusBuilder,
    HealthFetcher,
    JsonObject,
    ResearchProviderOutput,
    json_object,
    safe_error_note,
    stable_hash,
)
from agentic_trader.schemas import (
    EvidenceInferenceBreakdown,
    ProviderMetadata,
    RawEvidenceRecord,
)
from agentic_trader.security import is_loopback_host
from agentic_trader.system.camofox_service import build_camofox_service_status
from agentic_trader.system.tool_roots import local_tool_manifest_notes


class CamofoxBrowserResearchProvider:
    """Opt-in local Camofox health provider for browser-backed research readiness."""

    def __init__(
        self,
        *,
        settings: Settings,
        health_fetcher: HealthFetcher | None = None,
        service_status_builder: CamofoxServiceStatusBuilder | None = None,
    ) -> None:
        """
        Initialize the CamofoxBrowserResearchProvider with configuration and injectable helpers.

        Parameters:
            settings (Settings): Application settings used to determine enabled state, base URL, timeouts, and provider configuration.
            health_fetcher (callable | None): Optional function to fetch the Camofox health JSON from a URL; if omitted a default HTTP fetcher is used.
            service_status_builder (callable | None): Optional factory that builds a CamofoxServiceStatus from settings; if omitted a default builder is used.
        """
        self._settings = settings
        self._enabled = settings.research_camofox_enabled
        self._base_url = settings.research_camofox_base_url.rstrip("/")
        parsed_base_url = urlparse(self._base_url)
        self._loopback_only = parsed_base_url.scheme in {
            "http",
            "https",
        } and is_loopback_host(parsed_base_url.hostname or "")
        self._timeout = min(max(settings.request_timeout_seconds, 1.0), 10.0)
        self._fetcher = health_fetcher or _fetch_camofox_health
        self._service_status_builder = (
            service_status_builder or build_camofox_service_status
        )
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
                *local_tool_manifest_notes("camofox-browser"),
            ],
        )

    def metadata(self) -> ProviderMetadata:
        return self._metadata

    def _missing_output(self, *reasons: str) -> ResearchProviderOutput:
        return ResearchProviderOutput(
            metadata=self._metadata,
            missing_reasons=list(reasons),
        )

    def _launch_failure_output(self) -> ResearchProviderOutput | None:
        service_status = self._service_status_builder(self._settings)
        if (
            service_status.app_owned
            and service_status.base_url.rstrip("/") == self._base_url
            and not service_status.health_ok
        ):
            return self._missing_output("camofox_browser_launch_failed")
        return None

    def _health_payload(self) -> JsonObject | ResearchProviderOutput:
        try:
            return self._fetcher(f"{self._base_url}/health", self._timeout)
        except (httpx.HTTPError, ValueError, TypeError, TimeoutError) as exc:
            return self._missing_output("camofox_health_failed", safe_error_note(exc))

    def _health_record(
        self, payload: JsonObject, *, fetched_at: str
    ) -> RawEvidenceRecord:
        ok = bool(payload.get("ok"))
        return RawEvidenceRecord(
            record_id=f"camofox-health:{stable_hash(self._base_url)}",
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
            source_payload_ref=f"camofox-health://{stable_hash(self._base_url)}",
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

    def collect(self, *, symbols: list[str], limit: int) -> ResearchProviderOutput:
        _ = (symbols, limit)
        if not self._enabled:
            return self._missing_output("provider_disabled")
        if not self._loopback_only:
            return self._missing_output("camofox_base_url_must_be_loopback")
        launch_failure = self._launch_failure_output()
        if launch_failure is not None:
            return launch_failure
        payload = self._health_payload()
        if isinstance(payload, ResearchProviderOutput):
            return payload
        fetched_at = utc_now_iso()
        ok = bool(payload.get("ok"))
        record = self._health_record(payload, fetched_at=fetched_at)
        missing = [] if ok else ["camofox_unhealthy"]
        return ResearchProviderOutput(
            metadata=self._metadata,
            raw_evidence=[record],
            missing_reasons=missing,
        )


def _fetch_camofox_health(url: str, timeout_seconds: float) -> JsonObject:
    response = httpx.get(url, timeout=timeout_seconds)
    response.raise_for_status()
    payload: object = response.json()
    json_payload = json_object(payload)
    if json_payload is None:
        raise ValueError("camofox_health_payload_not_object")
    return json_payload
