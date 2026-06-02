"""SEC EDGAR companyfacts evidence normalization."""

from __future__ import annotations

from collections.abc import Mapping

from agentic_trader.providers.base import source_attribution, utc_now_iso
from agentic_trader.researchd.provider_core import JsonObject, json_object, object_list
from agentic_trader.researchd.sec_edgar_common import (
    SEC_COMPANY_FACT_CONCEPTS,
    SEC_COMPANY_FACTS_URL_TEMPLATE,
    CompanyFactEvidence,
    SecTickerMatch,
    string_value,
)
from agentic_trader.schemas import (
    EvidenceInferenceBreakdown,
    ProviderMetadata,
    RawEvidenceRecord,
)


def record_from_company_facts(
    *,
    provider: ProviderMetadata,
    symbol: str,
    match: SecTickerMatch,
    payload: Mapping[str, object],
) -> RawEvidenceRecord | None:
    us_gaap = _us_gaap_facts(payload)
    if not us_gaap:
        return None

    fetched_at = utc_now_iso()
    entity_name = string_value(payload.get("entityName")) or match.entity_name
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
) -> CompanyFactEvidence | None:
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
        end = string_value(item.get("end"))
        filed = string_value(item.get("filed"))
        form = string_value(item.get("form"))
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
    return CompanyFactEvidence(
        evidence=evidence,
        concept_notes=concept_notes,
        missing_fields=missing_fields,
        observed_at=observed_at,
        completeness=len(evidence) / len(SEC_COMPANY_FACT_CONCEPTS),
    )


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
        string_value(item.get("filed")),
        string_value(item.get("end")),
        string_value(item.get("accn")),
    )


def _company_fact_period(item: Mapping[str, object]) -> str:
    fy = string_value(item.get("fy"))
    fp = string_value(item.get("fp"))
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
    return f"{string_value(value) or 'unknown'} {unit}".strip()
