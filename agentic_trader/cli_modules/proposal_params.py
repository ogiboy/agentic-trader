from __future__ import annotations

from typing import Any, cast

import click
from typer.core import TyperCommand

from agentic_trader.ui_text import t as ui_t


def _json_option() -> click.Option:
    return click.Option(
        ["--json", "json_output"], is_flag=True, default=False, help=ui_t("help.json")
    )


def _proposal_quantity_params() -> list[click.Parameter]:
    return [
        click.Option(
            ["--quantity"],
            type=click.FloatRange(min=0.0),
            default=None,
            help=ui_t("help.trade_quantity"),
        ),
        click.Option(
            ["--notional"],
            type=click.FloatRange(min=0.0),
            default=None,
            help=ui_t("help.trade_notional"),
        ),
    ]


def _proposal_price_params() -> list[click.Parameter]:
    return [
        click.Option(
            ["--limit-price", "limit_price"],
            type=click.FloatRange(min=0.01),
            default=None,
            help=ui_t("help.trade_limit_price"),
        ),
        click.Option(
            ["--reference-price", "reference_price"],
            type=click.FloatRange(min=0.01),
            required=True,
            help=ui_t("help.trade_reference_price"),
        ),
    ]


def _proposal_risk_params() -> list[click.Parameter]:
    return [
        click.Option(
            ["--stop-loss", "stop_loss"],
            type=click.FloatRange(min=0.01),
            default=None,
            help=ui_t("help.trade_stop_loss"),
        ),
        click.Option(
            ["--take-profit", "take_profit"],
            type=click.FloatRange(min=0.01),
            default=None,
            help=ui_t("help.trade_take_profit"),
        ),
        click.Option(
            ["--invalidation-condition", "invalidation_condition"],
            default=None,
            help=ui_t("help.trade_invalidation"),
        ),
    ]


def _proposal_create_params() -> list[click.Parameter]:
    return [
        click.Option(["--symbol"], required=True, help=ui_t("help.symbol")),
        click.Option(
            ["--side"],
            default="buy",
            show_default=True,
            help=ui_t("help.trade_side"),
        ),
        *_proposal_quantity_params(),
        *_proposal_price_params(),
        click.Option(
            ["--confidence"],
            type=click.FloatRange(min=0.0, max=1.0),
            default=0.5,
            show_default=True,
            help=ui_t("help.trade_confidence"),
        ),
        click.Option(["--thesis"], required=True, help=ui_t("help.trade_thesis")),
        click.Option(
            ["--order-type", "order_type"],
            default="market",
            show_default=True,
            help=ui_t("help.trade_order_type"),
        ),
        *_proposal_risk_params(),
        click.Option(
            ["--source"],
            default="manual",
            show_default=True,
            help=ui_t("help.trade_source"),
        ),
        click.Option(
            ["--review-notes", "review_notes"],
            default="",
            help=ui_t("help.trade_review_notes"),
        ),
        _json_option(),
    ]


def _idea_market_params() -> list[click.Parameter]:
    return [
        click.Option(["--symbol"], required=True, help=ui_t("help.symbol")),
        click.Option(
            ["--preset"],
            default="momentum",
            show_default=True,
            help=ui_t("help.idea_preset"),
        ),
        click.Option(
            ["--price"],
            type=click.FloatRange(min=0.01),
            required=True,
            help=ui_t("help.idea_price"),
        ),
        click.Option(
            ["--volume"],
            type=click.FloatRange(min=0.0),
            required=True,
            help=ui_t("help.idea_volume"),
        ),
    ]


def _idea_momentum_params() -> list[click.Parameter]:
    return [
        click.Option(
            ["--change-pct", "change_pct"],
            type=float,
            required=True,
            help=ui_t("help.idea_change_pct"),
        ),
        click.Option(
            ["--relative-volume", "relative_volume"],
            type=click.FloatRange(min=0.0),
            default=0.0,
            show_default=True,
            help=ui_t("help.idea_relative_volume"),
        ),
        click.Option(
            ["--gap-pct", "gap_pct"],
            type=float,
            default=0.0,
            show_default=True,
            help=ui_t("help.idea_gap_pct"),
        ),
        click.Option(
            ["--range-pct", "range_pct"],
            type=click.FloatRange(min=0.0),
            default=0.0,
            show_default=True,
            help=ui_t("help.idea_range_pct"),
        ),
    ]


def _idea_indicator_params() -> list[click.Parameter]:
    return [
        click.Option(
            ["--rsi"],
            type=click.FloatRange(min=0.0, max=100.0),
            default=None,
            help=ui_t("help.idea_rsi"),
        ),
        click.Option(
            ["--ema-9", "ema_9"],
            type=click.FloatRange(min=0.0),
            default=None,
            help=ui_t("help.idea_ema_9"),
        ),
        click.Option(
            ["--sma-20", "sma_20"],
            type=click.FloatRange(min=0.0),
            default=None,
            help=ui_t("help.idea_sma_20"),
        ),
        click.Option(
            ["--sma-50", "sma_50"],
            type=click.FloatRange(min=0.0),
            default=None,
            help=ui_t("help.idea_sma_50"),
        ),
        click.Option(
            ["--vwap"],
            type=click.FloatRange(min=0.0),
            default=None,
            help=ui_t("help.idea_vwap"),
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
            help=ui_t("help.idea_spread_pct"),
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
