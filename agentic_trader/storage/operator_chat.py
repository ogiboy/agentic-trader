"""Operator chat history persistence helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import cast
from uuid import uuid4

import duckdb

from agentic_trader.memory.policy import MemoryActor, assert_memory_write_allowed
from agentic_trader.schemas import ChatHistoryEntry, ChatPersona


def insert_chat_history(
    conn: duckdb.DuckDBPyConnection,
    *,
    persona: str,
    user_message: str,
    response_text: str,
    actor: MemoryActor = "operator_chat",
) -> str:
    assert_memory_write_allowed("chat_memory", actor)
    entry_id = f"chat-{uuid4().hex[:12]}"
    conn.execute(
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


def list_chat_history(
    conn: duckdb.DuckDBPyConnection,
    limit: int = 20,
) -> list[ChatHistoryEntry]:
    rows = conn.execute(
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
