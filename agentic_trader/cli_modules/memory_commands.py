from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol, cast

import typer
from rich.panel import Panel
from rich.table import Table

from agentic_trader.ui_text import (
    HELP_INTERVAL,
    HELP_JSON,
    HELP_LOOKBACK,
    HELP_MEMORY_EXPLORER_LIMIT,
    HELP_MEMORY_EXPLORER_USE_LATEST_RUN,
    HELP_RUN_ID,
    HELP_SYMBOL,
    LABEL_ALLOWED_ACTORS,
    LABEL_APPROVED,
    LABEL_BIAS,
    LABEL_CREATED,
    LABEL_DOMAIN,
    LABEL_NOTE,
    LABEL_OBSERVER_MODE,
    LABEL_REASON,
    LABEL_RECENT_RUNS,
    LABEL_RETRIEVED_MEMORIES,
    LABEL_ROLE,
    LABEL_SCORE,
    LABEL_SHARED_BUS,
    LABEL_SOURCE,
    LABEL_STRATEGY,
    LABEL_SYMBOL,
    LABEL_TOOL_OUTPUTS,
    LABEL_TRADE_MEMORY,
    LABEL_WHY,
    MESSAGE_MEMORY_EXPLORER_TEMPORARILY_UNAVAILABLE,
    MESSAGE_NO_HISTORICAL_MEMORIES,
    MESSAGE_NO_RETRIEVAL_INSPECTION_CONTEXT,
    MESSAGE_NO_RETRIEVAL_STAGE_CONTEXT,
    MESSAGE_RETRIEVAL_INSPECTION_TEMPORARILY_UNAVAILABLE,
    STAGE_REGIME,
    TITLE_MEMORY_EXPLORER,
    TITLE_MEMORY_WRITE_POLICY,
    TITLE_RETRIEVAL_INSPECTION,
    TITLE_RETRIEVAL_INSPECTION_FOR_RUN,
    TITLE_RETRIEVAL_STAGE,
)
from agentic_trader.cli_modules.common import console
from agentic_trader.config import Settings
from agentic_trader.json_utils import object_mapping
from agentic_trader.memory.policy import MemoryWritePolicy
from agentic_trader.schemas import HistoricalMemoryMatch


class MemoryExplorerPayload(Protocol):
    def __call__(
        self,
        settings: Settings,
        *,
        symbol: str | None = None,
        interval: str | None = None,
        lookback: str = "180d",
        limit: int = 5,
        use_latest_run: bool = False,
    ) -> dict[str, object]: ...


class RetrievalInspectionPayload(Protocol):
    def __call__(
        self, settings: Settings, *, run_id: str | None = None
    ) -> dict[str, object]: ...


MemoryWritePolicySnapshot = Callable[[], dict[str, MemoryWritePolicy]]


@dataclass(frozen=True)
class MemoryCommandDeps:
    get_settings: Callable[[], Settings]
    emit_json: Callable[[object], None]
    memory_explorer_payload: MemoryExplorerPayload
    retrieval_inspection_payload: RetrievalInspectionPayload
    memory_write_policy_snapshot: MemoryWritePolicySnapshot


def register_memory_commands(app: typer.Typer, deps: MemoryCommandDeps) -> None:
    _register_memory_explorer_command(app, deps)
    _register_retrieval_inspection_command(app, deps)
    _register_memory_policy_command(app, deps)


def _register_memory_explorer_command(
    app: typer.Typer, deps: MemoryCommandDeps
) -> None:
    @app.command("memory-explorer")
    def memory_explorer(
        symbol: str | None = typer.Option(None, help=HELP_SYMBOL),
        interval: str | None = typer.Option(None, help=HELP_INTERVAL),
        lookback: str = typer.Option("180d", help=HELP_LOOKBACK),
        limit: int = typer.Option(
            5, min=1, max=20, help=HELP_MEMORY_EXPLORER_LIMIT
        ),
        use_latest_run: bool = typer.Option(
            True, help=HELP_MEMORY_EXPLORER_USE_LATEST_RUN
        ),
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    ) -> None:
        settings = deps.get_settings()
        payload = deps.memory_explorer_payload(
            settings,
            symbol=symbol,
            interval=interval,
            lookback=lookback,
            limit=limit,
            use_latest_run=use_latest_run,
        )
        if json_output:
            deps.emit_json(payload)
            return
        if not payload["available"]:
            console.print(
                Panel(
                    MESSAGE_MEMORY_EXPLORER_TEMPORARILY_UNAVAILABLE.format(
                        error=payload["error"]
                    ),
                    title=LABEL_OBSERVER_MODE,
                    border_style="yellow",
                )
            )
            raise typer.Exit(code=0)
        match_payloads = cast(list[dict[str, object]], payload["matches"])
        matches = [
            HistoricalMemoryMatch.model_validate(match) for match in match_payloads
        ]
        _render_memory_matches(matches)


def _register_retrieval_inspection_command(
    app: typer.Typer, deps: MemoryCommandDeps
) -> None:
    @app.command("retrieval-inspection")
    def retrieval_inspection(
        run_id: str | None = typer.Option(None, help=HELP_RUN_ID),
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    ) -> None:
        settings = deps.get_settings()
        payload = deps.retrieval_inspection_payload(settings, run_id=run_id)
        if json_output:
            deps.emit_json(payload)
            return
        if not payload["available"]:
            console.print(
                Panel(
                    MESSAGE_RETRIEVAL_INSPECTION_TEMPORARILY_UNAVAILABLE.format(
                        error=payload["error"]
                    ),
                    title=LABEL_OBSERVER_MODE,
                    border_style="yellow",
                )
            )
            raise typer.Exit(code=0)
        stages = cast(list[dict[str, object]], payload["stages"])
        if not stages:
            console.print(
                Panel(
                    MESSAGE_NO_RETRIEVAL_INSPECTION_CONTEXT,
                    title=TITLE_RETRIEVAL_INSPECTION,
                    border_style="yellow",
                )
            )
            raise typer.Exit(code=0)
        _render_retrieval_inspection(stages, payload["run_id"])


def _register_memory_policy_command(app: typer.Typer, deps: MemoryCommandDeps) -> None:
    @app.command("memory-policy")
    def memory_policy(
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    ) -> None:
        payload = deps.memory_write_policy_snapshot()
        if json_output:
            deps.emit_json(payload)
            return

        table = Table(title=TITLE_MEMORY_WRITE_POLICY)
        table.add_column(LABEL_DOMAIN)
        table.add_column(LABEL_ALLOWED_ACTORS)
        table.add_column(LABEL_NOTE)
        for domain, policy in payload.items():
            table.add_row(
                domain,
                ", ".join(policy["allowed_actors"]),
                str(policy["note"]),
            )
        console.print(table)


def _render_memory_matches(matches: Sequence[HistoricalMemoryMatch]) -> None:
    if not matches:
        console.print(
            Panel(
                MESSAGE_NO_HISTORICAL_MEMORIES,
                title=TITLE_MEMORY_EXPLORER,
                border_style="yellow",
            )
        )
        return
    table = Table(title=TITLE_MEMORY_EXPLORER)
    table.add_column(LABEL_CREATED)
    table.add_column(LABEL_SYMBOL)
    table.add_column(LABEL_SCORE)
    table.add_column(LABEL_SOURCE)
    table.add_column(STAGE_REGIME)
    table.add_column(LABEL_STRATEGY)
    table.add_column(LABEL_BIAS)
    table.add_column(LABEL_APPROVED)
    table.add_column(LABEL_REASON)
    for match in matches:
        table.add_row(
            match.created_at,
            match.symbol,
            f"{match.similarity_score:.2f}",
            match.retrieval_source,
            match.regime,
            match.strategy_family,
            match.manager_bias,
            str(match.approved),
            match.explanation.eligibility_reason,
        )
    console.print(table)


def _retrieval_stage_counts(
    stage: dict[str, object],
) -> tuple[str, str, str, str, str, str]:
    return (
        str(stage["role"]),
        str(len(cast(list[str], stage["retrieved_memories"]))),
        str(len(cast(list[dict[str, object]], stage["retrieval_explanations"]))),
        str(len(cast(list[str], stage["memory_notes"]))),
        str(len(cast(list[dict[str, object]], stage["shared_memory_bus"]))),
        str(len(cast(list[str], stage["recent_runs"]))),
    )


def _retrieval_stage_lines(stage: dict[str, object]) -> list[str]:
    retrieved_memories = cast(list[str], stage["retrieved_memories"])
    retrieval_explanations = cast(
        list[dict[str, object]], stage["retrieval_explanations"]
    )
    memory_notes = cast(list[str], stage["memory_notes"])
    shared_memory_bus = cast(list[dict[str, object]], stage["shared_memory_bus"])
    recent_runs = cast(list[str], stage["recent_runs"])
    tool_outputs = cast(list[str], stage["tool_outputs"])
    sections = [
        (f"{LABEL_RETRIEVED_MEMORIES}:", retrieved_memories),
        (f"{LABEL_WHY}:", _retrieval_explanation_lines(retrieval_explanations)),
        (f"{LABEL_TRADE_MEMORY}:", memory_notes),
        (f"{LABEL_RECENT_RUNS}:", recent_runs),
        (
            f"{LABEL_SHARED_BUS}:",
            [f"{entry['role']}: {entry['summary']}" for entry in shared_memory_bus],
        ),
        (f"{LABEL_TOOL_OUTPUTS}:", tool_outputs),
    ]
    lines: list[str] = []
    for title, values in sections:
        if not values:
            continue
        if lines:
            lines.append("")
        lines.append(title)
        lines.extend(f"- {line}" for line in values)
    return lines or [MESSAGE_NO_RETRIEVAL_STAGE_CONTEXT]


def _retrieval_explanation_lines(
    explanations: list[dict[str, object]],
) -> list[str]:
    lines: list[str] = []
    for item in explanations:
        run_id = str(item.get("run_id") or "-")
        explanation = object_mapping(item.get("explanation"))
        if not explanation:
            continue
        reason = str(explanation.get("eligibility_reason") or "-")
        freshness = str(explanation.get("freshness") or "-")
        outcome = str(explanation.get("outcome_tag") or "-")
        bucket = str(explanation.get("diversity_bucket") or "-")
        lines.append(
            f"{run_id}: reason={reason} freshness={freshness} "
            f"outcome={outcome} bucket={bucket}"
        )
    return lines


def _render_retrieval_inspection(
    stages: list[dict[str, object]], run_id: object
) -> None:
    table = Table(title=TITLE_RETRIEVAL_INSPECTION_FOR_RUN.format(run_id=run_id))
    table.add_column(LABEL_ROLE)
    table.add_column(LABEL_RETRIEVED_MEMORIES)
    table.add_column(LABEL_WHY)
    table.add_column(LABEL_TRADE_MEMORY)
    table.add_column(LABEL_SHARED_BUS)
    table.add_column(LABEL_RECENT_RUNS)
    for stage in stages:
        table.add_row(*_retrieval_stage_counts(stage))
    console.print(table)
    for stage in stages:
        console.print(
            Panel(
                "\n".join(_retrieval_stage_lines(stage)),
                title=TITLE_RETRIEVAL_STAGE.format(role=stage["role"]),
                border_style="cyan",
            )
        )
