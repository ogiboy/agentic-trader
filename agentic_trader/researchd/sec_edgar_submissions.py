"""SEC EDGAR submissions evidence normalization."""

from __future__ import annotations

from collections.abc import Mapping

from agentic_trader.providers.base import source_attribution, utc_now_iso
from agentic_trader.researchd.sec_edgar_common import (
    SEC_RESEARCH_FORMS,
    SecTickerMatch,
    SubmissionRecordFields,
    list_value,
    primary_document_note,
    recent_filings,
    sec_archive_url,
    sec_missing_fields,
    string_at,
    string_value,
)
from agentic_trader.schemas import (
    EvidenceInferenceBreakdown,
    ProviderMetadata,
    RawEvidenceRecord,
)


def records_from_submissions(
    *,
    provider: ProviderMetadata,
    symbol: str,
    match: SecTickerMatch,
    payload: Mapping[str, object],
    limit: int,
) -> list[RawEvidenceRecord]:
    if limit <= 0:
        return []
    recent = recent_filings(payload)
    if not isinstance(recent, dict):
        return []

    accessions = list_value(recent.get("accessionNumber"))
    forms = list_value(recent.get("form"))
    filing_dates = list_value(recent.get("filingDate"))
    report_dates = list_value(recent.get("reportDate"))
    primary_documents = list_value(recent.get("primaryDocument"))
    primary_descriptions = list_value(recent.get("primaryDocDescription"))
    fetched_at = utc_now_iso()
    entity_name = string_value(payload.get("name")) or match.entity_name
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


def _submission_record_fields(
    *,
    match: SecTickerMatch,
    accession_value: object,
    forms: list[object],
    filing_dates: list[object],
    report_dates: list[object],
    primary_documents: list[object],
    primary_descriptions: list[object],
    index: int,
    fetched_at: str,
) -> SubmissionRecordFields | None:
    accession = string_value(accession_value)
    form = string_at(forms, index)
    if not accession or form not in SEC_RESEARCH_FORMS:
        return None
    filing_date = string_at(filing_dates, index)
    report_date = string_at(report_dates, index)
    primary_document = string_at(primary_documents, index)
    primary_description = string_at(primary_descriptions, index)
    return SubmissionRecordFields(
        accession=accession,
        form=form,
        report_date=report_date,
        primary_description=primary_description,
        observed_at=filing_date or fetched_at,
        filing_label=filing_date or "unknown date",
        missing_fields=sec_missing_fields(
            cik=match.cik,
            accession=accession,
            report_date=report_date,
            primary_document=primary_document,
        ),
        url=sec_archive_url(
            cik=match.cik,
            accession=accession,
            primary_document=primary_document,
        ),
    )


def _submission_record(
    *,
    provider: ProviderMetadata,
    symbol: str,
    match: SecTickerMatch,
    fields: SubmissionRecordFields,
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
                    primary_document_note(fields.primary_description),
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
    match: SecTickerMatch,
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
