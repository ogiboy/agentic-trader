from __future__ import annotations

from collections.abc import Callable
from typing import cast

import typer
from rich.panel import Panel

from agentic_trader import ui_text as text
from agentic_trader.cli_modules.common import (
    console,
    emit_json,
    emit_json_error,
)
from agentic_trader.cli_modules.proposal_actions import (
    RefreshProposalOrder,
    approve_proposal_payload,
    promote_candidate_payload,
    reconcile_proposal_payload,
    refresh_proposal_payload,
    reject_proposal_payload,
)
from agentic_trader.cli_modules.proposal_params import (
    IdeaScoreCommand,
    ProposalCreateCommand,
)
from agentic_trader.cli_modules.proposal_records import (
    candidate_draft_from_options,
    create_candidate_record,
    create_trade_proposal_record,
    emit_candidate_created,
    raise_candidate_create_error,
    trade_proposal_draft_from_options,
)
from agentic_trader.cli_modules.proposal_support import (
    parse_candidate_status,
    parse_proposal_status,
    proposal_candidates_payload,
    render_proposal_candidates,
    render_trade_proposals,
    trade_proposals_payload,
)
from agentic_trader.cli_modules.proposal_strategy_commands import (
    idea_presets,
    idea_score,
    strategy_catalog,
    strategy_profile,
)
from agentic_trader.config import Settings, get_settings
from agentic_trader.execution.intent import ExecutionOutcome
from agentic_trader.finance.proposals import refresh_trade_proposal_order
from agentic_trader.schemas import (
    ProposalCandidateRecord,
    TradeProposalRecord,
)

SettingsProvider = Callable[[], Settings]

_settings_provider: SettingsProvider = get_settings
_refresh_trade_proposal_order: RefreshProposalOrder = refresh_trade_proposal_order


def _settings() -> Settings:
    return _settings_provider()


def trade_proposals(
    status: str | None = typer.Option(
        None,
        "--status",
        help=text.HELP_TRADE_PROPOSALS_STATUS_FILTER,
    ),
    limit: int = typer.Option(50, min=1, max=200, help=text.HELP_TRADE_PROPOSALS_LIMIT),
    json_output: bool = typer.Option(False, "--json", help=text.HELP_JSON),
) -> None:
    """
    Display the manual-review trade proposal queue.

    Parameters:
        status (str | None): Optional filter for proposal state; allowed values are
            "pending", "approved", "rejected", "executed", "failed", or "expired".
        limit (int): Maximum number of trade proposals to show (1–200).
        json_output (bool): If True, emit the full payload as JSON instead of rendering.
    """
    settings = _settings()
    parsed_status = parse_proposal_status(status)
    payload = trade_proposals_payload(settings, status=parsed_status, limit=limit)
    if json_output:
        emit_json(payload)
        return
    proposals = [
        TradeProposalRecord.model_validate(item)
        for item in cast(list[dict[str, object]], payload["proposals"])
    ]
    if not payload["available"]:
        console.print(
            Panel(
                text.MESSAGE_TRADE_PROPOSALS_TEMPORARILY_UNAVAILABLE.format(
                    error=payload["error"]
                ),
                title=text.LABEL_OBSERVER_MODE,
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)
    render_trade_proposals(proposals)


def proposal_candidates(
    status: str | None = typer.Option(
        None,
        "--status",
        help=text.HELP_PROPOSAL_CANDIDATES_STATUS_FILTER,
    ),
    limit: int = typer.Option(
        50, min=1, max=200, help=text.HELP_PROPOSAL_CANDIDATES_LIMIT
    ),
    json_output: bool = typer.Option(False, "--json", help=text.HELP_JSON),
) -> None:
    """Show scanner/research candidates that may be promoted into proposals."""
    settings = _settings()
    parsed_status = parse_candidate_status(status)
    payload = proposal_candidates_payload(
        settings,
        status=parsed_status,
        limit=limit,
    )
    if json_output:
        emit_json(payload)
        return
    candidates = [
        ProposalCandidateRecord.model_validate(item)
        for item in cast(list[dict[str, object]], payload["candidates"])
    ]
    if not payload["available"]:
        console.print(
            Panel(
                text.MESSAGE_PROPOSAL_CANDIDATES_TEMPORARILY_UNAVAILABLE.format(
                    error=payload["error"]
                ),
                title=text.LABEL_OBSERVER_MODE,
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)
    render_proposal_candidates(candidates)


def proposal_candidate_create(  # NOSONAR - Typer maps each CLI option into the command signature.
    symbol: str = typer.Option(..., "--symbol", help=text.HELP_SYMBOL),  # NOSONAR
    preset: str = typer.Option("momentum", "--preset", help=text.HELP_IDEA_PRESET),
    price: float = typer.Option(
        ..., "--price", min=0.01, help=text.HELP_TRADE_REFERENCE_PRICE
    ),
    volume: float = typer.Option(..., "--volume", min=0.0, help=text.HELP_IDEA_VOLUME),
    change_pct: float = typer.Option(
        ..., "--change-pct", help=text.HELP_IDEA_CHANGE_PCT
    ),
    relative_volume: float = typer.Option(0.0, "--relative-volume", min=0.0),
    gap_pct: float = typer.Option(0.0, "--gap-pct", help=text.HELP_IDEA_GAP_PCT),
    range_pct: float = typer.Option(0.0, "--range-pct", min=0.0),
    rsi: float | None = typer.Option(None, "--rsi", min=0.0, max=100.0),
    ema_9: float | None = typer.Option(None, "--ema-9", min=0.0),
    sma_20: float | None = typer.Option(None, "--sma-20", min=0.0),
    sma_50: float | None = typer.Option(None, "--sma-50", min=0.0),
    vwap: float | None = typer.Option(None, "--vwap", min=0.0),
    spread_pct: float = typer.Option(0.0, "--spread-pct", min=0.0),
    quantity: float | None = typer.Option(None, "--quantity", min=0.0),
    notional: float | None = typer.Option(None, "--notional", min=0.0),
    stop_loss: float | None = typer.Option(None, "--stop-loss", min=0.01),
    take_profit: float | None = typer.Option(None, "--take-profit", min=0.01),
    invalidation_condition: str | None = typer.Option(
        None,
        "--invalidation-condition",
        help=text.HELP_TRADE_INVALIDATION,
    ),
    thesis: str = typer.Option("", "--thesis", help=text.HELP_TRADE_THESIS),
    materiality: str = typer.Option(
        "", "--materiality", help=text.HELP_CANDIDATE_MATERIALITY
    ),
    freshness: str = typer.Option(
        "operator_supplied_current",
        "--freshness",
        help=text.HELP_CANDIDATE_FRESHNESS,
    ),
    liquidity: str = typer.Option(
        "", "--liquidity", help=text.HELP_CANDIDATE_LIQUIDITY
    ),
    risk_notes: str = typer.Option(
        "", "--risk-notes", help=text.HELP_CANDIDATE_RISK_NOTES
    ),
    source: str = typer.Option(
        "idea-scanner", "--source", help=text.HELP_CANDIDATE_SOURCE
    ),
    enrich_provider_context: bool = typer.Option(
        True,
        "--enrich-provider-context/--no-enrich-provider-context",
        help=text.HELP_ENRICH_PROVIDER_CONTEXT,
    ),
    fetch_provider_news: bool = typer.Option(
        False,
        "--fetch-provider-news/--no-fetch-provider-news",
        help=text.HELP_FETCH_PROVIDER_NEWS,
    ),
    json_output: bool = typer.Option(False, "--json", help=text.HELP_JSON),
) -> None:
    """Persist a scanner/research candidate without approving or submitting it."""
    settings = _settings()
    draft = candidate_draft_from_options(locals())
    try:
        candidate = create_candidate_record(
            settings=settings,
            draft=draft,
            enrich_provider_context=enrich_provider_context,
            fetch_provider_news=fetch_provider_news,
        )
    except ValueError as exc:
        raise_candidate_create_error(exc, json_output=json_output)
    emit_candidate_created(candidate, json_output=json_output)


def proposal_candidate_promote(
    candidate_id: str = typer.Argument(..., help=text.HELP_PROPOSAL_CANDIDATE_ID),
    review_notes: str = typer.Option("", help=text.HELP_PROMOTION_NOTES),
    json_output: bool = typer.Option(False, "--json", help=text.HELP_JSON),
) -> None:
    """
    Promote a proposal candidate into a pending manual-review trade proposal.

    Promotes the candidate identified by `candidate_id` into a stored trade proposal awaiting manual review.
    On success emits a JSON payload when `json_output` is true, otherwise prints a success panel.
    If promotion validation fails the command exits with code 2 and either prints a rejection panel or emits a redacted JSON error when `json_output` is true.

    Parameters:
        candidate_id (str): Proposal candidate id to promote.
        review_notes (str): Optional promotion notes to record with the promotion.
        json_output (bool): When true, emit machine-readable JSON output instead of printing terminal UI.
    """
    settings = _settings()
    try:
        payload = promote_candidate_payload(
            settings=settings,
            candidate_id=candidate_id,
            review_notes=review_notes,
        )
    except ValueError as exc:
        if json_output:
            emit_json_error(exc)
            raise typer.Exit(code=2) from exc
        console.print(
            Panel(str(exc), title=text.TITLE_PROMOTION_BLOCKED, border_style="red")
        )
        raise typer.Exit(code=2) from exc
    if json_output:
        emit_json(payload)
        return
    candidate = ProposalCandidateRecord.model_validate(payload["candidate"])
    proposal = TradeProposalRecord.model_validate(payload["proposal"])
    console.print(
        Panel(
            text.MESSAGE_PROPOSAL_CANDIDATE_PROMOTED.format(
                candidate_id=candidate.candidate_id,
                proposal_id=proposal.proposal_id,
            ),
            title=text.TITLE_PROPOSAL_CANDIDATE_PROMOTED,
            border_style="green",
        )
    )


def proposal_create(**options: str) -> None:
    """
    Create a pending trade proposal for manual review without sending any order.

    Parameters:
        **options: str
            A mapping of CLI option names to their string values. Recognized keys:
            - symbol: trading symbol (e.g., "AAPL")
            - side: "buy" or "sell"
            - order_type: "market" or "limit"
            - quantity: numeric quantity or empty
            - notional: numeric notional or empty
            - limit_price: numeric limit price or empty
            - reference_price: numeric reference price
            - confidence: numeric confidence score
            - thesis: short rationale for the proposal
            - stop_loss: numeric stop-loss price or empty
            - take_profit: numeric take-profit price or empty
            - invalidation_condition: optional string condition to invalidate the proposal
            - source: provenance/source string
            - review_notes: reviewer notes or rationale
            - json_output: truthy value to emit JSON instead of formatted console output

    Raises:
        typer.Exit: exits with code 2 when proposal validation fails; when `json_output`
        is set, a redacted JSON error is emitted before exit.
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
    """
    Approve a pending trade proposal and submit it to the configured paper broker.

    Persists the provided approval audit notes, attempts to submit the proposal to the broker,
    and either prints a human-readable result panel or emits a JSON payload when json_output is True.
    On validation or runtime failures, emits a redacted JSON error if json_output is True or displays
    an "Approval Blocked" panel, then exits with code 2.

    Parameters:
        proposal_id (str): Identifier of the trade proposal to approve.
        review_notes (str): Approval audit notes persisted with the approval; used for audit/history.
        json_output (bool): When True, emit a machine-readable JSON payload instead of printing panels.
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
    """
    Reconcile an approved trade proposal against a recorded execution outcome without resubmitting an order to the broker.

    Attempts to match and record an execution outcome for the given proposal; on success prints a reconciliation summary (or emits a JSON payload when `json_output` is true). On validation failure emits a redacted JSON error (if `json_output`) or prints a blocked panel, then exits with code 2.

    Parameters:
        proposal_id (str): In-flight approved proposal id to reconcile.
        review_notes (str): Reconciliation audit notes describing why the reconciliation is being performed.
        json_output (bool): If true, emit machine-readable JSON output instead of human-oriented console panels.
    """
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
    """
    Refreshes an executed trade proposal's broker order metadata without submitting a new order.

    Parameters:
        proposal_id (str): Executed proposal identifier to refresh.
        review_notes (str): Audit notes required for the refresh operation.
        json_output (bool): If true, emit a JSON payload instead of printing human-readable output.

    Notes:
        On runtime or validation errors the command emits a redacted JSON error when `json_output` is true
        (or a red error panel otherwise) and exits the CLI with code 2.
    """
    settings = _settings()
    try:
        payload = refresh_proposal_payload(
            settings=settings,
            proposal_id=proposal_id,
            review_notes=review_notes,
            refresh_trade_proposal_order_provider=_refresh_trade_proposal_order,
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
    """
    Rejects a pending trade proposal and records the decision for audit.

    When successful, the updated proposal is emitted as JSON if `json_output` is True;
    otherwise a human-readable confirmation panel is printed.

    Parameters:
        proposal_id (str): Identifier of the trade proposal to reject.
        reason (str): Human-readable reason for rejecting the proposal.
        json_output (bool): If True, emit machine-readable JSON output instead of printing a panel.

    Raises:
        typer.Exit: Exits with code 2 when rejection is blocked (validation or business-rule failure).
    """
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


def register_proposal_desk_commands(
    app: typer.Typer,
    *,
    settings_provider: SettingsProvider | None = None,
    refresh_trade_proposal_order_provider: RefreshProposalOrder | None = None,
) -> None:
    global _settings_provider, _refresh_trade_proposal_order
    if settings_provider is not None:
        _settings_provider = settings_provider
    if refresh_trade_proposal_order_provider is not None:
        _refresh_trade_proposal_order = refresh_trade_proposal_order_provider
    app.command("trade-proposals")(trade_proposals)
    app.command("proposal-candidates")(proposal_candidates)
    app.command("proposal-candidate-create")(proposal_candidate_create)
    app.command("proposal-candidate-promote")(proposal_candidate_promote)
    app.command("proposal-create", cls=ProposalCreateCommand)(proposal_create)
    app.command("proposal-approve")(proposal_approve)
    app.command("proposal-reconcile")(proposal_reconcile)
    app.command("proposal-refresh")(proposal_refresh)
    app.command("proposal-reject")(proposal_reject)
    app.command("idea-presets")(idea_presets)
    app.command("idea-score", cls=IdeaScoreCommand)(idea_score)
    app.command("strategy-catalog")(strategy_catalog)
    app.command("strategy-profile")(strategy_profile)
