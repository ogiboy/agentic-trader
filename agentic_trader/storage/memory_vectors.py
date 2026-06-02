"""Memory vector persistence helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import duckdb

from agentic_trader.memory.embeddings import (
    build_memory_document,
    embed_artifacts,
    embedding_metadata,
)
from agentic_trader.memory.policy import MemoryActor, assert_memory_write_allowed
from agentic_trader.schemas import RunArtifacts


def upsert_memory_vector(
    conn: duckdb.DuckDBPyConnection,
    run_id: str,
    artifacts: RunArtifacts,
    *,
    created_at: str | None = None,
    actor: MemoryActor = "system_runtime",
) -> None:
    assert_memory_write_allowed("trade_memory", actor)
    metadata = embedding_metadata()
    conn.execute(
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
    conn: duckdb.DuckDBPyConnection,
    limit: int = 200,
) -> list[tuple[str, str, str, list[float], str]]:
    rows = conn.execute(
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
