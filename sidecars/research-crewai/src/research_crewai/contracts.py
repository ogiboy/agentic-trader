from __future__ import annotations

from datetime import UTC, datetime
import json
import sys
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


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


class ResearchCrewRequest(BaseModel):
    """Input contract sent by the root runtime to the tracked CrewAI sidecar."""

    model_config = ConfigDict(extra="ignore")

    mode: str = "off"
    symbols: list[str] = Field(default_factory=list)
    provider_outputs: list[ResearchProviderOutputInput] = Field(default_factory=list)


class ResearchCrewContractOutput(BaseModel):
    """Pure JSON output contract returned to the root researchd backend."""

    status: Literal["completed", "failed"] = "completed"
    backend: str = "crewai"
    contract_version: str = "research-crewai.v1"
    generated_at: str
    observed_at: str
    watched_symbols: list[str] = Field(default_factory=list)
    summary: str = ""
    findings: list[dict[str, Any]] = Field(default_factory=list)
    dossiers: list[dict[str, Any]] = Field(default_factory=list)
    macro_events: list[dict[str, Any]] = Field(default_factory=list)
    social_signals: list[dict[str, Any]] = Field(default_factory=list)
    memory_update: dict[str, Any] = Field(default_factory=dict)
    raw_web_text_injected: bool = False
    broker_access: bool = False
    errors: list[str] = Field(default_factory=list)


def build_contract_output(
    request: ResearchCrewRequest,
) -> ResearchCrewContractOutput:
    """Build the deterministic sidecar contract without running LLM-backed tasks."""
    now = utc_now_iso()
    provider_ids = [
        output.metadata.provider_id for output in request.provider_outputs
    ]
    missing_count = sum(1 for output in request.provider_outputs if output.missing_reasons)
    payload_count = sum(
        len(output.raw_evidence)
        + len(output.macro_events)
        + len(output.social_signals)
        for output in request.provider_outputs
    )
    summary = (
        "CrewAI sidecar contract accepted normalized provider packets. "
        f"providers={len(provider_ids)} payload_items={payload_count} "
        f"missing_sources={missing_count}. "
        "No LLM-backed deep-dive task has run in this scaffold slice."
    )
    return ResearchCrewContractOutput(
        generated_at=now,
        observed_at=now,
        watched_symbols=request.symbols,
        summary=summary,
        memory_update={
            "status": "not_written",
            "reason": (
                "CrewAI sidecar contract is validated, but trade-memory writes "
                "remain disabled until explicit policy gates are added."
            ),
            "provider_ids": provider_ids,
            "raw_web_text_injected": False,
            "broker_access": False,
        },
        raw_web_text_injected=False,
        broker_access=False,
    )


def _failure_output(message: str) -> ResearchCrewContractOutput:
    now = utc_now_iso()
    return ResearchCrewContractOutput(
        status="failed",
        generated_at=now,
        observed_at=now,
        summary="CrewAI sidecar contract validation failed.",
        memory_update={
            "status": "not_written",
            "reason": "contract_validation_failed",
            "raw_web_text_injected": False,
            "broker_access": False,
        },
        errors=[message],
    )


def contract_cli() -> None:
    """Read one JSON request from stdin and emit one pure JSON contract payload."""
    raw_payload = sys.stdin.read().strip()
    try:
        request_payload = json.loads(raw_payload) if raw_payload else {}
        request = ResearchCrewRequest.model_validate(request_payload)
        output = build_contract_output(request)
    except (json.JSONDecodeError, ValidationError) as exc:
        output = _failure_output(str(exc))
        print(output.model_dump_json(indent=2))
        raise SystemExit(1) from exc

    print(output.model_dump_json(indent=2))
