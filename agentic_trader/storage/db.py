import json
from datetime import datetime, timezone
from typing import Any, cast
from uuid import uuid4

import duckdb

from agentic_trader.config import Settings
from agentic_trader.execution.intent import ExecutionIntent, ExecutionOutcome
from agentic_trader.memory.embeddings import (
    build_memory_document,
    embed_artifacts,
    embedding_metadata,
)
from agentic_trader.memory.policy import MemoryActor, assert_memory_write_allowed
from agentic_trader.schemas import (
    AccountMark,
    ChatHistoryEntry,
    ChatPersona,
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
from agentic_trader.storage import proposals as proposal_store
from agentic_trader.storage import portfolio as portfolio_store
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
from agentic_trader.storage.services import ServiceStateUpdate

type OrderRow = tuple[str, str, str, str, bool, float, float, float, float, float]


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
        pref_existing = self.conn.execute(
            "select count(*) from preferences where profile_id = 'default'"
        ).fetchone()
        if pref_existing and int(pref_existing[0]) == 0:
            self.save_preferences(InvestmentPreferences())

    def close(self) -> None:
        self.conn.close()

    def insert_run(self, run_id: str, artifacts: RunArtifacts) -> None:
        created_at = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """
            insert into runs (run_id, created_at, symbol, interval, approved, payload_json)
            values (?, ?, ?, ?, ?, ?)
            """,
            [
                run_id,
                created_at,
                artifacts.snapshot.symbol,
                artifacts.snapshot.interval,
                artifacts.execution.approved,
                artifacts.model_dump_json(indent=2),
            ],
        )
        self.upsert_memory_vector(
            run_id,
            artifacts,
            created_at=created_at,
            actor="system_runtime",
        )

    def insert_order(self, order: dict[str, Any]) -> None:
        """
        Persist an order record into the `orders` table.

        Parameters:
            order (dict[str, Any]): Mapping containing order fields to persist. Required keys:
                - order_id (str): Unique order identifier.
                - created_at (str): ISO-8601 timestamp when the order was created.
                - symbol (str): Market symbol for the order.
                - side (str): Order side, e.g., "buy" or "sell".
                - approved (bool): Whether the order was approved.
                - entry_price (float | None): Entry price for the order, if applicable.
                - stop_loss (float | None): Stop-loss price, if applicable.
                - take_profit (float | None): Take-profit price, if applicable.
                - position_size_pct (float | None): Position size as a percentage of portfolio.
                - confidence (float | None): Model confidence score for the order.
                - rationale (str | None): Human- or model-readable rationale for the order.
        """
        self.conn.execute(
            """
            insert into orders (
                order_id, created_at, symbol, side, approved, entry_price,
                stop_loss, take_profit, position_size_pct, confidence, rationale
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                order["order_id"],
                order["created_at"],
                order["symbol"],
                order["side"],
                order["approved"],
                order["entry_price"],
                order["stop_loss"],
                order["take_profit"],
                order["position_size_pct"],
                order["confidence"],
                order["rationale"],
            ],
        )

    def latest_order(self) -> OrderRow | None:
        """
        Fetch the most recent order row from the orders table.

        Returns:
            OrderRow | None: `OrderRow` tuple with fields (order_id, created_at, symbol, side, approved, entry_price, stop_loss, take_profit, position_size_pct, confidence), or `None` if no order row exists.
        """
        result = self.conn.execute("""
            select order_id, created_at, symbol, side, approved, entry_price,
                   stop_loss, take_profit, position_size_pct, confidence
            from orders
            order by created_at desc
            limit 1
            """).fetchone()
        if result is None:
            return None

        return (
            str(result[0]),
            str(result[1]),
            str(result[2]),
            str(result[3]),
            bool(result[4]),
            float(result[5]),
            float(result[6]),
            float(result[7]),
            float(result[8]),
            float(result[9]),
        )

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
        """
        Upserts the default preferences profile into the database.

        Stores the given InvestmentPreferences as JSON in the `preferences` table under profile_id `"default"`, updating the `updated_at` timestamp on conflict.

        Parameters:
            preferences (InvestmentPreferences): Preferences to persist; will be serialized to JSON.
        """
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """
            insert into preferences (profile_id, updated_at, payload_json)
            values ('default', ?, ?)
            on conflict(profile_id) do update set
                updated_at = excluded.updated_at,
                payload_json = excluded.payload_json
            """,
            [now, preferences.model_dump_json(indent=2)],
        )

    def load_preferences(self) -> InvestmentPreferences:
        """
        Load the default investment preferences from the database, creating and persisting a new default if none exists.

        Reads the row where profile_id is 'default' and parses its stored JSON into an InvestmentPreferences instance. If no row is found, creates a new InvestmentPreferences, saves it to the database, and returns it.

        Returns:
            preferences (InvestmentPreferences): The loaded or newly created default investment preferences.
        """
        row = self.conn.execute("""
            select payload_json
            from preferences
            where profile_id = 'default'
            """).fetchone()
        if row is None:
            preferences = InvestmentPreferences()
            self.save_preferences(preferences)
            return preferences
        return InvestmentPreferences.model_validate_json(str(row[0]))

    def list_recent_runs(
        self, limit: int = 10
    ) -> list[tuple[str, str, str, str, bool]]:
        rows = self.conn.execute(
            """
            select run_id, created_at, symbol, interval, approved
            from runs
            order by created_at desc
            limit ?
            """,
            [limit],
        ).fetchall()
        recent: list[tuple[str, str, str, str, bool]] = []
        for row in rows:
            recent.append(
                (
                    str(row[0]),
                    str(row[1]),
                    str(row[2]),
                    str(row[3]),
                    bool(row[4]),
                )
            )
        return recent

    def get_run(self, run_id: str) -> RunRecord | None:
        """
        Fetches a persisted run by its ID and returns a parsed RunRecord.

        Returns:
            A RunRecord built from the stored row (with `artifacts` validated/parsed from `payload_json`), or `None` if no run with the given `run_id` exists.
        """
        row = self.conn.execute(
            """
            select run_id, created_at, symbol, interval, approved, payload_json
            from runs
            where run_id = ?
            """,
            [run_id],
        ).fetchone()
        if row is None:
            return None
        return RunRecord(
            run_id=str(row[0]),
            created_at=str(row[1]),
            symbol=str(row[2]),
            interval=str(row[3]),
            approved=bool(row[4]),
            artifacts=RunArtifacts.model_validate_json(str(row[5])),
        )

    def latest_run(self) -> RunRecord | None:
        """
        Fetches the most recent run record.

        Returns:
            The `RunRecord` for the latest run ordered by creation time, or `None` if no run exists.
        """
        row = self.conn.execute("""
            select run_id
            from runs
            order by created_at desc
            limit 1
            """).fetchone()
        if row is None:
            return None
        return self.get_run(str(row[0]))

    def list_run_records(self, limit: int = 200) -> list[RunRecord]:
        rows = self.conn.execute(
            """
            select run_id
            from runs
            order by created_at desc
            limit ?
            """,
            [limit],
        ).fetchall()
        records: list[RunRecord] = []
        for row in rows:
            record = self.get_run(str(row[0]))
            if record is not None:
                records.append(record)
        return records

    def upsert_memory_vector(
        self,
        run_id: str,
        artifacts: RunArtifacts,
        *,
        created_at: str | None = None,
        actor: MemoryActor = "system_runtime",
    ) -> None:
        """
        Persist embedding and document data for a run into the memory_vectors table, inserting a new row or updating an existing one by run_id.

        This call enforces memory write authorization, computes embedding metadata and artifact embeddings, and stores provider/model metadata, embedding dimensions, embedding JSON, and a plain-text document for the given run. If created_at is not provided, the current UTC ISO timestamp is used.

        Parameters:
            run_id (str): Unique identifier for the run whose memory vector is being stored.
            artifacts (RunArtifacts): Run artifacts used to build the embedding and document payloads.
            created_at (str | None): ISO-formatted timestamp to record for the vector; defaults to current UTC time when None.
            actor (MemoryActor): Actor name used for authorization checks (e.g., "system_runtime").
        """
        assert_memory_write_allowed("trade_memory", actor)
        metadata = embedding_metadata()
        self.conn.execute(
            """
            insert into memory_vectors (
                run_id, created_at, symbol, embedding_provider, embedding_model,
                embedding_version, embedding_dimensions, embedding_json, document_text
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(run_id) do update set
                created_at = excluded.created_at,
                symbol = excluded.symbol,
                embedding_provider = excluded.embedding_provider,
                embedding_model = excluded.embedding_model,
                embedding_version = excluded.embedding_version,
                embedding_dimensions = excluded.embedding_dimensions,
                embedding_json = excluded.embedding_json,
                document_text = excluded.document_text
            """,
            [
                run_id,
                created_at or datetime.now(timezone.utc).isoformat(),
                artifacts.snapshot.symbol,
                metadata["provider"],
                metadata["model_name"],
                metadata["model_version"],
                metadata["dimensions"],
                json.dumps(embed_artifacts(artifacts)),
                build_memory_document(artifacts),
            ],
        )

    def list_memory_vectors(
        self, limit: int = 200
    ) -> list[tuple[str, str, str, list[float], str]]:
        rows = self.conn.execute(
            """
            select run_id, created_at, symbol, embedding_json, document_text
            from memory_vectors
            order by created_at desc
            limit ?
            """,
            [limit],
        ).fetchall()
        vectors: list[tuple[str, str, str, list[float], str]] = []
        for row in rows:
            vectors.append(
                (
                    str(row[0]),
                    str(row[1]),
                    str(row[2]),
                    [float(value) for value in json.loads(str(row[3]))],
                    str(row[4]),
                )
            )
        return vectors

    def insert_chat_history(
        self,
        *,
        persona: str,
        user_message: str,
        response_text: str,
        actor: MemoryActor = "operator_chat",
    ) -> str:
        assert_memory_write_allowed("chat_memory", actor)
        entry_id = f"chat-{uuid4().hex[:12]}"
        self.conn.execute(
            """
            insert into operator_chat_history (
                entry_id, created_at, persona, user_message, response_text
            )
            values (?, ?, ?, ?, ?)
            """,
            [
                entry_id,
                datetime.now(timezone.utc).isoformat(),
                persona,
                user_message,
                response_text,
            ],
        )
        return entry_id

    def list_chat_history(self, limit: int = 20) -> list[ChatHistoryEntry]:
        """
        Return the most recent operator chat history entries, ordered newest first.

        Returns:
            list[ChatHistoryEntry]: A list of chat history entries (most recent first), each containing
            `entry_id`, `created_at`, `persona`, `user_message`, and `response_text`.
        """
        rows = self.conn.execute(
            """
            select entry_id, created_at, persona, user_message, response_text
            from operator_chat_history
            order by created_at desc
            limit ?
            """,
            [limit],
        ).fetchall()
        history: list[ChatHistoryEntry] = []
        for row in rows:
            history.append(
                ChatHistoryEntry(
                    entry_id=str(row[0]),
                    created_at=str(row[1]),
                    persona=cast(ChatPersona, str(row[2])),
                    user_message=str(row[3]),
                    response_text=str(row[4]),
                )
            )
        return history

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
