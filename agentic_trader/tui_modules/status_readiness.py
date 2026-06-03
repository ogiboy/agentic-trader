from collections.abc import Mapping

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agentic_trader.config import Settings
from agentic_trader.diagnostics import v1_readiness_payload
from agentic_trader.json_utils import object_mapping, object_mapping_list
from agentic_trader.ui_text import (
    LABEL_BLOCKING,
    LABEL_CHECK,
    LABEL_DETAILS,
    LABEL_STATE,
    MESSAGE_V1_READINESS_STATUS_UNAVAILABLE,
    STYLE_KEY_COLUMN,
    TITLE_ALPACA_PAPER_CHECKS,
    TITLE_PAPER_OPERATION_CHECKS,
    TITLE_V1_READINESS,
    get_ui_text,
)

console = Console()


def render_readiness_table(title: str, payload: Mapping[str, object]) -> None:
    text = get_ui_text()
    table = Table(title=title)
    table.add_column(LABEL_CHECK, style=STYLE_KEY_COLUMN)
    table.add_column(LABEL_STATE)
    table.add_column(LABEL_BLOCKING)
    table.add_column(LABEL_DETAILS)
    for item in object_mapping_list(payload.get("checks")):
        table.add_row(
            str(item.get("name", "-")),
            (
                f"[green]{text.status_pass}[/green]"
                if item.get("passed")
                else f"[red]{text.status_fail}[/red]"
            ),
            str(item.get("blocking", True)),
            str(item.get("details", "")),
        )
    console.print(table)


def render_v1_readiness(settings: Settings) -> None:
    payload = object_mapping(v1_readiness_payload(settings, check_provider=False))
    paper = object_mapping(payload.get("paper_operations"))
    alpaca = object_mapping(payload.get("alpaca_paper"))
    paper_allowed = bool(paper.get("allowed"))
    console.print(
        Panel(
            str(payload.get("summary", MESSAGE_V1_READINESS_STATUS_UNAVAILABLE)),
            title=TITLE_V1_READINESS,
            border_style="green" if paper_allowed else "yellow",
        )
    )
    if paper:
        render_readiness_table(TITLE_PAPER_OPERATION_CHECKS, paper)
    if alpaca:
        render_readiness_table(TITLE_ALPACA_PAPER_CHECKS, alpaca)


__all__ = (
    "render_readiness_table",
    "render_v1_readiness",
)
