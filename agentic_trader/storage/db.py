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
    TradeSide,
)
from agentic_trader.storage import proposals as proposal_store
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
        snapshot = self.get_account_snapshot()
        mark_id = f"mark-{uuid4().hex[:12]}"
        self.conn.execute(
            """
            insert into account_marks (
                mark_id, created_at, source, note, cycle_count, symbol,
                cash, market_value, equity, realized_pnl, unrealized_pnl, open_positions
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                mark_id,
                datetime.now(timezone.utc).isoformat(),
                source,
                note,
                cycle_count,
                symbol,
                snapshot.cash,
                snapshot.market_value,
                snapshot.equity,
                snapshot.realized_pnl,
                snapshot.unrealized_pnl,
                snapshot.open_positions,
            ],
        )
        return mark_id

    def list_account_marks(self, limit: int = 20) -> list[AccountMark]:
        rows = self.conn.execute(
            """
            select mark_id, created_at, source, note, cycle_count, symbol,
                   cash, market_value, equity, realized_pnl, unrealized_pnl, open_positions
            from account_marks
            order by created_at desc
            limit ?
            """,
            [limit],
        ).fetchall()
        marks: list[AccountMark] = []
        for row in rows:
            marks.append(
                AccountMark(
                    mark_id=str(row[0]),
                    created_at=str(row[1]),
                    source=str(row[2]),
                    note=str(row[3]),
                    cycle_count=int(row[4]) if row[4] is not None else None,
                    symbol=str(row[5]) if row[5] is not None else None,
                    cash=float(row[6]),
                    market_value=float(row[7]),
                    equity=float(row[8]),
                    realized_pnl=float(row[9]),
                    unrealized_pnl=float(row[10]),
                    open_positions=int(row[11]),
                )
            )
        return marks

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
        """
        Builds a daily risk report summarizing portfolio and account metrics for a given date.

        Parameters:
            report_date (str | None): Optional ISO date string ("YYYY-MM-DD") to generate the report for. If omitted, the current UTC date is used.

        Returns:
            DailyRiskReport: Aggregated metrics for the report date including cash, market value, equity, realized and unrealized P&L, open position count, today's fills and realized P&L, gross exposure and largest position as percentages of equity, portfolio Herfindahl–Hirschman Index (HHI), up to five largest position symbols, drawdown from all-time peak, and any generated warnings when configured thresholds are exceeded.
        """
        resolved_date = report_date or datetime.now(timezone.utc).date().isoformat()
        snapshot = self.get_account_snapshot()
        positions = self.list_positions()
        fills_row = self.conn.execute(
            """
            select count(*), coalesce(sum(realized_pnl_delta), 0)
            from fills
            where created_at like ?
            """,
            [f"{resolved_date}%"],
        ).fetchone()
        marks_row = self.conn.execute(
            """
            select count(*), coalesce(max(equity), 0)
            from account_marks
            where created_at like ?
            """,
            [f"{resolved_date}%"],
        ).fetchone()
        peak_row = self.conn.execute("""
            select coalesce(max(equity), 0)
            from account_marks
            """).fetchone()
        fills_today = int(fills_row[0]) if fills_row is not None else 0
        daily_realized_pnl = float(fills_row[1]) if fills_row is not None else 0.0
        marks_recorded = int(marks_row[0]) if marks_row is not None else 0
        all_time_peak = float(peak_row[0]) if peak_row is not None else snapshot.equity
        gross_exposure = sum(abs(position.market_value) for position in positions)
        largest_position = max(
            (abs(position.market_value) for position in positions), default=0.0
        )
        top_positions = sorted(
            positions, key=lambda position: abs(position.market_value), reverse=True
        )
        equity = snapshot.equity if snapshot.equity != 0 else 1.0
        portfolio_hhi = (
            sum(
                (abs(position.market_value) / gross_exposure) ** 2
                for position in positions
            )
            if gross_exposure > 0
            else 0.0
        )
        drawdown_from_peak_pct = (
            max(0.0, (all_time_peak - snapshot.equity) / all_time_peak)
            if all_time_peak > 0
            else 0.0
        )

        warnings: list[str] = []
        if snapshot.open_positions >= self.settings.max_open_positions:
            warnings.append("Open position count is elevated.")
        if gross_exposure / equity > self.settings.max_gross_exposure_pct:
            warnings.append(
                f"Gross exposure is above {self.settings.max_gross_exposure_pct:.0%} of equity."
            )
        if largest_position / equity > self.settings.max_position_pct:
            warnings.append(
                f"Largest position is above {self.settings.max_position_pct:.0%} of equity."
            )
        if portfolio_hhi > 0.25:
            warnings.append(
                f"Portfolio concentration HHI is elevated at {portfolio_hhi:.3f}."
            )
        if drawdown_from_peak_pct > 0.1:
            warnings.append("Portfolio drawdown from peak is above 10%.")

        return DailyRiskReport(
            report_date=resolved_date,
            generated_at=datetime.now(timezone.utc).isoformat(),
            cash=snapshot.cash,
            market_value=snapshot.market_value,
            equity=snapshot.equity,
            realized_pnl=snapshot.realized_pnl,
            unrealized_pnl=snapshot.unrealized_pnl,
            open_positions=snapshot.open_positions,
            fills_today=fills_today,
            marks_recorded=marks_recorded,
            daily_realized_pnl=daily_realized_pnl,
            gross_exposure_pct=gross_exposure / equity,
            largest_position_pct=largest_position / equity,
            portfolio_hhi=portfolio_hhi,
            top_position_symbols=[position.symbol for position in top_positions[:5]],
            drawdown_from_peak_pct=drawdown_from_peak_pct,
            warnings=warnings,
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
        """
        Compute a portfolio snapshot for the 'paper' account.

        Raises:
            RuntimeError: If the 'paper' account state is missing from the database.

        Returns:
            PortfolioSnapshot: Snapshot with fields:
                - cash: current cash balance
                - market_value: total market value of open positions (quantity * market_price)
                - equity: cash + market_value
                - realized_pnl: accumulated realized P&L
                - unrealized_pnl: sum of unrealized P&L across open positions
                - open_positions: number of open positions
        """
        row = self.conn.execute("""
            select cash, realized_pnl
            from account_state
            where account_id = 'paper'
            """).fetchone()
        if row is None:
            raise RuntimeError("Paper account state is missing")

        positions = self.list_positions()
        market_value = sum(
            position.quantity * position.market_price for position in positions
        )
        unrealized_pnl = sum(position.unrealized_pnl for position in positions)
        cash = float(row[0])
        realized_pnl = float(row[1])
        equity = cash + market_value
        return PortfolioSnapshot(
            cash=cash,
            market_value=market_value,
            equity=equity,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            open_positions=len(positions),
        )

    def get_position(self, symbol: str) -> PositionSnapshot | None:
        """
        Return the position snapshot for the given symbol, or None if no position exists.

        Returns:
            PositionSnapshot: Snapshot containing symbol, quantity, average_price, market_price, market_value, and unrealized_pnl; or `None` if the symbol is not found.
        """
        row = self.conn.execute(
            """
            select symbol, quantity, average_price, market_price
            from positions
            where symbol = ?
            """,
            [symbol],
        ).fetchone()
        if row is None:
            return None

        quantity = float(row[1])
        average_price = float(row[2])
        market_price = float(row[3])
        market_value = quantity * market_price
        unrealized_pnl = (market_price - average_price) * quantity
        return PositionSnapshot(
            symbol=str(row[0]),
            quantity=quantity,
            average_price=average_price,
            market_price=market_price,
            market_value=market_value,
            unrealized_pnl=unrealized_pnl,
        )

    def list_positions(self) -> list[PositionSnapshot]:
        """
        Return snapshots for all positions that have a non-zero quantity, ordered by symbol.

        Each returned PositionSnapshot includes computed `market_value` (quantity * market_price) and
        `unrealized_pnl` ((market_price - average_price) * quantity).

        Returns:
            list[PositionSnapshot]: List of position snapshots with fields:
                symbol, quantity, average_price, market_price, market_value, unrealized_pnl.
        """
        rows = self.conn.execute("""
            select symbol, quantity, average_price, market_price
            from positions
            where abs(quantity) > 0
            order by symbol
            """).fetchall()
        positions: list[PositionSnapshot] = []
        for row in rows:
            quantity = float(row[1])
            average_price = float(row[2])
            market_price = float(row[3])
            positions.append(
                PositionSnapshot(
                    symbol=str(row[0]),
                    quantity=quantity,
                    average_price=average_price,
                    market_price=market_price,
                    market_value=quantity * market_price,
                    unrealized_pnl=(market_price - average_price) * quantity,
                )
            )
        return positions

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
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """
            insert into position_plans (
                symbol, side, entry_price, stop_loss, take_profit,
                max_holding_bars, holding_bars, invalidation_logic, updated_at
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(symbol) do update set
                side = excluded.side,
                entry_price = excluded.entry_price,
                stop_loss = excluded.stop_loss,
                take_profit = excluded.take_profit,
                max_holding_bars = excluded.max_holding_bars,
                holding_bars = excluded.holding_bars,
                invalidation_logic = excluded.invalidation_logic,
                updated_at = excluded.updated_at
            """,
            [
                symbol,
                side,
                entry_price,
                stop_loss,
                take_profit,
                max_holding_bars,
                holding_bars,
                invalidation_logic,
                now,
            ],
        )

    def get_position_plan(self, symbol: str) -> PositionPlanSnapshot | None:
        """
        Retrieve the stored position plan for the given trading symbol.

        Numeric fields are converted to floats/ints and timestamp fields to strings when constructing the returned snapshot.

        Returns:
            PositionPlanSnapshot for the symbol, or `None` if no plan exists.
        """
        row = self.conn.execute(
            """
            select symbol, side, entry_price, stop_loss, take_profit,
                   max_holding_bars, holding_bars, invalidation_logic, updated_at
            from position_plans
            where symbol = ?
            """,
            [symbol],
        ).fetchone()
        if row is None:
            return None
        return PositionPlanSnapshot(
            symbol=str(row[0]),
            side=cast(TradeSide, str(row[1])),
            entry_price=float(row[2]),
            stop_loss=float(row[3]),
            take_profit=float(row[4]),
            max_holding_bars=int(row[5]),
            holding_bars=int(row[6]),
            invalidation_logic=str(row[7]),
            updated_at=str(row[8]),
        )

    def list_position_plans(self) -> list[PositionPlanSnapshot]:
        """
        List saved position plans ordered by symbol.

        Each entry is a PositionPlanSnapshot containing symbol, side, entry_price, stop_loss, take_profit,
        max_holding_bars, holding_bars, invalidation_logic, and updated_at.

        Returns:
            list[PositionPlanSnapshot]: Position plans ordered by symbol.
        """
        rows = self.conn.execute("""
            select symbol, side, entry_price, stop_loss, take_profit,
                   max_holding_bars, holding_bars, invalidation_logic, updated_at
            from position_plans
            order by symbol
            """).fetchall()
        plans: list[PositionPlanSnapshot] = []
        for row in rows:
            plans.append(
                PositionPlanSnapshot(
                    symbol=str(row[0]),
                    side=cast(TradeSide, str(row[1])),
                    entry_price=float(row[2]),
                    stop_loss=float(row[3]),
                    take_profit=float(row[4]),
                    max_holding_bars=int(row[5]),
                    holding_bars=int(row[6]),
                    invalidation_logic=str(row[7]),
                    updated_at=str(row[8]),
                )
            )
        return plans

    def update_position_plan_holding(self, symbol: str, holding_bars: int) -> None:
        self.conn.execute(
            """
            update position_plans
            set holding_bars = ?, updated_at = ?
            where symbol = ?
            """,
            [holding_bars, datetime.now(timezone.utc).isoformat(), symbol],
        )

    def delete_position_plan(self, symbol: str) -> None:
        self.conn.execute(
            "delete from position_plans where symbol = ?",
            [symbol],
        )

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
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """
            insert into fills (
                fill_id, order_id, created_at, symbol, side, quantity, price,
                cash_delta, realized_pnl_delta
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                fill_id,
                order_id,
                now,
                symbol,
                side,
                quantity,
                price,
                cash_delta,
                realized_pnl_delta,
            ],
        )
        self.conn.execute(
            """
            update account_state
            set updated_at = ?, cash = cash + ?, realized_pnl = realized_pnl + ?
            where account_id = 'paper'
            """,
            [now, cash_delta, realized_pnl_delta],
        )
        self.conn.execute(
            """
            insert into positions (symbol, quantity, average_price, market_price, updated_at)
            values (?, ?, ?, ?, ?)
            on conflict(symbol) do update set
                quantity = excluded.quantity,
                average_price = excluded.average_price,
                market_price = excluded.market_price,
                updated_at = excluded.updated_at
            """,
            [symbol, new_quantity, new_average_price, price, now],
        )

    def mark_price(self, symbol: str, market_price: float) -> None:
        self.conn.execute(
            """
            update positions
            set market_price = ?, updated_at = ?
            where symbol = ?
            """,
            [market_price, datetime.now(timezone.utc).isoformat(), symbol],
        )
