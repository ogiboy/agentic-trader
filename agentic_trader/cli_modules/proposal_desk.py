"""Proposal desk CLI command registration facade."""

import typer

from agentic_trader.cli_modules.proposal_actions import RefreshProposalOrder
from agentic_trader.cli_modules.proposal_candidate_commands import (
    proposal_candidate_create,
    proposal_candidate_promote,
)
from agentic_trader.cli_modules.proposal_desk_state import (
    SettingsProvider,
    set_proposal_desk_providers,
)
from agentic_trader.cli_modules.proposal_listing_commands import (
    proposal_candidates,
    trade_proposals,
)
from agentic_trader.cli_modules.proposal_params import (
    IdeaScoreCommand,
    ProposalCreateCommand,
)
from agentic_trader.cli_modules.proposal_review_commands import (
    proposal_approve,
    proposal_create,
    proposal_reconcile,
    proposal_refresh,
    proposal_reject,
)
from agentic_trader.cli_modules.proposal_strategy_commands import (
    idea_presets,
    idea_score,
    strategy_catalog,
    strategy_profile,
)
from agentic_trader.cli_modules.proposal_support import (
    proposal_candidates_payload,
    trade_proposals_payload,
)

__all__ = [
    "proposal_candidates_payload",
    "register_proposal_desk_commands",
    "trade_proposals_payload",
]


def register_proposal_desk_commands(
    app: typer.Typer,
    *,
    settings_provider: SettingsProvider | None = None,
    refresh_trade_proposal_order_provider: RefreshProposalOrder | None = None,
) -> None:
    set_proposal_desk_providers(
        settings_provider=settings_provider,
        refresh_trade_proposal_order_provider=refresh_trade_proposal_order_provider,
    )
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
