"""Public-source provider adapters for canonical financial context."""

from collections.abc import Mapping
from typing import Any, Callable, TypeGuard

import httpx

from agentic_trader.config import Settings
from agentic_trader.providers.base import metadata, source_attribution, utc_now_iso
from agentic_trader.schemas import (
    DisclosureEvent,
    FundamentalSnapshot,
    ProviderMetadata,
    SymbolIdentity,
)
from agentic_trader.security import safe_exception_note

FUNDAMENTAL_FIELDS = (
    "revenue_growth",
    "profitability_stability",
    "cash_flow_alignment",
    "debt_risk",
    "reinvestment_potential",
)
SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_COMPANY_FACTS_URL_TEMPLATE = (
    "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
)
SEC_RESEARCH_FORMS = frozenset({"10-K", "10-K/A", "10-Q", "10-Q/A"})
SEC_ANNUAL_FORMS = frozenset({"10-K", "10-K/A"})
SEC_COMPANY_FACT_CONCEPTS: dict[str, tuple[str, ...]] = {
    "revenue": (
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ),
    "net_income": ("NetIncomeLoss",),
    "assets": ("Assets",),
    "liabilities": ("Liabilities",),
    "operating_cash_flow": ("NetCashProvidedByUsedInOperatingActivities",),
    "cash": ("CashAndCashEquivalentsAtCarryingValue",),
}
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
        return _fundamental_snapshot_from_sec_companyfacts(
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


def _fundamental_snapshot_from_sec_companyfacts(
    symbol: SymbolIdentity,
    *,
    cik: str,
    entity_name: str,
    payload: dict[str, Any],
) -> FundamentalSnapshot:
    """
    Convert an SEC companyfacts JSON payload into a V1 FundamentalSnapshot containing derived fundamental metrics, source attribution, completeness, and a human-readable summary.
    
    The function extracts US-GAAP facts from the provided payload, selects the latest reported facts for each target metric, derives five V1 ratios (revenue_growth, profitability_stability, cash_flow_alignment, debt_risk, reinvestment_potential), and computes an overall completeness score. If the payload lacks usable US-GAAP facts or does not provide enough metrics to produce a positive completeness score, a missing-style FundamentalSnapshot (attributed to "sec_edgar") is returned instead.
    
    Parameters:
        symbol (SymbolIdentity): Identity for the requested symbol; used in the returned snapshot.
        cik (str): Normalized 10-digit SEC CIK for the entity; included in attribution notes.
        entity_name (str): Fallback entity name used when payload does not include an entityName.
        payload (dict[str, Any]): Parsed SEC companyfacts JSON for the CIK.
    
    Returns:
        FundamentalSnapshot: A snapshot populated with derived metrics, attribution (including completeness and confidence), missing_fields and a formatted summary; or a missing snapshot attributed to "sec_edgar" when US-GAAP facts are unavailable or insufficient.
    """
    facts = payload.get("facts")
    us_gaap = facts.get("us-gaap") if isinstance(facts, dict) else None
    if not isinstance(us_gaap, dict):
        return _missing_fundamental_snapshot(
            symbol,
            source_name="sec_edgar",
            notes=["sec_companyfacts_api", f"cik={cik}", "us_gaap_facts_missing"],
            summary="SEC EDGAR companyfacts payload did not include usable US-GAAP facts.",
        )

    latest: dict[str, tuple[str, str, dict[str, Any]]] = {}
    missing_fields: list[str] = []
    concept_notes: list[str] = []
    for metric_id, concepts in SEC_COMPANY_FACT_CONCEPTS.items():
        fact = _latest_company_fact(us_gaap, concepts=concepts)
        if fact is None:
            missing_fields.append(f"company_fact:{metric_id}")
            continue
        latest[metric_id] = fact
        concept_notes.append(f"{metric_id}={fact[0]}")

    revenue_growth = _growth_ratio(us_gaap, SEC_COMPANY_FACT_CONCEPTS["revenue"])
    revenue = _fact_number(latest.get("revenue"))
    net_income = _fact_number(latest.get("net_income"))
    assets = _fact_number(latest.get("assets"))
    liabilities = _fact_number(latest.get("liabilities"))
    operating_cash_flow = _fact_number(latest.get("operating_cash_flow"))
    cash = _fact_number(latest.get("cash"))

    profitability_stability = _ratio(net_income, revenue)
    cash_flow_alignment = _ratio(operating_cash_flow, net_income)
    debt_risk = _ratio(liabilities, assets)
    reinvestment_potential = _ratio(cash, assets)
    derived_values = {
        "revenue_growth": revenue_growth,
        "profitability_stability": profitability_stability,
        "cash_flow_alignment": cash_flow_alignment,
        "debt_risk": debt_risk,
        "reinvestment_potential": reinvestment_potential,
    }
    missing_fields.extend(
        field for field, value in derived_values.items() if value is None
    )
    completeness = 1.0 - (len(set(missing_fields)) / (len(FUNDAMENTAL_FIELDS) + 6))
    completeness = _clamp_ratio(completeness)
    if completeness <= 0:
        return _missing_fundamental_snapshot(
            symbol,
            source_name="sec_edgar",
            notes=["sec_companyfacts_api", f"cik={cik}", *concept_notes],
            summary="SEC EDGAR companyfacts did not provide enough metrics for V1 fundamentals.",
        )

    entity = str(payload.get("entityName") or entity_name or symbol.symbol).strip()
    return FundamentalSnapshot(
        symbol_identity=symbol,
        revenue_growth=revenue_growth,
        profitability_stability=profitability_stability,
        cash_flow_alignment=cash_flow_alignment,
        debt_risk=debt_risk,
        fx_exposure="unknown",
        reinvestment_potential=reinvestment_potential,
        attribution=source_attribution(
            source_name="sec_edgar",
            provider_type="fundamental",
            source_role="primary",
            fetched_at=utc_now_iso(),
            freshness="fresh",
            confidence=0.95,
            completeness=completeness,
            notes=[
                "sec_companyfacts_api",
                f"cik={cik}",
                "raw_filing_text_not_downloaded",
                *concept_notes,
            ],
        ),
        missing_fields=sorted(set(missing_fields)),
        summary=(
            f"SEC companyfacts produced structured V1 fundamentals for {entity}: "
            f"revenue_growth={_format_optional_ratio(revenue_growth)}, "
            f"profitability={_format_optional_ratio(profitability_stability)}, "
            f"cash_flow_alignment={_format_optional_ratio(cash_flow_alignment)}, "
            f"debt_risk={_format_optional_ratio(debt_risk)}."
        ),
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
    if not isinstance(payload, dict):
        raise ValueError("JSON response was not an object")
    return payload


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
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("ticker") or "").strip().upper()
        cik = _normalize_cik(item.get("cik_str"))
        if not symbol or cik is None:
            continue
        result[symbol] = {
            "cik": cik,
            "entity_name": str(item.get("title") or symbol).strip(),
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


def _latest_company_fact(
    us_gaap: dict[str, Any], *, concepts: tuple[str, ...]
) -> tuple[str, str, dict[str, Any]] | None:
    """
    Select the most recent company fact entry from the provided US-GAAP facts for the given concepts.
    
    Parameters:
        us_gaap (dict[str, Any]): The `"us-gaap"` section from an SEC companyfacts payload.
        concepts (tuple[str, ...]): Candidate US-GAAP concept names to consider.
    
    Returns:
        tuple[str, str, dict[str, Any]] | None: A `(concept, unit, item)` tuple for the latest matching fact, or `None` if no matching entries are found.
    """
    entries = _company_fact_entries(us_gaap, concepts=concepts)
    if not entries:
        return None
    return max(entries, key=lambda item: _fact_sort_key(item[2]))


def _company_fact_entries(
    us_gaap: dict[str, Any], *, concepts: tuple[str, ...]
) -> list[tuple[str, str, dict[str, Any]]]:
    """
    Collect all company fact entries from a US-GAAP payload for the provided candidate concepts.
    
    Parameters:
        us_gaap (dict[str, Any]): The `facts["us-gaap"]` section of a companyfacts payload.
        concepts (tuple[str, ...]): Candidate US-GAAP concept identifiers to collect entries for.
    
    Returns:
        entries (list[tuple[str, str, dict[str, Any]]]): A list of tuples `(concept, unit, item)` for every supported fact item found for the given concepts.
    """
    entries: list[tuple[str, str, dict[str, Any]]] = []
    for concept in concepts:
        entries.extend(_company_fact_entries_for_concept(us_gaap, concept))
    return entries


def _company_fact_entries_for_concept(
    us_gaap: dict[str, Any], concept: str
) -> list[tuple[str, str, dict[str, Any]]]:
    """
    Collect supported company-fact entries for a specific US-GAAP concept across all reported units.
    
    Parameters:
        us_gaap (dict[str, Any]): The "us-gaap" section of an SEC companyfacts payload.
        concept (str): The US-GAAP concept name to collect entries for.
    
    Returns:
        entries (list[tuple[str, str, dict[str, Any]]]): A list of tuples `(concept, unit, item)` for each supported fact item found.
        Returns an empty list if the concept is missing or its `units` structure is not a dict.
    """
    concept_payload = us_gaap.get(concept)
    if not isinstance(concept_payload, dict):
        return []
    units = concept_payload.get("units")
    if not isinstance(units, dict):
        return []
    entries: list[tuple[str, str, dict[str, Any]]] = []
    for unit, unit_entries in units.items():
        entries.extend(_company_fact_entries_for_unit(concept, str(unit), unit_entries))
    return entries


def _company_fact_entries_for_unit(
    concept: str, unit: str, unit_entries: object
) -> list[tuple[str, str, dict[str, Any]]]:
    """
    Collects supported company fact entries for a specific concept and unit.
    
    Parameters:
        concept (str): US-GAAP concept identifier to associate with each entry.
        unit (str): Unit key (e.g., "USD") to associate with each entry.
        unit_entries (object): Raw entries for the unit; expected to be a list of item dicts.
    
    Returns:
        list[tuple[str, str, dict[str, Any]]]: List of `(concept, unit, item)` tuples for items that are supported company fact entries. Returns an empty list if `unit_entries` is not a list or contains no supported items.
    """
    if not isinstance(unit_entries, list):
        return []
    entries: list[tuple[str, str, dict[str, Any]]] = []
    for item in unit_entries:
        if _is_supported_company_fact_item(item, concept=concept, unit=unit):
            entries.append((concept, unit, item))
    return entries


def _is_supported_company_fact_item(
    item: object, *, concept: str, unit: str
) -> TypeGuard[dict[str, Any]]:
    """
    Determine whether a company fact item is supported for inclusion.
    
    Parameters:
        item: Candidate company fact item to test; may be any object.
        concept: The US-GAAP concept identifier associated with the item (used when extracting the numeric value).
        unit: The unit identifier associated with the item (used when extracting the numeric value).
    
    Returns:
        `True` if `item` is a dict, contains a numeric `val` for the given `concept`/`unit`, and its `form` is empty or is listed in `SEC_RESEARCH_FORMS`; `False` otherwise.
    """
    if not isinstance(item, dict):
        return False
    if _fact_number((concept, unit, item)) is None:
        return False
    form = str(item.get("form") or "").upper()
    return not form or form in SEC_RESEARCH_FORMS


def _growth_ratio(us_gaap: dict[str, Any], concepts: tuple[str, ...]) -> float | None:
    """
    Compute year-over-year growth using the two most recent annual US-GAAP fact entries for the provided concepts.
    
    Selects annual fact entries for the given concepts, picks the two most recent by filing/end dates, and returns (latest - previous) / abs(previous). Returns `None` if fewer than two annual entries exist, if the latest or previous value cannot be parsed as a number, or if the previous value is zero.
    
    Parameters:
        us_gaap (dict[str, Any]): The `us-gaap` section from an SEC companyfacts payload.
        concepts (tuple[str, ...]): Candidate US-GAAP concept names to search for (in priority order).
    
    Returns:
        float | None: Growth rate as a signed fraction (e.g., 0.10 for 10% growth) if computable, `None` otherwise.
    """
    entries = [
        item
        for item in _company_fact_entries(us_gaap, concepts=concepts)
        if _is_annual_fact(item[2])
    ]
    entries.sort(key=lambda item: _fact_sort_key(item[2]), reverse=True)
    if len(entries) < 2:
        return None
    latest = _fact_number(entries[0])
    previous = _fact_number(entries[1])
    if latest is None or previous in (None, 0):
        return None
    return (latest - previous) / abs(previous)


def _is_annual_fact(item: dict[str, Any]) -> bool:
    """
    Determine whether a companyfact item represents an annual (yearly) fact.
    
    Parameters:
        item (dict[str, Any]): A single companyfact entry as returned in the SEC `companyfacts` payload.
    
    Returns:
        bool: `True` if the item is reported on an annual basis (annual filing indicator, fiscal period "FY", or a calendar-year frame that is not quarterly and not an interim), `False` otherwise.
    """
    form = str(item.get("form") or "").upper()
    fiscal_period = str(item.get("fp") or "").upper()
    frame = str(item.get("frame") or "").upper()
    return (
        form in SEC_ANNUAL_FORMS
        or fiscal_period == "FY"
        or (frame.startswith("CY") and "Q" not in frame and not frame.endswith("I"))
    )


def _fact_sort_key(item: dict[str, Any]) -> tuple[str, str]:
    """
    Produce a deterministic sort key for a company fact item based on its filing and period end timestamps.
    
    Parameters:
        item (dict[str, Any]): A company-fact mapping; keys `"filed"` and `"end"` are read and coerced to strings (missing or falsy values become empty strings).
    
    Returns:
        tuple[str, str]: A `(filed, end)` tuple of strings suitable for chronological sorting.
    """
    filed = str(item.get("filed") or "")
    end = str(item.get("end") or "")
    return filed, end


def _fact_number(fact: tuple[str, str, dict[str, Any]] | None) -> float | None:
    """
    Extract a numeric value from a company fact tuple.
    
    Reads the third element's `val` field from `fact` and converts it to a float. Accepts integer or float values and numeric strings (commas allowed). Returns `None` when `fact` is `None`, the `val` field is missing, or the value cannot be parsed as a number.
    
    Parameters:
        fact (tuple[str, str, dict] | None): A company fact tuple `(concept, unit, item)` where `item` is a dict containing a `val` key, or `None`.
    
    Returns:
        float | None: The parsed numeric value from `fact[2]['val']` if parseable, `None` otherwise.
    """
    if fact is None:
        return None
    value = fact[2].get("val")
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", ""))
        except ValueError:
            return None
    return None


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    """
    Compute a bounded ratio of numerator to denominator.
    
    Parameters:
        numerator (float | None): The numerator value; if `None` the result is `None`.
        denominator (float | None): The denominator value; if `None` or zero the result is `None`.
    
    Returns:
        float: A value between 0.0 and 1.0 equal to numerator / abs(denominator) and clamped to [0.0, 1.0], or `None` if `numerator` is `None` or `denominator` is `None` or zero.
    """
    if numerator is None or denominator in (None, 0):
        return None
    return _clamp_ratio(numerator / abs(denominator))


def _clamp_ratio(value: float) -> float:
    """
    Clamp a numeric ratio into the inclusive range [0.0, 1.0].
    
    Parameters:
        value (float): The ratio to clamp; may be outside the [0.0, 1.0] range.
    
    Returns:
        float: The input constrained to be no less than 0.0 and no greater than 1.0.
    """
    return min(max(value, 0.0), 1.0)


def _format_optional_ratio(value: float | None) -> str:
    """
    Format an optional numeric ratio as a three-decimal string or `"missing"`.
    
    Parameters:
        value (float | None): Ratio value (typically between 0.0 and 1.0) or `None` when missing.
    
    Returns:
        str: `"missing"` if `value` is `None`, otherwise `value` formatted to three decimal places (e.g., `"0.123"`).
    """
    if value is None:
        return "missing"
    return f"{value:.3f}"
