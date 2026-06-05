from collections.abc import Mapping

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agentic_trader.config import Settings
from agentic_trader.diagnostics import v1_readiness_payload
from agentic_trader.json_utils import object_mapping, object_mapping_list
from agentic_trader.ui_text import t

console = Console()


def render_readiness_table(title: str, payload: Mapping[str, object]) -> None:
    table = Table(title=title)
    table.add_column(t("label.check"), style=t("style.key.column"))
    table.add_column(t("label.state"))
    table.add_column(t("label.blocking"))
    table.add_column(t("label.details"))
    for item in object_mapping_list(payload.get("checks")):
        table.add_row(
            str(item.get("name", "-")),
            (
                f"[green]{t('status.pass')}[/green]"
                if item.get("passed")
                else f"[red]{t('status.fail')}[/red]"
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
            str(payload.get("summary", t("message.v1.readiness.status.unavailable"))),
            title=t("title.v1.readiness"),
            border_style="green" if paper_allowed else "yellow",
        )
    )
    if paper:
        render_readiness_table(t("title.paper.operation.checks"), paper)
    if alpaca:
        render_readiness_table(t("title.alpaca.paper.checks"), alpaca)


__all__ = (
    "render_readiness_table",
    "render_v1_readiness",
)
