"""Trade proposal create/review CLI commands."""

from typing import cast

import typer
from rich.panel import Panel

from agentic_trader import ui_text as text
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
    """Create a pending trade proposal for manual review without sending an order."""
    settings = _settings()
    draft = trade_proposal_draft_from_options(cast(dict[str, object], options))
    try:
        proposal = create_trade_proposal_record(settings=settings, draft=draft)
    except ValueError as exc:
        if bool(options["json_output"]):
            emit_json_error(exc)
            raise typer.Exit(code=2) from exc
        console.print(
            Panel(str(exc), title=text.TITLE_PROPOSAL_REJECTED, border_style="red")
        )
        raise typer.Exit(code=2) from exc
    payload = proposal.model_dump(mode="json")
    if bool(options["json_output"]):
        emit_json(payload)
        return
    console.print(
        Panel(
            text.MESSAGE_TRADE_PROPOSAL_CREATED.format(
                proposal_id=proposal.proposal_id,
                symbol=proposal.symbol,
                side=proposal.side.upper(),
                reference_price=proposal.reference_price,
            ),
            title=text.TITLE_TRADE_PROPOSAL_CREATED,
            border_style="green",
        )
    )


def proposal_approve(
    proposal_id: str = typer.Argument(..., help=text.HELP_TRADE_PROPOSAL_ID_APPROVE),
    review_notes: str = typer.Option("", help=text.HELP_TRADE_PROPOSAL_APPROVAL_NOTES),
    json_output: bool = typer.Option(False, "--json", help=text.HELP_JSON),
) -> None:
    """Approve a pending trade proposal and submit it to the paper broker."""
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
            Panel(str(exc), title=text.TITLE_APPROVAL_BLOCKED, border_style="red")
        )
        raise typer.Exit(code=2) from exc
    if json_output:
        emit_json(payload)
        return
    proposal = TradeProposalRecord.model_validate(payload["proposal"])
    outcome = ExecutionOutcome.model_validate(payload["outcome"])
    console.print(
        Panel(
            text.MESSAGE_TRADE_PROPOSAL_APPROVED.format(
                proposal_id=proposal.proposal_id,
                status=proposal.status,
                order_id=proposal.execution_order_id or "-",
                outcome_status=outcome.status,
            ),
            title=text.TITLE_TRADE_PROPOSAL_APPROVED,
            border_style="green" if proposal.status == "executed" else "yellow",
        )
    )


def proposal_reconcile(
    proposal_id: str = typer.Argument(..., help=text.HELP_TRADE_PROPOSAL_RECONCILE_ID),
    review_notes: str = typer.Option(
        "", help=text.HELP_TRADE_PROPOSAL_RECONCILIATION_NOTES
    ),
    json_output: bool = typer.Option(False, "--json", help=text.HELP_JSON),
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
            Panel(str(exc), title=text.TITLE_RECONCILIATION_BLOCKED, border_style="red")
        )
        raise typer.Exit(code=2) from exc
    if json_output:
        emit_json(payload)
        return
    proposal = TradeProposalRecord.model_validate(payload["proposal"])
    console.print(
        Panel(
            text.MESSAGE_TRADE_PROPOSAL_RECONCILED.format(
                proposal_id=proposal.proposal_id,
                status=proposal.status,
                order_id=proposal.execution_order_id or "-",
                outcome_status=proposal.execution_outcome_status or "-",
            ),
            title=text.TITLE_TRADE_PROPOSAL_RECONCILED,
            border_style="green" if proposal.status == "executed" else "yellow",
        )
    )


def proposal_refresh(
    proposal_id: str = typer.Argument(..., help=text.HELP_TRADE_PROPOSAL_REFRESH_ID),
    review_notes: str = typer.Option("", help=text.HELP_TRADE_PROPOSAL_REFRESH_NOTES),
    json_output: bool = typer.Option(False, "--json", help=text.HELP_JSON),
) -> None:
    """Refresh an executed trade proposal's broker metadata."""
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
            Panel(str(exc), title=text.TITLE_REFRESH_BLOCKED, border_style="red")
        )
        raise typer.Exit(code=2) from exc
    if json_output:
        emit_json(payload)
        return
    proposal = TradeProposalRecord.model_validate(payload["proposal"])
    outcome = ExecutionOutcome.model_validate(payload["outcome"])
    console.print(
        Panel(
            text.MESSAGE_TRADE_PROPOSAL_REFRESHED.format(
                proposal_id=proposal.proposal_id,
                status=proposal.status,
                order_id=proposal.execution_order_id or "-",
                outcome_status=outcome.status,
            ),
            title=text.TITLE_TRADE_PROPOSAL_REFRESHED,
            border_style="green" if proposal.status == "executed" else "yellow",
        )
    )


def proposal_reject(
    proposal_id: str = typer.Argument(..., help=text.HELP_TRADE_PROPOSAL_ID_REJECT),
    reason: str = typer.Option(..., help=text.HELP_TRADE_PROPOSAL_REJECTION_REASON),
    json_output: bool = typer.Option(False, "--json", help=text.HELP_JSON),
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
            Panel(str(exc), title=text.TITLE_REJECTION_BLOCKED, border_style="red")
        )
        raise typer.Exit(code=2) from exc
    if json_output:
        emit_json(payload)
        return
    proposal = TradeProposalRecord.model_validate(payload)
    console.print(
        Panel(
            text.MESSAGE_TRADE_PROPOSAL_REJECTED.format(
                proposal_id=proposal.proposal_id,
                reason=proposal.rejection_reason,
            ),
            title=text.TITLE_TRADE_PROPOSAL_REJECTED,
            border_style="yellow",
        )
    )
