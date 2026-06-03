"""Shared state for proposal-desk CLI command modules."""

from collections.abc import Callable

from agentic_trader.cli_modules.proposal_actions import RefreshProposalOrder
from agentic_trader.config import Settings, get_settings
from agentic_trader.finance.proposals import refresh_trade_proposal_order

SettingsProvider = Callable[[], Settings]

_settings_provider: SettingsProvider = get_settings
_refresh_trade_proposal_order: RefreshProposalOrder = refresh_trade_proposal_order


def settings() -> Settings:
    return _settings_provider()


def refresh_trade_proposal_order_provider() -> RefreshProposalOrder:
    return _refresh_trade_proposal_order


def set_proposal_desk_providers(
    *,
    settings_provider: SettingsProvider | None = None,
    refresh_trade_proposal_order_provider: RefreshProposalOrder | None = None,
) -> None:
    global _settings_provider, _refresh_trade_proposal_order
    if settings_provider is not None:
        _settings_provider = settings_provider
    if refresh_trade_proposal_order_provider is not None:
        _refresh_trade_proposal_order = refresh_trade_proposal_order_provider
