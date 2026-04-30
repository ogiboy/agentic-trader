"""Optional research sidecar orchestration boundary.

The sidecar is intentionally separate from the trading runtime. It can assemble
research evidence and world-state packets, but it does not call broker,
execution, run persistence, or strict trading-gate code.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
from collections.abc import Callable
from typing import Protocol
from uuid import uuid4

from agentic_trader.config import Settings
from agentic_trader.researchd.crewai_setup import default_crewai_flow_dir
from agentic_trader.researchd.providers import (
    ResearchEvidenceProvider,
    ResearchProviderOutput,
    default_research_providers,
    missing_attribution,
    provider_health_from_output,
)
from agentic_trader.schemas import (
    EntityDossier,
    MacroEvent,
    RawEvidenceRecord,
    ResearchFinding,
    ResearchProviderHealth,
    ResearchSidecarState,
    SocialSignal,
    WorldStateSnapshot,
)

ContractRunner = Callable[
    [list[str], str, Path, dict[str, str], float],
    subprocess.CompletedProcess[str],
]


def utc_now_iso() -> str:
    """Return an ISO timestamp in UTC for sidecar metadata."""
    return datetime.now(UTC).isoformat()


def parse_research_symbols(raw_symbols: str) -> list[str]:
    """Parse comma-separated watch symbols from settings."""
    return [
        symbol.strip().upper()
        for symbol in raw_symbols.split(",")
        if symbol.strip()
    ]


@dataclass(frozen=True)
class ResearchPipelineResult:
    """Result of one sidecar pipeline pass."""

    state: ResearchSidecarState
    world_state: WorldStateSnapshot | None = None
    raw_evidence: list[RawEvidenceRecord] = field(default_factory=list)
    macro_events: list[MacroEvent] = field(default_factory=list)
    social_signals: list[SocialSignal] = field(default_factory=list)
    findings: list[ResearchFinding] = field(default_factory=list)
    dossiers: list[EntityDossier] = field(default_factory=list)
    memory_update: dict[str, object] = field(default_factory=dict)


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
        attributions = []

        for output in provider_outputs:
            raw_evidence.extend(output.raw_evidence)
            macro_events.extend(output.macro_events)
            social_signals.extend(output.social_signals)
            health.append(provider_health_from_output(output))
            attributions.append(missing_attribution(output.metadata))

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
            summary=(
                "Research sidecar foundation ran with provider scaffolds only; "
                "no live evidence or synthesized findings were produced."
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
    """Subprocess boundary for the tracked uv-managed CrewAI sidecar."""

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
        flow_dir = self.flow_dir or default_crewai_flow_dir(settings)
        uv_path = self.uv_path or shutil.which("uv")
        now = utc_now_iso()
        if uv_path is None:
            return self._failed_result(
                settings=settings,
                symbols=symbols,
                provider_outputs=provider_outputs,
                now=now,
                message="uv is required before the CrewAI sidecar can run.",
            )
        if not (flow_dir / "pyproject.toml").exists():
            return self._failed_result(
                settings=settings,
                symbols=symbols,
                provider_outputs=provider_outputs,
                now=now,
                message=f"CrewAI sidecar project is missing at {flow_dir}.",
            )
        if not (flow_dir / ".venv").exists():
            return self._failed_result(
                settings=settings,
                symbols=symbols,
                provider_outputs=provider_outputs,
                now=now,
                message=(
                    "CrewAI sidecar environment is not installed. "
                    "Run 'pnpm run setup:research-crewai' first."
                ),
            )

        request_payload = {
            "mode": settings.research_mode,
            "symbols": symbols,
            "provider_outputs": [
                self._provider_output_payload(output)
                for output in provider_outputs
            ],
        }
        env = os.environ.copy()
        env.setdefault("CREWAI_TRACING_ENABLED", "false")
        command = [
            uv_path,
            "run",
            "--locked",
            "--no-sync",
            "research-crewai-contract",
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
                message="CrewAI sidecar contract timed out.",
            )
        except Exception as exc:
            return self._failed_result(
                settings=settings,
                symbols=symbols,
                provider_outputs=provider_outputs,
                now=now,
                message=f"CrewAI sidecar contract failed to start: {exc}",
            )

        contract_payload = self._contract_payload_from_process(completed)
        if contract_payload is None:
            return self._failed_result(
                settings=settings,
                symbols=symbols,
                provider_outputs=provider_outputs,
                now=now,
                message=(
                    "CrewAI sidecar returned non-JSON output. "
                    f"stdout={self._trim(completed.stdout)} "
                    f"stderr={self._trim(completed.stderr)}"
                ),
            )
        if completed.returncode != 0 or contract_payload.get("status") != "completed":
            errors = contract_payload.get("errors")
            return self._failed_result(
                settings=settings,
                symbols=symbols,
                provider_outputs=provider_outputs,
                now=now,
                message=(
                    "; ".join(str(item) for item in errors)
                    if isinstance(errors, list) and errors
                    else "CrewAI sidecar contract returned a failed status."
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
        return payload if isinstance(payload, dict) else None

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

        payload_macro_events = payload.get("macro_events", [])
        if not isinstance(payload_macro_events, list):
            payload_macro_events = []
        payload_social_signals = payload.get("social_signals", [])
        if not isinstance(payload_social_signals, list):
            payload_social_signals = []
        payload_findings = payload.get("findings", [])
        if not isinstance(payload_findings, list):
            payload_findings = []
        payload_dossiers = payload.get("dossiers", [])
        if not isinstance(payload_dossiers, list):
            payload_dossiers = []

        macro_events.extend(
            MacroEvent.model_validate(item)
            for item in payload_macro_events
            if isinstance(item, dict)
        )
        social_signals.extend(
            SocialSignal.model_validate(item)
            for item in payload_social_signals
            if isinstance(item, dict)
        )
        findings = [
            ResearchFinding.model_validate(item)
            for item in payload_findings
            if isinstance(item, dict)
        ]
        dossiers = [
            EntityDossier.model_validate(item)
            for item in payload_dossiers
            if isinstance(item, dict)
        ]
        generated_at = str(payload.get("generated_at") or utc_now_iso())
        observed_at = str(payload.get("observed_at") or generated_at)
        attributions = [
            missing_attribution(output.metadata) for output in provider_outputs
        ]
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
            summary=str(payload.get("summary") or ""),
        )
        payload_memory_update = payload.get("memory_update", {})
        memory_update = (
            dict(payload_memory_update)
            if isinstance(payload_memory_update, dict)
            else {}
        )
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
