"""Run history persistence helpers."""

from __future__ import annotations

from datetime import datetime, timezone

import duckdb

from agentic_trader.memory.policy import MemoryActor
from agentic_trader.schemas import RunArtifacts, RunRecord
from agentic_trader.storage import memory_vectors


def insert_run(
    conn: duckdb.DuckDBPyConnection,
    run_id: str,
    artifacts: RunArtifacts,
) -> None:
    created_at = datetime.now(timezone.utc).isoformat()
    conn.execute(
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
    memory_vectors.upsert_memory_vector(
        conn,
        run_id,
        artifacts,
        created_at=created_at,
        actor="system_runtime",
    )


def list_recent_runs(
    conn: duckdb.DuckDBPyConnection,
    limit: int = 10,
) -> list[tuple[str, str, str, str, bool]]:
    rows = conn.execute(
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


def get_run(
    conn: duckdb.DuckDBPyConnection,
    run_id: str,
) -> RunRecord | None:
    row = conn.execute(
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


def latest_run(conn: duckdb.DuckDBPyConnection) -> RunRecord | None:
    row = conn.execute("""
        select run_id
        from runs
        order by created_at desc
        limit 1
        """).fetchone()
    if row is None:
        return None
    return get_run(conn, str(row[0]))


def list_run_records(
    conn: duckdb.DuckDBPyConnection,
    limit: int = 200,
) -> list[RunRecord]:
    rows = conn.execute(
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
        record = get_run(conn, str(row[0]))
        if record is not None:
            records.append(record)
    return records


def upsert_memory_vector(
    conn: duckdb.DuckDBPyConnection,
    run_id: str,
    artifacts: RunArtifacts,
    *,
    created_at: str | None = None,
    actor: MemoryActor = "system_runtime",
) -> None:
    memory_vectors.upsert_memory_vector(
        conn,
        run_id,
        artifacts,
        created_at=created_at,
        actor=actor,
    )
