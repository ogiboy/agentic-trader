"""Shared SEC EDGAR constants, value objects, and parsing helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from agentic_trader.researchd.provider_core import (
    JsonObject,
    json_object,
    object_list,
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
class SecTickerMatch:
    symbol: str
    cik: str
    entity_name: str


@dataclass(frozen=True)
class CompanyFactEvidence:
    evidence: list[str]
    concept_notes: list[str]
    missing_fields: list[str]
    observed_at: str
    completeness: float


@dataclass(frozen=True)
class SubmissionRecordFields:
    accession: str
    form: str
    report_date: str
    primary_description: str
    observed_at: str
    filing_label: str
    missing_fields: list[str]
    url: str | None


def sec_configuration_note(*, enabled: bool, user_agent: str) -> str:
    if not enabled:
        return "sec_provider_disabled"
    if user_agent:
        return "sec_user_agent_configured"
    return "sec_user_agent_missing"


def sec_ticker_index(payload: Mapping[str, object]) -> dict[str, SecTickerMatch]:
    index: dict[str, SecTickerMatch] = {}
    for value in payload.values():
        row = json_object(value)
        if row is None:
            continue
        ticker = string_value(row.get("ticker")).upper()
        cik_value = row.get("cik_str")
        entity_name = string_value(row.get("title")) or ticker
        if not ticker or cik_value is None:
            continue
        cik = string_value(cik_value).zfill(10)
        index[ticker] = SecTickerMatch(
            symbol=ticker,
            cik=cik,
            entity_name=entity_name,
        )
    return index


def list_value(value: object) -> list[object]:
    values = object_list(value)
    return values if values is not None else []


def string_value(value: object) -> str:
    return str(value).strip() if value is not None else ""


def string_at(values: list[object], index: int) -> str:
    if index >= len(values):
        return ""
    return string_value(values[index])


def sec_archive_url(
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


def sec_missing_fields(
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
        sec_archive_url(
            cik=cik,
            accession=accession,
            primary_document=primary_document,
        )
        is None
    ):
        missing_fields.append("url")
    return missing_fields


def primary_document_note(primary_description: str) -> str:
    if primary_description:
        return f"primary_doc_description={primary_description}"
    return "primary_doc_description_missing"


def recent_filings(payload: Mapping[str, object]) -> JsonObject | None:
    filings = json_object(payload.get("filings"))
    if filings is None:
        return None
    return json_object(filings.get("recent"))
