from typing import Any

import duckdb

from agentic_trader.config import Settings
from agentic_trader.execution.intent import ExecutionIntent, ExecutionOutcome
from agentic_trader.memory.policy import MemoryActor
from agentic_trader.schemas import (
    AccountMark,
    ChatHistoryEntry,
    DailyRiskReport,
    InvestmentPreferences,
    PortfolioSnapshot,
    PositionPlanSnapshot,
    PositionSnapshot,
    ProposalCandidateRecord,
    ProposalCandidateStatus,
    RunArtifacts,
    RunRecord,
    ServiceEvent,
    ServiceEventLevel,
    ServiceStateSnapshot,
    TradeContextRecord,
    TradeJournalEntry,
    TradeProposalRecord,
    TradeProposalStatus,
)
from agentic_trader.storage import portfolio as portfolio_store
from agentic_trader.storage import proposals as proposal_store
from agentic_trader.storage import memory_vectors as memory_vector_store
from agentic_trader.storage import operator_chat as operator_chat_store
from agentic_trader.storage import order_records as order_store
from agentic_trader.storage import preferences as preference_store
from agentic_trader.storage import run_records as run_store
from agentic_trader.storage import services as service_store
from agentic_trader.storage import trade_journal as trade_store
from agentic_trader.storage.schema import (
    create_core_tables,
    create_execution_tables,
    create_memory_tables,
    create_service_tables,
    ensure_default_account,
    migrate_memory_vector_columns,
    migrate_service_state_columns,
    migrate_trade_journal_constraints,
    migrate_trade_proposal_columns,
    table_exists,
)
from agentic_trader.storage.order_records import OrderRow
from agentic_trader.storage.services import ServiceStateUpdate


class TradingDatabase:
    def __init__(self, settings: Settings, *, read_only: bool = False):
        self.settings = settings
        self.path = settings.database_path
        self.read_only = read_only
        if read_only and self.path.exists():
            self.conn = duckdb.connect(str(self.path), read_only=True)
        else:
            self.conn = duckdb.connect(str(self.path))
            self._init_schema()

    def _table_exists(self, table_name: str) -> bool:
        return table_exists(self.conn, table_name)

    def _init_schema(self) -> None:
        """
        Create and migrate the database schema and ensure required seed rows exist.

        Creates any missing application tables and performs lightweight migrations for evolving schemas
        (e.g., adding columns to `service_state` and `memory_vectors` when introduced in newer versions).
        After schema creation/migration, ensures a `paper` account row exists in `account_state` (inserting it
        with the configured default cash when absent) and ensures a default preferences profile exists
        (inserting a default `InvestmentPreferences()` when absent).
        """
        create_core_tables(self.conn)
        migrate_trade_journal_constraints(self.conn)
        create_execution_tables(self.conn)
        migrate_trade_proposal_columns(self.conn)
        create_service_tables(self.conn)
        migrate_service_state_columns(self.conn)
        create_memory_tables(self.conn)
        migrate_memory_vector_columns(self.conn)
        ensure_default_account(
            self.conn,
            default_cash=self.settings.default_cash,
        )
        self._ensure_default_preferences()

    def repair_trade_journal_constraints(self) -> None:
        """Deduplicate trade-journal entry order IDs and recreate the unique index."""
        migrate_trade_journal_constraints(self.conn)

    def _ensure_default_preferences(self) -> None:
        preference_store.ensure_default_preferences(self.conn)

    def close(self) -> None:
        self.conn.close()

    def insert_run(self, run_id: str, artifacts: RunArtifacts) -> None:
        run_store.insert_run(self.conn, run_id, artifacts)

    def insert_order(self, order: dict[str, Any]) -> None:
        order_store.insert_order(self.conn, order)

    def latest_order(self) -> OrderRow | None:
        return order_store.latest_order(self.conn)

    def insert_trade_proposal(self, proposal: TradeProposalRecord) -> None:
        proposal_store.insert_trade_proposal(self.conn, proposal)

    def insert_proposal_candidate(self, candidate: ProposalCandidateRecord) -> None:
        proposal_store.insert_proposal_candidate(self.conn, candidate)

    def get_proposal_candidate(
        self, candidate_id: str
    ) -> ProposalCandidateRecord | None:
        return proposal_store.get_proposal_candidate(self.conn, candidate_id)

    def list_proposal_candidates(
        self, *, status: ProposalCandidateStatus | None = None, limit: int = 50
    ) -> list[ProposalCandidateRecord]:
        return proposal_store.list_proposal_candidates(
            self.conn,
            status=status,
            limit=limit,
        )

    def update_proposal_candidate(self, candidate: ProposalCandidateRecord) -> bool:
        return proposal_store.update_proposal_candidate(self.conn, candidate)

    def promote_proposal_candidate_with_proposal(
        self,
        *,
        candidate: ProposalCandidateRecord,
        proposal: TradeProposalRecord,
        expected_status: ProposalCandidateStatus = "candidate",
    ) -> bool:
        return proposal_store.promote_proposal_candidate_with_proposal(
            self.conn,
            candidate=candidate,
            proposal=proposal,
            expected_status=expected_status,
        )

    def get_trade_proposal(self, proposal_id: str) -> TradeProposalRecord | None:
        return proposal_store.get_trade_proposal(self.conn, proposal_id)

    def list_trade_proposals(
        self, *, status: TradeProposalStatus | None = None, limit: int = 50
    ) -> list[TradeProposalRecord]:
        return proposal_store.list_trade_proposals(
            self.conn,
            status=status,
            limit=limit,
        )

    def update_trade_proposal(
        self,
        proposal: TradeProposalRecord,
        *,
        expected_status: TradeProposalStatus | None = None,
    ) -> bool:
        return proposal_store.update_trade_proposal(
            self.conn,
            proposal,
            expected_status=expected_status,
        )

    def save_preferences(self, preferences: InvestmentPreferences) -> None:
        preference_store.save_preferences(self.conn, preferences)

    def load_preferences(self) -> InvestmentPreferences:
        return preference_store.load_preferences(self.conn)

    def list_recent_runs(
        self, limit: int = 10
    ) -> list[tuple[str, str, str, str, bool]]:
        return run_store.list_recent_runs(self.conn, limit=limit)

    def get_run(self, run_id: str) -> RunRecord | None:
        return run_store.get_run(self.conn, run_id)

    def latest_run(self) -> RunRecord | None:
        return run_store.latest_run(self.conn)

    def list_run_records(self, limit: int = 200) -> list[RunRecord]:
        return run_store.list_run_records(self.conn, limit=limit)

    def upsert_memory_vector(
        self,
        run_id: str,
        artifacts: RunArtifacts,
        *,
        created_at: str | None = None,
        actor: MemoryActor = "system_runtime",
    ) -> None:
        run_store.upsert_memory_vector(
            self.conn,
            run_id,
            artifacts,
            created_at=created_at,
            actor=actor,
        )

    def list_memory_vectors(
        self, limit: int = 200
    ) -> list[tuple[str, str, str, list[float], str]]:
        return memory_vector_store.list_memory_vectors(self.conn, limit=limit)

    def insert_chat_history(
        self,
        *,
        persona: str,
        user_message: str,
        response_text: str,
        actor: MemoryActor = "operator_chat",
    ) -> str:
        return operator_chat_store.insert_chat_history(
            self.conn,
            persona=persona,
            user_message=user_message,
            response_text=response_text,
            actor=actor,
        )

    def list_chat_history(self, limit: int = 20) -> list[ChatHistoryEntry]:
        return operator_chat_store.list_chat_history(self.conn, limit=limit)

    def record_account_mark(
        self,
        *,
        source: str,
        note: str,
        cycle_count: int | None = None,
        symbol: str | None = None,
    ) -> str:
        return portfolio_store.record_account_mark(
            self.conn,
            source=source,
            note=note,
            cycle_count=cycle_count,
            symbol=symbol,
        )

    def list_account_marks(self, limit: int = 20) -> list[AccountMark]:
        return portfolio_store.list_account_marks(self.conn, limit=limit)

    def order_has_fill(self, order_id: str) -> bool:
        return trade_store.order_has_fill(self.conn, order_id)

    def order_realized_pnl(self, order_id: str) -> float:
        return trade_store.order_realized_pnl(self.conn, order_id)

    def create_trade_journal(
        self,
        *,
        run_id: str | None,
        order_id: str,
        artifacts: RunArtifacts,
        journal_status: str,
        notes: str = "",
    ) -> str:
        return trade_store.create_trade_journal(
            self.conn,
            run_id=run_id,
            order_id=order_id,
            artifacts=artifacts,
            journal_status=journal_status,
            notes=notes,
        )

    def create_trade_journal_from_proposal(
        self,
        *,
        proposal: TradeProposalRecord,
        outcome: ExecutionOutcome,
    ) -> str | None:
        return trade_store.create_trade_journal_from_proposal(
            self.conn,
            proposal=proposal,
            outcome=outcome,
        )

    def persist_trade_context(
        self,
        *,
        trade_id: str,
        run_id: str | None,
        artifacts: RunArtifacts,
        execution_intent: ExecutionIntent | None = None,
        execution_outcome: ExecutionOutcome | None = None,
    ) -> None:
        trade_store.persist_trade_context(
            self.conn,
            trade_id=trade_id,
            run_id=run_id,
            artifacts=artifacts,
            execution_intent=execution_intent,
            execution_outcome=execution_outcome,
        )

    def record_execution_outcome(
        self,
        *,
        run_id: str | None,
        intent: ExecutionIntent,
        outcome: ExecutionOutcome,
    ) -> None:
        trade_store.record_execution_outcome(
            self.conn,
            run_id=run_id,
            intent=intent,
            outcome=outcome,
        )

    def latest_execution_record(self) -> dict[str, object] | None:
        return trade_store.latest_execution_record(self.conn)

    def get_execution_record(self, intent_id: str) -> dict[str, object] | None:
        return trade_store.get_execution_record(self.conn, intent_id)

    def close_trade_journal(
        self,
        *,
        symbol: str,
        exit_order_id: str,
        exit_reason: str,
        exit_price: float,
        realized_pnl: float,
        notes: str = "",
    ) -> None:
        trade_store.close_trade_journal(
            self.conn,
            symbol=symbol,
            exit_order_id=exit_order_id,
            exit_reason=exit_reason,
            exit_price=exit_price,
            realized_pnl=realized_pnl,
            notes=notes,
        )

    def list_trade_journal(self, limit: int = 20) -> list[TradeJournalEntry]:
        return trade_store.list_trade_journal(self.conn, limit=limit)

    def get_trade_context(self, trade_id: str) -> TradeContextRecord | None:
        return trade_store.get_trade_context(self.conn, trade_id)

    def latest_trade_context(self) -> TradeContextRecord | None:
        return trade_store.latest_trade_context(self.conn)

    def build_daily_risk_report(
        self, report_date: str | None = None
    ) -> DailyRiskReport:
        return portfolio_store.build_daily_risk_report(
            self.conn,
            self.settings,
            report_date=report_date,
        )

    def upsert_service_state(
        self,
        update: ServiceStateUpdate | None = None,
        **fields: Any,
    ) -> None:
        service_store.upsert_service_state(
            self.conn,
            self.settings,
            update=update,
            **fields,
        )

    def get_service_state(
        self, service_name: str = "orchestrator"
    ) -> ServiceStateSnapshot | None:
        return service_store.get_service_state(self.conn, service_name)

    def request_stop_service(self, service_name: str = "orchestrator") -> None:
        service_store.request_stop_service(self.conn, self.settings, service_name)

    def clear_stop_request(self, service_name: str = "orchestrator") -> None:
        service_store.clear_stop_request(self.conn, self.settings, service_name)

    def insert_service_event(
        self,
        *,
        service_name: str = "orchestrator",
        level: ServiceEventLevel,
        event_type: str,
        message: str,
        cycle_count: int | None = None,
        symbol: str | None = None,
    ) -> str:
        return service_store.insert_service_event(
            self.conn,
            self.settings,
            service_name=service_name,
            level=level,
            event_type=event_type,
            message=message,
            cycle_count=cycle_count,
            symbol=symbol,
        )

    def list_service_events(
        self, limit: int = 20, service_name: str = "orchestrator"
    ) -> list[ServiceEvent]:
        return service_store.list_service_events(
            self.conn,
            limit=limit,
            service_name=service_name,
        )

    def get_account_snapshot(self) -> PortfolioSnapshot:
        return portfolio_store.get_account_snapshot(self.conn)

    def get_position(self, symbol: str) -> PositionSnapshot | None:
        return portfolio_store.get_position(self.conn, symbol)

    def list_positions(self) -> list[PositionSnapshot]:
        return portfolio_store.list_positions(self.conn)

    def save_position_plan(
        self,
        *,
        symbol: str,
        side: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        max_holding_bars: int,
        holding_bars: int,
        invalidation_logic: str,
    ) -> None:
        portfolio_store.save_position_plan(
            self.conn,
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            max_holding_bars=max_holding_bars,
            holding_bars=holding_bars,
            invalidation_logic=invalidation_logic,
        )

    def get_position_plan(self, symbol: str) -> PositionPlanSnapshot | None:
        return portfolio_store.get_position_plan(self.conn, symbol)

    def list_position_plans(self) -> list[PositionPlanSnapshot]:
        return portfolio_store.list_position_plans(self.conn)

    def update_position_plan_holding(self, symbol: str, holding_bars: int) -> None:
        portfolio_store.update_position_plan_holding(self.conn, symbol, holding_bars)

    def delete_position_plan(self, symbol: str) -> None:
        portfolio_store.delete_position_plan(self.conn, symbol)

    def apply_fill(
        self,
        *,
        fill_id: str,
        order_id: str,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        cash_delta: float,
        realized_pnl_delta: float,
        new_quantity: float,
        new_average_price: float,
    ) -> None:
        portfolio_store.apply_fill(
            self.conn,
            fill_id=fill_id,
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            cash_delta=cash_delta,
            realized_pnl_delta=realized_pnl_delta,
            new_quantity=new_quantity,
            new_average_price=new_average_price,
        )

    def mark_price(self, symbol: str, market_price: float) -> None:
        portfolio_store.mark_price(self.conn, symbol, market_price)
