from __future__ import annotations

import os
from typing import cast

from agentic_trader.json_utils import object_dict_list as object_mapping_list
from agentic_trader.json_utils import object_dict_or_none as object_mapping
from agentic_trader.researchd.orchestrator_types import ContractPayloadItems
from agentic_trader.researchd.providers import (
    ResearchProviderOutput,
    source_attributions_from_output,
)
from agentic_trader.schemas import (
    DataSourceAttribution,
    EntityDossier,
    MacroEvent,
    RawEvidenceRecord,
    ResearchFinding,
    SocialSignal,
)

SHELL_ENV_ALLOWLIST = {
    "HOME",
    "LANG",
    "LC_ALL",
    "PATH",
    "PYTHONUTF8",
    "REQUESTS_CA_BUNDLE",
    "SSL_CERT_FILE",
    "TEMP",
    "TERM",
    "TMP",
    "TMPDIR",
    "UV_CACHE_DIR",
    "UV_PYTHON",
    "VIRTUAL_ENV",
}
MODEL_ENV_PREFIXES = (
    "ANTHROPIC_",
    "CREWAI_",
    "GEMINI_",
    "GOOGLE_",
    "GROQ_",
    "LITELLM_",
    "MISTRAL_",
    "OPENAI_",
)


def contract_payload_items(
    provider_outputs: list[ResearchProviderOutput],
    payload: dict[str, object],
) -> ContractPayloadItems:
    raw_evidence: list[RawEvidenceRecord] = []
    macro_events: list[MacroEvent] = []
    social_signals: list[SocialSignal] = []
    attributions: list[DataSourceAttribution] = []
    for output in provider_outputs:
        raw_evidence.extend(output.raw_evidence)
        macro_events.extend(output.macro_events)
        social_signals.extend(output.social_signals)
        attributions.extend(source_attributions_from_output(output))
    macro_events.extend(
        MacroEvent.model_validate(item)
        for item in object_mapping_list(payload.get("macro_events"))
    )
    social_signals.extend(
        SocialSignal.model_validate(item)
        for item in object_mapping_list(payload.get("social_signals"))
    )
    return ContractPayloadItems(
        raw_evidence=raw_evidence,
        macro_events=macro_events,
        social_signals=social_signals,
        findings=[
            ResearchFinding.model_validate(item)
            for item in object_mapping_list(payload.get("findings"))
        ],
        dossiers=[
            EntityDossier.model_validate(item)
            for item in object_mapping_list(payload.get("dossiers"))
        ],
        attributions=attributions,
    )


def contract_memory_update(payload: dict[str, object]) -> dict[str, object]:
    memory_update = object_mapping(payload.get("memory_update", {})) or {}
    memory_update.setdefault("status", "not_written")
    memory_update.setdefault("raw_web_text_injected", False)
    memory_update.setdefault("broker_access", False)
    memory_update["contract_version"] = str(payload.get("contract_version") or "unknown")
    return memory_update


def contract_error_items(value: object) -> list[object]:
    if isinstance(value, list):
        return cast(list[object], value)
    if isinstance(value, tuple):
        return list(cast(tuple[object, ...], value))
    if value is None:
        return []
    return [value]


def sidecar_process_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for key, value in os.environ.items():
        if key in SHELL_ENV_ALLOWLIST or key.startswith(MODEL_ENV_PREFIXES):
            env[key] = value
    env["CREWAI_TRACING_ENABLED"] = "false"
    return env


__all__ = (
    "contract_error_items",
    "contract_memory_update",
    "contract_payload_items",
    "sidecar_process_env",
)
