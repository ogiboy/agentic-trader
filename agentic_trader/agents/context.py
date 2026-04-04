from typing import Mapping

from pydantic import BaseModel

from agentic_trader.config import Settings
from agentic_trader.market.calendar import infer_market_session
from agentic_trader.memory.retrieval import retrieve_similar_memories
from agentic_trader.schemas import AgentContext, AgentRole, MarketSnapshot
from agentic_trader.storage.db import TradingDatabase


def _summarize_recent_runs(db: TradingDatabase, *, limit: int = 5) -> list[str]:
    return [
        f"{created_at} | {symbol} {interval} | approved={approved} | {run_id}"
        for run_id, created_at, symbol, interval, approved in db.list_recent_runs(limit=limit)
    ]


def _summarize_trade_memory(db: TradingDatabase, *, limit: int = 5) -> list[str]:
    entries = db.list_trade_journal(limit=limit)
    notes: list[str] = []
    for entry in entries:
        exit_fragment = f" -> {entry.exit_reason}" if entry.exit_reason else ""
        pnl_fragment = f" | pnl={entry.realized_pnl:.2f}" if entry.realized_pnl is not None else ""
        notes.append(
            f"{entry.symbol} {entry.planned_side} {entry.journal_status}{exit_fragment} | entry={entry.entry_price:.4f}{pnl_fragment}"
        )
    return notes


def _serialize_upstream(upstream_context: Mapping[str, BaseModel | str] | None) -> dict[str, str]:
    if not upstream_context:
        return {}
    rendered: dict[str, str] = {}
    for key, value in upstream_context.items():
        if isinstance(value, BaseModel):
            rendered[key] = value.model_dump_json(indent=2)
        else:
            rendered[key] = str(value)
    return rendered


def _summarize_retrieved_memories(db: TradingDatabase, snapshot: MarketSnapshot, *, limit: int = 3) -> list[str]:
    matches = retrieve_similar_memories(db, snapshot, limit=limit)
    return [
        f"{match.created_at} | {match.symbol} | score={match.similarity_score:.2f} | regime={match.regime} | strategy={match.strategy_family} | bias={match.manager_bias}"
        for match in matches
    ]


def build_agent_context(
    *,
    role: AgentRole,
    settings: Settings,
    db: TradingDatabase,
    snapshot: MarketSnapshot,
    tool_outputs: list[str] | None = None,
    upstream_context: Mapping[str, BaseModel | str] | None = None,
) -> AgentContext:
    preferences = db.load_preferences()
    market_session = infer_market_session(
        symbol=snapshot.symbol,
        preferences=preferences,
    )
    rendered_tool_outputs = [
        f"market_session: venue={market_session.venue} state={market_session.session_state} tradable_now={market_session.tradable_now} note={market_session.note}"
    ]
    rendered_tool_outputs.extend(list(tool_outputs or []))
    return AgentContext(
        role=role,
        model_name=settings.model_for_role(role),
        snapshot=snapshot,
        preferences=preferences,
        portfolio=db.get_account_snapshot(),
        market_session=market_session,
        service_state=db.get_service_state(),
        recent_runs=_summarize_recent_runs(db),
        memory_notes=_summarize_trade_memory(db),
        retrieved_memories=_summarize_retrieved_memories(db, snapshot),
        tool_outputs=rendered_tool_outputs,
        upstream_context=_serialize_upstream(upstream_context),
    )


def render_agent_context(context: AgentContext, *, task: str) -> str:
    sections = [
        f"Role: {context.role}",
        f"Routed Model: {context.model_name}",
        "Task:",
        task,
        "",
        "Market Snapshot:",
        context.snapshot.model_dump_json(indent=2),
        "",
        "Operator Preferences:",
        context.preferences.model_dump_json(indent=2),
        "",
        "Portfolio Snapshot:",
        context.portfolio.model_dump_json(indent=2),
    ]

    if context.market_session is not None:
        sections.extend(
            [
                "",
                "Market Session:",
                context.market_session.model_dump_json(indent=2),
            ]
        )

    if context.service_state is not None:
        sections.extend(
            [
                "",
                "Runtime State:",
                context.service_state.model_dump_json(indent=2),
            ]
        )
    if context.recent_runs:
        sections.extend(["", "Recent Runs:", "\n".join(f"- {line}" for line in context.recent_runs)])
    if context.memory_notes:
        sections.extend(["", "Trade Memory:", "\n".join(f"- {line}" for line in context.memory_notes)])
    if context.retrieved_memories:
        sections.extend(["", "Retrieved Similar Memories:", "\n".join(f"- {line}" for line in context.retrieved_memories)])
    if context.tool_outputs:
        sections.extend(["", "Tool Outputs:", "\n".join(f"- {line}" for line in context.tool_outputs)])
    if context.upstream_context:
        rendered = []
        for key, value in context.upstream_context.items():
            rendered.append(f"{key}:\n{value}")
        sections.extend(["", "Upstream Context:", "\n\n".join(rendered)])

    return "\n".join(sections).strip()
