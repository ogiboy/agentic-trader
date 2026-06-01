from collections.abc import Mapping
from datetime import datetime, timezone

import duckdb


CORE_TABLE_SQL: tuple[str, ...] = (
    """
    create table if not exists runs (
        run_id varchar primary key,
        created_at varchar not null,
        symbol varchar not null,
        interval varchar not null,
        approved boolean not null,
        payload_json varchar not null
    )
    """,
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
    """,
    """
    create table if not exists account_state (
        account_id varchar primary key,
        updated_at varchar not null,
        cash double not null,
        realized_pnl double not null
    )
    """,
    """
    create table if not exists positions (
        symbol varchar primary key,
        quantity double not null,
        average_price double not null,
        market_price double not null,
        updated_at varchar not null
    )
    """,
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
    """,
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
    """,
    """
    create table if not exists preferences (
        profile_id varchar primary key,
        updated_at varchar not null,
        payload_json varchar not null
    )
    """,
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
    """,
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
    """,
    """
    create table if not exists trade_contexts (
        trade_id varchar primary key,
        created_at varchar not null,
        run_id varchar,
        symbol varchar not null,
        payload_json varchar not null
    )
    """,
)


EXECUTION_TABLE_SQL: tuple[str, ...] = (
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
    """,
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
        execution_outcome_status varchar,
        limit_price double
    )
    """,
    """
    create table if not exists proposal_candidates (
        candidate_id varchar primary key,
        created_at varchar not null,
        updated_at varchar not null,
        symbol varchar not null,
        preset varchar not null,
        signal varchar not null,
        side varchar,
        score double not null,
        reference_price double not null,
        confidence double not null,
        quantity double,
        notional double,
        thesis varchar not null,
        stop_loss double,
        take_profit double,
        invalidation_condition varchar,
        source varchar not null,
        status varchar not null,
        materiality varchar not null,
        freshness varchar not null,
        liquidity varchar not null,
        spread_pct double not null,
        risk_notes varchar not null,
        evidence_json varchar not null,
        proposal_id varchar
    )
    """,
)


SERVICE_TABLE_SQL: tuple[str, ...] = (
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
    """,
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
    """,
    """
    create table if not exists operator_chat_history (
        entry_id varchar primary key,
        created_at varchar not null,
        persona varchar not null,
        user_message varchar not null,
        response_text varchar not null
    )
    """,
)


MEMORY_TABLE_SQL: tuple[str, ...] = (
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
    """,
)


SERVICE_STATE_COLUMN_MIGRATIONS: Mapping[str, str] = {
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
}


MEMORY_VECTOR_COLUMN_MIGRATIONS: Mapping[str, str] = {
    "embedding_provider": (
        "alter table memory_vectors add column embedding_provider varchar "
        "default 'local_hashing'"
    ),
    "embedding_model": (
        "alter table memory_vectors add column embedding_model varchar "
        "default 'agentic-hash-v1'"
    ),
    "embedding_version": (
        "alter table memory_vectors add column embedding_version varchar default '1'"
    ),
    "embedding_dimensions": (
        "alter table memory_vectors add column embedding_dimensions integer default 64"
    ),
}


TRADE_PROPOSAL_COLUMN_MIGRATIONS: Mapping[str, str] = {
    "limit_price": "alter table trade_proposals add column limit_price double",
}


def table_exists(conn: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    row = conn.execute(
        """
        select count(*)
        from information_schema.tables
        where table_name = ?
        """,
        [table_name],
    ).fetchone()
    return row is not None and int(row[0]) > 0


def column_names(conn: duckdb.DuckDBPyConnection, table_name: str) -> set[str]:
    return {
        str(row[1])
        for row in conn.execute(f"pragma table_info('{table_name}')").fetchall()
    }


def add_missing_columns(
    conn: duckdb.DuckDBPyConnection,
    table_name: str,
    column_statements: Mapping[str, str],
) -> None:
    existing_columns = column_names(conn, table_name)
    for column_name, statement in column_statements.items():
        if column_name not in existing_columns:
            conn.execute(statement)


def create_core_tables(conn: duckdb.DuckDBPyConnection) -> None:
    for statement in CORE_TABLE_SQL:
        conn.execute(statement)


def create_execution_tables(conn: duckdb.DuckDBPyConnection) -> None:
    for statement in EXECUTION_TABLE_SQL:
        conn.execute(statement)


def create_service_tables(conn: duckdb.DuckDBPyConnection) -> None:
    for statement in SERVICE_TABLE_SQL:
        conn.execute(statement)


def create_memory_tables(conn: duckdb.DuckDBPyConnection) -> None:
    for statement in MEMORY_TABLE_SQL:
        conn.execute(statement)


def migrate_service_state_columns(conn: duckdb.DuckDBPyConnection) -> None:
    add_missing_columns(conn, "service_state", SERVICE_STATE_COLUMN_MIGRATIONS)


def migrate_memory_vector_columns(conn: duckdb.DuckDBPyConnection) -> None:
    add_missing_columns(conn, "memory_vectors", MEMORY_VECTOR_COLUMN_MIGRATIONS)


def migrate_trade_proposal_columns(conn: duckdb.DuckDBPyConnection) -> None:
    add_missing_columns(conn, "trade_proposals", TRADE_PROPOSAL_COLUMN_MIGRATIONS)


def migrate_trade_journal_constraints(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("""
        delete from trade_journal
        where trade_id in (
            select trade_id
            from (
                select
                    trade_id,
                    row_number() over (
                        partition by entry_order_id
                        order by opened_at desc, trade_id desc
                    ) as duplicate_rank
                from trade_journal
            )
            where duplicate_rank > 1
        )
        """)
    conn.execute("""
        create unique index if not exists trade_journal_entry_order_id_idx
        on trade_journal(entry_order_id)
        """)


def ensure_default_account(
    conn: duckdb.DuckDBPyConnection, *, default_cash: float
) -> None:
    existing = conn.execute(
        "select count(*) from account_state where account_id = 'paper'"
    ).fetchone()
    if existing and int(existing[0]) == 0:
        conn.execute(
            """
            insert into account_state (account_id, updated_at, cash, realized_pnl)
            values ('paper', ?, ?, 0)
            """,
            [
                datetime.now(timezone.utc).isoformat(),
                default_cash,
            ],
        )
