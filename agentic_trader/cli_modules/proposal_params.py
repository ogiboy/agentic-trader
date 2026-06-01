from __future__ import annotations

from typing import Any, cast

import click
from typer.core import TyperCommand

from agentic_trader import ui_text as text


def _proposal_create_params() -> list[click.Parameter]:
    """
    Declare Click parameters for the `proposal-create` CLI command.

    Each returned Option corresponds to a CLI flag used to build a trade proposal:
    symbol, side, quantity or notional, limit/reference prices, confidence,
    thesis, order type, stop-loss/take-profit, invalidation condition, source,
    review notes, and a JSON output flag.

    Returns:
        list[click.Parameter]: Click Option objects for registering the command's options.
    """
    return [
        click.Option(["--symbol"], required=True, help=text.HELP_SYMBOL),
        click.Option(
            ["--side"],
            default="buy",
            show_default=True,
            help=text.HELP_TRADE_SIDE,
        ),
        click.Option(
            ["--quantity"],
            type=click.FloatRange(min=0.0),
            default=None,
            help=text.HELP_TRADE_QUANTITY,
        ),
        click.Option(
            ["--notional"],
            type=click.FloatRange(min=0.0),
            default=None,
            help=text.HELP_TRADE_NOTIONAL,
        ),
        click.Option(
            ["--limit-price", "limit_price"],
            type=click.FloatRange(min=0.01),
            default=None,
            help=text.HELP_TRADE_LIMIT_PRICE,
        ),
        click.Option(
            ["--reference-price", "reference_price"],
            type=click.FloatRange(min=0.01),
            required=True,
            help=text.HELP_TRADE_REFERENCE_PRICE,
        ),
        click.Option(
            ["--confidence"],
            type=click.FloatRange(min=0.0, max=1.0),
            default=0.5,
            show_default=True,
            help=text.HELP_TRADE_CONFIDENCE,
        ),
        click.Option(["--thesis"], required=True, help=text.HELP_TRADE_THESIS),
        click.Option(
            ["--order-type", "order_type"],
            default="market",
            show_default=True,
            help=text.HELP_TRADE_ORDER_TYPE,
        ),
        click.Option(
            ["--stop-loss", "stop_loss"],
            type=click.FloatRange(min=0.01),
            default=None,
            help=text.HELP_TRADE_STOP_LOSS,
        ),
        click.Option(
            ["--take-profit", "take_profit"],
            type=click.FloatRange(min=0.01),
            default=None,
            help=text.HELP_TRADE_TAKE_PROFIT,
        ),
        click.Option(
            ["--invalidation-condition", "invalidation_condition"],
            default=None,
            help=text.HELP_TRADE_INVALIDATION,
        ),
        click.Option(
            ["--source"],
            default="manual",
            show_default=True,
            help=text.HELP_TRADE_SOURCE,
        ),
        click.Option(
            ["--review-notes", "review_notes"],
            default="",
            help=text.HELP_TRADE_REVIEW_NOTES,
        ),
        click.Option(
            ["--json", "json_output"], is_flag=True, default=False, help=text.HELP_JSON
        ),
    ]


def _idea_score_params() -> list[click.Parameter]:
    """
    Return the list of Click parameters (options) used by the `idea-score` CLI command.

    Each returned `click.Option` defines a named CLI flag for providing market/indicator inputs
    used when scoring an idea (symbol, preset, price, volume, change_pct, relative_volume,
    gap_pct, range_pct, optional indicators like RSI/EMA/SMA/VWAP, spread_pct, and `--json`).
    Returns:
        list[click.Parameter]: Configured Click `Option` objects for the `idea-score` command.
    """
    return [
        click.Option(["--symbol"], required=True, help=text.HELP_SYMBOL),
        click.Option(
            ["--preset"],
            default="momentum",
            show_default=True,
            help=text.HELP_IDEA_PRESET,
        ),
        click.Option(
            ["--price"],
            type=click.FloatRange(min=0.01),
            required=True,
            help=text.HELP_IDEA_PRICE,
        ),
        click.Option(
            ["--volume"],
            type=click.FloatRange(min=0.0),
            required=True,
            help=text.HELP_IDEA_VOLUME,
        ),
        click.Option(
            ["--change-pct", "change_pct"],
            type=float,
            required=True,
            help=text.HELP_IDEA_CHANGE_PCT,
        ),
        click.Option(
            ["--relative-volume", "relative_volume"],
            type=click.FloatRange(min=0.0),
            default=0.0,
            show_default=True,
            help=text.HELP_IDEA_RELATIVE_VOLUME,
        ),
        click.Option(
            ["--gap-pct", "gap_pct"],
            type=float,
            default=0.0,
            show_default=True,
            help=text.HELP_IDEA_GAP_PCT,
        ),
        click.Option(
            ["--range-pct", "range_pct"],
            type=click.FloatRange(min=0.0),
            default=0.0,
            show_default=True,
            help=text.HELP_IDEA_RANGE_PCT,
        ),
        click.Option(
            ["--rsi"],
            type=click.FloatRange(min=0.0, max=100.0),
            default=None,
            help=text.HELP_IDEA_RSI,
        ),
        click.Option(
            ["--ema-9", "ema_9"],
            type=click.FloatRange(min=0.0),
            default=None,
            help=text.HELP_IDEA_EMA_9,
        ),
        click.Option(
            ["--sma-20", "sma_20"],
            type=click.FloatRange(min=0.0),
            default=None,
            help=text.HELP_IDEA_SMA_20,
        ),
        click.Option(
            ["--sma-50", "sma_50"],
            type=click.FloatRange(min=0.0),
            default=None,
            help=text.HELP_IDEA_SMA_50,
        ),
        click.Option(
            ["--vwap"],
            type=click.FloatRange(min=0.0),
            default=None,
            help=text.HELP_IDEA_VWAP,
        ),
        click.Option(
            ["--spread-pct", "spread_pct"],
            type=click.FloatRange(min=0.0),
            default=0.0,
            show_default=True,
            help=text.HELP_IDEA_SPREAD_PCT,
        ),
        click.Option(
            ["--json", "json_output"], is_flag=True, default=False, help=text.HELP_JSON
        ),
    ]


class ProposalCreateCommand(TyperCommand):
    def __init__(
        self,
        *args: Any,
        params: list[click.Parameter] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, params=cast(Any, _proposal_create_params()), **kwargs)


class IdeaScoreCommand(TyperCommand):
    def __init__(
        self,
        *args: Any,
        params: list[click.Parameter] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, params=cast(Any, _idea_score_params()), **kwargs)
