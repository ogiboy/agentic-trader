from __future__ import annotations

from typing import Any, cast

import click
from typer.core import TyperCommand

from agentic_trader.ui_text import t as ui_t


def _json_option() -> click.Option:
    """
    Create a Click option for enabling JSON-formatted output.
    
    Returns:
        click.Option: A boolean flag option for `--json` / `json_output` with default `False` and help text from the UI text registry.
    """
    return click.Option(
        ["--json", "json_output"], is_flag=True, default=False, help=ui_t("help.json")
    )


def _proposal_quantity_params() -> list[click.Parameter]:
    """
    Create CLI options for specifying a proposal's quantity or notional.
    
    Returns:
        params (list[click.Parameter]): Two click.Option objects:
            - `--quantity`: float >= 0.0, default None, help text for trade quantity.
            - `--notional`: float >= 0.0, default None, help text for trade notional.
    """
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
    """
    Builds the CLI options for a proposal's price inputs.
    
    The returned list contains two click.Option objects:
    - `--limit-price` / `limit_price`: optional float >= 0.01, defaults to None.
    - `--reference-price` / `reference_price`: required float >= 0.01.
    
    Returns:
        list[click.Parameter]: The option objects for limit and reference prices.
    """
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
    """
    Provide the CLI options used to specify risk-related fields for a proposal.
    
    Returns:
        list[click.Option]: Three CLI options:
            - `--stop-loss` / `stop_loss`: optional float >= 0.01, default `None`, sets the stop-loss price.
            - `--take-profit` / `take_profit`: optional float >= 0.01, default `None`, sets the take-profit price.
            - `--invalidation-condition` / `invalidation_condition`: optional string, default `None`, sets a custom invalidation condition.
    """
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
    """
    Builds and returns the CLI parameter list for the "proposal create" command.
    
    The returned list includes, in order: required --symbol; --side (default "buy"); quantity and price option groups; --confidence (0.5 default, 0.0–1.0 range); required --thesis; --order-type (default "market"); risk-related options (stop-loss, take-profit, invalidation condition); --source (default "manual"); --review-notes (default empty string); and the --json flag.
    
    Returns:
        params (list[click.Parameter]): Configured Click parameters for the proposal-create command.
    """
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
    """
    Builds the CLI option list for the "idea market" command.
    
    Returns:
        params (list[click.Parameter]): A list of Click parameters defining:
            - `--symbol`: required symbol string.
            - `--preset`: preset name (default "momentum").
            - `--price`: required float, minimum 0.01.
            - `--volume`: required float, minimum 0.0.
    """
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
    """
    Builds the CLI option objects for idea momentum parameters.
    
    Each option corresponds to a momentum-related flag used by idea scoring:
    - `--change-pct` / `change_pct`: required float change percentage.
    - `--relative-volume` / `relative_volume`: float >= 0.0, defaults to 0.0.
    - `--gap-pct` / `gap_pct`: float gap percentage, defaults to 0.0.
    - `--range-pct` / `range_pct`: float >= 0.0, defaults to 0.0.
    
    Returns:
        list[click.Parameter]: The configured Click options for momentum inputs.
    """
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
    """
    Builds CLI options for indicator-based idea filters.
    
    Returns:
        list[click.Parameter]: A list of `click.Option` objects for the indicator flags:
            - `--rsi`: Relative Strength Index value (0 to 100).
            - `--ema-9`: 9-period exponential moving average value (>= 0).
            - `--sma-20`: 20-period simple moving average value (>= 0).
            - `--sma-50`: 50-period simple moving average value (>= 0).
            - `--vwap`: Volume-weighted average price value (>= 0).
        Each option defaults to `None`.
    """
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
    """
    Builds the CLI parameter list for the "idea score" command.
    
    Returns:
        params (list[click.Parameter]): List of Click parameters including market-related options, momentum options, indicator options, a `--spread-pct` option (default 0.0), and a `--json` flag.
    """
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
