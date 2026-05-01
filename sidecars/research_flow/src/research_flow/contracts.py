from __future__ import annotations

from datetime import UTC, datetime
import json
import sys
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

CONTRACT_VERSION = "research-flow.v1"


def utc_now_iso() -> str:
    """Return an ISO timestamp in UTC for sidecar contract metadata."""
    return datetime.now(UTC).isoformat()


class ProviderMetadataInput(BaseModel):
    """Minimal provider metadata accepted from the root researchd process."""

    model_config = ConfigDict(extra="ignore")

    provider_id: str
    name: str = ""
    provider_type: str = "unknown"
    role: str = "missing"
    enabled: bool = True
    requires_network: bool = False
    notes: list[str] = Field(default_factory=list)


class ResearchProviderOutputInput(BaseModel):
    """Normalized provider output accepted by the sidecar boundary."""

    model_config = ConfigDict(extra="ignore")

    metadata: ProviderMetadataInput
    raw_evidence: list[dict[str, Any]] = Field(default_factory=list)
    macro_events: list[dict[str, Any]] = Field(default_factory=list)
    social_signals: list[dict[str, Any]] = Field(default_factory=list)
    missing_reasons: list[str] = Field(default_factory=list)


class ResearchFlowRequest(BaseModel):
    """Input contract sent by the root runtime to the tracked CrewAI Flow."""

    model_config = ConfigDict(extra="ignore")

    mode: str = "off"
    symbols: list[str] = Field(default_factory=list)
    provider_outputs: list[ResearchProviderOutputInput] = Field(default_factory=list)


class ResearchFlowContractOutput(BaseModel):
    """Pure JSON output contract returned to the root researchd backend."""

    status: Literal["completed", "failed"] = "completed"
    backend: str = "crewai"
    contract_version: str = CONTRACT_VERSION
    generated_at: str
    observed_at: str
    watched_symbols: list[str] = Field(default_factory=list)
    summary: str = ""
    planned_tasks: list[dict[str, Any]] = Field(default_factory=list)
    findings: list[dict[str, Any]] = Field(default_factory=list)
    dossiers: list[dict[str, Any]] = Field(default_factory=list)
    macro_events: list[dict[str, Any]] = Field(default_factory=list)
    social_signals: list[dict[str, Any]] = Field(default_factory=list)
    memory_update: dict[str, Any] = Field(default_factory=dict)
    raw_web_text_injected: bool = False
    broker_access: bool = False
    errors: list[str] = Field(default_factory=list)


def build_task_plan(request: ResearchFlowRequest) -> list[dict[str, Any]]:
    """Return deterministic future CrewAI Flow task definitions for the request."""
    symbols = request.symbols or ["WATCHLIST"]
    provider_ids = [output.metadata.provider_id for output in request.provider_outputs]
    tasks: list[dict[str, Any]] = []
    for symbol in symbols:
        subject = symbol.upper()
        tasks.extend(
            [
                {
                    "task_id": f"company-dossier:{subject}",
                    "kind": "company_dossier",
                    "subject": subject,
                    "description": (
                        "Build a source-attributed company dossier from normalized "
                        "provider packets, separating direct evidence, inference, "
                        "unknowns, and contradictions."
                    ),
                    "expected_output": (
                        "Entity dossier with timeline, current thesis, key findings, "
                        "contradiction file, source diversity score, and watch-next list."
                    ),
                    "requires_llm": True,
                    "requires_network": False,
                    "input_provider_ids": provider_ids,
                    "status": "planned",
                },
                {
                    "task_id": f"timeline-reconstruction:{subject}",
                    "kind": "timeline_reconstruction",
                    "subject": subject,
                    "description": (
                        "Reconstruct the recent event timeline from normalized evidence "
                        "records without using raw provider text in trading prompts."
                    ),
                    "expected_output": (
                        "Chronological event list with observed_at timestamps, source "
                        "attribution, staleness, and uncertainty markers."
                    ),
                    "requires_llm": True,
                    "requires_network": False,
                    "input_provider_ids": provider_ids,
                    "status": "planned",
                },
                {
                    "task_id": f"contradiction-check:{subject}",
                    "kind": "contradiction_check",
                    "subject": subject,
                    "description": (
                        "Compare evidence packets for conflicting claims, stale data, "
                        "missing sources, and unsupported inferences."
                    ),
                    "expected_output": (
                        "Contradiction report with verified facts, conflicts, unknowns, "
                        "and confidence impact."
                    ),
                    "requires_llm": True,
                    "requires_network": False,
                    "input_provider_ids": provider_ids,
                    "status": "planned",
                },
                {
                    "task_id": f"watch-next:{subject}",
                    "kind": "watch_next",
                    "subject": subject,
                    "description": (
                        "Identify the next official disclosures, macro releases, news "
                        "events, or social-watchlist changes that would materially alter "
                        "the dossier."
                    ),
                    "expected_output": (
                        "Prioritized watch-next checklist with source names, freshness "
                        "requirements, and trigger rationale."
                    ),
                    "requires_llm": True,
                    "requires_network": False,
                    "input_provider_ids": provider_ids,
                    "status": "planned",
                },
            ]
        )
    tasks.append(
        {
            "task_id": "sector-brief:watchlist",
            "kind": "sector_brief",
            "subject": ",".join(symbols),
            "description": (
                "Synthesize cross-symbol sector and macro context only from normalized "
                "provider packets and explicit missing-source states."
            ),
            "expected_output": (
                "Sector brief with source diversity, macro channels, shared risks, "
                "contradictions, and unresolved evidence gaps."
            ),
            "requires_llm": True,
            "requires_network": False,
            "input_provider_ids": provider_ids,
            "status": "planned",
        }
    )
    return tasks


def build_contract_output(request: ResearchFlowRequest) -> ResearchFlowContractOutput:
    """Build the deterministic sidecar contract without running LLM-backed tasks."""
    now = utc_now_iso()
    provider_ids = [output.metadata.provider_id for output in request.provider_outputs]
    missing_count = sum(1 for output in request.provider_outputs if output.missing_reasons)
    payload_count = sum(
        len(output.raw_evidence) + len(output.macro_events) + len(output.social_signals)
        for output in request.provider_outputs
    )
    summary = (
        "CrewAI Flow sidecar contract accepted normalized provider packets. "
        f"providers={len(provider_ids)} payload_items={payload_count} "
        f"missing_sources={missing_count}. "
        "No LLM-backed deep-dive task has run in this scaffold slice."
    )
    planned_tasks = build_task_plan(request)
    return ResearchFlowContractOutput(
        generated_at=now,
        observed_at=now,
        watched_symbols=request.symbols,
        summary=summary,
        planned_tasks=planned_tasks,
        memory_update={
            "status": "not_written",
            "reason": (
                "CrewAI Flow sidecar contract is validated, but trade-memory writes "
                "remain disabled until explicit policy gates are added."
            ),
            "provider_ids": provider_ids,
            "planned_tasks": planned_tasks,
            "raw_web_text_injected": False,
            "broker_access": False,
            "contract_version": CONTRACT_VERSION,
        },
        raw_web_text_injected=False,
        broker_access=False,
    )


def _failure_output(message: str) -> ResearchFlowContractOutput:
    now = utc_now_iso()
    return ResearchFlowContractOutput(
        status="failed",
        generated_at=now,
        observed_at=now,
        summary="CrewAI Flow sidecar contract validation failed.",
        memory_update={
            "status": "not_written",
            "reason": "contract_validation_failed",
            "raw_web_text_injected": False,
            "broker_access": False,
            "contract_version": CONTRACT_VERSION,
        },
        errors=[message],
    )


def contract_cli() -> None:
    """Read one JSON request from stdin and emit one pure JSON contract payload."""
    raw_payload = sys.stdin.read().strip()
    try:
        request_payload = json.loads(raw_payload) if raw_payload else {}
        request = ResearchFlowRequest.model_validate(request_payload)
        output = build_contract_output(request)
    except (json.JSONDecodeError, ValidationError) as exc:
        output = _failure_output(str(exc))
        print(output.model_dump_json(indent=2))
        raise SystemExit(1) from exc

    print(output.model_dump_json(indent=2))
