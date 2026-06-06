from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pandas import DataFrame

from agentic_trader.cli_modules.backtest_reports import (
    RunAblation,
    RunComparison,
    RunWalkForward,
)
from agentic_trader.cli_modules.memory_commands import (
    MemoryExplorerPayload,
    RetrievalInspectionPayload,
)
from agentic_trader.cli_modules.observer_payloads import (
    memory_explorer_payload as _memory_explorer_payload_impl,
)
from agentic_trader.cli_modules.observer_payloads import (
    retrieval_inspection_payload as _retrieval_inspection_payload_impl,
)
from agentic_trader.cli_modules.observer_payloads import (
    run_replay_payload as _run_replay_payload_impl,
)
from agentic_trader.cli_modules.proposal_actions import RefreshProposalOrder
from agentic_trader.cli_modules.record_payloads import (
    run_record_payload as _run_record_payload_impl,
)
from agentic_trader.cli_modules.run_reports import (
    manager_override_notes as _manager_override_notes,
)
from agentic_trader.cli_modules.run_reports import (
    manager_resolution_notes as _manager_resolution_notes,
)
from agentic_trader.cli_modules.service_commands import RunService
from agentic_trader.config import Settings
from agentic_trader.engine.broker_contracts import ExecutionOutcome
from agentic_trader.schemas import (
    BacktestAblationReport,
    BacktestComparisonReport,
    BacktestReport,
    InvestmentPreferences,
    OperatorInstruction,
    PreferenceUpdate,
    TradeProposalRecord,
)
from agentic_trader.storage.db import TradingDatabase


def _memory_explorer_payload(
    namespace: Any,
    settings: Settings,
    *,
    symbol: str | None = None,
    interval: str | None = None,
    lookback: str = "180d",
    limit: int = 5,
    use_latest_run: bool = False,
) -> dict[str, object]:
    """
    Generate a memory exploration payload.
    
    Parameters:
        symbol (str | None): Stock symbol to filter results (optional).
        interval (str | None): Time interval for data queries (optional).
        lookback (str): Historical lookback period, default "180d".
        limit (int): Maximum results to include, default 5.
        use_latest_run (bool): Whether to use the latest run, default False.
    
    Returns:
        dict[str, object]: Memory exploration payload dictionary.
    """
    return _memory_explorer_payload_impl(
        settings,
        open_db=namespace._open_db,
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        limit=limit,
        use_latest_run=use_latest_run,
    )


def _retrieval_inspection_payload(
    namespace: Any, settings: Settings, *, run_id: str | None = None
) -> dict[str, object]:
    """
    Builds a payload dictionary for a retrieval inspection CLI command using the namespace's database opener.
    
    Parameters:
        settings (Settings): Application settings used to configure the payload.
        run_id (str | None): Optional identifier of a specific run to inspect; when omitted the payload targets a broader inspection scope.
    
    Returns:
        dict[str, object]: A payload dictionary suitable for the retrieval inspection handler.
    """
    def run_record(settings: Settings, run_id: str | None = None) -> dict[str, object]:
        return _run_record_payload_impl(
            settings, open_db=namespace._open_db, run_id=run_id
        )

    return _retrieval_inspection_payload_impl(
        settings,
        run_id=run_id,
        run_record_payload=run_record,
    )


def run_replay_payload(
    namespace: Any, settings: Settings, *, run_id: str | None = None
) -> dict[str, object]:
    """
    Builds a payload dictionary for running a replay command using the namespace's database access.
    
    Parameters:
        run_id (str | None): Optional identifier of the run to replay; when omitted the payload may target the latest or a user-selected run.
    
    Returns:
        dict[str, object]: Payload dictionary containing parameters and helper callables (including a `run_record` callable) required by the replay CLI implementation.
    """
    def run_record(settings: Settings, run_id: str | None = None) -> dict[str, object]:
        return _run_record_payload_impl(
            settings, open_db=namespace._open_db, run_id=run_id
        )

    return _run_replay_payload_impl(
        settings,
        run_id=run_id,
        run_record_payload=run_record,
        manager_override_notes=_manager_override_notes,
        manager_resolution_notes=_manager_resolution_notes,
    )


def _run_backtest_comparison_provider(
    namespace: Any,
    *,
    settings: Settings,
    symbol: str,
    interval: str,
    lookback: str,
    warmup_bars: int = 120,
    allow_fallback: bool = False,
    frame: DataFrame | None = None,
) -> BacktestComparisonReport:
    """
    Run a backtest comparison using the provided namespace, settings, and market parameters.
    
    Parameters:
        settings (Settings): Configuration and runtime settings for the backtest.
        symbol (str): Market symbol to backtest (e.g., "BTC/USD").
        interval (str): Candle/price interval to use (e.g., "1h").
        lookback (str): Historical range to use for the backtest (e.g., "180d").
        warmup_bars (int): Number of initial bars used to warm up indicators before reporting (default 120).
        allow_fallback (bool): Whether to permit fallback behaviors when the preferred strategy/setup is unavailable.
        frame (DataFrame | None): Optional explicit price/indicator DataFrame to run the backtest against.
    
    Returns:
        BacktestComparisonReport: A report containing comparison metrics and artifacts from the backtest run.
    """
    return namespace.run_backtest_comparison(
        settings=settings,
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        warmup_bars=warmup_bars,
        allow_fallback=allow_fallback,
        frame=frame,
    )


def _run_memory_ablation_backtest_provider(
    namespace: Any,
    *,
    settings: Settings,
    symbol: str,
    interval: str,
    lookback: str,
    warmup_bars: int = 120,
    allow_fallback: bool = False,
    frame: DataFrame | None = None,
) -> BacktestAblationReport:
    """
    Run a memory-ablation backtest using the provided namespace.
    
    Parameters:
        namespace (Any): Object exposing a `run_memory_ablation_backtest` method.
        settings (Settings): Runtime configuration and strategy settings to use for the backtest.
        symbol (str): Trading symbol to backtest (e.g., "BTC/USD").
        interval (str): Bar/candle interval (e.g., "1h").
        lookback (str): Historical lookback window (e.g., "180d").
        warmup_bars (int): Number of initial bars used to warm up indicators before evaluation.
        allow_fallback (bool): Whether to permit fallback behavior if the primary backtest path fails.
        frame (DataFrame | None): Optional preloaded market data frame to run the backtest against.
    
    Returns:
        BacktestAblationReport: Report summarizing the results of the memory-ablation backtest.
    """
    return namespace.run_memory_ablation_backtest(
        settings=settings,
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        warmup_bars=warmup_bars,
        allow_fallback=allow_fallback,
        frame=frame,
    )


def _run_walk_forward_backtest_provider(
    namespace: Any,
    *,
    settings: Settings,
    symbol: str,
    interval: str,
    lookback: str,
    warmup_bars: int = 120,
    allow_fallback: bool = False,
    memory_enabled: bool = True,
    frame: DataFrame | None = None,
) -> BacktestReport:
    """
    Run a walk-forward backtest using the provided namespace and parameters.
    
    Parameters:
        warmup_bars (int): Number of initial bars used to warm up indicators before scoring.
        allow_fallback (bool): If true, permit fallback behavior when the primary strategy or data is unavailable.
        memory_enabled (bool): If true, enable memory-related features during the backtest.
        frame (DataFrame | None): Optional preloaded market data to run the backtest against; if None the namespace will load data.
    
    Returns:
        BacktestReport: Report summarizing walk-forward backtest results.
    """
    return namespace.run_walk_forward_backtest(
        settings=settings,
        symbol=symbol,
        interval=interval,
        lookback=lookback,
        warmup_bars=warmup_bars,
        allow_fallback=allow_fallback,
        memory_enabled=memory_enabled,
        frame=frame,
    )


def _run_service_provider(
    namespace: Any,
    *,
    settings: Settings,
    symbols: list[str],
    interval: str,
    lookback: str,
    poll_seconds: int,
    continuous: bool,
    max_cycles: int | None,
) -> object:
    """
    Run the configured service loop using the provided runtime parameters.
    
    Parameters:
        settings (Settings): Runtime settings for the service.
        symbols (list[str]): Symbols the service should process.
        interval (str): Timeframe/interval to use for market data.
        lookback (str): Historical lookback period to seed the service.
        poll_seconds (int): Seconds to wait between polling cycles.
        continuous (bool): If true, the service repeats until externally stopped.
        max_cycles (int | None): Maximum number of polling cycles to execute, or `None` for no limit.
    
    Returns:
        object: Result produced by the service run; type and semantics depend on the namespace implementation.
    """
    return namespace.run_service(
        settings=settings,
        symbols=symbols,
        interval=interval,
        lookback=lookback,
        poll_seconds=poll_seconds,
        continuous=continuous,
        max_cycles=max_cycles,
    )


def _refresh_trade_proposal_order_provider(
    namespace: Any,
    *,
    db: TradingDatabase,
    settings: Settings,
    proposal_id: str,
    review_notes: str,
) -> tuple[TradeProposalRecord, ExecutionOutcome]:
    """
    Refreshes the order for a trade proposal and returns the updated proposal record with the execution outcome.
    
    Parameters:
        db (TradingDatabase): Database handle used to locate and update the proposal.
        settings (Settings): Runtime settings affecting order refresh behaviour.
        proposal_id (str): Identifier of the trade proposal to refresh.
        review_notes (str): Notes to attach to the proposal review performed during refresh.
    
    Returns:
        tuple[TradeProposalRecord, ExecutionOutcome]: The updated trade proposal record and the execution outcome produced when attempting to refresh its order.
    """
    return namespace.refresh_trade_proposal_order(
        db=db,
        settings=settings,
        proposal_id=proposal_id,
        review_notes=review_notes,
    )


def refresh_trade_proposal_order_callback(namespace: Any) -> RefreshProposalOrder:
    """
    Create a callback that refreshes a trade proposal's order using the provided namespace.
    
    The returned callable accepts database and runtime settings along with a proposal ID and review notes, then delegates to the namespace to refresh the proposal's execution order.
    
    Parameters:
        namespace (Any): An object exposing a `refresh_trade_proposal_order`-like method; provided by the caller's CLI namespace.
    
    Returns:
        refresh_order (Callable): A function with signature:
            (db: TradingDatabase, settings: Settings, proposal_id: str, review_notes: str) -> tuple[TradeProposalRecord, ExecutionOutcome]
        The callable returns a tuple of the updated TradeProposalRecord and the ExecutionOutcome.
    """
    def refresh_order(
        *,
        db: TradingDatabase,
        settings: Settings,
        proposal_id: str,
        review_notes: str,
    ) -> tuple[TradeProposalRecord, ExecutionOutcome]:
        return _refresh_trade_proposal_order_provider(
            namespace,
            db=db,
            settings=settings,
            proposal_id=proposal_id,
            review_notes=review_notes,
        )

    return refresh_order


def _chat_with_persona_provider(
    namespace: Any,
    *,
    llm: Any,
    db: TradingDatabase,
    settings: Settings,
    persona: Any,
    user_message: str,
) -> str:
    """
    Send a user message to a persona using the provided LLM and return the persona's reply.
    
    Parameters:
        llm: The language model instance used to generate the persona's response.
        persona: The persona description or object that defines behavior and context.
        user_message (str): The message from the user to deliver to the persona.
    
    Returns:
        str: The persona's reply message.
    """
    return namespace.chat_with_persona(
        llm=llm,
        db=db,
        settings=settings,
        persona=persona,
        user_message=user_message,
    )


def chat_with_persona_callback(namespace: Any) -> Callable[..., str]:
    """
    Create and return a chat-with-persona callback bound to the provided namespace.
    
    Parameters:
        namespace (Any): Object exposing a `chat_with_persona` handler (and related context) which the returned callback will call.
    
    Returns:
        Callable[..., str]: A function accepting keyword parameters `llm`, `db`, `settings`, `persona`, and `user_message` and returning the persona's response string.
    """
    def chat_with_persona(
        *,
        llm: Any,
        db: TradingDatabase,
        settings: Settings,
        persona: Any,
        user_message: str,
    ) -> str:
        return _chat_with_persona_provider(
            namespace,
            llm=llm,
            db=db,
            settings=settings,
            persona=persona,
            user_message=user_message,
        )

    return chat_with_persona


def _interpret_operator_instruction_provider(
    namespace: Any,
    *,
    llm: Any,
    db: TradingDatabase,
    settings: Settings,
    user_message: str,
    allow_fallback: bool,
) -> OperatorInstruction:
    """
    Interpret an operator's free-form message into a structured OperatorInstruction.
    
    Parameters:
        llm: Language model instance used to interpret the message.
        db: TradingDatabase providing contextual state for interpretation.
        settings: Settings that influence interpretation behavior.
        user_message: The operator's message to interpret.
        allow_fallback: If `True`, permit fallback/default interpretations when the intent is ambiguous.
    
    Returns:
        OperatorInstruction: A parsed instruction object representing the operator's intent and any required actions.
    """
    return namespace.interpret_operator_instruction(
        llm=llm,
        db=db,
        settings=settings,
        user_message=user_message,
        allow_fallback=allow_fallback,
    )


def interpret_operator_instruction_callback(
    namespace: Any,
) -> Callable[..., OperatorInstruction]:
    """
    Create a CLI-style callback that interprets an operator instruction via the provided namespace.
    
    Parameters:
        namespace (Any): An object that implements an `interpret_operator_instruction(...) -> OperatorInstruction` method.
    
    Returns:
        Callable[..., OperatorInstruction]: A function accepting keyword arguments `llm`, `db`, `settings`, `user_message`, and `allow_fallback`, and returning an `OperatorInstruction`.
    """
    def interpret_instruction(
        *,
        llm: Any,
        db: TradingDatabase,
        settings: Settings,
        user_message: str,
        allow_fallback: bool,
    ) -> OperatorInstruction:
        return _interpret_operator_instruction_provider(
            namespace,
            llm=llm,
            db=db,
            settings=settings,
            user_message=user_message,
            allow_fallback=allow_fallback,
        )

    return interpret_instruction


def _apply_preference_update_provider(
    namespace: Any, db: TradingDatabase, update: PreferenceUpdate
) -> InvestmentPreferences:
    """
    Apply a preference update to the trading database and return the updated investment preferences.
    
    Parameters:
        db (TradingDatabase): Database instance where the preference update will be applied.
        update (PreferenceUpdate): The preference changes to apply.
    
    Returns:
        InvestmentPreferences: The investment preferences after applying the update.
    """
    return namespace.apply_preference_update(db, update)


def apply_preference_update_callback(
    namespace: Any,
) -> Callable[..., InvestmentPreferences]:
    """
    Create a callback that applies a preference update to a trading database and returns the resulting investment preferences.
    
    The returned callable expects a TradingDatabase and a PreferenceUpdate and applies the update, returning the updated InvestmentPreferences.
    
    Returns:
        Callable[[TradingDatabase, PreferenceUpdate], InvestmentPreferences]: A function that applies a preference update to `db` and returns the resulting `InvestmentPreferences`.
    """
    def apply_update(
        db: TradingDatabase, update: PreferenceUpdate
    ) -> InvestmentPreferences:
        return _apply_preference_update_provider(namespace, db, update)

    return apply_update


def memory_explorer_callback(namespace: Any) -> MemoryExplorerPayload:
    """
    Create a memory-explorer payload callable bound to the provided namespace.
    
    The returned function accepts CLI-style query parameters and produces the payload dictionary consumed by the memory explorer implementation.
    
    Returns:
    	A callable that accepts (settings, *, symbol: str | None = None, interval: str | None = None, lookback: str = "180d", limit: int = 5, use_latest_run: bool = False) and returns a dict[str, object] containing the memory explorer payload.
    """
    def memory_explorer(
        settings: Settings,
        *,
        symbol: str | None = None,
        interval: str | None = None,
        lookback: str = "180d",
        limit: int = 5,
        use_latest_run: bool = False,
    ) -> dict[str, object]:
        return _memory_explorer_payload(
            namespace,
            settings,
            symbol=symbol,
            interval=interval,
            lookback=lookback,
            limit=limit,
            use_latest_run=use_latest_run,
        )

    return memory_explorer


def retrieval_inspection_callback(namespace: Any) -> RetrievalInspectionPayload:
    """
    Create a retrieval-inspection payload callback bound to the provided namespace.
    
    The returned function accepts a Settings object and an optional `run_id` and produces
    the payload dictionary used for retrieval inspection.
    
    Returns:
        Callable that accepts `(settings: Settings, *, run_id: str | None = None)` and
        returns `dict[str, object]` containing the retrieval inspection payload.
    """
    def retrieval_inspection(
        settings: Settings, *, run_id: str | None = None
    ) -> dict[str, object]:
        return _retrieval_inspection_payload(namespace, settings, run_id=run_id)

    return retrieval_inspection


def run_comparison_callback(namespace: Any) -> RunComparison:
    """
    Create a CLI-compatible callback that runs a backtest comparison using the provided namespace.
    
    The returned function accepts settings, symbol, interval, lookback, optional warmup_bars, allow_fallback, and an optional DataFrame frame, and executes a backtest comparison for the specified market data, returning the resulting BacktestComparisonReport.
    
    Returns:
        Callable[..., BacktestComparisonReport]: A function that runs the backtest comparison and returns a BacktestComparisonReport.
    """
    def run_comparison(
        *,
        settings: Settings,
        symbol: str,
        interval: str,
        lookback: str,
        warmup_bars: int = 120,
        allow_fallback: bool = False,
        frame: DataFrame | None = None,
    ) -> BacktestComparisonReport:
        return _run_backtest_comparison_provider(
            namespace,
            settings=settings,
            symbol=symbol,
            interval=interval,
            lookback=lookback,
            warmup_bars=warmup_bars,
            allow_fallback=allow_fallback,
            frame=frame,
        )

    return run_comparison


def run_ablation_callback(namespace: Any) -> RunAblation:
    """
    Create a CLI callback that runs a memory ablation backtest.
    
    The returned function accepts keyword arguments: `settings`, `symbol`, `interval`, `lookback`, `warmup_bars`, `allow_fallback`, and optional `frame`, and executes a memory ablation backtest with those parameters.
    
    Returns:
        Callable[..., BacktestAblationReport]: A `run_ablation` callable that runs the memory ablation backtest and returns a BacktestAblationReport.
    """
    def run_ablation(
        *,
        settings: Settings,
        symbol: str,
        interval: str,
        lookback: str,
        warmup_bars: int = 120,
        allow_fallback: bool = False,
        frame: DataFrame | None = None,
    ) -> BacktestAblationReport:
        return _run_memory_ablation_backtest_provider(
            namespace,
            settings=settings,
            symbol=symbol,
            interval=interval,
            lookback=lookback,
            warmup_bars=warmup_bars,
            allow_fallback=allow_fallback,
            frame=frame,
        )

    return run_ablation


def run_walk_forward_callback(namespace: Any) -> RunWalkForward:
    """
    Create a CLI-compatible callback that runs a walk-forward backtest using the provided namespace.
    
    The returned function accepts CLI-style parameters for a walk-forward backtest and delegates execution to the namespace-backed provider.
    
    Parameters:
        settings (Settings): Runtime settings and configuration for the backtest.
        symbol (str): Trading symbol to backtest.
        interval (str): Data interval (e.g., '1m', '1h') used for bar aggregation.
        lookback (str): Historical range to use for the backtest (e.g., '180d').
        warmup_bars (int): Number of initial bars used to warm up indicators before evaluation.
        allow_fallback (bool): Whether to allow fallback behaviour when primary data or logic is unavailable.
        memory_enabled (bool): Whether agent memory should be enabled during the backtest.
        frame (DataFrame | None): Optional preloaded price/history frame to use instead of loading from storage.
    
    Returns:
        BacktestReport: Report summarizing the results of the walk-forward backtest.
    """
    def run_walk_forward(
        *,
        settings: Settings,
        symbol: str,
        interval: str,
        lookback: str,
        warmup_bars: int = 120,
        allow_fallback: bool = False,
        memory_enabled: bool = True,
        frame: DataFrame | None = None,
    ) -> BacktestReport:
        return _run_walk_forward_backtest_provider(
            namespace,
            settings=settings,
            symbol=symbol,
            interval=interval,
            lookback=lookback,
            warmup_bars=warmup_bars,
            allow_fallback=allow_fallback,
            memory_enabled=memory_enabled,
            frame=frame,
        )

    return run_walk_forward


def run_service_callback(namespace: Any) -> RunService:
    """
    Return a CLI-compatible `run_service` callable that invokes the namespace service runner with CLI-style loop parameters.
    
    The returned function accepts the usual service loop arguments (settings, symbols, interval, lookback, poll_seconds, continuous, max_cycles) and executes the service, returning whatever result the namespace provides.
    
    Returns:
        Callable[..., object]: A function that runs the configured service loop and returns its result.
    """
    def run_service(
        *,
        settings: Settings,
        symbols: list[str],
        interval: str,
        lookback: str,
        poll_seconds: int,
        continuous: bool,
        max_cycles: int | None,
    ) -> object:
        return _run_service_provider(
            namespace,
            settings=settings,
            symbols=symbols,
            interval=interval,
            lookback=lookback,
            poll_seconds=poll_seconds,
            continuous=continuous,
            max_cycles=max_cycles,
        )

    return run_service
