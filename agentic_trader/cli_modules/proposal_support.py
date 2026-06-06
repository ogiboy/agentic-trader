from __future__ import annotations

from typing import Literal, cast

import typer
from rich.panel import Panel
from rich.table import Table

from agentic_trader.ui_text import t as ui_t
from agentic_trader.cli_modules.common import console, emit_json, open_db
from agentic_trader.config import Settings
from agentic_trader.finance.ideas import (
    PRESET_DESCRIPTIONS,
    IdeaCandidate,
    IdeaPresetName,
    rank_candidates,
)
from agentic_trader.finance.strategy_catalog import (
    StrategyStatus,
    score_strategy_context,
)
from agentic_trader.schemas import (
    ProposalCandidateRecord,
    ProposalCandidateStatus,
    TradeProposalRecord,
    TradeProposalStatus,
    TradeSide,
)
from agentic_trader.security import redact_sensitive_text

ProposalOrderType = Literal["market", "limit"]


def trade_proposals_payload(
    settings: Settings, *, status: TradeProposalStatus | None = None, limit: int = 50
) -> dict[str, object]:
    """
    Builds an observer payload with trade proposals optionally filtered by status.

    If the database cannot be opened or read, `available` will be `False` and `error` will contain a redacted error message.

    Parameters:
        settings (Settings): Application settings used to open the trading database.
        status (TradeProposalStatus | None): Optional status to filter proposals by; `None` returns proposals of any status.
        limit (int): Maximum number of proposals to return.

    Returns:
        dict: Payload containing:
            - `available` (bool): True when DB read succeeded, False on error.
            - `error` (str | None): Redacted error message when `available` is False, otherwise None.
            - `status` (TradeProposalStatus | None): The filter value echoed back.
            - `proposals` (list[dict]): List of proposals serialized for JSON (one dict per proposal).
    """
    try:
        db = open_db(settings, read_only=True)
        try:
            proposals = db.list_trade_proposals(status=status, limit=limit)
        finally:
            db.close()
        available = True
        error = None
    except Exception as exc:
        proposals = []
        available = False
        error = redact_sensitive_text(exc, max_length=240)
    return {
        "available": available,
        "error": error,
        "status": status,
        "proposals": [proposal.model_dump(mode="json") for proposal in proposals],
    }


def proposal_candidates_payload(
    settings: Settings,
    *,
    status: ProposalCandidateStatus | None = None,
    limit: int = 50,
) -> dict[str, object]:
    """
    Builds an observer payload containing the proposal-candidate queue.

    Parameters:
        status (ProposalCandidateStatus | None): Optional filter for candidate status to include in the payload.
        limit (int): Maximum number of candidates to return.

    Returns:
        dict: Payload with the following keys:
            - "available" (bool): `True` if the database read succeeded, `False` on error.
            - "error" (str | None): Redacted error message when read failed, otherwise `None`.
            - "status" (ProposalCandidateStatus | None): The status filter that was applied.
            - "candidates" (list[dict]): List of candidate records serialized to JSON-serializable dicts.
    """
    try:
        db = open_db(settings, read_only=True)
        try:
            candidates = db.list_proposal_candidates(status=status, limit=limit)
        finally:
            db.close()
        available = True
        error = None
    except Exception as exc:
        candidates = []
        available = False
        error = redact_sensitive_text(exc, max_length=240)
    return {
        "available": available,
        "error": error,
        "status": status,
        "candidates": [candidate.model_dump(mode="json") for candidate in candidates],
    }


def parse_trade_side(value: str) -> TradeSide:
    normalized = value.strip().lower()
    if normalized not in {"buy", "sell"}:
        raise typer.BadParameter("side must be buy or sell")
    return cast(TradeSide, normalized)


def parse_order_type(value: str) -> ProposalOrderType:
    normalized = value.strip().lower()
    if normalized not in {"market", "limit"}:
        raise typer.BadParameter("proposal order type must be market or limit")
    return cast(ProposalOrderType, normalized)


def parse_proposal_status(value: str | None) -> TradeProposalStatus | None:
    """
    Normalize and validate a proposal status string.

    Parameters:
        value (str | None): Candidate status string (case/whitespace-insensitive).

    Returns:
        TradeProposalStatus | None: The normalized `TradeProposalStatus` corresponding to `value`, or `None` if `value` is `None`.

    Raises:
        typer.BadParameter: If `value` is not one of "pending", "approved", "rejected", "executed", "failed", or "expired".
    """
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in {
        "pending",
        "approved",
        "rejected",
        "executed",
        "failed",
        "expired",
    }:
        raise typer.BadParameter("status is not a known proposal state")
    return cast(TradeProposalStatus, normalized)


def parse_candidate_status(value: str | None) -> ProposalCandidateStatus | None:
    """
    Normalize and validate a proposal candidate status string.

    Parameters:
        value: The status string to parse; accepted case-insensitive values are
            "candidate", "promoted", "rejected", and "expired". If `None`, the
            function returns `None`.

    Returns:
        `ProposalCandidateStatus` if `value` matches a known state, `None` if `value` is `None`.

    Raises:
        typer.BadParameter: If `value` is not one of the accepted status strings.
    """
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in {"candidate", "promoted", "rejected", "expired"}:
        raise typer.BadParameter("status is not a known proposal candidate state")
    return cast(ProposalCandidateStatus, normalized)


def parse_idea_preset(value: str) -> IdeaPresetName:
    """
    Normalize and validate an idea scanner preset name.

    Parameters:
        value (str): Candidate preset name; whitespace is trimmed and case is folded to lowercase.

    Returns:
        IdeaPresetName: The normalized preset name that is guaranteed to exist in PRESET_DESCRIPTIONS.

    Raises:
        typer.BadParameter: If the normalized value is not a known preset.
    """
    normalized = value.strip().lower()
    if normalized not in PRESET_DESCRIPTIONS:
        raise typer.BadParameter("preset is not a known idea scanner preset")
    return normalized


def parse_strategy_status(value: str | None) -> StrategyStatus | None:
    if value is None:
        return None
    normalized = value.strip().lower().replace("-", "_")
    if normalized not in {"implemented", "research_candidate", "v2_deferred"}:
        raise typer.BadParameter(
            "status must be implemented, research-candidate, or v2-deferred"
        )
    return cast(StrategyStatus, normalized)


def render_trade_proposals(proposals: list[TradeProposalRecord]) -> None:
    """
    Render trade proposals as a Rich table to the console.
    
    If `proposals` is empty, print a yellow panel with the localized "no trade proposals" message and title instead of a table.
    
    Parameters:
        proposals (list[TradeProposalRecord]): Trade proposal records to display.
    """
    if not proposals:
        console.print(
            Panel(
                ui_t("message.no_trade_proposals"),
                title=ui_t("title.trade_proposals"),
                border_style="yellow",
            )
        )
        return
    table = Table(title=ui_t("title.trade_proposals"))
    table.add_column(ui_t("label.id"))
    table.add_column(ui_t("label.status"))
    table.add_column(ui_t("label.symbol"))
    table.add_column(ui_t("label.side"))
    table.add_column(ui_t("label.size"))
    table.add_column(ui_t("label.ref"))
    table.add_column(ui_t("label.confidence"))
    table.add_column(ui_t("label.source"))
    for proposal in proposals:
        size = (
            f"qty {proposal.quantity:.6f}"
            if proposal.quantity is not None
            else f"${proposal.notional or 0.0:.2f}"
        )
        table.add_row(
            proposal.proposal_id,
            proposal.status,
            proposal.symbol,
            proposal.side,
            size,
            f"{proposal.reference_price:.4f}",
            f"{proposal.confidence:.2f}",
            proposal.source,
        )
    console.print(table)


def render_proposal_candidates(candidates: list[ProposalCandidateRecord]) -> None:
    """
    Render a terminal table of proposal candidates or show a placeholder panel when none are present.

    Parameters:
        candidates (list[ProposalCandidateRecord]): Sequence of proposal candidate records to display; each record's fields (candidate_id, status, symbol, preset, signal, score, reference_price, proposal_id) are shown as table columns.
    """
    if not candidates:
        console.print(
            Panel(
                ui_t("message.no_proposal_candidates"),
                title=ui_t("title.proposal_candidates"),
                border_style="yellow",
            )
        )
        return
    table = Table(title=ui_t("title.proposal_candidates"))
    table.add_column(ui_t("label.id"))
    table.add_column(ui_t("label.status"))
    table.add_column(ui_t("label.symbol"))
    table.add_column(ui_t("label.preset"))
    table.add_column(ui_t("label.signal"))
    table.add_column(ui_t("label.score"))
    table.add_column(ui_t("label.ref"))
    table.add_column(ui_t("label.proposal"))
    for candidate in candidates:
        table.add_row(
            candidate.candidate_id,
            candidate.status,
            candidate.symbol,
            candidate.preset,
            candidate.signal,
            f"{candidate.score:.2f}",
            f"{candidate.reference_price:.4f}",
            candidate.proposal_id or "-",
        )
    console.print(table)


def render_idea_score(
    *,
    candidate: IdeaCandidate,
    preset: str,
    json_output: bool,
) -> None:
    """
    Compute and present an idea score for a single candidate using a named preset.
    
    If `json_output` is True, emits a JSON payload containing the candidate score, strategy context, and execution policy. Otherwise prints a formatted panel showing the symbol, signal, numeric score, reasons, and warnings.
    
    Parameters:
        candidate (IdeaCandidate): The idea candidate to score.
        preset (str): The preset name to use; validated and normalized before scoring.
        json_output (bool): If True emit JSON output, otherwise render a console panel.
    
    Raises:
        typer.BadParameter: If no score is available for the candidate with the given preset.
    """
    parsed_preset = parse_idea_preset(preset)
    ranked = rank_candidates([candidate], preset=parsed_preset, limit=1)
    if not ranked:
        raise typer.BadParameter(
            ui_t("message.idea_score_unavailable").format(
                symbol=candidate.symbol,
                preset=parsed_preset,
            )
        )
    result = ranked[0]
    payload = {
        "score": result.__dict__,
        "strategy": score_strategy_context(result),
        "execution_policy": ui_t("message.idea_score_execution_policy"),
    }
    if json_output:
        emit_json(payload)
        return
    console.print(
        Panel(
            f"{result.symbol} {result.signal.upper()} score={result.score:.2f}\n\n"
            f"{ui_t('label.reasons')}: {', '.join(result.reasons) or '-'}\n"
            f"{ui_t('label.warnings')}: {', '.join(result.warnings) or '-'}",
            title=ui_t("title.idea_score").format(preset=result.preset),
            border_style="cyan",
        )
    )
