"""Firecrawl news research provider."""

import json
import os
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path

from agentic_trader.config import Settings
from agentic_trader.providers.base import metadata, source_attribution, utc_now_iso
from agentic_trader.researchd.provider_core import (
    MINIMAL_COMMAND_ENV_KEYS,
    CommandRunner,
    FirecrawlSdkSearcher,
    JsonObject,
    ResearchProviderOutput,
    callable_attr,
    domain_from_url,
    first_text,
    json_object,
    json_object_list,
    normalize_symbol,
    object_attr,
    object_sequence,
    run_command,
    sanitized_summary,
    stable_hash,
)
from agentic_trader.schemas import (
    EvidenceInferenceBreakdown,
    ProviderMetadata,
    RawEvidenceRecord,
)
from agentic_trader.security import redact_sensitive_text
from agentic_trader.system.tool_ownership import ownership_mode_for_tool
from agentic_trader.system.tool_roots import local_tool_manifest_notes


class FirecrawlNewsResearchProvider:
    """Opt-in Firecrawl news search provider with sanitized evidence output."""

    def __init__(
        self,
        *,
        settings: Settings,
        command_runner: CommandRunner | None = None,
        sdk_searcher: FirecrawlSdkSearcher | None = None,
    ) -> None:
        """
        Initialize the provider from application settings and optional execution/search hooks.

        Sets provider enablement, API key, CLI path, ownership mode, country (uppercased), a clamped timeout (1–300s), the command runner (injected or default), optional SDK searcher, a preference flag for SDK usage when no custom runner is supplied, and provider metadata/notes reflecting configuration and ownership.

        Parameters:
            settings: Application settings object that supplies provider flags, API key, CLI path, country, timeout, and ownership configuration.
            command_runner: Optional subprocess runner used to execute the Firecrawl CLI; when None the internal `run_command` is used.
            sdk_searcher: Optional SDK search callable used to perform Firecrawl searches directly; when provided it will be preferred when a command_runner is not supplied.
        """
        self._enabled = settings.research_firecrawl_enabled
        self._api_key = settings.firecrawl_api_key
        self._cli = settings.research_firecrawl_cli
        self._ownership_mode = ownership_mode_for_tool(settings, "firecrawl")
        self._country = settings.research_firecrawl_country.upper()
        self._timeout = min(
            max(settings.research_firecrawl_timeout_seconds, 1.0), 300.0
        )
        self._runner = command_runner or run_command
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
                f"ownership={self._ownership_mode}",
                "internal_sdk_first",
                (
                    "host_cli_fallback_enabled"
                    if self._ownership_mode == "host-owned"
                    else "host_cli_fallback_disabled"
                ),
                *local_tool_manifest_notes("firecrawl"),
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
        watched_symbols = [normalize_symbol(symbol) for symbol in symbols]
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
            symbol_records, symbol_missing, sdk_answered = self._sdk_symbol_records(
                symbol=symbol,
                per_symbol_limit=per_symbol_limit,
            )
            if not sdk_answered:
                symbol_records, symbol_missing = self._cli_symbol_records(
                    symbol=symbol,
                    per_symbol_limit=per_symbol_limit,
                )
            if not symbol_records:
                symbol_missing.append(f"firecrawl_no_news:{symbol}")
            missing_reasons.extend(symbol_missing)
            records.extend(symbol_records)
            if len(records) >= limit:
                break

        return ResearchProviderOutput(
            metadata=self._metadata,
            raw_evidence=records[:limit],
            missing_reasons=list(dict.fromkeys(missing_reasons)),
        )

    def _sdk_symbol_records(
        self,
        *,
        symbol: str,
        per_symbol_limit: int,
    ) -> tuple[list[RawEvidenceRecord], list[str], bool]:
        if not self._prefer_sdk:
            return [], [], False
        try:
            sdk_payload = _firecrawl_sdk_search_payload(
                query=_firecrawl_news_query(symbol),
                limit=per_symbol_limit,
                timeout_seconds=self._timeout,
                api_key=self._api_key,
                sdk_searcher=self._sdk_searcher,
            )
        except Exception as exc:
            return [], [f"firecrawl_sdk_failed:{symbol}:{type(exc).__name__}"], False
        if sdk_payload is None:
            return [], [], False
        return (
            _records_from_firecrawl_payload(
                provider=self._metadata,
                symbol=symbol,
                payload=sdk_payload,
                limit=per_symbol_limit,
            ),
            [],
            True,
        )

    def _cli_symbol_records(
        self,
        *,
        symbol: str,
        per_symbol_limit: int,
    ) -> tuple[list[RawEvidenceRecord], list[str]]:
        """
        Obtain Firecrawl news for a single symbol via the CLI fallback and convert the CLI JSON output into normalized evidence records.

        If the provider is not permitted to run the CLI, the CLI executable cannot be resolved, the command fails, the CLI exits non‑zero, or its output cannot be parsed as JSON, this returns an empty record list and one or more provider-specific missing-reason strings identifying the failure.

        Parameters:
            symbol (str): Uppercased symbol to query.
            per_symbol_limit (int): Maximum number of records to produce for this symbol.

        Returns:
            tuple[list[RawEvidenceRecord], list[str]]: A pair where the first element is the list of evidence records produced from the CLI payload (possibly empty), and the second element is a list of missing-reason strings (empty when records were produced successfully).
        """
        if self._ownership_mode != "host-owned":
            return [], [f"firecrawl_cli_fallback_disabled:{self._ownership_mode}"]
        cli_path = _resolve_cli(self._cli)
        if cli_path is None:
            return [], ["firecrawl_cli_missing"]
        try:
            completed = self._runner(
                _firecrawl_cli_command(
                    cli_path=cli_path,
                    symbol=symbol,
                    country=self._country,
                    limit=per_symbol_limit,
                ),
                self._timeout,
                _minimal_firecrawl_env(self._api_key),
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return [], [f"firecrawl_command_failed:{symbol}:{type(exc).__name__}"]
        if completed.returncode != 0:
            return [], [
                f"firecrawl_nonzero_exit:{symbol}:"
                f"{redact_sensitive_text(completed.stderr, max_length=120)}"
            ]
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return [], [f"firecrawl_json_parse_failed:{symbol}"]
        return (
            _records_from_firecrawl_payload(
                provider=self._metadata,
                symbol=symbol,
                payload=payload,
                limit=per_symbol_limit,
            ),
            [],
        )

    def cli_symbol_records(
        self,
        *,
        symbol: str,
        per_symbol_limit: int,
    ) -> tuple[list[RawEvidenceRecord], list[str]]:
        if not self._enabled:
            return [], ["provider_disabled"]
        return self._cli_symbol_records(
            symbol=symbol,
            per_symbol_limit=per_symbol_limit,
        )


def _minimal_firecrawl_env(api_key: str | None = None) -> dict[str, str]:
    """
    Build an environment dict suitable for running the Firecrawl CLI by copying a minimal set of whitelisted variables and optionally injecting a Firecrawl API key.

    Parameters:
        api_key (str | None): Optional API key to set as `FIRECRAWL_API_KEY`. If `None`, the function uses the current process environment's `FIRECRAWL_API_KEY` when present.

    Returns:
        dict[str, str]: A mapping of environment variable names to their values containing:
            - all keys from MINIMAL_COMMAND_ENV_KEYS that exist in the current process environment, and
            - `FIRECRAWL_API_KEY` set to `api_key` or the existing environment value when available.
    """
    env = {
        key: os.environ[key] for key in MINIMAL_COMMAND_ENV_KEYS if key in os.environ
    }
    resolved_api_key = api_key or os.environ.get("FIRECRAWL_API_KEY")
    if resolved_api_key:
        env["FIRECRAWL_API_KEY"] = resolved_api_key
    return env


def _firecrawl_news_query(symbol: str) -> str:
    return f"{symbol} stock news this week"


def _firecrawl_cli_command(
    *,
    cli_path: str,
    symbol: str,
    country: str,
    limit: int,
) -> list[str]:
    return [
        cli_path,
        "search",
        _firecrawl_news_query(symbol),
        "--sources",
        "news",
        "--country",
        country,
        "--limit",
        str(limit),
        "--json",
    ]


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
    mapping = json_object(value)
    if mapping is not None:
        return {key: _firecrawl_sdk_payload(item) for key, item in mapping.items()}
    sequence = object_sequence(value)
    if sequence is not None:
        return [_firecrawl_sdk_payload(item) for item in sequence]
    model_dump = callable_attr(value, "model_dump")
    if model_dump is not None:
        return _firecrawl_sdk_payload(model_dump())
    data = object_attr(value, "data")
    if data is not None:
        return {"data": _firecrawl_sdk_payload(data)}
    if hasattr(value, "__dict__"):
        object_vars = json_object(vars(value))
        if object_vars is None:
            return value
        return {
            key: _firecrawl_sdk_payload(item)
            for key, item in object_vars.items()
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


def _firecrawl_results(payload: object) -> list[JsonObject]:
    items = json_object_list(payload)
    if items is not None:
        return items
    payload_object = json_object(payload)
    if payload_object is None:
        return []
    for key in ("data", "results", "items", "web", "news"):
        value = payload_object.get(key)
        nested_items = json_object_list(value)
        if nested_items is not None:
            return nested_items
        nested_object = json_object(value)
        if nested_object is not None:
            nested = _firecrawl_results(nested_object)
            if nested:
                return nested
    success = json_object(payload_object.get("success"))
    if success is not None:
        return _firecrawl_results(success)
    return []


def _record_from_firecrawl_item(
    *,
    provider: ProviderMetadata,
    symbol: str,
    item: Mapping[str, object],
    fetched_at: str,
    index: int,
) -> RawEvidenceRecord | None:
    title = first_text(item, "title", "name")
    url = first_text(item, "url", "link")
    if not title and not url:
        return None
    source = first_text(item, "source", "provider", "site") or domain_from_url(url)
    published_at = first_text(
        item,
        "published_at",
        "publishedAt",
        "publishedDate",
        "date",
    )
    summary = sanitized_summary(first_text(item, "description", "snippet", "summary"))
    record_hash = stable_hash(f"{symbol}:{url}:{title}:{index}")
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
