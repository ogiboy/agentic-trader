from dataclasses import dataclass
from typing import Any, TypeGuard, cast

from agentic_trader.json_utils import object_dict_or_none as _object_mapping
from agentic_trader.providers.base import source_attribution, utc_now_iso
from agentic_trader.schemas import FundamentalSnapshot, SymbolIdentity

FUNDAMENTAL_FIELDS = (
    "revenue_growth",
    "profitability_stability",
    "cash_flow_alignment",
    "debt_risk",
    "reinvestment_potential",
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


@dataclass(frozen=True)
class _SecCompanyFactMetrics:
    latest: dict[str, tuple[str, str, dict[str, Any]]]
    missing_fields: list[str]
    concept_notes: list[str]


@dataclass(frozen=True)
class _FundamentalRatios:
    revenue_growth: float | None
    profitability_stability: float | None
    cash_flow_alignment: float | None
    debt_risk: float | None
    reinvestment_potential: float | None

    def missing_fields(self) -> list[str]:
        values = {
            "revenue_growth": self.revenue_growth,
            "profitability_stability": self.profitability_stability,
            "cash_flow_alignment": self.cash_flow_alignment,
            "debt_risk": self.debt_risk,
            "reinvestment_potential": self.reinvestment_potential,
        }
        return [field for field, value in values.items() if value is None]


def fundamental_snapshot_from_sec_companyfacts(
    symbol: SymbolIdentity,
    *,
    cik: str,
    entity_name: str,
    payload: dict[str, Any],
) -> FundamentalSnapshot:
    facts = _object_mapping(payload.get("facts"))
    us_gaap = _object_mapping(facts.get("us-gaap") if facts is not None else None)
    if us_gaap is None:
        return missing_sec_fundamental_snapshot(
            symbol,
            notes=["sec_companyfacts_api", f"cik={cik}", "us_gaap_facts_missing"],
            summary="SEC EDGAR companyfacts payload did not include usable US-GAAP facts.",
        )

    metrics = _sec_company_fact_metrics(us_gaap)
    ratios = _sec_companyfact_ratios(us_gaap, metrics.latest)
    missing_fields = [*metrics.missing_fields, *ratios.missing_fields()]
    completeness = 1.0 - (len(set(missing_fields)) / (len(FUNDAMENTAL_FIELDS) + 6))
    completeness = clamp_ratio(completeness)
    if completeness <= 0:
        return missing_sec_fundamental_snapshot(
            symbol,
            notes=["sec_companyfacts_api", f"cik={cik}", *metrics.concept_notes],
            summary="SEC EDGAR companyfacts did not provide enough metrics for V1 fundamentals.",
        )

    entity = str(payload.get("entityName") or entity_name or symbol.symbol).strip()
    return _sec_companyfacts_snapshot(
        symbol=symbol,
        cik=cik,
        entity=entity,
        ratios=ratios,
        concept_notes=metrics.concept_notes,
        missing_fields=missing_fields,
        completeness=completeness,
    )


def _sec_company_fact_metrics(us_gaap: dict[str, Any]) -> _SecCompanyFactMetrics:
    latest: dict[str, tuple[str, str, dict[str, Any]]] = {}
    missing_fields: list[str] = []
    concept_notes: list[str] = []
    for metric_id, concepts in SEC_COMPANY_FACT_CONCEPTS.items():
        fact = latest_company_fact(us_gaap, concepts=concepts)
        if fact is None:
            missing_fields.append(f"company_fact:{metric_id}")
            continue
        latest[metric_id] = fact
        concept_notes.append(f"{metric_id}={fact[0]}")
    return _SecCompanyFactMetrics(
        latest=latest,
        missing_fields=missing_fields,
        concept_notes=concept_notes,
    )


def _sec_companyfact_ratios(
    us_gaap: dict[str, Any],
    latest: dict[str, tuple[str, str, dict[str, Any]]],
) -> _FundamentalRatios:
    revenue = fact_number(latest.get("revenue"))
    net_income = fact_number(latest.get("net_income"))
    assets = fact_number(latest.get("assets"))
    liabilities = fact_number(latest.get("liabilities"))
    operating_cash_flow = fact_number(latest.get("operating_cash_flow"))
    cash = fact_number(latest.get("cash"))
    return _FundamentalRatios(
        revenue_growth=growth_ratio(us_gaap, SEC_COMPANY_FACT_CONCEPTS["revenue"]),
        profitability_stability=ratio(net_income, revenue),
        cash_flow_alignment=ratio(operating_cash_flow, net_income),
        debt_risk=ratio(liabilities, assets),
        reinvestment_potential=ratio(cash, assets),
    )


def _sec_companyfacts_snapshot(
    *,
    symbol: SymbolIdentity,
    cik: str,
    entity: str,
    ratios: _FundamentalRatios,
    concept_notes: list[str],
    missing_fields: list[str],
    completeness: float,
) -> FundamentalSnapshot:
    return FundamentalSnapshot(
        symbol_identity=symbol,
        revenue_growth=ratios.revenue_growth,
        profitability_stability=ratios.profitability_stability,
        cash_flow_alignment=ratios.cash_flow_alignment,
        debt_risk=ratios.debt_risk,
        fx_exposure="unknown",
        reinvestment_potential=ratios.reinvestment_potential,
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
            f"revenue_growth={format_optional_ratio(ratios.revenue_growth)}, "
            f"profitability={format_optional_ratio(ratios.profitability_stability)}, "
            f"cash_flow_alignment={format_optional_ratio(ratios.cash_flow_alignment)}, "
            f"debt_risk={format_optional_ratio(ratios.debt_risk)}."
        ),
    )


def missing_sec_fundamental_snapshot(
    symbol: SymbolIdentity, *, notes: list[str], summary: str
) -> FundamentalSnapshot:
    return FundamentalSnapshot(
        symbol_identity=symbol,
        fx_exposure="unknown",
        attribution=source_attribution(
            source_name="sec_edgar",
            provider_type="fundamental",
            source_role="missing",
            fetched_at=utc_now_iso(),
            freshness="missing",
            notes=notes,
        ),
        missing_fields=list(FUNDAMENTAL_FIELDS),
        summary=summary,
    )


def latest_company_fact(
    us_gaap: dict[str, Any], *, concepts: tuple[str, ...]
) -> tuple[str, str, dict[str, Any]] | None:
    entries = company_fact_entries(us_gaap, concepts=concepts)
    if not entries:
        return None
    return max(entries, key=lambda item: fact_sort_key(item[2]))


def company_fact_entries(
    us_gaap: dict[str, Any], *, concepts: tuple[str, ...]
) -> list[tuple[str, str, dict[str, Any]]]:
    entries: list[tuple[str, str, dict[str, Any]]] = []
    for concept in concepts:
        entries.extend(company_fact_entries_for_concept(us_gaap, concept))
    return entries


def company_fact_entries_for_concept(
    us_gaap: dict[str, Any], concept: str
) -> list[tuple[str, str, dict[str, Any]]]:
    concept_payload = _object_mapping(us_gaap.get(concept))
    if concept_payload is None:
        return []
    units = _object_mapping(concept_payload.get("units"))
    if units is None:
        return []
    entries: list[tuple[str, str, dict[str, Any]]] = []
    for unit, unit_entries in units.items():
        entries.extend(company_fact_entries_for_unit(concept, str(unit), unit_entries))
    return entries


def company_fact_entries_for_unit(
    concept: str, unit: str, unit_entries: object
) -> list[tuple[str, str, dict[str, Any]]]:
    if not isinstance(unit_entries, list):
        return []
    entries: list[tuple[str, str, dict[str, Any]]] = []
    for item in cast(list[object], unit_entries):
        if is_supported_company_fact_item(item, concept=concept, unit=unit):
            entries.append((concept, unit, item))
    return entries


def is_supported_company_fact_item(
    item: object, *, concept: str, unit: str
) -> TypeGuard[dict[str, Any]]:
    if not isinstance(item, dict):
        return False
    item_payload = cast(dict[str, Any], item)
    if fact_number((concept, unit, item_payload)) is None:
        return False
    form = str(item_payload.get("form") or "").upper()
    return not form or form in SEC_RESEARCH_FORMS


def growth_ratio(us_gaap: dict[str, Any], concepts: tuple[str, ...]) -> float | None:
    entries = [
        item
        for item in company_fact_entries(us_gaap, concepts=concepts)
        if is_annual_fact(item[2])
    ]
    entries.sort(key=lambda item: fact_sort_key(item[2]), reverse=True)
    if len(entries) < 2:
        return None
    latest = fact_number(entries[0])
    previous = fact_number(entries[1])
    if latest is None or previous in (None, 0):
        return None
    return (latest - previous) / abs(previous)


def is_annual_fact(item: dict[str, Any]) -> bool:
    form = str(item.get("form") or "").upper()
    fiscal_period = str(item.get("fp") or "").upper()
    frame = str(item.get("frame") or "").upper()
    return (
        form in SEC_ANNUAL_FORMS
        or fiscal_period == "FY"
        or (frame.startswith("CY") and "Q" not in frame and not frame.endswith("I"))
    )


def fact_sort_key(item: dict[str, Any]) -> tuple[str, str]:
    filed = str(item.get("filed") or "")
    end = str(item.get("end") or "")
    return filed, end


def fact_number(fact: tuple[str, str, dict[str, Any]] | None) -> float | None:
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


def ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return clamp_ratio(numerator / abs(denominator))


def clamp_ratio(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def format_optional_ratio(value: float | None) -> str:
    if value is None:
        return "missing"
    return f"{value:.3f}"
