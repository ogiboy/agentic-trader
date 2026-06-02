from __future__ import annotations

import json

from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agentic_trader.cli_modules.common import console
from agentic_trader.schemas import RunArtifacts
from agentic_trader.ui_text import (
    LABEL_APPROVED,
    LABEL_CONFIDENCE,
    LABEL_DECISION_PATH,
    LABEL_ENTRY,
    LABEL_FALLBACK,
    LABEL_FIELD,
    LABEL_LLM,
    LABEL_NOTES,
    LABEL_ORDER_ID,
    LABEL_SIDE,
    LABEL_SOURCE,
    LABEL_STAGE,
    LABEL_STOP,
    LABEL_STRUCTURED_LLM,
    LABEL_TAKE_PROFIT,
    LABEL_VALUE,
    MESSAGE_ALL_AGENT_STAGES_LLM_PATH,
    MESSAGE_FALLBACK_USED_IN,
    STAGE_COORDINATOR,
    STAGE_MANAGER,
    STAGE_REGIME,
    STAGE_RISK,
    STAGE_STRATEGY,
    TITLE_EXECUTION_SUMMARY,
    TITLE_LLM_STATUS,
    TITLE_PIPELINE,
    TITLE_RUN_ARTIFACTS,
    TITLE_WARNING,
)


def render_execution_panels(order_id: str, artifacts: RunArtifacts) -> None:
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
            title=TITLE_RUN_ARTIFACTS,
        )
    )


def _execution_summary_table(
    order_id: str, artifacts: RunArtifacts, fallback_components: list[str]
) -> Table:
    summary = Table(title=TITLE_EXECUTION_SUMMARY)
    summary.add_column(LABEL_FIELD)
    summary.add_column(LABEL_VALUE)
    summary.add_row(LABEL_ORDER_ID, order_id)
    summary.add_row(LABEL_APPROVED, str(artifacts.execution.approved))
    summary.add_row(LABEL_SIDE, artifacts.execution.side)
    summary.add_row(LABEL_CONFIDENCE, f"{artifacts.execution.confidence:.2f}")
    summary.add_row(LABEL_ENTRY, f"{artifacts.execution.entry_price:.4f}")
    summary.add_row(LABEL_STOP, f"{artifacts.execution.stop_loss:.4f}")
    summary.add_row(LABEL_TAKE_PROFIT, f"{artifacts.execution.take_profit:.4f}")
    summary.add_row(
        LABEL_DECISION_PATH,
        LABEL_FALLBACK if fallback_components else LABEL_LLM,
    )
    return summary


def _pipeline_table(artifacts: RunArtifacts) -> Table:
    pipeline = Table(title=TITLE_PIPELINE)
    pipeline.add_column(LABEL_STAGE)
    pipeline.add_column(LABEL_SOURCE)
    pipeline.add_column(LABEL_NOTES)
    pipeline.add_row(
        STAGE_COORDINATOR,
        artifacts.coordinator.source,
        artifacts.coordinator.fallback_reason or LABEL_STRUCTURED_LLM,
    )
    pipeline.add_row(
        STAGE_REGIME,
        artifacts.regime.source,
        artifacts.regime.fallback_reason or LABEL_STRUCTURED_LLM,
    )
    pipeline.add_row(
        STAGE_STRATEGY,
        artifacts.strategy.source,
        artifacts.strategy.fallback_reason or LABEL_STRUCTURED_LLM,
    )
    pipeline.add_row(
        STAGE_RISK,
        artifacts.risk.source,
        artifacts.risk.fallback_reason or LABEL_STRUCTURED_LLM,
    )
    pipeline.add_row(
        STAGE_MANAGER,
        artifacts.manager.source,
        artifacts.manager.fallback_reason or LABEL_STRUCTURED_LLM,
    )
    return pipeline


def _render_execution_path_panel(fallback_components: list[str]) -> None:
    if fallback_components:
        console.print(
            Panel(
                Text(
                    f"{MESSAGE_FALLBACK_USED_IN}: {', '.join(fallback_components)}",
                    style="yellow",
                ),
                title=TITLE_WARNING,
                border_style="yellow",
            )
        )
        return
    console.print(
        Panel(
            Text(MESSAGE_ALL_AGENT_STAGES_LLM_PATH, style="green"),
            title=TITLE_LLM_STATUS,
            border_style="green",
        )
    )
