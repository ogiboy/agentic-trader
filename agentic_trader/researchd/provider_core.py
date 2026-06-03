"""Shared contracts and helpers for research sidecar providers."""

import hashlib
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Callable, Protocol, cast, runtime_checkable
from urllib.parse import urlparse

import httpx

from agentic_trader.config import Settings
from agentic_trader.providers.base import metadata, source_attribution, utc_now_iso
from agentic_trader.schemas import (
    DataProviderKind,
    DataSourceAttribution,
    DataSourceRole,
    MacroEvent,
    ProviderMetadata,
    RawEvidenceRecord,
    ResearchProviderHealth,
    SocialSignal,
)
from agentic_trader.security import redact_sensitive_text
from agentic_trader.system.camofox_service import CamofoxServiceStatus

JsonObject = dict[str, object]
JsonFetcher = Callable[[str, Mapping[str, str], float], JsonObject]
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
        """
        Execute a subprocess command and return the completed process result.

        Parameters:
            command (list[str]): Command and arguments to execute.
            timeout_seconds (float): Maximum time in seconds to allow the command to run before timing out.
            env (Mapping[str, str]): Environment variables to use for the subprocess; typically a minimal, controlled env.

        Returns:
            subprocess.CompletedProcess[str]: Completed process including return code, stdout, and stderr.
        """
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
HealthFetcher = Callable[[str, float], JsonObject]


def _empty_raw_evidence_records() -> list[RawEvidenceRecord]:
    return []


def _empty_macro_events() -> list[MacroEvent]:
    return []


def _empty_social_signals() -> list[SocialSignal]:
    return []


def _empty_missing_reasons() -> list[str]:
    return []


@dataclass(frozen=True)
class ResearchProviderOutput:
    """Normalized output shape returned by sidecar research providers."""

    metadata: ProviderMetadata
    raw_evidence: list[RawEvidenceRecord] = field(
        default_factory=_empty_raw_evidence_records
    )
    macro_events: list[MacroEvent] = field(default_factory=_empty_macro_events)
    social_signals: list[SocialSignal] = field(default_factory=_empty_social_signals)
    missing_reasons: list[str] = field(default_factory=_empty_missing_reasons)


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


def provider_health_from_output(
    output: ResearchProviderOutput,
) -> ResearchProviderHealth:
    """
    Produce an operator-facing health summary derived from a provider's normalized output.

    Parameters:
        output (ResearchProviderOutput): Normalized output from a research provider.

    Returns:
        ResearchProviderHealth: Health summary that reflects whether the provider returned any payload (affects `freshness`, `source_role`, and `last_successful_update_at`), includes a human-readable `message`, and merges provider metadata notes with any `missing_reasons`.
    """
    meta = output.metadata
    has_payload = bool(
        output.raw_evidence or output.macro_events or output.social_signals
    )
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


def json_object(value: object) -> JsonObject | None:
    if not isinstance(value, dict):
        return None
    return {
        str(key): item for key, item in cast(Mapping[object, object], value).items()
    }


def object_sequence(value: object) -> list[object] | None:
    if isinstance(value, list):
        return cast(list[object], value)
    if isinstance(value, tuple):
        return list(cast(tuple[object, ...], value))
    return None


def object_list(value: object) -> list[object] | None:
    if not isinstance(value, list):
        return None
    return cast(list[object], value)


def json_object_list(value: object) -> list[JsonObject] | None:
    items = object_list(value)
    if items is None:
        return None
    objects: list[JsonObject] = []
    for item in items:
        item_object = json_object(item)
        if item_object is not None:
            objects.append(item_object)
    return objects


def callable_attr(value: object, name: str) -> Callable[[], object] | None:
    candidate: object = getattr(value, name, None)
    if not callable(candidate):
        return None
    return cast(Callable[[], object], candidate)


def object_attr(value: object, name: str) -> object | None:
    attribute: object | None = getattr(value, name, None)
    return attribute


def fetch_json(
    url: str,
    headers: Mapping[str, str],
    timeout_seconds: float,
) -> JsonObject:
    response = httpx.get(url, headers=dict(headers), timeout=timeout_seconds)
    response.raise_for_status()
    payload: object = response.json()
    json_payload = json_object(payload)
    if json_payload is None:
        raise ValueError("json_payload_not_object")
    return json_payload


def run_command(
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


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def safe_error_note(exc: BaseException) -> str:
    return f"provider_error:{type(exc).__name__}"


def first_text(item: Mapping[str, object], *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def sanitized_summary(value: str) -> str:
    text = redact_sensitive_text(" ".join(value.split()))
    if len(text) > 500:
        return f"{text[:500]}...<truncated>"
    return text


def domain_from_url(url: str) -> str:
    if not url:
        return ""
    return urlparse(url).netloc.lower()


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


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
