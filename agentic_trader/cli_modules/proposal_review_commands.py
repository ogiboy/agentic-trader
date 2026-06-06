"""Trade proposal create/review CLI commands."""

from typing import cast

import typer
from rich.panel import Panel

from agentic_trader.ui_text import t as ui_t
from agentic_trader.cli_modules.common import console, emit_json, emit_json_error
from agentic_trader.cli_modules.proposal_actions import (
    approve_proposal_payload,
    reconcile_proposal_payload,
    refresh_proposal_payload,
    reject_proposal_payload,
)
from agentic_trader.cli_modules.proposal_desk_state import (
    refresh_trade_proposal_order_provider,
)
from agentic_trader.cli_modules.proposal_desk_state import settings as _settings
from agentic_trader.cli_modules.proposal_records import (
    create_trade_proposal_record,
    trade_proposal_draft_from_options,
)
from agentic_trader.execution.intent import ExecutionOutcome
from agentic_trader.schemas import TradeProposalRecord


def proposal_create(**options: str) -> None:
    """
    Create a pending trade proposal for manual review without sending an order.
    
    Builds a proposal draft from the provided CLI options and attempts to persist it as a pending trade proposal. On success either emits the proposal as JSON (when `options["json_output"]` is truthy) or prints a localized success panel with the proposal id, symbol, side, and reference price. If persistence fails with a `ValueError`, emits a localized error as JSON when `options["json_output"]` is truthy; otherwise prints a localized error panel. In both failure cases the command exits with code 2.
    
    Parameters:
        options (dict[str, str]): CLI options used to construct the proposal draft. Recognized keys include:
            - "json_output": when truthy, cause success and error output to be emitted as JSON instead of printed panels.
    """
    settings = _settings()
    draft = trade_proposal_draft_from_options(cast(dict[str, object], options))
    try:
        proposal = create_trade_proposal_record(settings=settings, draft=draft)
    except ValueError as exc:
        if bool(options["json_output"]):
            emit_json_error(exc)
            raise typer.Exit(code=2) from exc
        console.print(
            Panel(str(exc), title=ui_t("title.proposal_rejected"), border_style="red")
        )
        raise typer.Exit(code=2) from exc
    payload = proposal.model_dump(mode="json")
    if bool(options["json_output"]):
        emit_json(payload)
        return
    console.print(
        Panel(
            ui_t("message.trade_proposal_created").format(
                proposal_id=proposal.proposal_id,
                symbol=proposal.symbol,
                side=proposal.side.upper(),
                reference_price=proposal.reference_price,
            ),
            title=ui_t("title.trade_proposal_created"),
            border_style="green",
        )
    )


def proposal_approve(
    proposal_id: str = typer.Argument(..., help=ui_t("help.trade_proposal_id_approve")),
    review_notes: str = typer.Option(
        "", help=ui_t("help.trade_proposal_approval_notes")
    ),
    json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
) -> None:
    """
    Approve a pending trade proposal and submit it to the paper broker.
    
    Parameters:
        proposal_id (str): Identifier of the trade proposal to approve.
        review_notes (str): Optional reviewer notes to record with the approval.
        json_output (bool): When true, emit the resulting payload as JSON instead of human-readable output.
    
    Notes:
        Exits with code 2 on failure; when `json_output` is true an error JSON is emitted before exiting.
    """
    settings = _settings()
    try:
        payload = approve_proposal_payload(
            settings=settings,
            proposal_id=proposal_id,
            review_notes=review_notes,
        )
    except (RuntimeError, ValueError) as exc:
        if json_output:
            emit_json_error(exc)
            raise typer.Exit(code=2) from exc
        console.print(
            Panel(str(exc), title=ui_t("title.approval_blocked"), border_style="red")
        )
        raise typer.Exit(code=2) from exc
    if json_output:
        emit_json(payload)
        return
    proposal = TradeProposalRecord.model_validate(payload["proposal"])
    outcome = ExecutionOutcome.model_validate(payload["outcome"])
    console.print(
        Panel(
            ui_t("message.trade_proposal_approved").format(
                proposal_id=proposal.proposal_id,
                status=proposal.status,
                order_id=proposal.execution_order_id or "-",
                outcome_status=outcome.status,
            ),
            title=ui_t("title.trade_proposal_approved"),
            border_style="green" if proposal.status == "executed" else "yellow",
        )
    )


def proposal_reconcile(
    proposal_id: str = typer.Argument(
        ..., help=ui_t("help.trade_proposal_reconcile_id")
    ),
    review_notes: str = typer.Option(
        "", help=ui_t("help.trade_proposal_reconciliation_notes")
    ),
    json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
) -> None:
    """Reconcile an approved trade proposal against a recorded execution outcome."""
    settings = _settings()
    try:
        payload = reconcile_proposal_payload(
            settings=settings,
            proposal_id=proposal_id,
            review_notes=review_notes,
        )
    except ValueError as exc:
        if json_output:
            emit_json_error(exc)
            raise typer.Exit(code=2) from exc
        console.print(
            Panel(
                str(exc), title=ui_t("title.reconciliation_blocked"), border_style="red"
            )
        )
        raise typer.Exit(code=2) from exc
    if json_output:
        emit_json(payload)
        return
    proposal = TradeProposalRecord.model_validate(payload["proposal"])
    console.print(
        Panel(
            ui_t("message.trade_proposal_reconciled").format(
                proposal_id=proposal.proposal_id,
                status=proposal.status,
                order_id=proposal.execution_order_id or "-",
                outcome_status=proposal.execution_outcome_status or "-",
            ),
            title=ui_t("title.trade_proposal_reconciled"),
            border_style="green" if proposal.status == "executed" else "yellow",
        )
    )


def proposal_refresh(
    proposal_id: str = typer.Argument(..., help=ui_t("help.trade_proposal_refresh_id")),
    review_notes: str = typer.Option(
        "", help=ui_t("help.trade_proposal_refresh_notes")
    ),
    json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
) -> None:
    """
    Refreshes a trade proposal's broker metadata and displays the updated proposal and execution outcome.
    
    When `json_output` is true the command emits the raw payload as JSON; otherwise it prints a human-readable panel showing the proposal id, status, order id and outcome status. On failures that block the refresh (e.g. `RuntimeError` or `ValueError`) the command exits.
    
    Parameters:
        json_output (bool): If true emit JSON payload instead of printing a panel.
    
    Raises:
        typer.Exit: Exits with code 2 when the refresh is blocked by an error.
    """
    settings = _settings()
    try:
        payload = refresh_proposal_payload(
            settings=settings,
            proposal_id=proposal_id,
            review_notes=review_notes,
            refresh_trade_proposal_order_provider=(
                refresh_trade_proposal_order_provider()
            ),
        )
    except (RuntimeError, ValueError) as exc:
        if json_output:
            emit_json_error(exc)
            raise typer.Exit(code=2) from exc
        console.print(
            Panel(str(exc), title=ui_t("title.refresh_blocked"), border_style="red")
        )
        raise typer.Exit(code=2) from exc
    if json_output:
        emit_json(payload)
        return
    proposal = TradeProposalRecord.model_validate(payload["proposal"])
    outcome = ExecutionOutcome.model_validate(payload["outcome"])
    console.print(
        Panel(
            ui_t("message.trade_proposal_refreshed").format(
                proposal_id=proposal.proposal_id,
                status=proposal.status,
                order_id=proposal.execution_order_id or "-",
                outcome_status=outcome.status,
            ),
            title=ui_t("title.trade_proposal_refreshed"),
            border_style="green" if proposal.status == "executed" else "yellow",
        )
    )


def proposal_reject(
    proposal_id: str = typer.Argument(..., help=ui_t("help.trade_proposal_id_reject")),
    reason: str = typer.Option(..., help=ui_t("help.trade_proposal_rejection_reason")),
    json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
) -> None:
    """Reject a pending trade proposal and record the decision for audit."""
    settings = _settings()
    try:
        payload = reject_proposal_payload(
            settings=settings,
            proposal_id=proposal_id,
            reason=reason,
        )
    except ValueError as exc:
        if json_output:
            emit_json_error(exc)
            raise typer.Exit(code=2) from exc
        console.print(
            Panel(str(exc), title=ui_t("title.rejection_blocked"), border_style="red")
        )
        raise typer.Exit(code=2) from exc
    if json_output:
        emit_json(payload)
        return
    proposal = TradeProposalRecord.model_validate(payload)
    console.print(
        Panel(
            ui_t("message.trade_proposal_rejected").format(
                proposal_id=proposal.proposal_id,
                reason=proposal.rejection_reason,
            ),
            title=ui_t("title.trade_proposal_rejected"),
            border_style="yellow",
        )
    )
