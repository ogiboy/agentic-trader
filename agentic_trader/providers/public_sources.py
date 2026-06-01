"""Public-source provider adapters for canonical financial context."""

from collections.abc import Mapping
from typing import Any, Callable

import httpx

from agentic_trader.config import Settings
from agentic_trader.json_utils import object_dict_or_none as _object_mapping
from agentic_trader.providers.base import metadata, source_attribution, utc_now_iso
from agentic_trader.providers.sec_companyfacts import (
    FUNDAMENTAL_FIELDS,
    fundamental_snapshot_from_sec_companyfacts,
)
from agentic_trader.schemas import (
    DisclosureEvent,
    FundamentalSnapshot,
    ProviderMetadata,
    SymbolIdentity,
)
from agentic_trader.security import safe_exception_note

SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_COMPANY_FACTS_URL_TEMPLATE = (
    "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
)
JsonFetcher = Callable[[str, Mapping[str, str], float], dict[str, Any]]


class SecEdgarFundamentalProvider:
    """Opt-in SEC companyfacts provider for structured US fundamentals."""

    def __init__(
        self,
        settings: Settings,
        *,
        fetcher: JsonFetcher | None = None,
    ) -> None:
        """
        Initialize the SecEdgarFundamentalProvider with configuration and an optional HTTP JSON fetcher.

        Parameters:
            settings (Settings): Provider configuration and feature flags used to determine enablement, user-agent, and API keys.
            fetcher (JsonFetcher | None): Optional override for the HTTP JSON fetch function used to retrieve SEC endpoints. If omitted, the internal `_fetch_json` implementation is used. The fetcher must accept `(url: str, headers: dict, timeout_seconds: float)` and return a parsed `dict`.
        """
        self._settings = settings
        self._fetcher = fetcher or _fetch_json

    def metadata(self) -> ProviderMetadata:
        """
        Builds ProviderMetadata for the SEC EDGAR fundamentals provider.

        Reads provider configuration to determine enabled state and whether network access is required (based on the configured User-Agent). The returned metadata includes provider identifiers, role, priority, enabled/requires_network flags, and notes indicating the data sources and SEC configuration status.

        Returns:
            ProviderMetadata: Metadata describing the SEC EDGAR fundamentals provider, including provider_id, name, provider_type, role, priority, enabled, requires_network, and notes.
        """
        enabled = self._settings.research_sec_edgar_enabled
        user_agent = bool((self._settings.research_sec_edgar_user_agent or "").strip())
        return metadata(
            provider_id="sec_edgar_fundamentals",
            name="SEC EDGAR Fundamentals",
            provider_type="fundamental",
            role="primary",
            priority=10,
            enabled=enabled,
            requires_network=enabled and user_agent,
            notes=[
                "sec_10k_10q_8k_source",
                "sec_companyfacts_api",
                _sec_configuration_note(enabled=enabled, user_agent=user_agent),
            ],
        )

    def get_fundamental_data(self, symbol: SymbolIdentity) -> FundamentalSnapshot:
        """
        Fetches and returns a V1 FundamentalSnapshot for the given symbol using SEC EDGAR companyfacts.

        This will return either a populated FundamentalSnapshot derived from the SEC companyfacts JSON for the symbol's CIK, or a "missing" snapshot describing why structured fundamentals could not be provided. Failure reasons that produce a missing snapshot include: the symbol's region is not "US", the SEC provider is disabled in settings, an identifying User-Agent is not configured, failure to resolve the symbol to a CIK, or failure to fetch/parse the companyfacts payload.

        Parameters:
            symbol (SymbolIdentity): Identifier for the target security; only US-region symbols are supported.

        Returns:
            FundamentalSnapshot: A snapshot containing derived V1 fundamental metrics and attribution when successful, or a missing snapshot with explanatory notes and summary when not.
        """
        notes = ["sec_10k_10q_8k_source", "sec_companyfacts_api"]
        if symbol.region != "US":
            return _missing_fundamental_snapshot(
                symbol,
                source_name="sec_edgar",
                notes=[*notes, f"unsupported_region={symbol.region}"],
                summary="SEC EDGAR companyfacts supports US issuers only in V1.",
            )
        if not self._settings.research_sec_edgar_enabled:
            return _missing_fundamental_snapshot(
                symbol,
                source_name="sec_edgar",
                notes=[*notes, "provider_disabled"],
                summary="SEC EDGAR companyfacts ingestion is disabled by configuration.",
            )
        user_agent = (self._settings.research_sec_edgar_user_agent or "").strip()
        if not user_agent:
            return _missing_fundamental_snapshot(
                symbol,
                source_name="sec_edgar",
                notes=[*notes, "sec_user_agent_missing"],
                summary="SEC EDGAR companyfacts requires an identifying User-Agent.",
            )
        headers = {"Accept": "application/json", "User-Agent": user_agent}
        timeout = min(max(self._settings.request_timeout_seconds, 1.0), 30.0)
        try:
            ticker_index = _sec_ticker_index(
                self._fetcher(SEC_COMPANY_TICKERS_URL, headers, timeout)
            )
        except (httpx.HTTPError, ValueError, TypeError, TimeoutError) as exc:
            return _missing_fundamental_snapshot(
                symbol,
                source_name="sec_edgar",
                notes=[
                    *notes,
                    "sec_ticker_lookup_failed",
                    safe_exception_note("sec_edgar", exc),
                ],
                summary="SEC EDGAR ticker lookup failed.",
            )
        match = ticker_index.get(symbol.symbol.upper())
        if match is None:
            return _missing_fundamental_snapshot(
                symbol,
                source_name="sec_edgar",
                notes=[*notes, f"sec_cik_missing:{symbol.symbol.upper()}"],
                summary="SEC EDGAR CIK lookup did not find this symbol.",
            )
        try:
            facts_payload = self._fetcher(
                SEC_COMPANY_FACTS_URL_TEMPLATE.format(cik=match["cik"]),
                headers,
                timeout,
            )
        except (httpx.HTTPError, ValueError, TypeError, TimeoutError) as exc:
            return _missing_fundamental_snapshot(
                symbol,
                source_name="sec_edgar",
                notes=[
                    *notes,
                    f"sec_companyfacts_fetch_failed:{symbol.symbol.upper()}",
                    safe_exception_note("sec_edgar", exc),
                ],
                summary="SEC EDGAR companyfacts fetch failed.",
            )
        return fundamental_snapshot_from_sec_companyfacts(
            symbol,
            cik=match["cik"],
            entity_name=match["entity_name"],
            payload=facts_payload,
        )


class FinnhubFundamentalProvider:
    """Finnhub scaffold for optional free-friendly enrichment."""

    def __init__(self, settings: Settings) -> None:
        """
        Initialize the provider with runtime settings.

        Parameters:
            settings (Settings): Configuration and credentials used by the provider; stored on `self._settings`.
        """
        self._settings = settings

    def metadata(self) -> ProviderMetadata:
        """
        Provide metadata describing the Finnhub fundamentals provider configuration.

        Returns:
            ProviderMetadata: Metadata with provider_id "finnhub_fundamentals", name "Finnhub Fundamentals",
            provider_type "fundamental", role "fallback", priority 40, boolean `enabled` and `requires_network`
            determined by whether an API key is configured, and `notes` that indicate optional free enrichment,
            the API key status, and that ingestion is pending.
        """
        configured = bool(self._settings.finnhub_api_key)
        return metadata(
            provider_id="finnhub_fundamentals",
            name="Finnhub Fundamentals",
            provider_type="fundamental",
            role="fallback",
            priority=40,
            enabled=configured,
            requires_network=configured,
            notes=[
                "optional_free_enrichment",
                "api_key_configured" if configured else "api_key_missing",
                "ingestion_pending",
            ],
        )

    def get_fundamental_data(self, symbol: SymbolIdentity) -> FundamentalSnapshot:
        """
        Return a placeholder FundamentalSnapshot for the given symbol indicating Finnhub enrichment is pending.

        Parameters:
            symbol (SymbolIdentity): The identity of the security to describe.

        Returns:
            FundamentalSnapshot: Snapshot with:
                - symbol_identity set to `symbol`
                - `fx_exposure` set to `"unknown"`
                - `attribution` identifying `source_name="finnhub"`, `provider_type="fundamental"`, `source_role="missing"`, `freshness="missing"`, `fetched_at` set to the current UTC timestamp, and `notes` containing `"optional_free_enrichment"`, either `"api_key_configured"` or `"api_key_missing"` depending on configuration, and `"ingestion_pending"`
                - `missing_fields` equal to `FUNDAMENTAL_FIELDS`
                - `summary` stating that structured fundamental ingestion is not implemented yet
        """
        configured = bool(self._settings.finnhub_api_key)
        return FundamentalSnapshot(
            symbol_identity=symbol,
            fx_exposure="unknown",
            attribution=source_attribution(
                source_name="finnhub",
                provider_type="fundamental",
                source_role="missing",
                fetched_at=utc_now_iso(),
                freshness="missing",
                notes=[
                    "optional_free_enrichment",
                    "api_key_configured" if configured else "api_key_missing",
                    "ingestion_pending",
                ],
            ),
            missing_fields=list(FUNDAMENTAL_FIELDS),
            summary=(
                "Finnhub enrichment is configured as an optional source, but "
                "structured fundamental ingestion is not implemented yet."
            ),
        )


class FmpFundamentalProvider:
    """Financial Modeling Prep scaffold for optional free-friendly enrichment."""

    def __init__(self, settings: Settings) -> None:
        """
        Initialize the provider with runtime settings.

        Parameters:
            settings (Settings): Configuration and credentials used by the provider; stored on `self._settings`.
        """
        self._settings = settings

    def metadata(self) -> ProviderMetadata:
        """
        Provider metadata for the Financial Modeling Prep fundamentals adapter.

        Returns:
            ProviderMetadata: Metadata describing the provider (provider_id "fmp_fundamentals", name "Financial Modeling Prep Fundamentals", provider_type "fundamental", role "fallback", priority 50). The `enabled` and `requires_network` flags reflect whether an API key is configured. `notes` contains "optional_free_enrichment", either "api_key_configured" or "api_key_missing" depending on configuration, and "ingestion_pending".
        """
        configured = bool(self._settings.fmp_api_key)
        return metadata(
            provider_id="fmp_fundamentals",
            name="Financial Modeling Prep Fundamentals",
            provider_type="fundamental",
            role="fallback",
            priority=50,
            enabled=configured,
            requires_network=configured,
            notes=[
                "optional_free_enrichment",
                "api_key_configured" if configured else "api_key_missing",
                "ingestion_pending",
            ],
        )

    def get_fundamental_data(self, symbol: SymbolIdentity) -> FundamentalSnapshot:
        """
        Produce a FundamentalSnapshot that marks Financial Modeling Prep enrichment as pending for the given symbol.

        Parameters:
            symbol (SymbolIdentity): The symbol identity for which the snapshot is produced.

        Returns:
            FundamentalSnapshot: Snapshot with `fx_exposure` set to `"unknown"`, `missing_fields` populated from `FUNDAMENTAL_FIELDS`, and `attribution` notes indicating optional enrichment, API key status, and that ingestion is pending.
        """
        configured = bool(self._settings.fmp_api_key)
        return FundamentalSnapshot(
            symbol_identity=symbol,
            fx_exposure="unknown",
            attribution=source_attribution(
                source_name="fmp",
                provider_type="fundamental",
                source_role="missing",
                fetched_at=utc_now_iso(),
                freshness="missing",
                notes=[
                    "optional_free_enrichment",
                    "api_key_configured" if configured else "api_key_missing",
                    "ingestion_pending",
                ],
            ),
            missing_fields=list(FUNDAMENTAL_FIELDS),
            summary=(
                "Financial Modeling Prep enrichment is configured as an optional "
                "source, but structured fundamental ingestion is not implemented yet."
            ),
        )


class KapDisclosureProvider:
    """KAP scaffold for future Turkey public disclosure ingestion."""

    def __init__(self, settings: Settings) -> None:
        """
        Initialize the provider with runtime settings.

        Parameters:
            settings (Settings): Configuration and credentials used by the provider; stored on `self._settings`.
        """
        self._settings = settings

    def metadata(self) -> ProviderMetadata:
        """
        Provider metadata for the KAP (Turkey public disclosure) scaffold.

        Returns:
            ProviderMetadata: Metadata for the KAP disclosures provider with
            provider_id="kap_disclosures", name="KAP Disclosures", provider_type="disclosure",
            role="primary", priority=10, enabled=True, requires_network=False, and notes
            ["turkey_public_disclosure_platform", "ingestion_pending"].
        """
        return metadata(
            provider_id="kap_disclosures",
            name="KAP Disclosures",
            provider_type="disclosure",
            role="primary",
            priority=10,
            enabled=True,
            requires_network=False,
            notes=["turkey_public_disclosure_platform", "ingestion_pending"],
        )

    def get_disclosures(
        self, symbol: SymbolIdentity, *, limit: int
    ) -> list[DisclosureEvent]:
        """
        Return disclosure events for the given symbol (scaffold; not implemented).

        Parameters:
            symbol (SymbolIdentity): Security identifier (ignored).
            limit (int): Maximum number of events requested (ignored).

        Returns:
            list[DisclosureEvent]: An empty list because disclosure ingestion is not implemented.
        """
        _ = (symbol, limit, self._settings)
        return []


def _missing_fundamental_snapshot(
    symbol: SymbolIdentity,
    *,
    source_name: str,
    notes: list[str],
    summary: str,
) -> FundamentalSnapshot:
    """
    Builds a FundamentalSnapshot representing unavailable or missing fundamental data for a symbol.

    Parameters:
        symbol (SymbolIdentity): The symbol identity for which the snapshot is created.
        source_name (str): Source identifier used in the attribution entry (e.g., "sec_edgar").
        notes (list[str]): Attribution notes describing why data is missing or any contextual details.
        summary (str): Human-readable summary explaining the missing-data state.

    Returns:
        FundamentalSnapshot: A snapshot with `fx_exposure="unknown"`, attribution set with
        `provider_type="fundamental"`, `source_role="missing"`, `freshness="missing"`,
        `fetched_at` set to the current UTC time, `missing_fields` populated from FUNDAMENTAL_FIELDS,
        and the provided `summary`.
    """
    return FundamentalSnapshot(
        symbol_identity=symbol,
        fx_exposure="unknown",
        attribution=source_attribution(
            source_name=source_name,
            provider_type="fundamental",
            source_role="missing",
            fetched_at=utc_now_iso(),
            freshness="missing",
            notes=notes,
        ),
        missing_fields=list(FUNDAMENTAL_FIELDS),
        summary=summary,
    )


def _fetch_json(
    url: str, headers: Mapping[str, str], timeout_seconds: float
) -> dict[str, Any]:
    """
    Fetches JSON from the given URL via HTTP GET and returns the parsed JSON object.

    Performs a blocking GET request using the provided headers and timeout, calls raise_for_status() on the response, and ensures the parsed JSON is a mapping.

    Parameters:
        url (str): The request URL.
        headers (Mapping[str, str]): Headers to include with the request; will be copied into a plain dict.
        timeout_seconds (float): Request timeout in seconds.

    Returns:
        dict[str, Any]: The parsed JSON object.

    Raises:
        httpx.HTTPError: If the HTTP request failed or returned a non-success status.
        ValueError: If the response JSON is not a JSON object (mapping).
    """
    response = httpx.get(url, headers=dict(headers), timeout=timeout_seconds)
    response.raise_for_status()
    payload = response.json()
    payload_object = _object_mapping(payload)
    if payload_object is None:
        raise ValueError("JSON response was not an object")
    return payload_object


def _sec_configuration_note(*, enabled: bool, user_agent: bool) -> str:
    """
    Produce a short configuration note describing whether the SEC provider is enabled and whether a User-Agent is configured.

    Parameters:
        enabled (bool): True if SEC ingestion is enabled in settings.
        user_agent (bool): True if a non-empty User-Agent is configured.

    Returns:
        str: One of:
            - "sec_provider_disabled" when `enabled` is False.
            - "sec_user_agent_configured" when `enabled` is True and `user_agent` is True.
            - "sec_user_agent_missing" when `enabled` is True and `user_agent` is False.
    """
    if not enabled:
        return "sec_provider_disabled"
    if user_agent:
        return "sec_user_agent_configured"
    return "sec_user_agent_missing"


def _sec_ticker_index(payload: dict[str, Any]) -> dict[str, dict[str, str]]:
    """
    Construct an index mapping normalized ticker symbols to their CIK and entity name from an SEC company-tickers payload.

    Parameters:
        payload (dict[str, Any]): Parsed JSON object from the SEC company_tickers endpoint where each value may describe a company (expected keys include "ticker", "cik_str", and "title").

    Returns:
        dict[str, dict[str, str]]: A mapping keyed by uppercase ticker symbol to a dictionary with:
            - "cik": the 10-digit zero-padded CIK string
            - "entity_name": the company's title (or the ticker if title is missing)
        Only entries with a non-empty ticker and a successfully normalized CIK are included.
    """
    result: dict[str, dict[str, str]] = {}
    for item in payload.values():
        item_payload = _object_mapping(item)
        if item_payload is None:
            continue
        symbol = str(item_payload.get("ticker") or "").strip().upper()
        cik = _normalize_cik(item_payload.get("cik_str"))
        if not symbol or cik is None:
            continue
        result[symbol] = {
            "cik": cik,
            "entity_name": str(item_payload.get("title") or symbol).strip(),
        }
    return result


def _normalize_cik(value: object) -> str | None:
    """
    Normalize various CIK representations into a 10-digit, zero-padded CIK string.

    Accepts integers, numeric strings, or strings containing digits; leading/trailing whitespace is ignored. If the input is None, empty after stripping, or contains no digits, returns None.

    Parameters:
        value (object): Input CIK representation (e.g., int, str, or other object with a digit-containing string form).

    Returns:
        str | None: A 10-digit zero-padded CIK string when digits are present, `None` otherwise.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return f"{int(text):010d}"
    except ValueError:
        digits = "".join(char for char in text if char.isdigit())
        return f"{int(digits):010d}" if digits else None
