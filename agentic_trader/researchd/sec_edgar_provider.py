"""SEC EDGAR research provider."""

from __future__ import annotations

import httpx

from agentic_trader.config import Settings
from agentic_trader.providers.base import metadata
from agentic_trader.researchd.provider_core import (
    JsonFetcher,
    ResearchProviderOutput,
    fetch_json,
    normalize_symbol,
    safe_error_note,
)
from agentic_trader.researchd.sec_edgar_common import (
    SEC_COMPANY_FACTS_URL_TEMPLATE,
    SEC_COMPANY_TICKERS_URL,
    SEC_SUBMISSIONS_URL_TEMPLATE,
    SecTickerMatch,
    sec_configuration_note,
    sec_ticker_index,
)
from agentic_trader.researchd.sec_edgar_companyfacts import record_from_company_facts
from agentic_trader.researchd.sec_edgar_submissions import records_from_submissions
from agentic_trader.schemas import ProviderMetadata, RawEvidenceRecord


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
        self._fetcher = fetcher or fetch_json
        configuration_note = sec_configuration_note(
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
        early_output = self._early_collect_output(symbols)
        if early_output is not None:
            return early_output

        watched_symbols = self._watched_symbols(symbols)
        safe_limit = max(1, limit)
        headers = self._headers()
        ticker_output = self._ticker_index(headers)
        if isinstance(ticker_output, ResearchProviderOutput):
            return ticker_output

        records: list[RawEvidenceRecord] = []
        missing_reasons: list[str] = []
        for symbol in watched_symbols:
            if len(records) >= safe_limit:
                break
            symbol_records, symbol_missing = self._collect_symbol_records(
                symbol=symbol,
                ticker_index=ticker_output,
                headers=headers,
                remaining=safe_limit - len(records),
            )
            records.extend(symbol_records)
            missing_reasons.extend(symbol_missing)

        return ResearchProviderOutput(
            metadata=self._metadata,
            raw_evidence=records[:safe_limit],
            missing_reasons=list(dict.fromkeys(missing_reasons)),
        )

    def _early_collect_output(
        self, symbols: list[str]
    ) -> ResearchProviderOutput | None:
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
        if not self._watched_symbols(symbols):
            return ResearchProviderOutput(
                metadata=self._metadata,
                missing_reasons=["watchlist_missing"],
            )
        return None

    @staticmethod
    def _watched_symbols(symbols: list[str]) -> list[str]:
        """Normalize and filter symbol strings into uppercase tickers."""

        return [
            symbol for symbol in (normalize_symbol(item) for item in symbols) if symbol
        ]

    def _headers(self) -> dict[str, str]:
        """Return HTTP headers used for SEC API requests."""

        return {
            "Accept": "application/json",
            "User-Agent": self._user_agent,
        }

    def _ticker_index(
        self, headers: dict[str, str]
    ) -> dict[str, SecTickerMatch] | ResearchProviderOutput:
        try:
            ticker_payload = self._fetcher(
                SEC_COMPANY_TICKERS_URL,
                headers,
                self._timeout,
            )
        except (httpx.HTTPError, ValueError, TypeError, TimeoutError) as exc:
            return ResearchProviderOutput(
                metadata=self._metadata,
                missing_reasons=["sec_ticker_lookup_failed", safe_error_note(exc)],
            )
        return sec_ticker_index(ticker_payload)

    def _collect_symbol_records(
        self,
        *,
        symbol: str,
        ticker_index: dict[str, SecTickerMatch],
        headers: dict[str, str],
        remaining: int,
    ) -> tuple[list[RawEvidenceRecord], list[str]]:
        match = ticker_index.get(symbol)
        if match is None:
            return [], [f"sec_cik_missing:{symbol}"]

        records: list[RawEvidenceRecord] = []
        missing_reasons = self._collect_company_facts_record(
            symbol=symbol,
            match=match,
            headers=headers,
            records=records,
        )
        if len(records) >= remaining:
            return records[:remaining], missing_reasons

        submission_records, submission_missing = self._submission_records(
            symbol=symbol,
            match=match,
            headers=headers,
            limit=remaining - len(records),
        )
        records.extend(submission_records)
        missing_reasons.extend(submission_missing)
        return records[:remaining], missing_reasons

    def _collect_company_facts_record(
        self,
        *,
        symbol: str,
        match: SecTickerMatch,
        headers: dict[str, str],
        records: list[RawEvidenceRecord],
    ) -> list[str]:
        try:
            facts_payload = self._fetcher(
                SEC_COMPANY_FACTS_URL_TEMPLATE.format(cik=match.cik),
                headers,
                self._timeout,
            )
        except (httpx.HTTPError, ValueError, TypeError, TimeoutError) as exc:
            return [f"sec_companyfacts_fetch_failed:{symbol}", safe_error_note(exc)]

        facts_record = record_from_company_facts(
            provider=self._metadata,
            symbol=symbol,
            match=match,
            payload=facts_payload,
        )
        if facts_record is None:
            return [f"sec_companyfacts_missing:{symbol}"]
        records.append(facts_record)
        return []

    def _submission_records(
        self,
        *,
        symbol: str,
        match: SecTickerMatch,
        headers: dict[str, str],
        limit: int,
    ) -> tuple[list[RawEvidenceRecord], list[str]]:
        try:
            submissions_payload = self._fetcher(
                SEC_SUBMISSIONS_URL_TEMPLATE.format(cik=match.cik),
                headers,
                self._timeout,
            )
        except (httpx.HTTPError, ValueError, TypeError, TimeoutError) as exc:
            return [], [f"sec_submissions_fetch_failed:{symbol}", safe_error_note(exc)]

        records = records_from_submissions(
            provider=self._metadata,
            symbol=symbol,
            match=match,
            payload=submissions_payload,
            limit=limit,
        )
        if not records:
            return [], [f"sec_target_filings_missing:{symbol}"]
        return records, []
