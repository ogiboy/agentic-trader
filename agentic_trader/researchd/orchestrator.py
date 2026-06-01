"""Optional research sidecar orchestration boundary.

The sidecar is intentionally separate from the trading runtime. It can assemble
research evidence and world-state packets, but it does not call broker,
execution, run persistence, or strict trading-gate code.
"""

import json
import os
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, cast
from uuid import uuid4

from agentic_trader.config import Settings
from agentic_trader.json_utils import object_dict_list as _object_mapping_list
from agentic_trader.json_utils import object_dict_or_none as _object_mapping
from agentic_trader.researchd.crewai_setup import default_crewai_flow_dir
from agentic_trader.researchd.providers import (
    ResearchEvidenceProvider,
    ResearchProviderOutput,
    default_research_providers,
    provider_health_from_output,
    source_attributions_from_output,
)
from agentic_trader.schemas import (
    DataSourceAttribution,
    EntityDossier,
    MacroEvent,
    RawEvidenceRecord,
    ResearchFinding,
    ResearchProviderHealth,
    ResearchSidecarState,
    SocialSignal,
    WorldStateSnapshot,
)
from agentic_trader.security import redact_sensitive_text
from agentic_trader.time_utils import utc_now_iso

ContractRunner = Callable[
    [list[str], str, Path, dict[str, str], float],
    subprocess.CompletedProcess[str],
]

_SHELL_ENV_ALLOWLIST = {
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
_MODEL_ENV_PREFIXES = (
    "ANTHROPIC_",
    "CREWAI_",
    "GEMINI_",
    "GOOGLE_",
    "GROQ_",
    "LITELLM_",
    "MISTRAL_",
    "OPENAI_",
)


def _contract_error_items(value: object) -> list[object]:
    """
    Normalize an error-like value into a list of items.

    Parameters:
        value (object): An error value which may already be a list or tuple, may be None, or may be a single item.

    Returns:
        list[object]: A list of items: the same list if `value` is a list, the tuple converted to a list if `value` is a tuple, an empty list if `value` is None, or a single-element list containing `value` otherwise.
    """
    if isinstance(value, list):
        return cast(list[object], value)
    if isinstance(value, tuple):
        return list(cast(tuple[object, ...], value))
    if value is None:
        return []
    return [value]


def _sidecar_process_env() -> dict[str, str]:
    """
    Create a restricted environment mapping for running the research sidecar subprocess.

    Only environment variables whose names are in the internal allowlist or start with configured model/provider prefixes are included; the returned mapping also forces CREWAI_TRACING_ENABLED to "false" to disable tracing.

    Returns:
        env (dict[str, str]): Environment variable name -> value mapping suitable for passing to a subprocess.
    """
    env: dict[str, str] = {}
    for key, value in os.environ.items():
        if key in _SHELL_ENV_ALLOWLIST or key.startswith(_MODEL_ENV_PREFIXES):
            env[key] = value
    env["CREWAI_TRACING_ENABLED"] = "false"
    return env


def parse_research_symbols(raw_symbols: str) -> list[str]:
    """
    Parse a comma-separated string of symbols into a list of normalized symbols.

    Parameters:
        raw_symbols (str): Comma-separated symbols; whitespace around entries is ignored.

    Returns:
        list[str]: Trimmed symbols converted to uppercase, with empty entries removed.
    """
    return [
        symbol.strip().upper() for symbol in raw_symbols.split(",") if symbol.strip()
    ]


def _empty_raw_evidence_records() -> list[RawEvidenceRecord]:
    return []


def _empty_macro_events() -> list[MacroEvent]:
    return []


def _empty_social_signals() -> list[SocialSignal]:
    return []


def _empty_research_findings() -> list[ResearchFinding]:
    return []


def _empty_entity_dossiers() -> list[EntityDossier]:
    return []


def _empty_memory_update() -> dict[str, object]:
    return {}


@dataclass(frozen=True)
class ResearchPipelineResult:
    """Result of one sidecar pipeline pass."""

    state: ResearchSidecarState
    world_state: WorldStateSnapshot | None = None
    raw_evidence: list[RawEvidenceRecord] = field(
        default_factory=_empty_raw_evidence_records
    )
    macro_events: list[MacroEvent] = field(default_factory=_empty_macro_events)
    social_signals: list[SocialSignal] = field(default_factory=_empty_social_signals)
    findings: list[ResearchFinding] = field(default_factory=_empty_research_findings)
    dossiers: list[EntityDossier] = field(default_factory=_empty_entity_dossiers)
    memory_update: dict[str, object] = field(default_factory=_empty_memory_update)


class ResearchSidecarBackend(Protocol):
    """Backend interface for optional future engines such as CrewAI."""

    name: str

    def run(
        self,
        *,
        settings: Settings,
        symbols: list[str],
        provider_outputs: list[ResearchProviderOutput],
    ) -> ResearchPipelineResult:
        """Run research synthesis for already-normalized provider output."""
        ...


class NoopResearchBackend:
    """Safe backend that records source state without synthesizing fake findings."""

    name = "noop"

    def run(
        self,
        *,
        settings: Settings,
        symbols: list[str],
        provider_outputs: list[ResearchProviderOutput],
    ) -> ResearchPipelineResult:
        now = utc_now_iso()
        raw_evidence: list[RawEvidenceRecord] = []
        macro_events: list[MacroEvent] = []
        social_signals: list[SocialSignal] = []
        health: list[ResearchProviderHealth] = []
        attributions: list[DataSourceAttribution] = []

        for output in provider_outputs:
            raw_evidence.extend(output.raw_evidence)
            macro_events.extend(output.macro_events)
            social_signals.extend(output.social_signals)
            health.append(provider_health_from_output(output))
            attributions.extend(source_attributions_from_output(output))

        world_state = WorldStateSnapshot(
            snapshot_id=f"world-{uuid4()}",
            mode=settings.research_mode,
            generated_at=now,
            observed_at=now,
            source_attributions=attributions,
            watched_symbols=symbols,
            macro_events=macro_events,
            social_signals=social_signals,
            findings=[],
            summary=_research_world_state_summary(
                raw_evidence_count=len(raw_evidence),
                macro_event_count=len(macro_events),
                social_signal_count=len(social_signals),
                finding_count=0,
            ),
        )
        state = ResearchSidecarState(
            mode=settings.research_mode,
            enabled=settings.research_sidecar_enabled,
            backend=self.name,
            status="completed",
            updated_at=now,
            last_started_at=now,
            last_successful_update_at=now,
            watched_symbols=symbols,
            provider_health=health,
            source_health_summary=summarize_provider_health(health),
        )
        return ResearchPipelineResult(
            state=state,
            world_state=world_state,
            raw_evidence=raw_evidence,
            macro_events=macro_events,
            social_signals=social_signals,
            memory_update={
                "status": "not_written",
                "reason": "trade memory writes are intentionally disabled for research snapshots",
                "raw_web_text_injected": False,
            },
        )


class CrewAiResearchBackend:
    """Subprocess boundary for the tracked uv-managed CrewAI Flow sidecar."""

    name = "crewai"

    def __init__(
        self,
        *,
        flow_dir: Path | None = None,
        uv_path: str | None = None,
        timeout_seconds: float = 60.0,
        command_runner: ContractRunner | None = None,
    ) -> None:
        self.flow_dir = flow_dir
        self.uv_path = uv_path
        self.timeout_seconds = timeout_seconds
        self.command_runner = command_runner or self._run_contract_process

    def run(
        self,
        *,
        settings: Settings,
        symbols: list[str],
        provider_outputs: list[ResearchProviderOutput],
    ) -> ResearchPipelineResult:
        """
        Invoke the configured CrewAI Flow sidecar to synthesize a research pipeline result for the given symbols and provider outputs.

        Runs the CrewAI Flow contract (using the configured flow directory and uv executable), supplies a JSON request built from the provided settings, symbols, and normalized provider outputs, and translates the contract response into a ResearchPipelineResult. On detection of missing prerequisites, non-JSON or failing contract output, timeouts, or startup errors, returns a failed ResearchPipelineResult describing the problem.

        Parameters:
            settings (Settings): Runtime settings that control mode and backend configuration.
            symbols (list[str]): List of watched symbol identifiers for the research run.
            provider_outputs (list[ResearchProviderOutput]): Normalized outputs from research providers to include in the request payload.

        Returns:
            ResearchPipelineResult: The pipeline result produced from the CrewAI Flow contract output, or a failed result explaining why the sidecar run did not complete.
        """
        flow_dir = self.flow_dir or default_crewai_flow_dir(settings)
        uv_path = self.uv_path or shutil.which("uv")
        now = utc_now_iso()
        if uv_path is None:
            return self._failed_result(
                settings=settings,
                symbols=symbols,
                provider_outputs=provider_outputs,
                now=now,
                message="uv is required before the CrewAI Flow sidecar can run.",
            )
        if not (flow_dir / "pyproject.toml").exists():
            return self._failed_result(
                settings=settings,
                symbols=symbols,
                provider_outputs=provider_outputs,
                now=now,
                message=f"CrewAI Flow sidecar project is missing at {flow_dir}.",
            )
        if not (flow_dir / ".venv").exists():
            return self._failed_result(
                settings=settings,
                symbols=symbols,
                provider_outputs=provider_outputs,
                now=now,
                message=(
                    "CrewAI Flow sidecar environment is not installed. "
                    "Run 'pnpm run setup:research-flow' first."
                ),
            )

        request_payload = {
            "mode": settings.research_mode,
            "symbols": symbols,
            "provider_outputs": [
                self._provider_output_payload(output) for output in provider_outputs
            ],
        }
        env = _sidecar_process_env()
        command = [
            uv_path,
            "run",
            "--locked",
            "--no-sync",
            "research-flow-contract",
        ]
        try:
            completed = self.command_runner(
                command,
                json.dumps(request_payload),
                flow_dir,
                env,
                self.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return self._failed_result(
                settings=settings,
                symbols=symbols,
                provider_outputs=provider_outputs,
                now=now,
                message="CrewAI Flow sidecar contract timed out.",
            )
        except Exception as exc:
            return self._failed_result(
                settings=settings,
                symbols=symbols,
                provider_outputs=provider_outputs,
                now=now,
                message=(
                    "CrewAI Flow sidecar contract failed to start: "
                    f"{redact_sensitive_text(exc, max_length=240)}"
                ),
            )

        contract_payload = self._contract_payload_from_process(completed)
        if contract_payload is None:
            return self._failed_result(
                settings=settings,
                symbols=symbols,
                provider_outputs=provider_outputs,
                now=now,
                message=(
                    "CrewAI Flow sidecar returned non-JSON output. "
                    f"stdout={redact_sensitive_text(self._trim(completed.stdout), max_length=500)} "
                    f"stderr={redact_sensitive_text(self._trim(completed.stderr), max_length=500)}"
                ),
            )
        if completed.returncode != 0 or contract_payload.get("status") != "completed":
            errors = contract_payload.get("errors")
            error_items = _contract_error_items(errors)
            return self._failed_result(
                settings=settings,
                symbols=symbols,
                provider_outputs=provider_outputs,
                now=now,
                message=(
                    "; ".join(str(item) for item in error_items)
                    if error_items
                    else "CrewAI Flow sidecar contract returned a failed status."
                ),
            )

        return self._result_from_contract_payload(
            settings=settings,
            symbols=symbols,
            provider_outputs=provider_outputs,
            payload=contract_payload,
        )

    @staticmethod
    def _run_contract_process(
        command: list[str],
        stdin_payload: str,
        cwd: Path,
        env: dict[str, str],
        timeout_seconds: float,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            input=stdin_payload,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )

    @staticmethod
    def _provider_output_payload(output: ResearchProviderOutput) -> dict[str, object]:
        return {
            "metadata": output.metadata.model_dump(mode="json"),
            "raw_evidence": [
                item.model_dump(mode="json") for item in output.raw_evidence
            ],
            "macro_events": [
                item.model_dump(mode="json") for item in output.macro_events
            ],
            "social_signals": [
                item.model_dump(mode="json") for item in output.social_signals
            ],
            "missing_reasons": list(output.missing_reasons),
        }

    @staticmethod
    def _contract_payload_from_process(
        completed: subprocess.CompletedProcess[str],
    ) -> dict[str, object] | None:
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return None
        return _object_mapping(payload)

    @staticmethod
    def _trim(value: str, *, limit: int = 500) -> str:
        return value.strip().replace("\n", " ")[:limit]

    def _failed_result(
        self,
        *,
        settings: Settings,
        symbols: list[str],
        provider_outputs: list[ResearchProviderOutput],
        now: str,
        message: str,
    ) -> ResearchPipelineResult:
        health = [provider_health_from_output(output) for output in provider_outputs]
        state = ResearchSidecarState(
            mode=settings.research_mode,
            enabled=settings.research_sidecar_enabled,
            backend=self.name,
            status="failed",
            updated_at=now,
            last_started_at=now,
            last_error=message,
            watched_symbols=symbols,
            provider_health=health,
            source_health_summary=summarize_provider_health(health),
        )
        return ResearchPipelineResult(
            state=state,
            memory_update={
                "status": "not_written",
                "reason": "crewai_backend_failed",
                "error": message,
                "raw_web_text_injected": False,
                "broker_access": False,
            },
        )

    def _result_from_contract_payload(
        self,
        *,
        settings: Settings,
        symbols: list[str],
        provider_outputs: list[ResearchProviderOutput],
        payload: dict[str, object],
    ) -> ResearchPipelineResult:
        health = [provider_health_from_output(output) for output in provider_outputs]
        raw_evidence: list[RawEvidenceRecord] = []
        macro_events: list[MacroEvent] = []
        social_signals: list[SocialSignal] = []
        for output in provider_outputs:
            raw_evidence.extend(output.raw_evidence)
            macro_events.extend(output.macro_events)
            social_signals.extend(output.social_signals)

        macro_events.extend(
            MacroEvent.model_validate(item)
            for item in _object_mapping_list(payload.get("macro_events"))
        )
        social_signals.extend(
            SocialSignal.model_validate(item)
            for item in _object_mapping_list(payload.get("social_signals"))
        )
        findings = [
            ResearchFinding.model_validate(item)
            for item in _object_mapping_list(payload.get("findings"))
        ]
        dossiers = [
            EntityDossier.model_validate(item)
            for item in _object_mapping_list(payload.get("dossiers"))
        ]
        generated_at = str(payload.get("generated_at") or utc_now_iso())
        observed_at = str(payload.get("observed_at") or generated_at)
        attributions: list[DataSourceAttribution] = []
        for output in provider_outputs:
            attributions.extend(source_attributions_from_output(output))
        world_state = WorldStateSnapshot(
            snapshot_id=f"world-{uuid4()}",
            mode=settings.research_mode,
            generated_at=generated_at,
            observed_at=observed_at,
            source_attributions=attributions,
            watched_symbols=symbols,
            entity_dossiers=dossiers,
            macro_events=macro_events,
            social_signals=social_signals,
            findings=findings,
            summary=str(
                payload.get("summary")
                or _research_world_state_summary(
                    raw_evidence_count=len(raw_evidence),
                    macro_event_count=len(macro_events),
                    social_signal_count=len(social_signals),
                    finding_count=len(findings),
                )
            ),
        )
        payload_memory_update = payload.get("memory_update", {})
        memory_update = _object_mapping(payload_memory_update) or {}
        memory_update.setdefault("status", "not_written")
        memory_update.setdefault("raw_web_text_injected", False)
        memory_update.setdefault("broker_access", False)
        memory_update["contract_version"] = str(
            payload.get("contract_version") or "unknown"
        )
        state = ResearchSidecarState(
            mode=settings.research_mode,
            enabled=settings.research_sidecar_enabled,
            backend=self.name,
            status="completed",
            updated_at=generated_at,
            last_started_at=generated_at,
            last_successful_update_at=generated_at,
            watched_symbols=symbols,
            provider_health=health,
            source_health_summary=summarize_provider_health(health),
        )
        return ResearchPipelineResult(
            state=state,
            world_state=world_state,
            raw_evidence=raw_evidence,
            macro_events=macro_events,
            social_signals=social_signals,
            findings=findings,
            dossiers=dossiers,
            memory_update=memory_update,
        )


def summarize_provider_health(
    provider_health: list[ResearchProviderHealth],
) -> dict[str, int]:
    """Count provider health by freshness status for dashboard consumers."""
    summary = {"fresh": 0, "stale": 0, "unknown": 0, "missing": 0}
    for item in provider_health:
        summary[item.freshness] = summary.get(item.freshness, 0) + 1
    return summary


def _research_world_state_summary(
    *,
    raw_evidence_count: int,
    macro_event_count: int,
    social_signal_count: int,
    finding_count: int,
) -> str:
    if any(
        count > 0
        for count in (
            raw_evidence_count,
            macro_event_count,
            social_signal_count,
            finding_count,
        )
    ):
        return (
            "Research sidecar assembled normalized evidence packets: "
            f"raw_evidence={raw_evidence_count}, macro_events={macro_event_count}, "
            f"social_signals={social_signal_count}, findings={finding_count}. "
            "Trade-memory writes remain disabled."
        )
    return (
        "Research sidecar foundation ran with provider scaffolds only; "
        "no live evidence or synthesized findings were produced."
    )


class ResearchSidecar:
    """Small sidecar runner with isolated provider and backend seams."""

    def __init__(
        self,
        settings: Settings,
        *,
        providers: list[ResearchEvidenceProvider] | None = None,
        backend: ResearchSidecarBackend | None = None,
    ) -> None:
        self.settings = settings
        if providers is None and settings.research_camofox_enabled:
            from agentic_trader.system.runtime_tools import (
                ensure_camofox_service_if_configured,
            )

            ensure_camofox_service_if_configured(settings)
        self.providers = providers or default_research_providers(settings)
        self.backend = backend or self._backend_from_settings(settings)

    def _backend_from_settings(self, settings: Settings) -> ResearchSidecarBackend:
        if settings.research_sidecar_backend == "crewai":
            return CrewAiResearchBackend()
        return NoopResearchBackend()

    def collect_once(self) -> ResearchPipelineResult:
        """Run one sidecar collection pass if the sidecar is enabled."""
        symbols = parse_research_symbols(self.settings.research_symbols)
        if (
            not self.settings.research_sidecar_enabled
            or self.settings.research_mode == "off"
        ):
            now = utc_now_iso()
            state = ResearchSidecarState(
                mode=self.settings.research_mode,
                enabled=False,
                backend=self.settings.research_sidecar_backend,
                status="disabled",
                updated_at=now,
                watched_symbols=symbols,
                provider_health=[],
                source_health_summary={},
            )
            return ResearchPipelineResult(state=state)

        provider_outputs = [
            provider.collect(
                symbols=symbols,
                limit=self.settings.research_max_events_per_source,
            )
            for provider in self.providers
        ]
        return self.backend.run(
            settings=self.settings,
            symbols=symbols,
            provider_outputs=provider_outputs,
        )
