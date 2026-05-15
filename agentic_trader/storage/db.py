from datetime import datetime, timezone
from dataclasses import dataclass
import json
from typing import Any, Literal, cast, get_args
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
from agentic_trader.runtime_feed import append_service_event, write_service_state
from agentic_trader.schemas import (
    AccountMark,
    AgentStageTrace,
    ChatPersona,
    ChatHistoryEntry,
    CoordinatorFocus,
    DailyRiskReport,
    ExecutionSide,
    InvestmentPreferences,
    JournalStatus,
    PortfolioSnapshot,
    PositionPlanSnapshot,
    PositionSnapshot,
    RunRecord,
    RunArtifacts,
    ServiceEventLevel,
    ServiceState,
    ServiceEvent,
    ServiceStateSnapshot,
    RuntimeMode,
    TradeSide,
    TradeProposalRecord,
    TradeProposalStatus,
    TradeContextRecord,
    TradeJournalEntry,
)

type OrderRow = tuple[str, str, str, str, bool, float, float, float, float, float]
TERMINAL_SERVICE_STATES: set[ServiceState] = {
    "stopped",
    "completed",
    "failed",
    "blocked",
}
SERVICE_STATE_VALUES = set(get_args(ServiceState))
RUNTIME_MODE_VALUES = set(get_args(RuntimeMode))


@dataclass
class ServiceStateUpdate:
    state: str
    continuous: bool
    poll_seconds: int | None
    cycle_count: int
    message: str
    service_name: str = "orchestrator"
    runtime_mode: RuntimeMode | None = None
    symbols: list[str] | None = None
    interval: str | None = None
    lookback: str | None = None
    max_cycles: int | None = None
    current_symbol: str | None = None
    last_error: str | None = None
    pid: int | None = None
    clear_pid: bool = False
    stop_requested: bool | None = None
    background_mode: bool | None = None
    launch_count: int | None = None
    restart_count: int | None = None
    stdout_log_path: str | None = None
    stderr_log_path: str | None = None


@dataclass
class _TraceContextSummaries:
    routed_models: dict[str, str]
    retrieved_memory_summary: dict[str, list[str]]
    retrieval_explanation_summary: dict[str, list[dict[str, object]]]
    tool_outputs: dict[str, list[str]]
    shared_memory_summary: dict[str, list[str]]


@dataclass
class _ResolvedServiceStateValues:
    runtime_mode: RuntimeMode
    started_at: str
    pid: int | None
    stop_requested: bool
    symbols: list[str]
    interval: str | None
    lookback: str | None
    max_cycles: int | None
    background_mode: bool
    launch_count: int
    restart_count: int
    last_terminal_state: str | None
    last_terminal_at: str | None
    stdout_log_path: str | None
    stderr_log_path: str | None


def _empty_trace_context_summaries() -> _TraceContextSummaries:
    return _TraceContextSummaries(
        routed_models={},
        retrieved_memory_summary={},
        retrieval_explanation_summary={},
        tool_outputs={},
        shared_memory_summary={},
    )


def _str_or_none(value: Any) -> str | None:
    """
    Return the string representation of value, or None when value is None.

    Returns:
        `str` if `value` is not `None`, `None` otherwise.
    """
    return str(value) if value is not None else None


def _int_or_none(value: Any) -> int | None:
    """
    Convert a value to an integer when present.

    Parameters:
        value (Any): The input to convert; if `None`, no conversion is performed.

    Returns:
        int if value is not None, `None` otherwise.
    """
    return int(value) if value is not None else None


def _bool_or_default(value: Any, default: bool) -> bool:
    """
    Resolve a boolean from an input, falling back to a provided default when the input is None.

    Parameters:
        value (Any): The input to convert to bool; if `None`, the `default` is used instead.
        default (bool): The boolean value returned when `value` is `None`.

    Returns:
        bool: `bool(value)` if `value` is not `None`, otherwise `default`.
    """
    return bool(value) if value is not None else default


def _resolve_value[T](new_value: T | None, existing_value: T | None, default: T) -> T:
    """
    Choose a resolved value from `new_value`, `existing_value`, or `default`.

    Parameters:
        new_value (T | None): Preferred value; used if not `None`.
        existing_value (T | None): Fallback value; used if `new_value` is `None` and this is not `None`.
        default (T): Final fallback returned if both `new_value` and `existing_value` are `None`.

    Returns:
        T: `new_value` if it is not `None`, otherwise `existing_value` if it is not `None`, otherwise `default`.
    """
    if new_value is not None:
        return new_value
    if existing_value is not None:
        return existing_value
    return default


def _resolve_optional_value[T](
    new_value: T | None, existing_value: T | None
) -> T | None:
    """
    Selects a value between a new candidate and an existing fallback, preferring the new when present.

    Parameters:
        new_value (T | None): Candidate value to use if not `None`.
        existing_value (T | None): Fallback value returned when `new_value` is `None`.

    Returns:
        `new_value` if it is not `None`, otherwise `existing_value` (which may be `None`).
    """
    return new_value if new_value is not None else existing_value


def _existing_value(
    existing: ServiceStateSnapshot | None,
    attr: str,
) -> Any | None:
    if existing is None:
        return None
    return getattr(existing, attr)


def _resolve_started_at(
    *,
    update: ServiceStateUpdate,
    existing: ServiceStateSnapshot | None,
    now: str,
) -> str:
    started_at = _existing_value(existing, "started_at")
    if update.state == "starting" or started_at is None:
        return now
    return started_at


def _resolve_service_pid(
    update: ServiceStateUpdate, existing: ServiceStateSnapshot | None
) -> int | None:
    if update.clear_pid:
        return None
    return _resolve_optional_value(update.pid, _existing_value(existing, "pid"))


def _resolve_symbols(
    symbols: list[str] | None, existing: ServiceStateSnapshot | None
) -> list[str]:
    """
    Selects the symbols list to use for a service state update.

    Parameters:
        symbols (list[str] | None): Explicit symbols provided for the update; if not None, these are used.
        existing (ServiceStateSnapshot | None): Existing service state to fall back to when `symbols` is None.

    Returns:
        list[str]: The resolved symbols list — `symbols` if provided, otherwise `existing.symbols` if `existing` is present, otherwise an empty list.
    """
    if symbols is not None:
        return list(symbols)
    if existing is not None:
        return existing.symbols
    return []


def _resolve_terminal_state(
    *, state: str, existing: ServiceStateSnapshot | None, now: str
) -> tuple[str | None, str | None]:
    """
    Determine the terminal state and timestamp to record when updating a service's state.

    If the provided `state` is in TERMINAL_SERVICE_STATES, returns `(state, now)`. Otherwise, if an existing snapshot is provided, returns its `last_terminal_state` and `last_terminal_at`; if no existing snapshot is available, returns `(None, None)`.

    Parameters:
        state: The new service state string being applied.
        existing: The prior ServiceStateSnapshot for the service, or `None` if none exists.
        now: ISO-8601 timestamp string representing the current time used when marking a terminal state.

    Returns:
        A tuple `(last_terminal_state, last_terminal_at)` where `last_terminal_state` is the terminal state string or `None`, and `last_terminal_at` is the timestamp string when that terminal state was recorded or `None`.
    """
    if state in TERMINAL_SERVICE_STATES:
        return state, now
    if existing is None:
        return None, None
    return existing.last_terminal_state, existing.last_terminal_at


def _coerce_service_state(value: Any) -> ServiceState:
    state = str(value)
    return cast(ServiceState, state) if state in SERVICE_STATE_VALUES else "stopped"


def _coerce_runtime_mode(value: Any) -> RuntimeMode:
    mode = str(value)
    return cast(RuntimeMode, mode) if mode in RUNTIME_MODE_VALUES else "operation"


def _decode_symbols(value: Any) -> list[str]:
    return json.loads(str(value)) if value is not None else []


def _int_or_default(value: Any, default: int) -> int:
    return int(value) if value is not None else default


def _trace_context(trace: AgentStageTrace) -> dict[str, Any] | None:
    try:
        context = json.loads(trace.context_json)
    except json.JSONDecodeError:
        return None
    return context if isinstance(context, dict) else None


def _summarize_trace_contexts(
    traces: list[AgentStageTrace],
) -> _TraceContextSummaries:
    summaries = _empty_trace_context_summaries()
    for trace in traces:
        summaries.routed_models[trace.role] = trace.model_name
        context = _trace_context(trace)
        if context is None:
            continue
        _collect_trace_context_summary(summaries, trace.role, context)
    return summaries


def _collect_trace_context_summary(
    summaries: _TraceContextSummaries,
    role: str,
    context: dict[str, Any],
) -> None:
    retrieved_memories = context.get("retrieved_memories")
    if isinstance(retrieved_memories, list):
        summaries.retrieved_memory_summary[role] = [
            str(item) for item in retrieved_memories[:5]
        ]

    retrieval_explanations = context.get("retrieval_explanations")
    if isinstance(retrieval_explanations, list):
        summaries.retrieval_explanation_summary[role] = [
            item for item in retrieval_explanations[:5] if isinstance(item, dict)
        ]

    trace_tool_outputs = context.get("tool_outputs")
    if isinstance(trace_tool_outputs, list):
        summaries.tool_outputs[role] = [str(item) for item in trace_tool_outputs[:5]]

    shared_memory_bus = context.get("shared_memory_bus")
    if isinstance(shared_memory_bus, list):
        summaries.shared_memory_summary[role] = [
            str(item.get("summary", ""))
            for item in shared_memory_bus[:5]
            if isinstance(item, dict)
        ]


def _execution_adapter_name(
    execution_intent: ExecutionIntent | None,
    execution_outcome: ExecutionOutcome | None,
) -> str | None:
    if execution_outcome is not None:
        return execution_outcome.adapter_name
    if execution_intent is not None:
        return execution_intent.adapter_name
    return None


def _service_state_from_row(row: tuple[Any, ...]) -> ServiceStateSnapshot:
    """
    Convert a database row tuple into a ServiceStateSnapshot.

    The input `row` is expected to follow the service_state table column order:
    (service_name, state, runtime_mode, updated_at, started_at, last_heartbeat_at, continuous,
     poll_seconds, cycle_count, symbols_json, interval, lookback, max_cycles,
     current_symbol, last_error, pid, stop_requested, background_mode,
     launch_count, restart_count, last_terminal_state, last_terminal_at,
     stdout_log_path, stderr_log_path, message).

    Parameters:
        row (tuple[Any, ...]): A database row tuple matching the columns above. `symbols_json` may be None or a JSON string.

    Unknown state strings are normalized to "stopped" so stale or manually
    edited runtime rows cannot break observer/status surfaces. The current
    schema already accepts the transitional "stopping" state.

    Returns:
        ServiceStateSnapshot: Parsed snapshot with coerced types (strings, ints, bools, lists) and sensible defaults for missing/None fields.
    """
    return ServiceStateSnapshot(
        service_name=str(row[0]),
        state=_coerce_service_state(row[1]),
        runtime_mode=_coerce_runtime_mode(row[2]),
        updated_at=str(row[3]),
        started_at=_str_or_none(row[4]),
        last_heartbeat_at=_str_or_none(row[5]),
        continuous=bool(row[6]),
        poll_seconds=_int_or_none(row[7]),
        cycle_count=int(row[8]),
        symbols=_decode_symbols(row[9]),
        interval=_str_or_none(row[10]),
        lookback=_str_or_none(row[11]),
        max_cycles=_int_or_none(row[12]),
        current_symbol=_str_or_none(row[13]),
        last_error=_str_or_none(row[14]),
        pid=_int_or_none(row[15]),
        stop_requested=_bool_or_default(row[16], False),
        background_mode=_bool_or_default(row[17], False),
        launch_count=_int_or_default(row[18], 0),
        restart_count=_int_or_default(row[19], 0),
        last_terminal_state=_str_or_none(row[20]),
        last_terminal_at=_str_or_none(row[21]),
        stdout_log_path=_str_or_none(row[22]),
        stderr_log_path=_str_or_none(row[23]),
        message=str(row[24]),
    )


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
        row = self.conn.execute(
            """
            select count(*)
            from information_schema.tables
            where table_name = ?
            """,
            [table_name],
        ).fetchone()
        return row is not None and int(row[0]) > 0

    def _init_schema(self) -> None:
        """
        Create and migrate the database schema and ensure required seed rows exist.

        Creates any missing application tables and performs lightweight migrations for evolving schemas
        (e.g., adding columns to `service_state` and `memory_vectors` when introduced in newer versions).
        After schema creation/migration, ensures a `paper` account row exists in `account_state` (inserting it
        with the configured default cash when absent) and ensures a default preferences profile exists
        (inserting a default `InvestmentPreferences()` when absent).
        """
        self._create_core_tables()
        self._create_execution_tables()
        self._create_service_tables()
        self._migrate_service_state_columns()
        self._create_memory_tables()
        self._migrate_memory_vector_columns()
        self._ensure_default_account()
        self._ensure_default_preferences()

    def _create_core_tables(self) -> None:
        self.conn.execute(
            """
            create table if not exists runs (
                run_id varchar primary key,
                created_at varchar not null,
                symbol varchar not null,
                interval varchar not null,
                approved boolean not null,
                payload_json varchar not null
            )
            """
        )
        self.conn.execute(
            """
            create table if not exists orders (
                order_id varchar primary key,
                created_at varchar not null,
                symbol varchar not null,
                side varchar not null,
                approved boolean not null,
                entry_price double not null,
                stop_loss double not null,
                take_profit double not null,
                position_size_pct double not null,
                confidence double not null,
                rationale varchar not null
            )
            """
        )
        self.conn.execute(
            """
            create table if not exists account_state (
                account_id varchar primary key,
                updated_at varchar not null,
                cash double not null,
                realized_pnl double not null
            )
            """
        )
        self.conn.execute(
            """
            create table if not exists positions (
                symbol varchar primary key,
                quantity double not null,
                average_price double not null,
                market_price double not null,
                updated_at varchar not null
            )
            """
        )
        self.conn.execute(
            """
            create table if not exists fills (
                fill_id varchar primary key,
                order_id varchar not null,
                created_at varchar not null,
                symbol varchar not null,
                side varchar not null,
                quantity double not null,
                price double not null,
                cash_delta double not null,
                realized_pnl_delta double not null
            )
            """
        )
        self.conn.execute(
            """
            create table if not exists position_plans (
                symbol varchar primary key,
                side varchar not null,
                entry_price double not null,
                stop_loss double not null,
                take_profit double not null,
                max_holding_bars integer not null,
                holding_bars integer not null,
                invalidation_logic varchar not null,
                updated_at varchar not null
            )
            """
        )
        self.conn.execute(
            """
            create table if not exists preferences (
                profile_id varchar primary key,
                updated_at varchar not null,
                payload_json varchar not null
            )
            """
        )
        self.conn.execute(
            """
            create table if not exists account_marks (
                mark_id varchar primary key,
                created_at varchar not null,
                source varchar not null,
                note varchar not null,
                cycle_count integer,
                symbol varchar,
                cash double not null,
                market_value double not null,
                equity double not null,
                realized_pnl double not null,
                unrealized_pnl double not null,
                open_positions integer not null
            )
            """
        )
        self.conn.execute(
            """
            create table if not exists trade_journal (
                trade_id varchar primary key,
                opened_at varchar not null,
                closed_at varchar,
                symbol varchar not null,
                run_id varchar,
                entry_order_id varchar not null,
                exit_order_id varchar,
                planned_side varchar not null,
                approved boolean not null,
                journal_status varchar not null,
                entry_price double not null,
                exit_price double,
                stop_loss double not null,
                take_profit double not null,
                position_size_pct double not null,
                confidence double not null,
                coordinator_focus varchar not null,
                strategy_family varchar not null,
                manager_bias varchar not null,
                review_summary varchar not null,
                exit_reason varchar,
                realized_pnl double,
                notes varchar not null
            )
            """
        )
        self.conn.execute(
            """
            create table if not exists trade_contexts (
                trade_id varchar primary key,
                created_at varchar not null,
                run_id varchar,
                symbol varchar not null,
                payload_json varchar not null
            )
            """
        )

    def _create_execution_tables(self) -> None:
        self.conn.execute(
            """
            create table if not exists execution_records (
                intent_id varchar primary key,
                created_at varchar not null,
                run_id varchar,
                order_id varchar,
                symbol varchar not null,
                execution_backend varchar not null,
                adapter_name varchar not null,
                status varchar not null,
                rejection_reason varchar,
                intent_json varchar not null,
                outcome_json varchar not null
            )
            """
        )
        self.conn.execute(
            """
            create table if not exists trade_proposals (
                proposal_id varchar primary key,
                created_at varchar not null,
                updated_at varchar not null,
                symbol varchar not null,
                side varchar not null,
                order_type varchar not null,
                quantity double,
                notional double,
                reference_price double not null,
                confidence double not null,
                thesis varchar not null,
                stop_loss double,
                take_profit double,
                invalidation_condition varchar,
                source varchar not null,
                status varchar not null,
                review_notes varchar not null,
                rejection_reason varchar,
                execution_intent_id varchar,
                execution_order_id varchar,
                execution_outcome_status varchar
            )
            """
        )

    def _create_service_tables(self) -> None:
        self.conn.execute(
            """
            create table if not exists service_state (
                service_name varchar primary key,
                state varchar not null,
                runtime_mode varchar not null default 'operation',
                updated_at varchar not null,
                started_at varchar,
                last_heartbeat_at varchar,
                continuous boolean not null,
                poll_seconds integer,
                cycle_count integer not null,
                symbols_json varchar not null default '[]',
                interval varchar,
                lookback varchar,
                max_cycles integer,
                current_symbol varchar,
                last_error varchar,
                pid bigint,
                stop_requested boolean not null default false,
                background_mode boolean not null default false,
                launch_count integer not null default 0,
                restart_count integer not null default 0,
                last_terminal_state varchar,
                last_terminal_at varchar,
                stdout_log_path varchar,
                stderr_log_path varchar,
                message varchar not null
            )
            """
        )
        self.conn.execute(
            """
            create table if not exists service_events (
                event_id varchar primary key,
                created_at varchar not null,
                service_name varchar not null,
                level varchar not null,
                event_type varchar not null,
                message varchar not null,
                cycle_count integer,
                symbol varchar
            )
            """
        )
        self.conn.execute(
            """
            create table if not exists operator_chat_history (
                entry_id varchar primary key,
                created_at varchar not null,
                persona varchar not null,
                user_message varchar not null,
                response_text varchar not null
            )
            """
        )

    def _column_names(self, table_name: str) -> set[str]:
        return {
            str(row[1])
            for row in self.conn.execute(f"pragma table_info('{table_name}')").fetchall()
        }

    def _add_missing_columns(
        self, table_name: str, column_statements: dict[str, str]
    ) -> None:
        existing_columns = self._column_names(table_name)
        for column_name, statement in column_statements.items():
            if column_name not in existing_columns:
                self.conn.execute(statement)

    def _migrate_service_state_columns(self) -> None:
        self._add_missing_columns(
            "service_state",
            {
                "pid": "alter table service_state add column pid bigint",
                "runtime_mode": "alter table service_state add column runtime_mode varchar default 'operation'",
                "stop_requested": "alter table service_state add column stop_requested boolean",
                "symbols_json": "alter table service_state add column symbols_json varchar",
                "interval": "alter table service_state add column interval varchar",
                "lookback": "alter table service_state add column lookback varchar",
                "max_cycles": "alter table service_state add column max_cycles integer",
                "background_mode": "alter table service_state add column background_mode boolean",
                "launch_count": "alter table service_state add column launch_count integer",
                "restart_count": "alter table service_state add column restart_count integer",
                "last_terminal_state": "alter table service_state add column last_terminal_state varchar",
                "last_terminal_at": "alter table service_state add column last_terminal_at varchar",
                "stdout_log_path": "alter table service_state add column stdout_log_path varchar",
                "stderr_log_path": "alter table service_state add column stderr_log_path varchar",
            },
        )

    def _create_memory_tables(self) -> None:
        self.conn.execute(
            """
            create table if not exists memory_vectors (
                run_id varchar primary key,
                created_at varchar not null,
                symbol varchar not null,
                embedding_provider varchar not null default 'local_hashing',
                embedding_model varchar not null default 'agentic-hash-v1',
                embedding_version varchar not null default '1',
                embedding_dimensions integer not null default 64,
                embedding_json varchar not null,
                document_text varchar not null
            )
            """
        )

    def _migrate_memory_vector_columns(self) -> None:
        self._add_missing_columns(
            "memory_vectors",
            {
                "embedding_provider": "alter table memory_vectors add column embedding_provider varchar default 'local_hashing'",
                "embedding_model": "alter table memory_vectors add column embedding_model varchar default 'agentic-hash-v1'",
                "embedding_version": "alter table memory_vectors add column embedding_version varchar default '1'",
                "embedding_dimensions": "alter table memory_vectors add column embedding_dimensions integer default 64",
            },
        )

    def _ensure_default_account(self) -> None:
        existing = self.conn.execute(
            "select count(*) from account_state where account_id = 'paper'"
        ).fetchone()
        if existing and int(existing[0]) == 0:
            self.conn.execute(
                """
                insert into account_state (account_id, updated_at, cash, realized_pnl)
                values ('paper', ?, ?, 0)
                """,
                [
                    datetime.now(timezone.utc).isoformat(),
                    self.settings.default_cash,
                ],
            )

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
        result = self.conn.execute(
            """
            select order_id, created_at, symbol, side, approved, entry_price,
                   stop_loss, take_profit, position_size_pct, confidence
            from orders
            order by created_at desc
            limit 1
            """
        ).fetchone()
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
        self.conn.execute(
            """
            insert into trade_proposals (
                proposal_id, created_at, updated_at, symbol, side, order_type,
                quantity, notional, reference_price, confidence, thesis, stop_loss,
                take_profit, invalidation_condition, source, status, review_notes,
                rejection_reason, execution_intent_id, execution_order_id,
                execution_outcome_status
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                proposal.proposal_id,
                proposal.created_at,
                proposal.updated_at,
                proposal.symbol,
                proposal.side,
                proposal.order_type,
                proposal.quantity,
                proposal.notional,
                proposal.reference_price,
                proposal.confidence,
                proposal.thesis,
                proposal.stop_loss,
                proposal.take_profit,
                proposal.invalidation_condition,
                proposal.source,
                proposal.status,
                proposal.review_notes,
                proposal.rejection_reason,
                proposal.execution_intent_id,
                proposal.execution_order_id,
                proposal.execution_outcome_status,
            ],
        )

    def get_trade_proposal(self, proposal_id: str) -> TradeProposalRecord | None:
        if not self._table_exists("trade_proposals"):
            return None
        rows = self._trade_proposal_rows(
            """
            select *
            from trade_proposals
            where proposal_id = ?
            """,
            [proposal_id],
        )
        return rows[0] if rows else None

    def list_trade_proposals(
        self, *, status: TradeProposalStatus | None = None, limit: int = 50
    ) -> list[TradeProposalRecord]:
        if not self._table_exists("trade_proposals"):
            return []
        if status is None:
            return self._trade_proposal_rows(
                """
                select *
                from trade_proposals
                order by created_at desc
                limit ?
                """,
                [limit],
            )
        return self._trade_proposal_rows(
            """
            select *
            from trade_proposals
            where status = ?
            order by created_at desc
            limit ?
            """,
            [status, limit],
        )

    def update_trade_proposal(
        self,
        proposal: TradeProposalRecord,
        *,
        expected_status: TradeProposalStatus | None = None,
    ) -> bool:
        if not self._table_exists("trade_proposals"):
            return False
        if expected_status is not None:
            self.conn.execute("begin transaction")
            try:
                current = self.conn.execute(
                    """
                    select status
                    from trade_proposals
                    where proposal_id = ?
                    """,
                    [proposal.proposal_id],
                ).fetchone()
                if current is None or str(current[0]) != expected_status:
                    self.conn.execute("commit")
                    return False
                self._execute_trade_proposal_update(proposal)
                self.conn.execute("commit")
                return True
            except Exception:
                self.conn.execute("rollback")
                raise
        self._execute_trade_proposal_update(proposal)
        return True

    def _execute_trade_proposal_update(self, proposal: TradeProposalRecord) -> None:
        self.conn.execute(
            """
            update trade_proposals
            set updated_at = ?,
                status = ?,
                review_notes = ?,
                rejection_reason = ?,
                execution_intent_id = ?,
                execution_order_id = ?,
                execution_outcome_status = ?
            where proposal_id = ?
            """,
            [
                proposal.updated_at,
                proposal.status,
                proposal.review_notes,
                proposal.rejection_reason,
                proposal.execution_intent_id,
                proposal.execution_order_id,
                proposal.execution_outcome_status,
                proposal.proposal_id,
            ],
        )

    def _trade_proposal_rows(
        self, query: str, params: list[object]
    ) -> list[TradeProposalRecord]:
        rows = self.conn.execute(query, params).fetchall()
        return [
            TradeProposalRecord(
                proposal_id=str(row[0]),
                created_at=str(row[1]),
                updated_at=str(row[2]),
                symbol=str(row[3]),
                side=cast(TradeSide, str(row[4])),
                order_type=cast(Literal["market", "limit"], str(row[5])),
                quantity=float(row[6]) if row[6] is not None else None,
                notional=float(row[7]) if row[7] is not None else None,
                reference_price=float(row[8]),
                confidence=float(row[9]),
                thesis=str(row[10]),
                stop_loss=float(row[11]) if row[11] is not None else None,
                take_profit=float(row[12]) if row[12] is not None else None,
                invalidation_condition=_str_or_none(row[13]),
                source=str(row[14]),
                status=cast(TradeProposalStatus, str(row[15])),
                review_notes=str(row[16]),
                rejection_reason=_str_or_none(row[17]),
                execution_intent_id=_str_or_none(row[18]),
                execution_order_id=_str_or_none(row[19]),
                execution_outcome_status=_str_or_none(row[20]),
            )
            for row in rows
        ]

    def save_preferences(self, preferences: InvestmentPreferences) -> None:
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
        row = self.conn.execute(
            """
            select payload_json
            from preferences
            where profile_id = 'default'
            """
        ).fetchone()
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
        row = self.conn.execute(
            """
            select run_id
            from runs
            order by created_at desc
            limit 1
            """
        ).fetchone()
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
        row = self.conn.execute(
            """
            select count(*)
            from fills
            where order_id = ?
            """,
            [order_id],
        ).fetchone()
        return bool(row and int(row[0]) > 0)

    def order_realized_pnl(self, order_id: str) -> float:
        row = self.conn.execute(
            """
            select coalesce(sum(realized_pnl_delta), 0)
            from fills
            where order_id = ?
            """,
            [order_id],
        ).fetchone()
        if row is None:
            return 0.0
        return float(row[0])

    def create_trade_journal(
        self,
        *,
        run_id: str | None,
        order_id: str,
        artifacts: RunArtifacts,
        journal_status: str,
        notes: str = "",
    ) -> str:
        trade_id = f"trade-{uuid4().hex[:12]}"
        self.conn.execute(
            """
            insert into trade_journal (
                trade_id, opened_at, symbol, run_id, entry_order_id, planned_side,
                approved, journal_status, entry_price, stop_loss, take_profit,
                position_size_pct, confidence, coordinator_focus, strategy_family,
                manager_bias, review_summary, notes
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                trade_id,
                datetime.now(timezone.utc).isoformat(),
                artifacts.snapshot.symbol,
                run_id,
                order_id,
                artifacts.execution.side,
                artifacts.execution.approved,
                journal_status,
                artifacts.execution.entry_price,
                artifacts.execution.stop_loss,
                artifacts.execution.take_profit,
                artifacts.execution.position_size_pct,
                artifacts.execution.confidence,
                artifacts.coordinator.market_focus,
                artifacts.strategy.strategy_family,
                artifacts.manager.action_bias,
                artifacts.review.summary,
                notes,
            ],
        )
        return trade_id

    def persist_trade_context(
        self,
        *,
        trade_id: str,
        run_id: str | None,
        artifacts: RunArtifacts,
        execution_intent: ExecutionIntent | None = None,
        execution_outcome: ExecutionOutcome | None = None,
    ) -> None:
        """
        Persist a consolidated trade context for a given trade into the `trade_contexts` table.

        Builds a TradeContextRecord from the provided `artifacts` and optional execution metadata, extracts routed model names and up to five items per trace for `retrieved_memories`, `tool_outputs`, and `shared_memory_bus` summaries (skipping traces with invalid or non-dict context), includes market snapshot, decision and review data, and the artifact-provided `fundamental_assessment` and `fundamental_summary`. The resulting record is serialized to JSON and upserted by `trade_id` into the `trade_contexts` table.

        Parameters:
            trade_id (str): Identifier used as the upsert key for the persisted trade context.
            run_id (str | None): Optional run identifier associated with this context.
            artifacts (RunArtifacts): Run artifacts containing agent traces, snapshots, decision features, and manager/review/execution data.
            execution_intent (ExecutionIntent | None): Optional execution intent; its backend/adapter and JSON form are included when present.
            execution_outcome (ExecutionOutcome | None): Optional execution outcome; its adapter, status, rejection reason, simulated metadata, and JSON form are included when present.
        """
        trace_summaries = _summarize_trace_contexts(artifacts.agent_traces)

        record = TradeContextRecord(
            trade_id=trade_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            run_id=run_id,
            symbol=artifacts.snapshot.symbol,
            market_snapshot=artifacts.snapshot,
            market_context_pack=artifacts.snapshot.context_pack,
            canonical_snapshot=artifacts.canonical_snapshot,
            decision_features=artifacts.decision_features,
            routed_models=trace_summaries.routed_models,
            retrieved_memory_summary=trace_summaries.retrieved_memory_summary,
            retrieval_explanation_summary=(
                trace_summaries.retrieval_explanation_summary
            ),
            tool_outputs=trace_summaries.tool_outputs,
            shared_memory_summary=trace_summaries.shared_memory_summary,
            consensus=artifacts.consensus,
            fundamental_assessment=artifacts.fundamental,
            fundamental_summary=artifacts.fundamental.summary,
            macro_summary=artifacts.macro.summary,
            manager_rationale=artifacts.manager.rationale,
            manager_conflicts=artifacts.manager.conflicts,
            manager_resolution_notes=artifacts.manager.resolution_notes,
            execution_rationale=artifacts.execution.rationale,
            execution_backend=(
                execution_intent.execution_backend
                if execution_intent is not None
                else None
            ),
            execution_adapter=_execution_adapter_name(
                execution_intent,
                execution_outcome,
            ),
            execution_intent=(
                execution_intent.model_dump(mode="json")
                if execution_intent is not None
                else None
            ),
            execution_outcome_status=(
                execution_outcome.status if execution_outcome is not None else None
            ),
            execution_rejection_reason=(
                execution_outcome.rejection_reason
                if execution_outcome is not None
                else None
            ),
            execution_outcome=(
                execution_outcome.model_dump(mode="json")
                if execution_outcome is not None
                else None
            ),
            simulated_fill_metadata=(
                execution_outcome.simulated_metadata
                if execution_outcome is not None
                else {}
            ),
            review_summary=artifacts.review.summary,
            review_warnings=artifacts.review.warnings,
        )
        self.conn.execute(
            """
            insert into trade_contexts (trade_id, created_at, run_id, symbol, payload_json)
            values (?, ?, ?, ?, ?)
            on conflict(trade_id) do update set
                created_at = excluded.created_at,
                run_id = excluded.run_id,
                symbol = excluded.symbol,
                payload_json = excluded.payload_json
            """,
            [
                trade_id,
                record.created_at,
                run_id,
                artifacts.snapshot.symbol,
                record.model_dump_json(indent=2),
            ],
        )

    def record_execution_outcome(
        self,
        *,
        run_id: str | None,
        intent: ExecutionIntent,
        outcome: ExecutionOutcome,
    ) -> None:
        """
        Persist the broker-facing execution intent and its adapter outcome.

        The table is intentionally append/update by intent id so future live
        adapters can replay exactly what was requested, which backend handled it,
        and why the adapter filled, rejected, or blocked the order.
        """
        self.conn.execute(
            """
            insert into execution_records (
                intent_id, created_at, run_id, order_id, symbol, execution_backend,
                adapter_name, status, rejection_reason, intent_json, outcome_json
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(intent_id) do update set
                created_at = excluded.created_at,
                run_id = excluded.run_id,
                order_id = excluded.order_id,
                symbol = excluded.symbol,
                execution_backend = excluded.execution_backend,
                adapter_name = excluded.adapter_name,
                status = excluded.status,
                rejection_reason = excluded.rejection_reason,
                intent_json = excluded.intent_json,
                outcome_json = excluded.outcome_json
            """,
            [
                intent.intent_id,
                outcome.created_at,
                run_id,
                outcome.order_id,
                intent.symbol,
                outcome.execution_backend,
                outcome.adapter_name,
                outcome.status,
                outcome.rejection_reason,
                intent.model_dump_json(indent=2),
                outcome.model_dump_json(indent=2),
            ],
        )

    def latest_execution_record(self) -> dict[str, object] | None:
        row = self.conn.execute(
            """
            select intent_id, created_at, run_id, order_id, symbol, execution_backend,
                   adapter_name, status, rejection_reason, intent_json, outcome_json
            from execution_records
            order by created_at desc
            limit 1
            """
        ).fetchone()
        return self._execution_record_from_row(row)

    def get_execution_record(self, intent_id: str) -> dict[str, object] | None:
        row = self.conn.execute(
            """
            select intent_id, created_at, run_id, order_id, symbol, execution_backend,
                   adapter_name, status, rejection_reason, intent_json, outcome_json
            from execution_records
            where intent_id = ?
            """,
            [intent_id],
        ).fetchone()
        return self._execution_record_from_row(row)

    def _execution_record_from_row(self, row: object | None) -> dict[str, object] | None:
        if row is None:
            return None
        values = cast(tuple[object, ...], row)
        return {
            "intent_id": str(values[0]),
            "created_at": str(values[1]),
            "run_id": str(values[2]) if values[2] is not None else None,
            "order_id": str(values[3]) if values[3] is not None else None,
            "symbol": str(values[4]),
            "execution_backend": str(values[5]),
            "adapter_name": str(values[6]),
            "status": str(values[7]),
            "rejection_reason": str(values[8]) if values[8] is not None else None,
            "intent": json.loads(str(values[9])),
            "outcome": json.loads(str(values[10])),
        }

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
        row = self.conn.execute(
            """
            select trade_id
            from trade_journal
            where symbol = ? and journal_status = 'open'
            order by opened_at desc
            limit 1
            """,
            [symbol],
        ).fetchone()
        if row is None:
            return
        self.conn.execute(
            """
            update trade_journal
            set closed_at = ?,
                exit_order_id = ?,
                journal_status = 'closed',
                exit_price = ?,
                exit_reason = ?,
                realized_pnl = ?,
                notes = case
                    when notes = '' then ?
                    else notes || ' ' || ?
                end
            where trade_id = ?
            """,
            [
                datetime.now(timezone.utc).isoformat(),
                exit_order_id,
                exit_price,
                exit_reason,
                realized_pnl,
                notes,
                notes,
                str(row[0]),
            ],
        )

    def list_trade_journal(self, limit: int = 20) -> list[TradeJournalEntry]:
        """
        List recent trade journal entries ordered by most recent opening time.

        Parameters:
            limit (int): Maximum number of entries to return (default 20).

        Returns:
            list[TradeJournalEntry]: Entries ordered by `opened_at` descending, up to `limit` records.
        """
        rows = self.conn.execute(
            """
            select trade_id, opened_at, closed_at, symbol, run_id, entry_order_id, exit_order_id,
                   planned_side, approved, journal_status, entry_price, exit_price, stop_loss,
                   take_profit, position_size_pct, confidence, coordinator_focus, strategy_family,
                   manager_bias, review_summary, exit_reason, realized_pnl, notes
            from trade_journal
            order by opened_at desc
            limit ?
            """,
            [limit],
        ).fetchall()
        entries: list[TradeJournalEntry] = []
        for row in rows:
            entries.append(
                TradeJournalEntry(
                    trade_id=str(row[0]),
                    opened_at=str(row[1]),
                    closed_at=str(row[2]) if row[2] is not None else None,
                    symbol=str(row[3]),
                    run_id=str(row[4]) if row[4] is not None else None,
                    entry_order_id=str(row[5]),
                    exit_order_id=str(row[6]) if row[6] is not None else None,
                    planned_side=cast(ExecutionSide, str(row[7])),
                    approved=bool(row[8]),
                    journal_status=cast(JournalStatus, str(row[9])),
                    entry_price=float(row[10]),
                    exit_price=float(row[11]) if row[11] is not None else None,
                    stop_loss=float(row[12]),
                    take_profit=float(row[13]),
                    position_size_pct=float(row[14]),
                    confidence=float(row[15]),
                    coordinator_focus=cast(CoordinatorFocus, str(row[16])),
                    strategy_family=str(row[17]),
                    manager_bias=cast(ExecutionSide, str(row[18])),
                    review_summary=str(row[19]),
                    exit_reason=str(row[20]) if row[20] is not None else None,
                    realized_pnl=float(row[21]) if row[21] is not None else None,
                    notes=str(row[22]),
                )
            )
        return entries

    def get_trade_context(self, trade_id: str) -> TradeContextRecord | None:
        row = self.conn.execute(
            """
            select payload_json
            from trade_contexts
            where trade_id = ?
            """,
            [trade_id],
        ).fetchone()
        if row is None:
            return None
        return TradeContextRecord.model_validate_json(str(row[0]))

    def latest_trade_context(self) -> TradeContextRecord | None:
        row = self.conn.execute(
            """
            select payload_json
            from trade_contexts
            order by created_at desc
            limit 1
            """
        ).fetchone()
        if row is None:
            return None
        return TradeContextRecord.model_validate_json(str(row[0]))

    def build_daily_risk_report(
        self, report_date: str | None = None
    ) -> DailyRiskReport:
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
        peak_row = self.conn.execute(
            """
            select coalesce(max(equity), 0)
            from account_marks
            """
        ).fetchone()
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
            sum((abs(position.market_value) / gross_exposure) ** 2 for position in positions)
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

    def _resolve_service_state_values(
        self,
        *,
        update: ServiceStateUpdate,
        existing: ServiceStateSnapshot | None,
        now: str,
    ) -> _ResolvedServiceStateValues:
        resolved_runtime_mode = cast(
            RuntimeMode,
            _resolve_value(
                update.runtime_mode,
                cast(RuntimeMode | None, _existing_value(existing, "runtime_mode")),
                self.settings.runtime_mode,
            ),
        )
        last_terminal_state, last_terminal_at = _resolve_terminal_state(
            state=update.state, existing=existing, now=now
        )
        return _ResolvedServiceStateValues(
            runtime_mode=resolved_runtime_mode,
            started_at=_resolve_started_at(
                update=update,
                existing=existing,
                now=now,
            ),
            pid=_resolve_service_pid(update, existing),
            stop_requested=_resolve_value(
                update.stop_requested,
                _existing_value(existing, "stop_requested"),
                False,
            ),
            symbols=_resolve_symbols(update.symbols, existing),
            interval=_resolve_optional_value(
                update.interval, _existing_value(existing, "interval")
            ),
            lookback=_resolve_optional_value(
                update.lookback, _existing_value(existing, "lookback")
            ),
            max_cycles=_resolve_optional_value(
                update.max_cycles,
                _existing_value(existing, "max_cycles"),
            ),
            background_mode=_resolve_value(
                update.background_mode,
                _existing_value(existing, "background_mode"),
                False,
            ),
            launch_count=_resolve_value(
                update.launch_count,
                _existing_value(existing, "launch_count"),
                0,
            ),
            restart_count=_resolve_value(
                update.restart_count,
                _existing_value(existing, "restart_count"),
                0,
            ),
            last_terminal_state=last_terminal_state,
            last_terminal_at=last_terminal_at,
            stdout_log_path=_resolve_optional_value(
                update.stdout_log_path,
                _existing_value(existing, "stdout_log_path"),
            ),
            stderr_log_path=_resolve_optional_value(
                update.stderr_log_path,
                _existing_value(existing, "stderr_log_path"),
            ),
        )

    def _upsert_service_state_row(
        self,
        *,
        update: ServiceStateUpdate,
        resolved: _ResolvedServiceStateValues,
        now: str,
    ) -> None:
        self.conn.execute(
            """
            insert into service_state (
                service_name, state, runtime_mode, updated_at, started_at, last_heartbeat_at,
                continuous, poll_seconds, cycle_count, symbols_json, interval, lookback, max_cycles,
                current_symbol, last_error, pid, stop_requested, background_mode,
                launch_count, restart_count, last_terminal_state, last_terminal_at,
                stdout_log_path, stderr_log_path, message
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(service_name) do update set
                state = excluded.state,
                runtime_mode = excluded.runtime_mode,
                updated_at = excluded.updated_at,
                started_at = excluded.started_at,
                last_heartbeat_at = excluded.last_heartbeat_at,
                continuous = excluded.continuous,
                poll_seconds = excluded.poll_seconds,
                cycle_count = excluded.cycle_count,
                symbols_json = excluded.symbols_json,
                interval = excluded.interval,
                lookback = excluded.lookback,
                max_cycles = excluded.max_cycles,
                current_symbol = excluded.current_symbol,
                last_error = excluded.last_error,
                pid = excluded.pid,
                stop_requested = excluded.stop_requested,
                background_mode = excluded.background_mode,
                launch_count = excluded.launch_count,
                restart_count = excluded.restart_count,
                last_terminal_state = excluded.last_terminal_state,
                last_terminal_at = excluded.last_terminal_at,
                stdout_log_path = excluded.stdout_log_path,
                stderr_log_path = excluded.stderr_log_path,
                message = excluded.message
            """,
            [
                update.service_name,
                update.state,
                resolved.runtime_mode,
                now,
                resolved.started_at,
                now,
                update.continuous,
                update.poll_seconds,
                update.cycle_count,
                json.dumps(resolved.symbols),
                resolved.interval,
                resolved.lookback,
                resolved.max_cycles,
                update.current_symbol,
                update.last_error,
                resolved.pid,
                resolved.stop_requested,
                resolved.background_mode,
                resolved.launch_count,
                resolved.restart_count,
                resolved.last_terminal_state,
                resolved.last_terminal_at,
                resolved.stdout_log_path,
                resolved.stderr_log_path,
                update.message,
            ],
        )

    def _write_service_state_snapshot(
        self,
        *,
        update: ServiceStateUpdate,
        resolved: _ResolvedServiceStateValues,
        now: str,
    ) -> None:
        write_service_state(
            self.settings,
            ServiceStateSnapshot(
                service_name=update.service_name,
                state=cast(ServiceState, update.state),
                runtime_mode=resolved.runtime_mode,
                updated_at=now,
                started_at=resolved.started_at,
                last_heartbeat_at=now,
                continuous=update.continuous,
                poll_seconds=update.poll_seconds,
                cycle_count=update.cycle_count,
                symbols=resolved.symbols,
                interval=resolved.interval,
                lookback=resolved.lookback,
                max_cycles=resolved.max_cycles,
                current_symbol=update.current_symbol,
                last_error=update.last_error,
                pid=resolved.pid,
                stop_requested=resolved.stop_requested,
                background_mode=resolved.background_mode,
                launch_count=resolved.launch_count,
                restart_count=resolved.restart_count,
                last_terminal_state=resolved.last_terminal_state,
                last_terminal_at=resolved.last_terminal_at,
                stdout_log_path=resolved.stdout_log_path,
                stderr_log_path=resolved.stderr_log_path,
                message=update.message,
            ),
        )

    def upsert_service_state(
        self,
        update: ServiceStateUpdate | None = None,
        **fields: Any,
    ) -> None:
        """
        Update or insert the persisted runtime snapshot for a named service.

        Merges provided fields with any existing stored snapshot (preserving omitted values), resolves runtime-mode and other defaults, updates terminal-state markers when the new state is terminal, ensures `started_at` is set when appropriate, writes the resolved row into the database, and emits a mirrored ServiceStateSnapshot via write_service_state.

        Parameters:
            runtime_mode: If provided, sets the service's runtime mode; if `None`, preserves the existing runtime mode or falls back to settings.
            symbols: If provided, replaces the stored symbol list; if `None`, preserves existing symbols (or `[]` when no existing snapshot).
            stop_requested: If provided, sets the explicit stop request flag; if `None`, preserves the existing flag.
        """
        if update is None:
            update = ServiceStateUpdate(**fields)
        elif fields:
            raise TypeError(
                "Pass either ServiceStateUpdate or keyword fields, not both."
            )

        now = datetime.now(timezone.utc).isoformat()
        existing = self.get_service_state(update.service_name)
        resolved = self._resolve_service_state_values(
            update=update,
            existing=existing,
            now=now,
        )
        self._upsert_service_state_row(update=update, resolved=resolved, now=now)
        self._write_service_state_snapshot(update=update, resolved=resolved, now=now)

    def get_service_state(
        self, service_name: str = "orchestrator"
    ) -> ServiceStateSnapshot | None:
        """
        Retrieve the persisted service state snapshot for the named service.

        Parameters:
            service_name (str): Service identifier to fetch (defaults to "orchestrator").

        Returns:
            ServiceStateSnapshot | None: The service's snapshot if present, or `None` when no persisted state exists.
        """
        row = self.conn.execute(
            """
            select service_name, state, runtime_mode, updated_at, started_at, last_heartbeat_at,
                   continuous, poll_seconds, cycle_count, symbols_json, interval, lookback, max_cycles,
                   current_symbol, last_error, pid, stop_requested, background_mode,
                   launch_count, restart_count, last_terminal_state, last_terminal_at,
                   stdout_log_path, stderr_log_path, message
            from service_state
            where service_name = ?
            """,
            [service_name],
        ).fetchone()
        if row is None:
            return None
        return _service_state_from_row(row)

    def request_stop_service(self, service_name: str = "orchestrator") -> None:
        """
        Mark the named service as stopping and persist the updated service snapshot.

        Updates the service record to request a stop (sets stop_requested to true, sets state to "stopping", updates timestamps and message) and, if a service snapshot exists after the update, writes that snapshot via write_service_state.

        Parameters:
            service_name (str): The service to request stop for (defaults to "orchestrator").
        """
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """
            update service_state
            set stop_requested = true,
                state = 'stopping',
                updated_at = ?,
                last_heartbeat_at = ?,
                message = 'Stop requested by operator.'
            where service_name = ?
            """,
            [now, now, service_name],
        )
        state = self.get_service_state(service_name)
        if state is not None:
            write_service_state(self.settings, state)

    def clear_stop_request(self, service_name: str = "orchestrator") -> None:
        self.conn.execute(
            """
            update service_state
            set stop_requested = false
            where service_name = ?
            """,
            [service_name],
        )
        state = self.get_service_state(service_name)
        if state is not None:
            write_service_state(self.settings, state)

    def insert_service_event(
        self,
        *,
        service_name: str = "orchestrator",
        level: str,
        event_type: str,
        message: str,
        cycle_count: int | None = None,
        symbol: str | None = None,
    ) -> str:
        event_id = f"evt-{uuid4().hex[:12]}"
        created_at = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """
            insert into service_events (
                event_id, created_at, service_name, level, event_type, message, cycle_count, symbol
            )
            values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                event_id,
                created_at,
                service_name,
                level,
                event_type,
                message,
                cycle_count,
                symbol,
            ],
        )
        append_service_event(
            self.settings,
            ServiceEvent(
                event_id=event_id,
                created_at=created_at,
                level=level,  # type: ignore[arg-type]
                event_type=event_type,
                message=message,
                cycle_count=cycle_count,
                symbol=symbol,
            ),
        )
        return event_id

    def list_service_events(
        self, limit: int = 20, service_name: str = "orchestrator"
    ) -> list[ServiceEvent]:
        """
        Fetch recent service events for the given service, ordered newest first.

        Parameters:
            limit (int): Maximum number of events to return.
            service_name (str): Service name to filter events by.

        Returns:
            list[ServiceEvent]: List of service events for the service, ordered by created_at descending and limited by `limit`.
        """
        rows = self.conn.execute(
            """
            select event_id, created_at, level, event_type, message, cycle_count, symbol
            from service_events
            where service_name = ?
            order by created_at desc
            limit ?
            """,
            [service_name, limit],
        ).fetchall()
        events: list[ServiceEvent] = []
        for row in rows:
            events.append(
                ServiceEvent(
                    event_id=str(row[0]),
                    created_at=str(row[1]),
                    level=cast(ServiceEventLevel, str(row[2])),
                    event_type=str(row[3]),
                    message=str(row[4]),
                    cycle_count=int(row[5]) if row[5] is not None else None,
                    symbol=str(row[6]) if row[6] is not None else None,
                )
            )
        return events

    def get_account_snapshot(self) -> PortfolioSnapshot:
        row = self.conn.execute(
            """
            select cash, realized_pnl
            from account_state
            where account_id = 'paper'
            """
        ).fetchone()
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
        rows = self.conn.execute(
            """
            select symbol, quantity, average_price, market_price
            from positions
            where abs(quantity) > 0
            order by symbol
            """
        ).fetchall()
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
        Return all saved position plans ordered by symbol.

        Each entry is a PositionPlanSnapshot containing symbol, side, entry_price, stop_loss,
        take_profit, max_holding_bars, holding_bars, invalidation_logic, and updated_at.

        Returns:
            list[PositionPlanSnapshot]: Position plans ordered by symbol.
        """
        rows = self.conn.execute(
            """
            select symbol, side, entry_price, stop_loss, take_profit,
                   max_holding_bars, holding_bars, invalidation_logic, updated_at
            from position_plans
            order by symbol
            """
        ).fetchall()
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
