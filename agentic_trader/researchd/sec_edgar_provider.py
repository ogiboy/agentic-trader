"""SEC EDGAR research provider."""

from collections.abc import Mapping
from dataclasses import dataclass

import httpx

from agentic_trader.config import Settings
from agentic_trader.providers.base import metadata, source_attribution, utc_now_iso
from agentic_trader.researchd.provider_core import (
    JsonFetcher,
    JsonObject,
    ResearchProviderOutput,
    fetch_json,
    json_object,
    normalize_symbol,
    object_list,
    safe_error_note,
)
from agentic_trader.schemas import (
    EvidenceInferenceBreakdown,
    ProviderMetadata,
    RawEvidenceRecord,
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


@dataclass(frozen=True)
class _SecTickerMatch:
    symbol: str
    cik: str
    entity_name: str


@dataclass(frozen=True)
class _CompanyFactEvidence:
    evidence: list[str]
    concept_notes: list[str]
    missing_fields: list[str]
    observed_at: str
    completeness: float


@dataclass(frozen=True)
class _SubmissionRecordFields:
    accession: str
    form: str
    report_date: str
    primary_description: str
    observed_at: str
    filing_label: str
    missing_fields: list[str]
    url: str | None


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
        early_output = self._early_collect_output(symbols)
        if early_output is not None:
            return early_output

        watched_symbols = self._watched_symbols(symbols)
        safe_limit = max(1, limit)
        headers = self._headers()
        ticker_output = self._ticker_index(headers)
        if isinstance(ticker_output, ResearchProviderOutput):
            return ticker_output

        ticker_index = ticker_output
        records: list[RawEvidenceRecord] = []
        missing_reasons: list[str] = []
        for symbol in watched_symbols:
            if len(records) >= safe_limit:
                break
            symbol_records, symbol_missing = self._collect_symbol_records(
                symbol=symbol,
                ticker_index=ticker_index,
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
    ) -> dict[str, _SecTickerMatch] | ResearchProviderOutput:
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
        return _sec_ticker_index(ticker_payload)

    def _collect_symbol_records(
        self,
        *,
        symbol: str,
        ticker_index: dict[str, _SecTickerMatch],
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
        match: _SecTickerMatch,
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
        facts_record = _record_from_company_facts(
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
        match: _SecTickerMatch,
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
        records = _records_from_submissions(
            provider=self._metadata,
            symbol=symbol,
            match=match,
            payload=submissions_payload,
            limit=limit,
        )
        if not records:
            return [], [f"sec_target_filings_missing:{symbol}"]
        return records, []


def _sec_configuration_note(*, enabled: bool, user_agent: str) -> str:
    if not enabled:
        return "sec_provider_disabled"
    if user_agent:
        return "sec_user_agent_configured"
    return "sec_user_agent_missing"


def _sec_ticker_index(payload: Mapping[str, object]) -> dict[str, _SecTickerMatch]:
    index: dict[str, _SecTickerMatch] = {}
    for value in payload.values():
        row = json_object(value)
        if row is None:
            continue
        ticker = _string_value(row.get("ticker")).upper()
        cik_value = row.get("cik_str")
        entity_name = _string_value(row.get("title")) or ticker
        if not ticker or cik_value is None:
            continue
        cik = _string_value(cik_value).zfill(10)
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
    payload: Mapping[str, object],
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
    entity_name = _string_value(payload.get("name")) or match.entity_name
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
    payload: Mapping[str, object],
) -> RawEvidenceRecord | None:
    us_gaap = _us_gaap_facts(payload)
    if not us_gaap:
        return None

    fetched_at = utc_now_iso()
    entity_name = _string_value(payload.get("entityName")) or match.entity_name
    company_facts = _company_fact_evidence(us_gaap, fetched_at=fetched_at)
    if company_facts is None:
        return None
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
        observed_at=company_facts.observed_at,
        last_verified_at=fetched_at,
        normalized_summary=(
            f"SEC company facts reports {len(company_facts.evidence)} compact XBRL metric(s) "
            f"for {entity_name}: {'; '.join(company_facts.evidence)}"
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
                completeness=company_facts.completeness,
                notes=[
                    "sec_companyfacts_api",
                    f"cik={match.cik}",
                    *company_facts.concept_notes,
                ],
            )
        ],
        evidence_vs_inference=EvidenceInferenceBreakdown(
            evidence=company_facts.evidence,
            inference=[],
            uncertainty=[
                "SEC company facts aggregate normalized XBRL facts; filing text was not downloaded or parsed in this pass.",
                "Company-specific extension taxonomy concepts are not included in this compact V1 summary.",
            ],
        ),
        missing_fields=company_facts.missing_fields,
    )


def _company_fact_evidence(
    us_gaap: Mapping[str, object],
    *,
    fetched_at: str,
) -> _CompanyFactEvidence | None:
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
    return _CompanyFactEvidence(
        evidence=evidence,
        concept_notes=concept_notes,
        missing_fields=missing_fields,
        observed_at=observed_at,
        completeness=len(evidence) / len(SEC_COMPANY_FACT_CONCEPTS),
    )


def _recent_filings(payload: Mapping[str, object]) -> JsonObject | None:
    filings = json_object(payload.get("filings"))
    if filings is None:
        return None
    return json_object(filings.get("recent"))


def _submission_record_fields(
    *,
    match: _SecTickerMatch,
    accession_value: object,
    forms: list[object],
    filing_dates: list[object],
    report_dates: list[object],
    primary_documents: list[object],
    primary_descriptions: list[object],
    index: int,
    fetched_at: str,
) -> _SubmissionRecordFields | None:
    accession = _string_value(accession_value)
    form = _string_at(forms, index)
    if not accession or form not in SEC_RESEARCH_FORMS:
        return None
    filing_date = _string_at(filing_dates, index)
    report_date = _string_at(report_dates, index)
    primary_document = _string_at(primary_documents, index)
    primary_description = _string_at(primary_descriptions, index)
    return _SubmissionRecordFields(
        accession=accession,
        form=form,
        report_date=report_date,
        primary_description=primary_description,
        observed_at=filing_date or fetched_at,
        filing_label=filing_date or "unknown date",
        missing_fields=_sec_missing_fields(
            cik=match.cik,
            accession=accession,
            report_date=report_date,
            primary_document=primary_document,
        ),
        url=_sec_archive_url(
            cik=match.cik,
            accession=accession,
            primary_document=primary_document,
        ),
    )


def _submission_record(
    *,
    provider: ProviderMetadata,
    symbol: str,
    match: _SecTickerMatch,
    fields: _SubmissionRecordFields,
    fetched_at: str,
    entity_name: str,
) -> RawEvidenceRecord:
    return RawEvidenceRecord(
        record_id=f"sec:{symbol}:{fields.accession}",
        source_kind="disclosure",
        source_name=provider.provider_id,
        title=f"{symbol} {fields.form} filed {fields.filing_label}",
        symbol=symbol,
        entity_name=entity_name,
        region="US",
        url=fields.url,
        observed_at=fields.observed_at,
        last_verified_at=fetched_at,
        normalized_summary=(
            f"SEC EDGAR submissions API reports {entity_name} filed "
            f"{fields.form} accession {fields.accession} on {fields.filing_label}"
            f" for report date {fields.report_date or 'unknown'}."
        ),
        source_payload_ref=f"sec-submissions://CIK{match.cik}/{fields.accession}",
        source_attributions=[
            source_attribution(
                source_name=provider.provider_id,
                provider_type=provider.provider_type,
                source_role=provider.role,
                fetched_at=fetched_at,
                freshness="fresh",
                confidence=0.95,
                completeness=0.85 if not fields.missing_fields else 0.7,
                notes=[
                    "sec_submissions_api",
                    f"cik={match.cik}",
                    f"form={fields.form}",
                    _primary_document_note(fields.primary_description),
                ],
            )
        ],
        evidence_vs_inference=EvidenceInferenceBreakdown(
            evidence=[
                f"SEC ticker mapping associates {symbol} with CIK {match.cik}.",
                (
                    f"SEC submissions metadata lists accession {fields.accession} "
                    f"as form {fields.form} filed on {fields.filing_label}."
                ),
            ],
            inference=[],
            uncertainty=[
                "Filing text and XBRL facts were not downloaded or parsed in this pass."
            ],
        ),
        missing_fields=fields.missing_fields,
    )


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
    fields = _submission_record_fields(
        match=match,
        accession_value=accession_value,
        forms=forms,
        filing_dates=filing_dates,
        report_dates=report_dates,
        primary_documents=primary_documents,
        primary_descriptions=primary_descriptions,
        index=index,
        fetched_at=fetched_at,
    )
    if fields is None:
        return None

    return _submission_record(
        provider=provider,
        symbol=symbol,
        match=match,
        fields=fields,
        fetched_at=fetched_at,
        entity_name=entity_name,
    )


def _sec_missing_fields(
    *,
    cik: str,
    accession: str,
    report_date: str,
    primary_document: str,
) -> list[str]:
    """Identify missing SEC submission fields for a filing."""
    missing_fields: list[str] = []
    if not report_date:
        missing_fields.append("report_date")
    if not primary_document:
        missing_fields.append("primary_document")
    if (
        _sec_archive_url(
            cik=cik,
            accession=accession,
            primary_document=primary_document,
        )
        is None
    ):
        missing_fields.append("url")
    return missing_fields


def _primary_document_note(primary_description: str) -> str:
    if primary_description:
        return f"primary_doc_description={primary_description}"
    return "primary_doc_description_missing"


def _list_value(value: object) -> list[object]:
    values = object_list(value)
    return values if values is not None else []


def _us_gaap_facts(payload: Mapping[str, object]) -> JsonObject | None:
    facts = json_object(payload.get("facts"))
    if facts is None:
        return None
    return json_object(facts.get("us-gaap"))


def _latest_company_fact(
    us_gaap: Mapping[str, object],
    *,
    concepts: tuple[str, ...],
) -> tuple[str, str, JsonObject] | None:
    candidates = list(_company_fact_candidates(us_gaap, concepts=concepts))
    if not candidates:
        return None
    _, concept, unit, item = max(candidates, key=lambda candidate: candidate[0])
    return concept, unit, item


def _company_fact_candidates(
    us_gaap: Mapping[str, object],
    *,
    concepts: tuple[str, ...],
) -> list[tuple[tuple[str, str, str], str, str, JsonObject]]:
    """Collect candidate company-fact entries for requested GAAP concepts."""
    candidates: list[tuple[tuple[str, str, str], str, str, JsonObject]] = []
    for concept in concepts:
        for unit, item in _usd_company_fact_items(us_gaap.get(concept)):
            candidates.append((_company_fact_sort_key(item), concept, unit, item))
    return candidates


def _usd_company_fact_items(
    concept_payload: object,
) -> list[tuple[str, JsonObject]]:
    """Extract USD-denominated fact items from a concept payload."""
    units = _company_fact_units(concept_payload)
    if units is None:
        return []
    values = object_list(units.get("USD"))
    if values is None:
        return []
    items: list[tuple[str, JsonObject]] = []
    for value in values:
        item = json_object(value)
        if item is not None and item.get("val") is not None:
            items.append(("USD", item))
    return items


def _company_fact_units(concept_payload: object) -> JsonObject | None:
    payload = json_object(concept_payload)
    if payload is None:
        return None
    return json_object(payload.get("units"))


def _company_fact_sort_key(item: Mapping[str, object]) -> tuple[str, str, str]:
    return (
        _string_value(item.get("filed")),
        _string_value(item.get("end")),
        _string_value(item.get("accn")),
    )


def _company_fact_period(item: Mapping[str, object]) -> str:
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
