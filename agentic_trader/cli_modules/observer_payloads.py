from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from agentic_trader.config import Settings
from agentic_trader.market.calendar import infer_market_session
from agentic_trader.market.data import fetch_ohlcv
from agentic_trader.market.features import build_snapshot
from agentic_trader.market.news import fetch_news_brief
from agentic_trader.memory.retrieval import retrieve_similar_memories
from agentic_trader.runtime_feed import read_chat_history, read_service_state
from agentic_trader.runtime_status import RuntimeStatusView, build_runtime_status_view
from agentic_trader.schemas import (
    AgentStageTrace,
    CanonicalAnalysisSnapshot,
    InvestmentPreferences,
    RunRecord,
    RunReplay,
    RunReplayStage,
)
from agentic_trader.storage.db import TradingDatabase


class OpenDatabase(Protocol):
    def __call__(self, settings: Settings, *, read_only: bool = False) -> TradingDatabase:
        ...


RunRecordPayload = Callable[..., dict[str, object]]
ManagerNotes = Callable[..., list[str]]
ReadTextTail = Callable[[Path | None], list[str]]


def market_context_payload(
    settings: Settings, *, open_db: OpenDatabase
) -> dict[str, object]:
    try:
        db = open_db(settings, read_only=True)
        try:
            record = db.latest_run()
        finally:
            db.close()
        context_pack = (
            record.artifacts.snapshot.context_pack if record is not None else None
        )
        available = context_pack is not None
        error = None if available else "No persisted market context pack is available."
    except Exception as exc:
        context_pack = None
        available = False
        error = str(exc)
    return {
        "available": available,
        "error": error,
        "contextPack": (
            context_pack.model_dump(mode="json") if context_pack is not None else None
        ),
    }


def canonical_analysis_payload(
    settings: Settings, *, open_db: OpenDatabase
) -> dict[str, object]:
    try:
        db = open_db(settings, read_only=True)
        try:
            record = db.latest_run()
            canonical_snapshot = (
                record.artifacts.canonical_snapshot if record is not None else None
            )
            if canonical_snapshot is None:
                trade_context = db.latest_trade_context()
                canonical_snapshot = (
                    trade_context.canonical_snapshot
                    if trade_context is not None
                    else None
                )
        finally:
            db.close()
        available = canonical_snapshot is not None
        error = None if available else "No canonical analysis snapshot is available."
    except Exception as exc:
        canonical_snapshot = None
        available = False
        error = str(exc)
    return {
        "available": available,
        "error": error,
        "snapshot": (
            canonical_snapshot.model_dump(mode="json")
            if canonical_snapshot is not None
            else None
        ),
    }


def canonical_analysis_lines(
    canonical_snapshot: CanonicalAnalysisSnapshot | None,
) -> list[str]:
    if canonical_snapshot is None:
        return ["No canonical analysis snapshot is attached to this trade context."]
    source_lines = [
        f"{item.provider_type}:{item.source_name} role={item.source_role} freshness={item.freshness}"
        for item in canonical_snapshot.source_attributions
    ]
    return [
        f"Summary: {canonical_snapshot.summary or '-'}",
        f"Completeness: {canonical_snapshot.completeness_score:.2f}",
        f"Missing Sections: {', '.join(canonical_snapshot.missing_sections) or '-'}",
        (
            "Primary Sources: "
            f"market={canonical_snapshot.market.attribution.source_name} | "
            f"fundamental={canonical_snapshot.fundamental.attribution.source_name} | "
            f"macro={canonical_snapshot.macro.attribution.source_name}"
        ),
        (
            "Event Counts: "
            f"news={len(canonical_snapshot.news_events)} | "
            f"disclosures={len(canonical_snapshot.disclosures)}"
        ),
        "Sources:",
        *(source_lines or ["-"]),
    ]


def service_supervisor_payload(
    settings: Settings, *, read_text_tail: ReadTextTail
) -> dict[str, object]:
    state = read_service_state(settings)
    view = build_runtime_status_view(state)
    stdout_path = Path(state.stdout_log_path) if state and state.stdout_log_path else None
    stderr_path = Path(state.stderr_log_path) if state and state.stderr_log_path else None
    return {
        "runtime_state": view.runtime_state,
        "live_process": view.live_process,
        "is_stale": view.is_stale,
        "age_seconds": view.age_seconds,
        "status_message": view.status_message,
        "state": state.model_dump(mode="json") if state is not None else None,
        "stdout_tail": read_text_tail(stdout_path),
        "stderr_tail": read_text_tail(stderr_path),
    }


def runtime_status_payload(
    view: RuntimeStatusView, settings: Settings
) -> dict[str, object]:
    return {
        "runtime_mode": (
            view.state.runtime_mode if view.state is not None else settings.runtime_mode
        ),
        "runtime_state": view.runtime_state,
        "live_process": view.live_process,
        "is_stale": view.is_stale,
        "age_seconds": view.age_seconds,
        "status_message": view.status_message,
        "state": view.state.model_dump(mode="json") if view.state is not None else None,
    }


def default_symbol_from_preferences(preferences: InvestmentPreferences) -> str:
    if "BIST" in preferences.exchanges or "TR" in preferences.regions:
        return "THYAO.IS"
    if (
        "NASDAQ" in preferences.exchanges
        or "NYSE" in preferences.exchanges
        or "US" in preferences.regions
    ):
        return "AAPL"
    return "BTC-USD"


def calendar_payload(
    settings: Settings, *, open_db: OpenDatabase, symbol: str | None = None
) -> dict[str, object]:
    try:
        preferences, record = _preferences_and_latest_run(settings, open_db=open_db)
        resolved_symbol = symbol or (
            record.symbol
            if record is not None
            else default_symbol_from_preferences(preferences)
        )
        session = infer_market_session(symbol=resolved_symbol, preferences=preferences)
        available = True
        error = None
    except Exception as exc:
        session = None
        available = False
        error = str(exc)
    return {
        "available": available,
        "error": error,
        "session": session.model_dump(mode="json") if session is not None else None,
    }


def news_payload(
    settings: Settings, *, open_db: OpenDatabase, symbol: str | None = None
) -> dict[str, object]:
    try:
        preferences, record = _preferences_and_latest_run(settings, open_db=open_db)
        resolved_symbol = symbol or (
            record.symbol
            if record is not None
            else default_symbol_from_preferences(preferences)
        )
        headlines = fetch_news_brief(resolved_symbol, settings)
        available = True
        error = None
    except Exception as exc:
        resolved_symbol = symbol
        headlines = []
        available = False
        error = str(exc)
    return {
        "available": available,
        "error": error,
        "mode": settings.news_mode,
        "symbol": resolved_symbol,
        "headlines": [item.model_dump(mode="json") for item in headlines],
    }


def _preferences_and_latest_run(
    settings: Settings, *, open_db: OpenDatabase
) -> tuple[InvestmentPreferences, RunRecord | None]:
    db = open_db(settings, read_only=True)
    try:
        return db.load_preferences(), db.latest_run()
    finally:
        db.close()


def market_cache_payload(settings: Settings) -> dict[str, object]:
    settings.ensure_directories()
    cache_dir = settings.market_data_cache_dir
    entries: list[dict[str, object]] = []
    for path in sorted(
        cache_dir.glob("*.csv"), key=lambda item: item.stat().st_mtime, reverse=True
    ):
        entries.append(
            {
                "filename": path.name,
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "modified_at": path.stat().st_mtime,
            }
        )
    return {
        "mode": settings.market_data_mode,
        "cache_dir": str(cache_dir),
        "count": len(entries),
        "entries": entries,
    }


def memory_explorer_payload(
    settings: Settings,
    *,
    open_db: OpenDatabase,
    symbol: str | None = None,
    interval: str | None = None,
    lookback: str = "180d",
    limit: int = 5,
    use_latest_run: bool = False,
) -> dict[str, object]:
    try:
        db = open_db(settings, read_only=True)
        try:
            snapshot = None
            resolved_symbol = symbol
            resolved_interval = interval
            if use_latest_run or resolved_symbol is None:
                record = db.latest_run()
                if record is not None:
                    snapshot = record.artifacts.snapshot
                    resolved_symbol = snapshot.symbol
                    resolved_interval = snapshot.interval
            if snapshot is None:
                if resolved_symbol is None or resolved_interval is None:
                    raise ValueError(
                        "A symbol and interval are required when no latest run snapshot is available."
                    )
                frame = fetch_ohlcv(
                    resolved_symbol,
                    interval=resolved_interval,
                    lookback=lookback,
                    settings=settings,
                )
                snapshot = build_snapshot(
                    frame,
                    symbol=resolved_symbol,
                    interval=resolved_interval,
                    lookback=lookback,
                )
            matches = retrieve_similar_memories(db, snapshot, limit=limit)
        finally:
            db.close()
        available = True
        error = None
    except Exception as exc:
        snapshot = None
        matches = []
        available = False
        error = str(exc)

    return {
        "available": available,
        "error": error,
        "snapshot": snapshot.model_dump(mode="json") if snapshot is not None else None,
        "matches": [match.model_dump(mode="json") for match in matches],
    }


def retrieval_inspection_payload(
    settings: Settings,
    *,
    run_id: str | None = None,
    run_record_payload: RunRecordPayload,
) -> dict[str, object]:
    record_payload = run_record_payload(settings, run_id=run_id)
    record_json = record_payload["record"]
    if record_payload["available"] is False or record_json is None:
        return {
            "available": bool(record_payload["available"]),
            "error": record_payload["error"],
            "run_id": (
                record_json["run_id"]
                if isinstance(record_json, dict) and "run_id" in record_json
                else None
            ),
            "stages": [],
        }

    record = RunRecord.model_validate(record_json)
    stages: list[dict[str, object]] = []
    for trace in record.artifacts.agent_traces:
        context = json.loads(trace.context_json)
        stages.append(
            {
                "role": trace.role,
                "model_name": trace.model_name,
                "used_fallback": trace.used_fallback,
                "retrieved_memories": context.get("retrieved_memories", []),
                "retrieval_explanations": context.get("retrieval_explanations", []),
                "memory_notes": context.get("memory_notes", []),
                "shared_memory_bus": context.get("shared_memory_bus", []),
                "recent_runs": context.get("recent_runs", []),
                "tool_outputs": context.get("tool_outputs", []),
            }
        )

    return {
        "available": True,
        "error": None,
        "run_id": record.run_id,
        "symbol": record.symbol,
        "interval": record.interval,
        "stages": stages,
    }


def chat_history_payload(settings: Settings, *, limit: int = 12) -> dict[str, object]:
    try:
        entries = read_chat_history(settings, limit=limit)
        available = True
        error = None
    except Exception as exc:
        entries = []
        available = False
        error = str(exc)
    return {
        "available": available,
        "error": error,
        "entries": [entry.model_dump(mode="json") for entry in entries],
    }


def run_replay_payload(
    settings: Settings,
    *,
    run_id: str | None = None,
    run_record_payload: RunRecordPayload,
    manager_override_notes: ManagerNotes,
    manager_resolution_notes: ManagerNotes,
) -> dict[str, object]:
    record_payload = run_record_payload(settings, run_id=run_id)
    record_json = record_payload["record"]
    if record_payload["available"] is False or record_json is None:
        return {
            "available": bool(record_payload["available"]),
            "error": record_payload["error"],
            "replay": None,
        }

    record = RunRecord.model_validate(record_json)
    stages = [_replay_stage_from_trace(trace) for trace in record.artifacts.agent_traces]
    replay = RunReplay(
        run_id=record.run_id,
        created_at=record.created_at,
        symbol=record.symbol,
        interval=record.interval,
        approved=record.approved,
        final_side=record.artifacts.execution.side,
        final_rationale=record.artifacts.execution.rationale,
        snapshot=record.artifacts.snapshot,
        consensus=record.artifacts.consensus,
        manager_override_notes=manager_override_notes(record.artifacts),
        manager_conflicts=record.artifacts.manager.conflicts,
        manager_resolution_notes=manager_resolution_notes(record.artifacts),
        stages=stages,
    )
    return {
        "available": True,
        "error": None,
        "replay": replay.model_dump(mode="json"),
    }


def _replay_stage_from_trace(trace: AgentStageTrace) -> RunReplayStage:
    context = json.loads(trace.context_json)
    try:
        output: dict[str, object] | str = json.loads(trace.output_json)
    except json.JSONDecodeError:
        output = trace.output_json
    return RunReplayStage(
        role=trace.role,
        model_name=trace.model_name,
        used_fallback=trace.used_fallback,
        market_session=context.get("market_session"),
        retrieved_memories=context.get("retrieved_memories", []),
        memory_notes=context.get("memory_notes", []),
        shared_memory_bus=context.get("shared_memory_bus", []),
        recent_runs=context.get("recent_runs", []),
        tool_outputs=context.get("tool_outputs", []),
        upstream_context=context.get("upstream_context", {}),
        output=output,
    )
