from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import cast

import typer
from rich.panel import Panel
from rich.table import Table

from agentic_trader.ui_text import t as ui_t
from agentic_trader.cli_modules.common import console, emit_json
from agentic_trader.config import Settings, get_settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SettingsProvider = Callable[[], Settings]
AcceleratorProvider = Callable[[], dict[str, object]]
CpuCountProvider = Callable[[], int | None]
TotalMemoryProvider = Callable[[], int | None]

_settings_provider: SettingsProvider = get_settings
_accelerator_provider: AcceleratorProvider | None = None
_cpu_count_provider: CpuCountProvider | None = None
_total_memory_provider: TotalMemoryProvider | None = None


def _settings() -> Settings:
    return _settings_provider()


def _accelerator() -> dict[str, object]:
    if _accelerator_provider is not None:
        return _accelerator_provider()
    return accelerator_payload()


def _cpu_count() -> int | None:
    if _cpu_count_provider is not None:
        return _cpu_count_provider()
    return os.cpu_count()


def _total_memory() -> int | None:
    if _total_memory_provider is not None:
        return _total_memory_provider()
    return total_memory_bytes()


def _run_probe_command(command: list[str], *, timeout: float = 2.0) -> str | None:
    try:
        proc = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    output = proc.stdout.strip()
    return output or None


def total_memory_bytes() -> int | None:
    if sys.platform == "darwin":
        output = _run_probe_command(["sysctl", "-n", "hw.memsize"])
        if output and output.isdigit():
            return int(output)
    sysconf_total = _sysconf_total_memory_bytes()
    if sysconf_total is not None:
        return sysconf_total
    return _linux_meminfo_total_memory_bytes()


def _sysconf_total_memory_bytes() -> int | None:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
    except (AttributeError, OSError, ValueError):
        pages = page_size = None
    if (
        isinstance(pages, int)
        and isinstance(page_size, int)
        and pages > 0
        and page_size > 0
    ):
        return pages * page_size
    return None


def _linux_meminfo_total_memory_bytes() -> int | None:
    meminfo = Path("/proc/meminfo")
    if not meminfo.exists():
        return None
    try:
        lines = meminfo.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        total = _parse_memtotal_line(line)
        if total is not None:
            return total
    return None


def _parse_memtotal_line(line: str) -> int | None:
    if not line.startswith("MemTotal:"):
        return None
    parts = line.split()
    if len(parts) >= 2 and parts[1].isdigit():
        return int(parts[1]) * 1024
    return None


def _model_size_billions(model_name: str) -> float | None:
    separators = ":/,_-()[]{}"
    normalized = model_name.lower()
    for separator in separators:
        normalized = normalized.replace(separator, " ")
    for token in normalized.split():
        size = _model_size_token_billions(token)
        if size is not None:
            return size
    return None


def _model_size_token_billions(token: str) -> float | None:
    if not token.endswith("b"):
        return None
    numeric = token[:-1]
    if not numeric or numeric.startswith(".") or numeric.endswith("."):
        return None
    try:
        return float(numeric)
    except ValueError:
        return None


def accelerator_payload() -> dict[str, object]:
    if sys.platform == "darwin" and platform.machine().lower() == "arm64":
        return {
            "type": "apple_silicon",
            "detail": "Apple Silicon unified-memory accelerator available to supported local runtimes.",
        }
    if shutil.which("nvidia-smi"):
        output = _run_probe_command(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader",
            ]
        )
        if output:
            return {"type": "nvidia", "detail": output.splitlines()}
    return {
        "type": "unknown",
        "detail": "No accelerator probe succeeded with stdlib-safe local checks.",
    }


def _recommended_parallel_agents(
    cpu_count: int, memory_gb: float | None, model_b: float | None
) -> int:
    cpu_floor = max(1, cpu_count // 4)
    if memory_gb is None:
        recommended = min(2, cpu_floor)
    elif memory_gb < 24:
        recommended = 1
    elif memory_gb < 48:
        recommended = min(2, cpu_floor)
    else:
        recommended = min(4, cpu_floor)
    if model_b is not None and model_b >= 13 and (memory_gb is None or memory_gb < 48):
        recommended = 1
    return max(1, recommended)


def build_hardware_profile_payload(settings: Settings) -> dict[str, object]:
    """
    Build a local read-only snapshot of platform, hardware, and runtime recommendations.

    Produces a payload describing detected platform and hardware, configured model/runtime settings, safe parallelism and other operator-facing recommendations, and explanatory notes.

    Parameters:
        settings (Settings): Application settings containing runtime/model configuration used to estimate recommendations.

    Returns:
        dict: A mapping with these top-level keys:
            - "platform": system and Python version information.
            - "hardware": detected CPU count, total memory (bytes and GB), and accelerator details.
            - "configured_runtime": model name and related request/configuration fields from `settings`.
            - "recommendations": suggested safe parallel agents, adjusted token/timeout limits, and a profile hint.
            - "notes": human-readable operator guidance.
    """
    cpu_count = _cpu_count() or 1
    memory_bytes = _total_memory()
    memory_gb = round(memory_bytes / (1024**3), 2) if memory_bytes else None
    model_b = _model_size_billions(settings.model_name)
    safe_parallel_agents = _recommended_parallel_agents(cpu_count, memory_gb, model_b)
    constrained = safe_parallel_agents == 1
    return {
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python": sys.version.split()[0],
        },
        "hardware": {
            "cpu_count": cpu_count,
            "memory_bytes": memory_bytes,
            "memory_gb": memory_gb,
            "accelerator": _accelerator(),
        },
        "configured_runtime": {
            "model_name": settings.model_name,
            "estimated_model_size_b": model_b,
            "max_output_tokens": settings.max_output_tokens,
            "request_timeout_seconds": settings.request_timeout_seconds,
            "max_retries": settings.max_retries,
        },
        "recommendations": {
            "safe_parallel_agents": safe_parallel_agents,
            "max_output_tokens": (
                min(settings.max_output_tokens, 2048)
                if constrained
                else settings.max_output_tokens
            ),
            "request_timeout_seconds": max(settings.request_timeout_seconds, 180.0),
            "profile": "constrained-local" if constrained else "standard-local",
        },
        "notes": [
            "This is an operator hint, not an automatic runtime override.",
            "Use the lower of configured and recommended limits before long paper-operation runs.",
        ],
    }


def _workflow_step(
    order: int,
    *,
    name: str,
    command: str,
    purpose: str,
    required_before_long_run: bool,
) -> dict[str, object]:
    return {
        "order": order,
        "name": name,
        "command": command,
        "purpose": purpose,
        "required_before_long_run": required_before_long_run,
    }


OPERATOR_WORKFLOW_STEPS = [
    _workflow_step(
        1,
        name="environment_doctor",
        command="agentic-trader doctor",
        purpose="Verify model, runtime directory, database path, and basic provider reachability.",
        required_before_long_run=True,
    ),
    _workflow_step(
        2,
        name="hardware_profile",
        command="agentic-trader hardware-profile",
        purpose="Inspect local CPU, memory, accelerator hints, model size, and safe parallelism recommendations.",
        required_before_long_run=True,
    ),
    _workflow_step(
        3,
        name="provider_diagnostics",
        command="agentic-trader provider-diagnostics",
        purpose="Inspect source ladder, API-key readiness, and fallback warnings without leaking secrets.",
        required_before_long_run=True,
    ),
    _workflow_step(
        4,
        name="v1_readiness",
        command="agentic-trader v1-readiness --provider-check",
        purpose="Verify paper-operation gates and Alpaca external-paper readiness before longer operation.",
        required_before_long_run=True,
    ),
    _workflow_step(
        5,
        name="fast_smoke",
        command="pnpm run qa",
        purpose="Run CLI/Rich/Ink smoke QA and produce smoke-summary.json plus qa-report.md.",
        required_before_long_run=True,
    ),
    _workflow_step(
        6,
        name="one_cycle",
        command="pnpm run qa -- --include-runtime-cycle --runtime-symbol AAPL --runtime-interval 1d --runtime-lookback 180d",
        purpose="Optionally prove one strict foreground agent cycle with isolated runtime storage.",
        required_before_long_run=False,
    ),
    _workflow_step(
        7,
        name="review_outputs",
        command="agentic-trader review-run && agentic-trader trace-run && agentic-trader trade-context",
        purpose="Inspect decision, stage trace, context pack, broker outcome, and reviewable rationale.",
        required_before_long_run=True,
    ),
    _workflow_step(
        8,
        name="evidence_bundle",
        command="agentic-trader evidence-bundle",
        purpose="Package shared runtime truth, readiness payloads, logs, hardware profile, and latest smoke report.",
        required_before_long_run=True,
    ),
    _workflow_step(
        9,
        name="background_paper_operation",
        command="agentic-trader launch --symbols AAPL,MSFT --interval 1d --lookback 180d --continuous --background",
        purpose="Start longer paper operation only after the readiness and evidence steps are understood.",
        required_before_long_run=False,
    ),
]


def _operator_workflow_steps() -> list[dict[str, object]]:
    return [dict(step) for step in OPERATOR_WORKFLOW_STEPS]


def build_operator_workflow_payload(settings: Settings) -> dict[str, object]:
    """Return the canonical V1 operator review workflow without executing it."""
    return {
        "workflow_version": "operator-workflow.v1",
        "runtime_mode": settings.runtime_mode,
        "execution_backend": settings.execution_backend,
        "live_execution_enabled": settings.live_execution_enabled,
        "kill_switch_active": settings.execution_kill_switch_active,
        "paper_first": settings.execution_backend == "paper"
        and not settings.live_execution_enabled,
        "steps": _operator_workflow_steps(),
        "safety_notes": [
            "This workflow is descriptive and does not execute runtime actions.",
            "Live execution remains blocked until explicitly approved and implemented.",
            "Paper evidence and operator review should precede any longer background run.",
        ],
    }


def operator_workflow_command(
    json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
) -> None:
    """Show the canonical V1 operator review workflow without executing it."""
    settings = _settings()
    payload = build_operator_workflow_payload(settings)
    if json_output:
        emit_json(payload)
        return
    table = Table(title=ui_t("title.v1_operator_workflow"))
    table.add_column("#", style="cyan")
    table.add_column(ui_t("label.step"))
    table.add_column(ui_t("label.command"))
    table.add_column(ui_t("label.purpose"))
    for step in cast(list[dict[str, object]], payload["steps"]):
        table.add_row(
            str(step["order"]),
            str(step["name"]),
            str(step["command"]),
            str(step["purpose"]),
        )
    console.print(
        Panel(
            ui_t("message.operator_workflow_guidance"),
            title=ui_t("title.operator_workflow"),
            border_style="cyan",
        )
    )
    console.print(table)


def hardware_profile_command(
    json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
) -> None:
    """Show local hardware and model-capacity hints before long paper runs."""
    settings = _settings()
    payload = build_hardware_profile_payload(settings)
    if json_output:
        emit_json(payload)
        return

    hardware = cast(dict[str, object], payload["hardware"])
    configured = cast(dict[str, object], payload["configured_runtime"])
    recommendations = cast(dict[str, object], payload["recommendations"])
    table = Table(title=ui_t("title.hardware_profile"))
    table.add_column(ui_t("label.field"), style="cyan")
    table.add_column(ui_t("label.value"))
    table.add_row(ui_t("label.cpu_count"), str(hardware["cpu_count"]))
    table.add_row(ui_t("label.memory_gb"), str(hardware["memory_gb"]))
    accelerator = cast(dict[str, object], hardware["accelerator"])
    table.add_row(ui_t("label.accelerator"), str(accelerator.get("type", "unknown")))
    table.add_row(ui_t("label.model"), str(configured["model_name"]))
    table.add_row(
        ui_t("label.estimated_model_size"),
        str(configured["estimated_model_size_b"]),
    )
    table.add_row(
        ui_t("label.safe_parallel_agents"),
        str(recommendations["safe_parallel_agents"]),
    )
    table.add_row(ui_t("label.token_hint"), str(recommendations["max_output_tokens"]))
    table.add_row(ui_t("label.profile"), str(recommendations["profile"]))
    console.print(table)


def register_operator_readiness_commands(
    app: typer.Typer,
    *,
    settings_provider: SettingsProvider | None = None,
    accelerator_provider: AcceleratorProvider | None = None,
    cpu_count_provider: CpuCountProvider | None = None,
    total_memory_provider: TotalMemoryProvider | None = None,
) -> None:
    global \
        _settings_provider, \
        _accelerator_provider, \
        _cpu_count_provider, \
        _total_memory_provider
    if settings_provider is not None:
        _settings_provider = settings_provider
    if accelerator_provider is not None:
        _accelerator_provider = accelerator_provider
    if cpu_count_provider is not None:
        _cpu_count_provider = cpu_count_provider
    if total_memory_provider is not None:
        _total_memory_provider = total_memory_provider
    app.command("operator-workflow")(operator_workflow_command)
    app.command("hardware-profile")(hardware_profile_command)
