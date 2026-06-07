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
    return namespace.refresh_trade_proposal_order(
        db=db,
        settings=settings,
        proposal_id=proposal_id,
        review_notes=review_notes,
    )


def refresh_trade_proposal_order_callback(namespace: Any) -> RefreshProposalOrder:
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
    return namespace.chat_with_persona(
        llm=llm,
        db=db,
        settings=settings,
        persona=persona,
        user_message=user_message,
    )


def chat_with_persona_callback(namespace: Any) -> Callable[..., str]:
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
    return namespace.apply_preference_update(db, update)


def apply_preference_update_callback(
    namespace: Any,
) -> Callable[..., InvestmentPreferences]:
    def apply_update(
        db: TradingDatabase, update: PreferenceUpdate
    ) -> InvestmentPreferences:
        return _apply_preference_update_provider(namespace, db, update)

    return apply_update


def memory_explorer_callback(namespace: Any) -> MemoryExplorerPayload:
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
    def retrieval_inspection(
        settings: Settings, *, run_id: str | None = None
    ) -> dict[str, object]:
        return _retrieval_inspection_payload(namespace, settings, run_id=run_id)

    return retrieval_inspection


def run_comparison_callback(namespace: Any) -> RunComparison:
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
