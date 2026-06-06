from __future__ import annotations

from collections.abc import Callable, Sized
from dataclasses import dataclass
from typing import Protocol, cast

import typer
from rich.panel import Panel
from rich.table import Table

from agentic_trader.ui_text import t as ui_t
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
    """
    Register the "news-intelligence" CLI command that builds and displays a news research plan for a symbol.
    
    When invoked the command:
    - Calls deps.news_research_plan(...) to produce a payload and converts any ValueError into a typer.BadParameter.
    - Optionally augments the payload with a `classified_source` entry when `--classify-source` is provided (includes `source` and `tier` from deps.classify_source_tier).
    - Emits the payload as JSON when `--json` is set via deps.emit_json.
    - Otherwise renders a panel showing `prompt_policy` and a table of `query_templates` (columns: kind, query, materiality_hint).
    
    Parameters:
        app (typer.Typer): Typer application to register the command on.
        deps (MarketCommandDeps): Dependency container providing payload builders, emit_json, and helper functions.
    """
    @app.command("news-intelligence")
    def news_intelligence(
        symbol: str = typer.Option(..., help=ui_t("help.symbol")),
        company_name: str | None = typer.Option(
            None, "--company-name", help=ui_t("help.news_company_name")
        ),
        sector: str | None = typer.Option(
            None, "--sector", help=ui_t("help.news_sector")
        ),
        classify_source: str | None = typer.Option(
            None,
            "--classify-source",
            help=ui_t("help.news_classify_source"),
        ),
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
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
                title=ui_t("title.news_intelligence").format(symbol=payload["symbol"]),
                border_style="cyan",
            )
        )
        table = Table(title=ui_t("title.news_query_plan"))
        table.add_column(ui_t("label.kind"))
        table.add_column(ui_t("label.query"))
        table.add_column(ui_t("label.materiality"))
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
    """
    Register the "research-cycle-plan" Typer command which builds and presents a research cycle plan.
    
    The command accepts CLI options for symbols, cadence_seconds, max_proposals_per_cycle and a --json flag. It parses the symbols, obtains a plan payload from deps.research_cycle_plan_payload using the provided options, converts a raised ValueError into a typer.BadParameter, and either emits the payload as JSON via deps.emit_json (when --json is set) or renders the plan with _render_research_cycle_plan.
    """
    @app.command("research-cycle-plan")
    def research_cycle_plan(
        symbols: str = typer.Option(
            "AAPL",
            "--symbols",
            help=ui_t("help.research_cycle_plan_symbols"),
        ),
        cadence_seconds: int = typer.Option(
            900,
            "--cadence-seconds",
            min=60,
            help=ui_t("help.research_cycle_plan_cadence_seconds"),
        ),
        max_proposals_per_cycle: int = typer.Option(
            1,
            "--max-proposals-per-cycle",
            min=0,
            max=10,
            help=ui_t("help.research_cycle_plan_max_proposals_per_cycle"),
        ),
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
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
    """
    Register the "research-cycle-run" CLI command on the provided Typer app.
    
    The command runs one or more research cycles for the given comma-separated symbols
    with configurable cadence, cycle count, proposal limits, persistence, and optional
    sleep between cycles. If JSON output is requested, the command emits the raw
    payload; otherwise it prints a summary showing the number of executed cycles.
    """
    @app.command("research-cycle-run")
    def research_cycle_run(
        symbols: str = typer.Option(
            ..., "--symbols", help=ui_t("help.research_cycle_run_symbols")
        ),
        cycles: int = typer.Option(
            1, min=1, max=24, help=ui_t("help.research_cycle_run_cycles")
        ),
        cadence_seconds: int = typer.Option(
            60,
            "--cadence-seconds",
            min=1,
            help=ui_t("help.research_cycle_run_cadence_seconds"),
        ),
        max_proposals_per_cycle: int = typer.Option(
            1,
            "--max-proposals-per-cycle",
            min=0,
            max=10,
            help=ui_t("help.research_cycle_run_max_proposals_per_cycle"),
        ),
        persist: bool = typer.Option(
            True,
            "--persist/--no-persist",
            help=ui_t("help.research_cycle_run_persist"),
        ),
        sleep_between_cycles: bool = typer.Option(
            True,
            "--sleep/--no-sleep",
            help=ui_t("help.research_cycle_run_sleep"),
        ),
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
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
                ui_t("message.research_cycle_run_summary").format(
                    executed_cycles=payload["executed_cycles"]
                ),
                title=ui_t("title.research_cycle_run"),
                border_style="green",
            )
        )


def _parse_symbols(symbols: str) -> list[str]:
    return [item.strip().upper() for item in symbols.split(",") if item.strip()]


def _render_research_cycle_plan(payload: dict[str, object]) -> None:
    """
    Render a formatted research cycle plan to the console.
    
    Parameters:
        payload (dict): Mapping with keys:
            - "safety_policy": text to show in the top panel.
            - "cycle": identifier used in the panel title.
            - "phases": list of phase mappings; each phase may include:
                - "name": phase name (shown as "-" if missing).
                - "purpose": phase purpose (shown as "-" if missing).
                - "produce": iterable of strings describing outputs (defaults to empty).
    
    The function prints a panel containing the safety policy and a table of phases with columns
    for phase name, purpose, and a comma-separated list of produced items.
    """
    console.print(
        Panel(
            str(payload["safety_policy"]),
            title=ui_t("title.research_cycle_plan").format(cycle=payload["cycle"]),
            border_style="cyan",
        )
    )
    table = Table(title=ui_t("title.research_cycle_phases"))
    table.add_column(ui_t("label.phase"))
    table.add_column(ui_t("label.purpose"))
    table.add_column(ui_t("label.produces"))
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
    """
    Register the "calendar-status" CLI command on the provided Typer application.
    
    The command accepts an optional symbol and a `--json` flag. It queries calendar/session information via the provided dependencies, emits the raw payload when `--json` is set, prints an "unavailable" panel and exits when no session is available, and otherwise validates and renders the market session status.
    
    Parameters:
        app (typer.Typer): Typer application to which the command will be registered.
        deps (MarketCommandDeps): Dependency container used to fetch settings, payloads, renderers, and emit JSON.
    """
    @app.command("calendar-status")
    def calendar_status(
        symbol: str | None = typer.Option(
            None,
            help=ui_t("help.calendar_status_symbol"),
        ),
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
    ) -> None:
        settings = deps.get_settings()
        payload = deps.calendar_payload(settings, symbol=symbol)
        if json_output:
            deps.emit_json(payload)
            return
        if not payload["available"] or payload["session"] is None:
            console.print(
                Panel(
                    ui_t("message.calendar_status_unavailable").format(
                        error=payload["error"]
                    ),
                    title=ui_t("title.calendar_status"),
                    border_style="yellow",
                )
            )
            raise typer.Exit(code=0)
        session = MarketSessionStatus.model_validate(payload["session"])
        _render_market_session(session)


def _render_market_session(session: MarketSessionStatus) -> None:
    """
    Render a market session status as a two-column table and print it to the console.
    
    Displays the session's venue, asset class, timezone, session state, whether it is tradable now, and any note. The table title includes the session's symbol.
    
    Parameters:
        session (MarketSessionStatus): Market session to render; expected to provide
            `symbol`, `venue`, `asset_class`, `timezone`, `session_state`,
            `tradable_now`, and `note`.
    """
    table = Table(title=ui_t("title.market_session").format(symbol=session.symbol))
    table.add_column(ui_t("label.field"))
    table.add_column(ui_t("label.value"))
    table.add_row(ui_t("label.venue"), session.venue)
    table.add_row(ui_t("label.asset_class"), session.asset_class)
    table.add_row(ui_t("label.timezone"), session.timezone)
    table.add_row(ui_t("label.state"), session.session_state)
    table.add_row(ui_t("label.tradable_now"), str(session.tradable_now))
    table.add_row(ui_t("label.note"), session.note)
    console.print(table)


def _register_news_brief_command(app: typer.Typer, deps: MarketCommandDeps) -> None:
    """
    Register the "news-brief" CLI command that displays a short news summary for a symbol.
    
    When invoked, the command fetches a news payload from the provided dependencies. If `--json` is used, the raw payload is emitted via the dependency's JSON emitter; otherwise the command prints a table showing mode, availability, and the number of headlines, then renders each headline.
    
    Parameters:
        app (typer.Typer): Typer application to register the command on.
        deps (MarketCommandDeps): Dependency container used to fetch payloads and emit JSON.
    """
    @app.command("news-brief")
    def news_brief(
        symbol: str | None = typer.Option(None, help=ui_t("help.news_brief_symbol")),
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
    ) -> None:
        settings = deps.get_settings()
        payload = deps.news_payload(settings, symbol=symbol)
        if json_output:
            deps.emit_json(payload)
            return
        news_title = ui_t("title.news_brief").format(
            symbol=value_or_dash(payload["symbol"])
        )
        table = Table(title=news_title)
        table.add_column(ui_t("label.field"))
        table.add_column(ui_t("label.value"))
        table.add_row(ui_t("label.mode"), str(payload["mode"]))
        table.add_row(ui_t("label.available"), str(payload["available"]))
        headlines = cast(list[dict[str, object]], payload["headlines"])
        table.add_row(ui_t("label.headlines"), str(len(headlines)))
        console.print(table)
        _render_headlines(headlines)


def _render_headlines(headlines: list[dict[str, object]]) -> None:
    """
    Render a list of news headlines to the console as styled panels.
    
    If `headlines` is empty, prints a yellow panel with a "no headlines" message titled with the news tool label. Otherwise prints one cyan-bordered panel per headline whose body is "<publisher> | <title>" and whose panel title is the headline's `symbol`.
    
    Parameters:
    	headlines (list[dict[str, object]]): Sequence of headline objects. Each headline is expected to contain the keys:
    	- `publisher`: publisher name shown in the panel body
    	- `title`: headline title shown in the panel body
    	- `symbol`: value used as the panel title
    """
    if not headlines:
        console.print(
            Panel(
                ui_t("message.no_tool_news_headlines"),
                title=ui_t("title.news_tool"),
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
    """
    Register CLI commands for managing and inspecting cached market OHLCV data.
    
    Defines two Typer subcommands:
    - "cache-market-data": fetches OHLCV for a given symbol with specified interval and lookback, stores it in the cache, and prints a summary panel with bar count, cache directory, interval, lookback, and snapshot count.
    - "market-cache": shows metadata about the market snapshot cache or emits the cache payload as JSON when `--json` is provided.
    
    Parameters:
        app (typer.Typer): Typer application to register the commands on.
        deps (MarketCommandDeps): Dependency container providing settings, fetchers, payload builders, and JSON emission.
    """
    @app.command("cache-market-data")
    def cache_market_data(
        symbol: str = typer.Option(..., help=ui_t("help.symbol")),
        interval: str = typer.Option("1d", help=ui_t("help.interval")),
        lookback: str = typer.Option("180d", help=ui_t("help.lookback")),
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
                ui_t("message.market_snapshot_cached").format(
                    bar_count=len(frame),
                    cache_dir=payload["cache_dir"],
                    cache_dir_label=ui_t("label.cache_dir"),
                    interval=interval,
                    lookback=lookback,
                    snapshot_count=payload["count"],
                    snapshot_count_label=ui_t("label.snapshot_count"),
                    symbol=symbol,
                ),
                title=ui_t("title.market_snapshot_cached"),
                border_style="green",
            )
        )

    @app.command("market-cache")
    def market_cache(
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
    ) -> None:
        """
        Show market snapshot cache contents; emit the cache payload as JSON when requested.
        
        Parameters:
            json_output (bool): If True, emit the cache payload as JSON instead of rendering human-friendly output.
        """
        settings = deps.get_settings()
        payload = deps.market_cache_payload(settings)
        if json_output:
            deps.emit_json(payload)
            return
        _render_market_cache(payload)


def _render_market_cache(payload: dict[str, object]) -> None:
    """
    Render a table of cached market snapshot files and a summary panel showing cache status.
    
    Parameters:
        payload (dict): A mapping containing cache information with these keys:
            - "entries": list of dicts each with "filename", "size_bytes", and "modified_at".
            - "cache_dir": path or name of the cache directory.
            - "mode": cache mode string.
            - "count": total number of snapshots.
    
    Description:
        Prints a table (up to the first 20 entries) with filename, size, and last-modified values.
        If no entries are present a single placeholder row is printed. After the table, prints a
        panel summarizing the cache directory, mode, and snapshot count.
    """
    table = Table(title=ui_t("title.market_snapshot_cache"))
    table.add_column(ui_t("label.filename"))
    table.add_column(ui_t("label.size"))
    table.add_column(ui_t("label.modified"))
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
            ui_t("message.cache_status").format(
                cache_dir=payload["cache_dir"],
                cache_dir_label=ui_t("label.cache_dir"),
                mode=payload["mode"],
                mode_label=ui_t("label.mode"),
                snapshot_count=payload["count"],
                snapshot_count_label=ui_t("label.snapshot_count"),
            ),
            title=ui_t("title.cache_status"),
            border_style="cyan",
        )
    )
