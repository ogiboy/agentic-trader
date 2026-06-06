from __future__ import annotations

from typing import Any, cast

import click
from typer.core import TyperCommand

from agentic_trader import ui_text as text


def _json_option() -> click.Option:
    return click.Option(
        ["--json", "json_output"], is_flag=True, default=False, help=text.HELP_JSON
    )


def _proposal_quantity_params() -> list[click.Parameter]:
    return [
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
    ]


def _proposal_price_params() -> list[click.Parameter]:
    return [
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
    ]


def _proposal_risk_params() -> list[click.Parameter]:
    return [
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
    ]


def _proposal_create_params() -> list[click.Parameter]:
    return [
        click.Option(["--symbol"], required=True, help=text.HELP_SYMBOL),
        click.Option(
            ["--side"],
            default="buy",
            show_default=True,
            help=text.HELP_TRADE_SIDE,
        ),
        *_proposal_quantity_params(),
        *_proposal_price_params(),
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
        *_proposal_risk_params(),
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
        _json_option(),
    ]


def _idea_market_params() -> list[click.Parameter]:
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
    ]


def _idea_momentum_params() -> list[click.Parameter]:
    return [
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
    ]


def _idea_indicator_params() -> list[click.Parameter]:
    return [
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
    ]


def _idea_score_params() -> list[click.Parameter]:
    return [
        *_idea_market_params(),
        *_idea_momentum_params(),
        *_idea_indicator_params(),
        click.Option(
            ["--spread-pct", "spread_pct"],
            type=click.FloatRange(min=0.0),
            default=0.0,
            show_default=True,
            help=text.HELP_IDEA_SPREAD_PCT,
        ),
        _json_option(),
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
