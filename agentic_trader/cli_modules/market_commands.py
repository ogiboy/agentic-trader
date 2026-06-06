from __future__ import annotations

from collections.abc import Callable, Sized
from dataclasses import dataclass
from typing import Protocol, cast

import typer
from rich.panel import Panel
from rich.table import Table

from agentic_trader.ui_text import (
    HELP_CALENDAR_STATUS_SYMBOL,
    HELP_INTERVAL,
    HELP_JSON,
    HELP_LOOKBACK,
    HELP_NEWS_BRIEF_SYMBOL,
    HELP_NEWS_CLASSIFY_SOURCE,
    HELP_NEWS_COMPANY_NAME,
    HELP_NEWS_SECTOR,
    HELP_RESEARCH_CYCLE_PLAN_CADENCE_SECONDS,
    HELP_RESEARCH_CYCLE_PLAN_MAX_PROPOSALS_PER_CYCLE,
    HELP_RESEARCH_CYCLE_PLAN_SYMBOLS,
    HELP_RESEARCH_CYCLE_RUN_CADENCE_SECONDS,
    HELP_RESEARCH_CYCLE_RUN_CYCLES,
    HELP_RESEARCH_CYCLE_RUN_MAX_PROPOSALS_PER_CYCLE,
    HELP_RESEARCH_CYCLE_RUN_PERSIST,
    HELP_RESEARCH_CYCLE_RUN_SLEEP,
    HELP_RESEARCH_CYCLE_RUN_SYMBOLS,
    HELP_SYMBOL,
    LABEL_ASSET_CLASS,
    LABEL_AVAILABLE,
    LABEL_CACHE_DIR,
    LABEL_FIELD,
    LABEL_FILENAME,
    LABEL_HEADLINES,
    LABEL_KIND,
    LABEL_MATERIALITY,
    LABEL_MODE,
    LABEL_MODIFIED,
    LABEL_NOTE,
    LABEL_PHASE,
    LABEL_PRODUCES,
    LABEL_PURPOSE,
    LABEL_QUERY,
    LABEL_SIZE,
    LABEL_SNAPSHOT_COUNT,
    LABEL_STATE,
    LABEL_TIMEZONE,
    LABEL_TRADABLE_NOW,
    LABEL_VALUE,
    LABEL_VENUE,
    MESSAGE_CACHE_STATUS,
    MESSAGE_CALENDAR_STATUS_UNAVAILABLE,
    MESSAGE_MARKET_SNAPSHOT_CACHED,
    MESSAGE_NO_TOOL_NEWS_HEADLINES,
    MESSAGE_RESEARCH_CYCLE_RUN_SUMMARY,
    TITLE_CACHE_STATUS,
    TITLE_CALENDAR_STATUS,
    TITLE_MARKET_SESSION,
    TITLE_MARKET_SNAPSHOT_CACHE,
    TITLE_MARKET_SNAPSHOT_CACHED,
    TITLE_NEWS_BRIEF,
    TITLE_NEWS_INTELLIGENCE,
    TITLE_NEWS_QUERY_PLAN,
    TITLE_NEWS_TOOL,
    TITLE_RESEARCH_CYCLE_PHASES,
    TITLE_RESEARCH_CYCLE_PLAN,
    TITLE_RESEARCH_CYCLE_RUN,
)
from agentic_trader.cli_modules.common import console
from agentic_trader.cli_modules.run_reports import value_or_dash
from agentic_trader.config import Settings
from agentic_trader.schemas import MarketSessionStatus


class SymbolPayload(Protocol):
    def __call__(
        self, settings: Settings, *, symbol: str | None = None
    ) -> dict[str, object]: ...


class MarketCachePayload(Protocol):
    def __call__(self, settings: Settings) -> dict[str, object]: ...


class FetchOhlcv(Protocol):
    def __call__(
        self, symbol: str, *, interval: str, lookback: str, settings: Settings
    ) -> Sized: ...


class NewsResearchPlan(Protocol):
    def __call__(
        self, *, symbol: str, company_name: str | None = None, sector: str | None = None
    ) -> dict[str, object]: ...


class ResearchCyclePlanPayload(Protocol):
    def __call__(
        self,
        *,
        symbols: list[str],
        cadence_seconds: int,
        max_proposals_per_cycle: int,
    ) -> dict[str, object]: ...


class ResearchCycleRunner(Protocol):
    def __call__(
        self,
        settings: Settings,
        *,
        symbols: list[str],
        cycles: int,
        cadence_seconds: int,
        max_proposals_per_cycle: int,
        persist: bool,
        sleep_between_cycles: bool,
    ) -> dict[str, object]: ...


@dataclass(frozen=True)
class MarketCommandDeps:
    get_settings: Callable[[], Settings]
    emit_json: Callable[[object], None]
    calendar_payload: SymbolPayload
    news_payload: SymbolPayload
    market_cache_payload: MarketCachePayload
    fetch_ohlcv: FetchOhlcv
    news_research_plan: NewsResearchPlan
    classify_source_tier: Callable[[str], str]
    research_cycle_plan_payload: ResearchCyclePlanPayload
    run_research_cycle: ResearchCycleRunner


def register_market_commands(app: typer.Typer, deps: MarketCommandDeps) -> None:
    _register_news_intelligence_command(app, deps)
    _register_research_cycle_commands(app, deps)
    _register_calendar_status_command(app, deps)
    _register_news_brief_command(app, deps)
    _register_market_cache_commands(app, deps)


def _register_news_intelligence_command(
    app: typer.Typer, deps: MarketCommandDeps
) -> None:
    @app.command("news-intelligence")
    def news_intelligence(
        symbol: str = typer.Option(..., help=HELP_SYMBOL),
        company_name: str | None = typer.Option(
            None, "--company-name", help=HELP_NEWS_COMPANY_NAME
        ),
        sector: str | None = typer.Option(None, "--sector", help=HELP_NEWS_SECTOR),
        classify_source: str | None = typer.Option(
            None,
            "--classify-source",
            help=HELP_NEWS_CLASSIFY_SOURCE,
        ),
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    ) -> None:
        try:
            payload = deps.news_research_plan(
                symbol=symbol, company_name=company_name, sector=sector
            )
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        if classify_source:
            payload["classified_source"] = {
                "source": classify_source,
                "tier": deps.classify_source_tier(classify_source),
            }
        if json_output:
            deps.emit_json(payload)
            return
        console.print(
            Panel(
                str(payload["prompt_policy"]),
                title=TITLE_NEWS_INTELLIGENCE.format(symbol=payload["symbol"]),
                border_style="cyan",
            )
        )
        table = Table(title=TITLE_NEWS_QUERY_PLAN)
        table.add_column(LABEL_KIND)
        table.add_column(LABEL_QUERY)
        table.add_column(LABEL_MATERIALITY)
        for query in cast(list[dict[str, str]], payload["query_templates"]):
            table.add_row(query["kind"], query["query"], query["materiality_hint"])
        console.print(table)


def _register_research_cycle_commands(
    app: typer.Typer, deps: MarketCommandDeps
) -> None:
    _register_research_cycle_plan_command(app, deps)
    _register_research_cycle_run_command(app, deps)


def _register_research_cycle_plan_command(
    app: typer.Typer, deps: MarketCommandDeps
) -> None:
    @app.command("research-cycle-plan")
    def research_cycle_plan(
        symbols: str = typer.Option(
            "AAPL",
            "--symbols",
            help=HELP_RESEARCH_CYCLE_PLAN_SYMBOLS,
        ),
        cadence_seconds: int = typer.Option(
            900,
            "--cadence-seconds",
            min=60,
            help=HELP_RESEARCH_CYCLE_PLAN_CADENCE_SECONDS,
        ),
        max_proposals_per_cycle: int = typer.Option(
            1,
            "--max-proposals-per-cycle",
            min=0,
            max=10,
            help=HELP_RESEARCH_CYCLE_PLAN_MAX_PROPOSALS_PER_CYCLE,
        ),
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    ) -> None:
        symbol_list = _parse_symbols(symbols)
        try:
            payload = deps.research_cycle_plan_payload(
                symbols=symbol_list,
                cadence_seconds=cadence_seconds,
                max_proposals_per_cycle=max_proposals_per_cycle,
            )
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        if json_output:
            deps.emit_json(payload)
            return
        _render_research_cycle_plan(payload)


def _register_research_cycle_run_command(
    app: typer.Typer, deps: MarketCommandDeps
) -> None:
    @app.command("research-cycle-run")
    def research_cycle_run(
        symbols: str = typer.Option(
            ..., "--symbols", help=HELP_RESEARCH_CYCLE_RUN_SYMBOLS
        ),
        cycles: int = typer.Option(
            1, min=1, max=24, help=HELP_RESEARCH_CYCLE_RUN_CYCLES
        ),
        cadence_seconds: int = typer.Option(
            60,
            "--cadence-seconds",
            min=1,
            help=HELP_RESEARCH_CYCLE_RUN_CADENCE_SECONDS,
        ),
        max_proposals_per_cycle: int = typer.Option(
            1,
            "--max-proposals-per-cycle",
            min=0,
            max=10,
            help=HELP_RESEARCH_CYCLE_RUN_MAX_PROPOSALS_PER_CYCLE,
        ),
        persist: bool = typer.Option(
            True,
            "--persist/--no-persist",
            help=HELP_RESEARCH_CYCLE_RUN_PERSIST,
        ),
        sleep_between_cycles: bool = typer.Option(
            True,
            "--sleep/--no-sleep",
            help=HELP_RESEARCH_CYCLE_RUN_SLEEP,
        ),
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    ) -> None:
        settings = deps.get_settings()
        symbol_list = _parse_symbols(symbols)
        try:
            payload = deps.run_research_cycle(
                settings,
                symbols=symbol_list,
                cycles=cycles,
                cadence_seconds=cadence_seconds,
                max_proposals_per_cycle=max_proposals_per_cycle,
                persist=persist,
                sleep_between_cycles=sleep_between_cycles,
            )
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        if json_output:
            deps.emit_json(payload)
            return
        console.print(
            Panel(
                MESSAGE_RESEARCH_CYCLE_RUN_SUMMARY.format(
                    executed_cycles=payload["executed_cycles"]
                ),
                title=TITLE_RESEARCH_CYCLE_RUN,
                border_style="green",
            )
        )


def _parse_symbols(symbols: str) -> list[str]:
    return [item.strip().upper() for item in symbols.split(",") if item.strip()]


def _render_research_cycle_plan(payload: dict[str, object]) -> None:
    console.print(
        Panel(
            str(payload["safety_policy"]),
            title=TITLE_RESEARCH_CYCLE_PLAN.format(cycle=payload["cycle"]),
            border_style="cyan",
        )
    )
    table = Table(title=TITLE_RESEARCH_CYCLE_PHASES)
    table.add_column(LABEL_PHASE)
    table.add_column(LABEL_PURPOSE)
    table.add_column(LABEL_PRODUCES)
    for phase in cast(list[dict[str, object]], payload["phases"]):
        produce = cast(list[str] | tuple[str, ...], phase.get("produce", []))
        table.add_row(
            str(phase.get("name", "-")),
            str(phase.get("purpose", "-")),
            ", ".join(str(item) for item in produce),
        )
    console.print(table)


def _register_calendar_status_command(
    app: typer.Typer, deps: MarketCommandDeps
) -> None:
    @app.command("calendar-status")
    def calendar_status(
        symbol: str | None = typer.Option(
            None,
            help=HELP_CALENDAR_STATUS_SYMBOL,
        ),
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    ) -> None:
        settings = deps.get_settings()
        payload = deps.calendar_payload(settings, symbol=symbol)
        if json_output:
            deps.emit_json(payload)
            return
        if not payload["available"] or payload["session"] is None:
            console.print(
                Panel(
                    MESSAGE_CALENDAR_STATUS_UNAVAILABLE.format(
                        error=payload["error"]
                    ),
                    title=TITLE_CALENDAR_STATUS,
                    border_style="yellow",
                )
            )
            raise typer.Exit(code=0)
        session = MarketSessionStatus.model_validate(payload["session"])
        _render_market_session(session)


def _render_market_session(session: MarketSessionStatus) -> None:
    table = Table(title=TITLE_MARKET_SESSION.format(symbol=session.symbol))
    table.add_column(LABEL_FIELD)
    table.add_column(LABEL_VALUE)
    table.add_row(LABEL_VENUE, session.venue)
    table.add_row(LABEL_ASSET_CLASS, session.asset_class)
    table.add_row(LABEL_TIMEZONE, session.timezone)
    table.add_row(LABEL_STATE, session.session_state)
    table.add_row(LABEL_TRADABLE_NOW, str(session.tradable_now))
    table.add_row(LABEL_NOTE, session.note)
    console.print(table)


def _register_news_brief_command(app: typer.Typer, deps: MarketCommandDeps) -> None:
    @app.command("news-brief")
    def news_brief(
        symbol: str | None = typer.Option(None, help=HELP_NEWS_BRIEF_SYMBOL),
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    ) -> None:
        settings = deps.get_settings()
        payload = deps.news_payload(settings, symbol=symbol)
        if json_output:
            deps.emit_json(payload)
            return
        news_title = TITLE_NEWS_BRIEF.format(
            symbol=value_or_dash(payload["symbol"])
        )
        table = Table(title=news_title)
        table.add_column(LABEL_FIELD)
        table.add_column(LABEL_VALUE)
        table.add_row(LABEL_MODE, str(payload["mode"]))
        table.add_row(LABEL_AVAILABLE, str(payload["available"]))
        headlines = cast(list[dict[str, object]], payload["headlines"])
        table.add_row(LABEL_HEADLINES, str(len(headlines)))
        console.print(table)
        _render_headlines(headlines)


def _render_headlines(headlines: list[dict[str, object]]) -> None:
    if not headlines:
        console.print(
            Panel(
                MESSAGE_NO_TOOL_NEWS_HEADLINES,
                title=TITLE_NEWS_TOOL,
                border_style="yellow",
            )
        )
        return
    for headline in headlines:
        console.print(
            Panel(
                f"{headline['publisher']} | {headline['title']}",
                title=str(headline["symbol"]),
                border_style="cyan",
            )
        )


def _register_market_cache_commands(app: typer.Typer, deps: MarketCommandDeps) -> None:
    @app.command("cache-market-data")
    def cache_market_data(
        symbol: str = typer.Option(..., help=HELP_SYMBOL),
        interval: str = typer.Option("1d", help=HELP_INTERVAL),
        lookback: str = typer.Option("180d", help=HELP_LOOKBACK),
    ) -> None:
        settings = deps.get_settings()
        refresh_settings = settings.model_copy(
            update={"market_data_mode": "refresh_cache"}
        )
        frame = deps.fetch_ohlcv(
            symbol, interval=interval, lookback=lookback, settings=refresh_settings
        )
        payload = deps.market_cache_payload(refresh_settings)
        console.print(
            Panel(
                MESSAGE_MARKET_SNAPSHOT_CACHED.format(
                    bar_count=len(frame),
                    cache_dir=payload["cache_dir"],
                    cache_dir_label=LABEL_CACHE_DIR,
                    interval=interval,
                    lookback=lookback,
                    snapshot_count=payload["count"],
                    snapshot_count_label=LABEL_SNAPSHOT_COUNT,
                    symbol=symbol,
                ),
                title=TITLE_MARKET_SNAPSHOT_CACHED,
                border_style="green",
            )
        )

    @app.command("market-cache")
    def market_cache(
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    ) -> None:
        settings = deps.get_settings()
        payload = deps.market_cache_payload(settings)
        if json_output:
            deps.emit_json(payload)
            return
        _render_market_cache(payload)


def _render_market_cache(payload: dict[str, object]) -> None:
    table = Table(title=TITLE_MARKET_SNAPSHOT_CACHE)
    table.add_column(LABEL_FILENAME)
    table.add_column(LABEL_SIZE)
    table.add_column(LABEL_MODIFIED)
    entries = cast(list[dict[str, object]], payload["entries"])
    if not entries:
        table.add_row("-", "-", "-")
    else:
        for entry in entries[:20]:
            table.add_row(
                str(entry["filename"]),
                str(entry["size_bytes"]),
                str(entry["modified_at"]),
            )
    console.print(table)
    console.print(
        Panel(
            MESSAGE_CACHE_STATUS.format(
                cache_dir=payload["cache_dir"],
                cache_dir_label=LABEL_CACHE_DIR,
                mode=payload["mode"],
                mode_label=LABEL_MODE,
                snapshot_count=payload["count"],
                snapshot_count_label=LABEL_SNAPSHOT_COUNT,
            ),
            title=TITLE_CACHE_STATUS,
            border_style="cyan",
        )
    )
