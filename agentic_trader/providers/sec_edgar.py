"""SEC EDGAR public-source adapter for structured US fundamentals."""

from typing import Any

import httpx

from agentic_trader.config import Settings
from agentic_trader.json_utils import object_dict_or_none as _object_mapping
from agentic_trader.providers.base import metadata, source_attribution, utc_now_iso
from agentic_trader.providers.public_source_http import JsonFetcher, fetch_json
from agentic_trader.providers.sec_companyfacts import (
    FUNDAMENTAL_FIELDS,
    fundamental_snapshot_from_sec_companyfacts,
)
from agentic_trader.schemas import FundamentalSnapshot, ProviderMetadata, SymbolIdentity
from agentic_trader.security import safe_exception_note

SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_COMPANY_FACTS_URL_TEMPLATE = (
    "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
)


class SecEdgarFundamentalProvider:
    """Opt-in SEC companyfacts provider for structured US fundamentals."""

    def __init__(
        self,
        settings: Settings,
        *,
        fetcher: JsonFetcher | None = None,
    ) -> None:
        self._settings = settings
        self._fetcher = fetcher or fetch_json

    def metadata(self) -> ProviderMetadata:
        """Build provider metadata for SEC EDGAR fundamentals."""
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

    def _missing_snapshot(
        self,
        symbol: SymbolIdentity,
        *,
        notes: list[str],
        summary: str,
    ) -> FundamentalSnapshot:
        return _missing_fundamental_snapshot(
            symbol,
            source_name="sec_edgar",
            notes=notes,
            summary=summary,
        )

    def _configuration_missing_snapshot(
        self,
        symbol: SymbolIdentity,
        notes: list[str],
    ) -> FundamentalSnapshot | None:
        if symbol.region != "US":
            return self._missing_snapshot(
                symbol,
                notes=[*notes, f"unsupported_region={symbol.region}"],
                summary="SEC EDGAR companyfacts supports US issuers only in V1.",
            )
        if not self._settings.research_sec_edgar_enabled:
            return self._missing_snapshot(
                symbol,
                notes=[*notes, "provider_disabled"],
                summary="SEC EDGAR companyfacts ingestion is disabled by configuration.",
            )
        if not (self._settings.research_sec_edgar_user_agent or "").strip():
            return self._missing_snapshot(
                symbol,
                notes=[*notes, "sec_user_agent_missing"],
                summary="SEC EDGAR companyfacts requires an identifying User-Agent.",
            )
        return None

    def _request_context(self) -> tuple[dict[str, str], float]:
        user_agent = (self._settings.research_sec_edgar_user_agent or "").strip()
        return (
            {"Accept": "application/json", "User-Agent": user_agent},
            min(max(self._settings.request_timeout_seconds, 1.0), 30.0),
        )

    def _fetch_ticker_index(
        self,
        *,
        symbol: SymbolIdentity,
        notes: list[str],
        headers: dict[str, str],
        timeout: float,
    ) -> dict[str, dict[str, str]] | FundamentalSnapshot:
        try:
            return _sec_ticker_index(
                self._fetcher(SEC_COMPANY_TICKERS_URL, headers, timeout)
            )
        except (httpx.HTTPError, ValueError, TypeError, TimeoutError) as exc:
            return self._missing_snapshot(
                symbol,
                notes=[
                    *notes,
                    "sec_ticker_lookup_failed",
                    safe_exception_note("sec_edgar", exc),
                ],
                summary="SEC EDGAR ticker lookup failed.",
            )

    def _fetch_companyfacts(
        self,
        *,
        symbol: SymbolIdentity,
        cik: str,
        notes: list[str],
        headers: dict[str, str],
        timeout: float,
    ) -> dict[str, Any] | FundamentalSnapshot:
        try:
            return self._fetcher(
                SEC_COMPANY_FACTS_URL_TEMPLATE.format(cik=cik),
                headers,
                timeout,
            )
        except (httpx.HTTPError, ValueError, TypeError, TimeoutError) as exc:
            return self._missing_snapshot(
                symbol,
                notes=[
                    *notes,
                    f"sec_companyfacts_fetch_failed:{symbol.symbol.upper()}",
                    safe_exception_note("sec_edgar", exc),
                ],
                summary="SEC EDGAR companyfacts fetch failed.",
            )

    def get_fundamental_data(self, symbol: SymbolIdentity) -> FundamentalSnapshot:
        """Fetch a V1 fundamental snapshot from SEC companyfacts."""
        notes = ["sec_10k_10q_8k_source", "sec_companyfacts_api"]
        missing_snapshot = self._configuration_missing_snapshot(symbol, notes)
        if missing_snapshot is not None:
            return missing_snapshot
        headers, timeout = self._request_context()
        ticker_index = self._fetch_ticker_index(
            symbol=symbol,
            notes=notes,
            headers=headers,
            timeout=timeout,
        )
        if isinstance(ticker_index, FundamentalSnapshot):
            return ticker_index
        match = ticker_index.get(symbol.symbol.upper())
        if match is None:
            return self._missing_snapshot(
                symbol,
                notes=[*notes, f"sec_cik_missing:{symbol.symbol.upper()}"],
                summary="SEC EDGAR CIK lookup did not find this symbol.",
            )
        facts_payload = self._fetch_companyfacts(
            symbol=symbol,
            cik=match["cik"],
            notes=notes,
            headers=headers,
            timeout=timeout,
        )
        if isinstance(facts_payload, FundamentalSnapshot):
            return facts_payload
        return fundamental_snapshot_from_sec_companyfacts(
            symbol,
            cik=match["cik"],
            entity_name=match["entity_name"],
            payload=facts_payload,
        )


def _missing_fundamental_snapshot(
    symbol: SymbolIdentity,
    *,
    source_name: str,
    notes: list[str],
    summary: str,
) -> FundamentalSnapshot:
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


def _sec_configuration_note(*, enabled: bool, user_agent: bool) -> str:
    if not enabled:
        return "sec_provider_disabled"
    if user_agent:
        return "sec_user_agent_configured"
    return "sec_user_agent_missing"


def _sec_ticker_index(payload: dict[str, Any]) -> dict[str, dict[str, str]]:
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
