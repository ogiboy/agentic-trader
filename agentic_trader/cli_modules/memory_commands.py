from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol, cast

import typer
from rich.panel import Panel
from rich.table import Table

from agentic_trader.ui_text import t as ui_t
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
    """
    Register the "memory-explorer" CLI command on the provided Typer app.
    
    The registered command accepts options for `symbol`, `interval`, `lookback`, `limit`, `use_latest_run`, and `--json`. When invoked it:
    - Retrieves settings from `deps` and requests a memory explorer payload.
    - If `--json` is passed, emits the raw payload as JSON.
    - If the service reports unavailable, prints a warning panel and exits.
    - Otherwise validates returned match entries into `HistoricalMemoryMatch` instances and renders them.
    
    Parameters:
        app: The Typer application to register the command on.
        deps: Dependency container providing settings, payload providers, JSON emitter, and other utilities used by the command.
    """
    @app.command("memory-explorer")
    def memory_explorer(
        symbol: str | None = typer.Option(None, help=ui_t("help.symbol")),
        interval: str | None = typer.Option(None, help=ui_t("help.interval")),
        lookback: str = typer.Option("180d", help=ui_t("help.lookback")),
        limit: int = typer.Option(
            5, min=1, max=20, help=ui_t("help.memory_explorer_limit")
        ),
        use_latest_run: bool = typer.Option(
            True, help=ui_t("help.memory_explorer_use_latest_run")
        ),
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
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
                    ui_t("message.memory_explorer_temporarily_unavailable").format(
                        error=payload["error"]
                    ),
                    title=ui_t("label.observer_mode"),
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
    """
    Register the "retrieval-inspection" subcommand on the given Typer app.
    
    The command accepts an optional run_id and a --json flag. When invoked it:
    - obtains settings from deps and fetches a retrieval inspection payload;
    - if --json is set, emits the raw payload as JSON;
    - if the payload is unavailable, prints a yellow panel explaining the temporary unavailability and exits with code 0;
    - if the payload contains no stages, prints a yellow panel indicating no context and exits with code 0;
    - otherwise renders the retrieval inspection view for the payload's stages and run_id.
    
    Parameters:
        app: The Typer application to register the command on.
        deps: Dependency container providing settings retrieval, payload fetchers, JSON emitter, and other helpers.
    """
    @app.command("retrieval-inspection")
    def retrieval_inspection(
        run_id: str | None = typer.Option(None, help=ui_t("help.run_id")),
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
    ) -> None:
        settings = deps.get_settings()
        payload = deps.retrieval_inspection_payload(settings, run_id=run_id)
        if json_output:
            deps.emit_json(payload)
            return
        if not payload["available"]:
            console.print(
                Panel(
                    ui_t("message.retrieval_inspection_temporarily_unavailable").format(
                        error=payload["error"]
                    ),
                    title=ui_t("label.observer_mode"),
                    border_style="yellow",
                )
            )
            raise typer.Exit(code=0)
        stages = cast(list[dict[str, object]], payload["stages"])
        if not stages:
            console.print(
                Panel(
                    ui_t("message.no_retrieval_inspection_context"),
                    title=ui_t("title.retrieval_inspection"),
                    border_style="yellow",
                )
            )
            raise typer.Exit(code=0)
        _render_retrieval_inspection(stages, payload["run_id"])


def _register_memory_policy_command(app: typer.Typer, deps: MemoryCommandDeps) -> None:
    """
    Register the "memory-policy" CLI command which displays the current memory write policies.
    
    When invoked the command obtains a snapshot of the memory write policies. If the `--json` flag is provided the snapshot is emitted as JSON; otherwise the command prints a table with columns for domain, allowed actors (comma-separated), and note.
    """
    @app.command("memory-policy")
    def memory_policy(
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
    ) -> None:
        payload = deps.memory_write_policy_snapshot()
        if json_output:
            deps.emit_json(payload)
            return

        table = Table(title=ui_t("title.memory_write_policy"))
        table.add_column(ui_t("label.domain"))
        table.add_column(ui_t("label.allowed_actors"))
        table.add_column(ui_t("label.note"))
        for domain, policy in payload.items():
            table.add_row(
                domain,
                ", ".join(policy["allowed_actors"]),
                str(policy["note"]),
            )
        console.print(table)


def _render_memory_matches(matches: Sequence[HistoricalMemoryMatch]) -> None:
    """
    Render a sequence of historical memory matches to the console as a formatted table.
    
    If `matches` is empty, display a yellow panel indicating no historical memories instead.
    
    Parameters:
        matches (Sequence[HistoricalMemoryMatch]): Ordered collection of historical memory match records to display.
    """
    if not matches:
        console.print(
            Panel(
                ui_t("message.no_historical_memories"),
                title=ui_t("title.memory_explorer"),
                border_style="yellow",
            )
        )
        return
    table = Table(title=ui_t("title.memory_explorer"))
    table.add_column(ui_t("label.created"))
    table.add_column(ui_t("label.symbol"))
    table.add_column(ui_t("label.score"))
    table.add_column(ui_t("label.source"))
    table.add_column(ui_t("stage.regime"))
    table.add_column(ui_t("label.strategy"))
    table.add_column(ui_t("label.bias"))
    table.add_column(ui_t("label.approved"))
    table.add_column(ui_t("label.reason"))
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
    """
    Assemble formatted lines describing the contents of a retrieval stage for display.
    
    Parameters:
    	stage (dict[str, object]): Mapping representing a retrieval stage. Expected keys:
    		- "retrieved_memories": list[str]
    		- "retrieval_explanations": list[dict] (explanation objects consumed by _retrieval_explanation_lines)
    		- "memory_notes": list[str]
    		- "shared_memory_bus": list[dict] with keys "role" and "summary"
    		- "recent_runs": list[str]
    		- "tool_outputs": list[str]
    
    Returns:
    	lines (list[str]): A list of display-ready lines grouped into titled sections; if the stage has no content returns a single localized fallback message.
    """
    retrieved_memories = cast(list[str], stage["retrieved_memories"])
    retrieval_explanations = cast(
        list[dict[str, object]], stage["retrieval_explanations"]
    )
    memory_notes = cast(list[str], stage["memory_notes"])
    shared_memory_bus = cast(list[dict[str, object]], stage["shared_memory_bus"])
    recent_runs = cast(list[str], stage["recent_runs"])
    tool_outputs = cast(list[str], stage["tool_outputs"])
    sections = [
        (f"{ui_t('label.retrieved_memories')}:", retrieved_memories),
        (f"{ui_t('label.why')}:", _retrieval_explanation_lines(retrieval_explanations)),
        (f"{ui_t('label.trade_memory')}:", memory_notes),
        (f"{ui_t('label.recent_runs')}:", recent_runs),
        (
            f"{ui_t('label.shared_bus')}:",
            [f"{entry['role']}: {entry['summary']}" for entry in shared_memory_bus],
        ),
        (f"{ui_t('label.tool_outputs')}:", tool_outputs),
    ]
    lines: list[str] = []
    for title, values in sections:
        if not values:
            continue
        if lines:
            lines.append("")
        lines.append(title)
        lines.extend(f"- {line}" for line in values)
    return lines or [ui_t("message.no_retrieval_stage_context")]


def _retrieval_explanation_lines(
    explanations: list[dict[str, object]],
) -> list[str]:
    """
    Build formatted summary lines from retrieval explanation entries.
    
    Parameters:
    	explanations (list[dict[str, object]]): Items expected to contain optional 'run_id' and an 'explanation' mapping with keys 'eligibility_reason', 'freshness', 'outcome_tag', and 'diversity_bucket'.
    
    Returns:
    	lines (list[str]): One formatted string per entry with an explanation, e.g. "run_id: reason=<...> freshness=<...> outcome=<...> bucket=<...>".
    """
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
    """
    Render a retrieval inspection summary table and detailed panels for each retrieval stage.
    
    Parameters:
        stages (list[dict[str, object]]): A sequence of retrieval stage dictionaries containing keys used by the renderer
            (e.g., "role", retrieved lists and explanation entries).
        run_id (object): Identifier for the run being inspected; inserted into the table title.
    """
    table = Table(
        title=ui_t("title.retrieval_inspection_for_run").format(run_id=run_id)
    )
    table.add_column(ui_t("label.role"))
    table.add_column(ui_t("label.retrieved_memories"))
    table.add_column(ui_t("label.why"))
    table.add_column(ui_t("label.trade_memory"))
    table.add_column(ui_t("label.shared_bus"))
    table.add_column(ui_t("label.recent_runs"))
    for stage in stages:
        table.add_row(*_retrieval_stage_counts(stage))
    console.print(table)
    for stage in stages:
        console.print(
            Panel(
                "\n".join(_retrieval_stage_lines(stage)),
                title=ui_t("title.retrieval_stage").format(role=stage["role"]),
                border_style="cyan",
            )
        )
