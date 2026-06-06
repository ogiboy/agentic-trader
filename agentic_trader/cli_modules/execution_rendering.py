from __future__ import annotations

import json

from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agentic_trader.cli_modules.common import console
from agentic_trader.schemas import RunArtifacts
from agentic_trader.ui_text import t as ui_t


def render_execution_panels(order_id: str, artifacts: RunArtifacts) -> None:
    """
    Render UI panels showing an execution summary, pipeline stage details, fallback/LLM path status, and the raw run artifacts.
    
    Displays a two-column layout with an execution summary table (order id, approval, side, confidence, pricing, and decision-path label) alongside a pipeline table listing each stage's source and notes. Shows a status panel that indicates which components used fallback logic (or that all stages used the LLM path), and finally prints the JSON-serialized `artifacts` in a titled panel.
    
    Parameters:
        order_id (str): Identifier for the execution/order displayed in the summary.
        artifacts (RunArtifacts): Object containing execution metadata and pipeline stage information.
    """
    fallback_components = artifacts.fallback_components()
    console.print(
        Columns(
            [
                _execution_summary_table(order_id, artifacts, fallback_components),
                _pipeline_table(artifacts),
            ]
        )
    )
    _render_execution_path_panel(fallback_components)
    console.print(
        Panel(
            json.dumps(artifacts.model_dump(mode="json"), indent=2),
            title=ui_t("title.run_artifacts"),
        )
    )


def _execution_summary_table(
    order_id: str, artifacts: RunArtifacts, fallback_components: list[str]
) -> Table:
    """
    Builds a rich Table summarizing execution details for a given order.
    
    Parameters:
        artifacts (RunArtifacts): Object containing execution and stage data used to populate the table.
        fallback_components (list[str]): Names of pipeline components that fell back; if non-empty the decision-path row is labeled as a fallback.
    
    Returns:
        Table: A rich Table with rows for order id, approval status, side, confidence (formatted to 2 decimals), entry/stop/take_profit (formatted to 4 decimals), and a decision-path label (either a fallback label or an LLM label).
    """
    summary = Table(title=ui_t("title.execution_summary"))
    summary.add_column(ui_t("label.field"))
    summary.add_column(ui_t("label.value"))
    summary.add_row(ui_t("label.order_id"), order_id)
    summary.add_row(ui_t("label.approved"), str(artifacts.execution.approved))
    summary.add_row(ui_t("label.side"), artifacts.execution.side)
    summary.add_row(ui_t("label.confidence"), f"{artifacts.execution.confidence:.2f}")
    summary.add_row(ui_t("label.entry"), f"{artifacts.execution.entry_price:.4f}")
    summary.add_row(ui_t("label.stop"), f"{artifacts.execution.stop_loss:.4f}")
    summary.add_row(ui_t("label.take_profit"), f"{artifacts.execution.take_profit:.4f}")
    summary.add_row(
        ui_t("label.decision_path"),
        ui_t("label.fallback") if fallback_components else ui_t("label.llm"),
    )
    return summary


def _pipeline_table(artifacts: RunArtifacts) -> Table:
    """
    Builds a rich Table describing each pipeline stage with its source and notes.
    
    Parameters:
        artifacts (RunArtifacts): Execution artifacts containing stage entries
            (`coordinator`, `regime`, `strategy`, `risk`, `manager`). Each stage
            entry must expose `source` and optional `fallback_reason`.
    
    Returns:
        Table: A `rich.table.Table` titled with the pipeline label and three columns
        (stage, source, notes). Each row corresponds to a pipeline stage; the
        notes column contains the stage's `fallback_reason` when present, or a
        localized "structured LLM" label otherwise.
    """
    pipeline = Table(title=ui_t("title.pipeline"))
    pipeline.add_column(ui_t("label.stage"))
    pipeline.add_column(ui_t("label.source"))
    pipeline.add_column(ui_t("label.notes"))
    pipeline.add_row(
        ui_t("stage.coordinator"),
        artifacts.coordinator.source,
        artifacts.coordinator.fallback_reason or ui_t("label.structured_llm"),
    )
    pipeline.add_row(
        ui_t("stage.regime"),
        artifacts.regime.source,
        artifacts.regime.fallback_reason or ui_t("label.structured_llm"),
    )
    pipeline.add_row(
        ui_t("stage.strategy"),
        artifacts.strategy.source,
        artifacts.strategy.fallback_reason or ui_t("label.structured_llm"),
    )
    pipeline.add_row(
        ui_t("stage.risk"),
        artifacts.risk.source,
        artifacts.risk.fallback_reason or ui_t("label.structured_llm"),
    )
    pipeline.add_row(
        ui_t("stage.manager"),
        artifacts.manager.source,
        artifacts.manager.fallback_reason or ui_t("label.structured_llm"),
    )
    return pipeline


def _render_execution_path_panel(fallback_components: list[str]) -> None:
    """
    Render a status panel indicating whether any pipeline components used a fallback path.
    
    Displays a yellow warning panel listing the component names when `fallback_components` is non-empty;
    otherwise displays a green panel indicating all agent stages used the LLM path.
    
    Parameters:
        fallback_components (list[str]): Names of pipeline components that fell back to an alternative
            execution path; an empty list indicates no fallbacks were used.
    """
    if fallback_components:
        console.print(
            Panel(
                Text(
                    f"{ui_t('message.fallback_used_in')}: {', '.join(fallback_components)}",
                    style="yellow",
                ),
                title=ui_t("title.warning"),
                border_style="yellow",
            )
        )
        return
    console.print(
        Panel(
            Text(ui_t("message.all_agent_stages_llm_path"), style="green"),
            title=ui_t("title.llm_status"),
            border_style="green",
        )
    )
