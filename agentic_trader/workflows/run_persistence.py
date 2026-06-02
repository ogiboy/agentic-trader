"""Persistence helpers for a completed one-shot workflow run."""

from __future__ import annotations

from uuid import uuid4

from agentic_trader.config import Settings
from agentic_trader.engine.broker import get_broker_adapter
from agentic_trader.execution.intent import build_execution_intent
from agentic_trader.schemas import RunArtifacts
from agentic_trader.storage.db import TradingDatabase


def persist_position_plan(*, settings: Settings, artifacts: RunArtifacts) -> None:
    db = TradingDatabase(settings)
    try:
        broker = get_broker_adapter(db=db, settings=settings)
        broker.record_position_plan(
            symbol=artifacts.snapshot.symbol,
            decision=artifacts.execution,
            strategy=artifacts.strategy,
            max_holding_bars=artifacts.risk.max_holding_bars,
        )
    finally:
        db.close()


def persist_run(*, settings: Settings, artifacts: RunArtifacts) -> str:
    db = TradingDatabase(settings)
    try:
        broker = get_broker_adapter(db=db, settings=settings)
        run_id = f"run-{uuid4().hex[:12]}"
        db.insert_run(run_id, artifacts)
        account = broker.get_account_state()
        intent = build_execution_intent(
            decision=artifacts.execution,
            settings=settings,
            run_id=run_id,
            reasoning_id="manager",
            trace_link=f"run:{run_id}/trace",
            invalidation_condition=artifacts.strategy.invalidation_logic,
            reference_equity=account.equity,
            adapter_name=broker.backend_name,
        )
        outcome = broker.place_order(intent)
        if outcome.order_id is None:
            raise RuntimeError("Broker adapter did not return an order id.")
        order_id = outcome.order_id
        db.record_execution_outcome(run_id=run_id, intent=intent, outcome=outcome)
        journal_status = _journal_status(
            approved=artifacts.execution.approved,
            side=artifacts.execution.side,
            order_has_fill=db.order_has_fill(order_id),
        )
        trade_id = db.create_trade_journal(
            run_id=run_id,
            order_id=order_id,
            artifacts=artifacts,
            journal_status=journal_status,
            notes=artifacts.review.summary,
        )
        db.persist_trade_context(
            trade_id=trade_id,
            run_id=run_id,
            artifacts=artifacts,
            execution_intent=intent,
            execution_outcome=outcome,
        )
        broker.record_position_plan(
            symbol=artifacts.snapshot.symbol,
            decision=artifacts.execution,
            strategy=artifacts.strategy,
            max_holding_bars=artifacts.risk.max_holding_bars,
        )
        db.record_account_mark(
            source="run_persisted",
            note=f"Run persisted for {artifacts.snapshot.symbol} with order {order_id}.",
            symbol=artifacts.snapshot.symbol,
        )
        return order_id
    finally:
        db.close()


def _journal_status(*, approved: bool, side: str, order_has_fill: bool) -> str:
    if not approved or side == "hold":
        return "rejected"
    if order_has_fill:
        return "open"
    return "no_fill"
