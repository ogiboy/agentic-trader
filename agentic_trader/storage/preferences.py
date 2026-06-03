"""Investment preference persistence helpers."""

from __future__ import annotations

from datetime import datetime, timezone

import duckdb

from agentic_trader.schemas import InvestmentPreferences


def ensure_default_preferences(conn: duckdb.DuckDBPyConnection) -> None:
    existing = conn.execute(
        "select count(*) from preferences where profile_id = 'default'"
    ).fetchone()
    if existing and int(existing[0]) == 0:
        save_preferences(conn, InvestmentPreferences())


def save_preferences(
    conn: duckdb.DuckDBPyConnection,
    preferences: InvestmentPreferences,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        insert into preferences (profile_id, updated_at, payload_json)
        values ('default', ?, ?)
        on conflict(profile_id) do update set
            updated_at = excluded.updated_at,
            payload_json = excluded.payload_json
        """,
        [now, preferences.model_dump_json(indent=2)],
    )


def load_preferences(conn: duckdb.DuckDBPyConnection) -> InvestmentPreferences:
    row = conn.execute("""
        select payload_json
        from preferences
        where profile_id = 'default'
        """).fetchone()
    if row is None:
        preferences = InvestmentPreferences()
        save_preferences(conn, preferences)
        return preferences
    return InvestmentPreferences.model_validate_json(str(row[0]))
