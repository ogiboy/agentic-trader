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
    """
    Render a readiness checks table to the shared console.
    
    Populate and print a rich Table with columns for check name, pass/fail state, whether the check is blocking, and details. The table is built from payload["checks"], where each check is a mapping that may contain the keys:
    - "name": display name of the check
    - "passed": truthy value indicates a passing check
    - "blocking": whether a failing check is blocking (defaults to True)
    - "details": additional information about the check
    
    Parameters:
        title (str): Title text for the table.
        payload (Mapping[str, object]): Mapping containing a "checks" iterable of check mappings described above.
    """
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
    """
    Render the v1 readiness summary panel and detailed readiness tables for paper and Alpaca paper operations.
    
    Generates a readiness payload from the provided Settings, prints a summary Panel whose border is green when paper operations are allowed and yellow otherwise, and renders a readiness table for paper operations and for Alpaca paper when their data is present.
    
    Parameters:
        settings (Settings): Configuration used to produce the readiness payload.
    """
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
