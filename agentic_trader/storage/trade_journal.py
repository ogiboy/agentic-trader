import json
from datetime import datetime, timezone
from typing import cast
from uuid import uuid4

import duckdb

from agentic_trader.execution.intent import ExecutionIntent, ExecutionOutcome
from agentic_trader.schemas import (
    CoordinatorFocus,
    ExecutionSide,
    JournalStatus,
    RunArtifacts,
    TradeContextRecord,
    TradeJournalEntry,
    TradeProposalRecord,
)
from agentic_trader.storage import trade_contexts as _trade_contexts


def order_has_fill(conn: duckdb.DuckDBPyConnection, order_id: str) -> bool:
    row = conn.execute(
        """
        select count(*)
        from fills
        where order_id = ?
        """,
        [order_id],
    ).fetchone()
    return bool(row and int(row[0]) > 0)


def order_realized_pnl(conn: duckdb.DuckDBPyConnection, order_id: str) -> float:
    row = conn.execute(
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
    conn: duckdb.DuckDBPyConnection,
    *,
    run_id: str | None,
    order_id: str,
    artifacts: RunArtifacts,
    journal_status: str,
    notes: str = "",
) -> str:
    trade_id = f"trade-{uuid4().hex[:12]}"
    conn.execute(
        """
        insert into trade_journal (
            trade_id, opened_at, symbol, run_id, entry_order_id, planned_side,
            approved, journal_status, entry_price, stop_loss, take_profit,
            position_size_pct, confidence, coordinator_focus, strategy_family,
            manager_bias, review_summary, notes
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(entry_order_id) do update set
            journal_status = excluded.journal_status,
            entry_price = excluded.entry_price,
            stop_loss = excluded.stop_loss,
            take_profit = excluded.take_profit,
            position_size_pct = excluded.position_size_pct,
            confidence = excluded.confidence,
            coordinator_focus = excluded.coordinator_focus,
            strategy_family = excluded.strategy_family,
            manager_bias = excluded.manager_bias,
            review_summary = excluded.review_summary,
            notes = excluded.notes
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
    stored = conn.execute(
        """
        select trade_id
        from trade_journal
        where entry_order_id = ?
        """,
        [order_id],
    ).fetchone()
    return str(stored[0]) if stored is not None else trade_id


def create_trade_journal_from_proposal(
    conn: duckdb.DuckDBPyConnection,
    *,
    proposal: TradeProposalRecord,
    outcome: ExecutionOutcome,
) -> str | None:
    if outcome.order_id is None:
        return None
    journal_status = _proposal_journal_status(outcome)
    entry_price = outcome.average_fill_price or proposal.reference_price
    stop_loss = proposal.stop_loss or proposal.reference_price
    take_profit = proposal.take_profit or proposal.reference_price
    note_parts = [
        f"proposal_id={proposal.proposal_id}",
        f"source={proposal.source}",
        f"outcome_status={outcome.status}",
    ]
    if proposal.review_notes:
        note_parts.append(f"review_notes={proposal.review_notes}")
    notes = " | ".join(note_parts)
    trade_id = f"trade-{uuid4().hex[:12]}"
    conn.execute(
        """
        insert into trade_journal (
            trade_id, opened_at, symbol, run_id, entry_order_id, planned_side,
            approved, journal_status, entry_price, stop_loss, take_profit,
            position_size_pct, confidence, coordinator_focus, strategy_family,
            manager_bias, review_summary, notes
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(entry_order_id) do update set
            journal_status = excluded.journal_status,
            entry_price = excluded.entry_price,
            stop_loss = excluded.stop_loss,
            take_profit = excluded.take_profit,
            confidence = excluded.confidence,
            review_summary = excluded.review_summary,
            notes = excluded.notes
        """,
        [
            trade_id,
            datetime.now(timezone.utc).isoformat(),
            proposal.symbol,
            None,
            outcome.order_id,
            proposal.side,
            True,
            journal_status,
            entry_price,
            stop_loss,
            take_profit,
            0.0,
            proposal.confidence,
            "capital_preservation",
            "manual_proposal",
            proposal.side,
            proposal.thesis,
            notes,
        ],
    )
    stored = conn.execute(
        """
        select trade_id
        from trade_journal
        where entry_order_id = ?
        """,
        [outcome.order_id],
    ).fetchone()
    return str(stored[0]) if stored is not None else trade_id


def _proposal_journal_status(outcome: ExecutionOutcome) -> JournalStatus:
    if outcome.status in {"accepted", "filled", "partially_filled"}:
        return "open"
    if outcome.status in {"cancelled", "no_fill"}:
        return "no_fill"
    return "rejected"


def persist_trade_context(
    conn: duckdb.DuckDBPyConnection,
    *,
    trade_id: str,
    run_id: str | None,
    artifacts: RunArtifacts,
    execution_intent: ExecutionIntent | None = None,
    execution_outcome: ExecutionOutcome | None = None,
) -> None:
    trace_summaries = _trade_contexts.summarize_trace_contexts(artifacts.agent_traces)
    record = _trade_contexts.trade_context_record(
        trade_id=trade_id,
        run_id=run_id,
        artifacts=artifacts,
        trace_summaries=trace_summaries,
        execution_context=_trade_contexts.execution_context_payload(
            execution_intent=execution_intent,
            execution_outcome=execution_outcome,
        ),
    )
    conn.execute(
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
    conn: duckdb.DuckDBPyConnection,
    *,
    run_id: str | None,
    intent: ExecutionIntent,
    outcome: ExecutionOutcome,
) -> None:
    conn.execute(
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


def latest_execution_record(
    conn: duckdb.DuckDBPyConnection,
) -> dict[str, object] | None:
    row = conn.execute("""
        select intent_id, created_at, run_id, order_id, symbol, execution_backend,
               adapter_name, status, rejection_reason, intent_json, outcome_json
        from execution_records
        order by created_at desc
        limit 1
        """).fetchone()
    return _execution_record_from_row(row)


def get_execution_record(
    conn: duckdb.DuckDBPyConnection,
    intent_id: str,
) -> dict[str, object] | None:
    row = conn.execute(
        """
        select intent_id, created_at, run_id, order_id, symbol, execution_backend,
               adapter_name, status, rejection_reason, intent_json, outcome_json
        from execution_records
        where intent_id = ?
        """,
        [intent_id],
    ).fetchone()
    return _execution_record_from_row(row)


def _execution_record_from_row(row: object | None) -> dict[str, object] | None:
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
    conn: duckdb.DuckDBPyConnection,
    *,
    symbol: str,
    exit_order_id: str,
    exit_reason: str,
    exit_price: float,
    realized_pnl: float,
    notes: str = "",
) -> None:
    row = conn.execute(
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
    conn.execute(
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


def list_trade_journal(
    conn: duckdb.DuckDBPyConnection,
    limit: int = 20,
) -> list[TradeJournalEntry]:
    rows = conn.execute(
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


def get_trade_context(
    conn: duckdb.DuckDBPyConnection,
    trade_id: str,
) -> TradeContextRecord | None:
    row = conn.execute(
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


def latest_trade_context(conn: duckdb.DuckDBPyConnection) -> TradeContextRecord | None:
    row = conn.execute("""
        select payload_json
        from trade_contexts
        order by created_at desc
        limit 1
        """).fetchone()
    if row is None:
        return None
    return TradeContextRecord.model_validate_json(str(row[0]))
