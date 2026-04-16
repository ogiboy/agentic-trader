from typing import Mapping

from pydantic import BaseModel

from agentic_trader.agents.calibration import build_confidence_calibration
from agentic_trader.config import Settings
from agentic_trader.market.calendar import infer_market_session
from agentic_trader.memory.retrieval import retrieve_similar_memories
from agentic_trader.market.news import fetch_news_brief
from agentic_trader.schemas import (
    AgentContext,
    AgentRole,
    CanonicalAnalysisSnapshot,
    DecisionFeatureBundle,
    MarketSnapshot,
    NewsSignal,
    SharedMemoryEntry,
)
from agentic_trader.storage.db import TradingDatabase


def _summarize_recent_runs(db: TradingDatabase, *, limit: int = 5) -> list[str]:
    return [
        f"{created_at} | {symbol} {interval} | approved={approved} | {run_id}"
        for run_id, created_at, symbol, interval, approved in db.list_recent_runs(
            limit=limit
        )
    ]


def _summarize_trade_memory(db: TradingDatabase, *, limit: int = 5) -> list[str]:
    entries = db.list_trade_journal(limit=limit)
    notes: list[str] = []
    for entry in entries:
        exit_fragment = f" -> {entry.exit_reason}" if entry.exit_reason else ""
        pnl_fragment = (
            f" | pnl={entry.realized_pnl:.2f}" if entry.realized_pnl is not None else ""
        )
        notes.append(
            f"{entry.symbol} {entry.planned_side} {entry.journal_status}{exit_fragment} | entry={entry.entry_price:.4f}{pnl_fragment}"
        )
    return notes


def _serialize_upstream(
    upstream_context: Mapping[str, BaseModel | str] | None,
) -> dict[str, str]:
    if not upstream_context:
        return {}
    rendered: dict[str, str] = {}
    for key, value in upstream_context.items():
        if isinstance(value, BaseModel):
            rendered[key] = value.model_dump_json(indent=2)
        else:
            rendered[key] = str(value)
    return rendered


def _summarize_retrieved_memories(
    db: TradingDatabase, snapshot: MarketSnapshot, *, limit: int = 3
) -> list[str]:
    matches = retrieve_similar_memories(db, snapshot, limit=limit)
    return [
        f"{match.created_at} | {match.symbol} | score={match.similarity_score:.2f} | regime={match.regime} | strategy={match.strategy_family} | bias={match.manager_bias}"
        for match in matches
    ]


def _render_canonical_snapshot_summary(context: AgentContext) -> str:
    """Render canonical provider context compactly so prompts stay focused."""
    canonical = context.canonical_snapshot
    if canonical is None:
        return "No canonical provider aggregation snapshot is attached."
    source_lines = [
        (
            f"- {item.provider_type}:{item.source_name} "
            f"role={item.source_role} freshness={item.freshness} "
            f"completeness={item.completeness:.2f}"
        )
        for item in canonical.source_attributions[:8]
    ]
    return "\n".join(
        [
            f"Summary: {canonical.summary}",
            f"Completeness: {canonical.completeness_score:.2f}",
            f"Missing sections: {', '.join(canonical.missing_sections) or 'none'}",
            (
                "Market: "
                f"rows={canonical.market.rows} "
                f"window={canonical.market.window_start or '-'}..{canonical.market.window_end or '-'} "
                f"last_close={canonical.market.last_close}"
            ),
            (
                "Fundamental: "
                f"source={canonical.fundamental.attribution.source_name} "
                f"missing={','.join(canonical.fundamental.missing_fields) or 'none'}"
            ),
            (
                "Macro: "
                f"source={canonical.macro.attribution.source_name} "
                f"fx_risk={canonical.macro.fx_risk} "
                f"missing={','.join(canonical.macro.missing_fields) or 'none'}"
            ),
            f"News events: {len(canonical.news_events)}",
            f"Disclosure events: {len(canonical.disclosures)}",
            "Sources:",
            "\n".join(source_lines) if source_lines else "- none",
        ]
    )


def _render_decision_feature_summary(context: AgentContext) -> str:
    """Render the decision feature bundle as a compact prompt-facing summary."""
    features = context.decision_features
    if features is None:
        return "No decision feature bundle is attached."
    technical = features.technical
    fundamental = features.fundamental
    macro = features.macro
    return "\n".join(
        [
            (
                "Symbol: "
                f"{features.symbol_identity.symbol} "
                f"region={features.symbol_identity.region} "
                f"exchange={features.symbol_identity.exchange or '-'} "
                f"currency={features.symbol_identity.currency}"
            ),
            (
                "Technical: "
                f"trend={technical.trend_classification} "
                f"volatility_20={technical.volatility_20} "
                f"support={technical.support} resistance={technical.resistance} "
                f"returns={technical.returns_by_window}"
            ),
            f"Technical summary: {technical.context_summary}",
            (
                "Fundamental: "
                f"fx_exposure={fundamental.fx_exposure} "
                f"flags={','.join(fundamental.quality_flags) or 'none'}"
            ),
            f"Fundamental summary: {fundamental.summary}",
            (
                "Macro: "
                f"region={macro.region} currency={macro.currency} "
                f"rates={macro.rates_bias} inflation={macro.inflation_bias} "
                f"fx_risk={macro.fx_risk} news_count={len(macro.news_signals)}"
            ),
            f"Macro summary: {macro.summary}",
        ]
    )


def build_agent_context(
    *,
    role: AgentRole,
    settings: Settings,
    db: TradingDatabase,
    snapshot: MarketSnapshot,
    canonical_snapshot: CanonicalAnalysisSnapshot | None = None,
    decision_features: DecisionFeatureBundle | None = None,
    news_items: list[NewsSignal] | None = None,
    memory_enabled: bool = True,
    tool_outputs: list[str] | None = None,
    upstream_context: Mapping[str, BaseModel | str] | None = None,
    shared_memory_bus: list[SharedMemoryEntry] | None = None,
) -> AgentContext:
    """Build the complete context bundle passed to one agent stage."""
    preferences = db.load_preferences()
    strategy_family = None
    strategy_context = upstream_context.get("strategy") if upstream_context else None
    if hasattr(strategy_context, "strategy_family"):
        strategy_family = str(getattr(strategy_context, "strategy_family"))
    market_session = infer_market_session(
        symbol=snapshot.symbol,
        preferences=preferences,
    )
    rendered_tool_outputs = [
        f"market_session: venue={market_session.venue} state={market_session.session_state} tradable_now={market_session.tradable_now} note={market_session.note}"
    ]
    news_items = (
        fetch_news_brief(snapshot.symbol, settings) if news_items is None else news_items
    )
    if settings.news_mode == "off":
        rendered_tool_outputs.append("news_tool: disabled")
    elif news_items:
        rendered_tool_outputs.extend(
            [
                f"news_tool: {item.publisher} | {item.title}"
                for item in news_items[: settings.news_headline_limit]
            ]
        )
    else:
        rendered_tool_outputs.append("news_tool: no headlines returned")
    if decision_features is not None:
        rendered_tool_outputs.append(
            "decision_features: "
            f"technical_trend={decision_features.technical.trend_classification} "
            f"fundamental_flags={','.join(decision_features.fundamental.quality_flags) or 'none'} "
            f"macro_news={len(decision_features.macro.news_signals)}"
        )
    if canonical_snapshot is not None:
        rendered_tool_outputs.append(
            "canonical_analysis: "
            f"completeness={canonical_snapshot.completeness_score:.2f} "
            f"missing={','.join(canonical_snapshot.missing_sections) or 'none'} "
            f"sources={len(canonical_snapshot.source_attributions)}"
        )
    rendered_tool_outputs.extend(list(tool_outputs or []))
    return AgentContext(
        role=role,
        model_name=settings.model_for_role(role),
        snapshot=snapshot,
        canonical_snapshot=canonical_snapshot,
        decision_features=decision_features,
        preferences=preferences,
        portfolio=db.get_account_snapshot(),
        market_session=market_session,
        service_state=db.get_service_state(),
        recent_runs=_summarize_recent_runs(db),
        memory_notes=_summarize_trade_memory(db) if memory_enabled else [],
        retrieved_memories=(
            _summarize_retrieved_memories(db, snapshot) if memory_enabled else []
        ),
        calibration=build_confidence_calibration(
            db,
            snapshot,
            strategy_family=strategy_family,
        ),
        shared_memory_bus=list(shared_memory_bus or []),
        tool_outputs=rendered_tool_outputs,
        upstream_context=_serialize_upstream(upstream_context),
    )


def render_agent_context(context: AgentContext, *, task: str) -> str:
    """
    Render an AgentContext into a newline-delimited prompt string with labeled sections.
    
    The output contains labeled blocks including: Role, Routed Model, Task, Market Context Pack (serialized if present, otherwise a fixed message), Market Snapshot (serialized excluding the `context_pack` field), Operator Preferences, Portfolio Snapshot, and optional sections for Market Session, Runtime State, Recent Runs, Trade Memory, Retrieved Similar Memories, Confidence Calibration, Shared Memory Bus, Tool Outputs, and Upstream Context.
    
    Parameters:
        task (str): The task text placed under the "Task:" header.
    
    Returns:
        str: The assembled prompt string containing the labeled sections.
    """
    sections = [
        f"Role: {context.role}",
        f"Routed Model: {context.model_name}",
        "Task:",
        task,
        "",
        "Market Context Pack:",
        (
            context.snapshot.context_pack.model_dump_json(indent=2)
            if context.snapshot.context_pack is not None
            else "No persisted market context pack is attached."
        ),
        "",
        "Market Snapshot:",
        context.snapshot.model_dump_json(indent=2, exclude={"context_pack"}),
        "",
        "Operator Preferences:",
        context.preferences.model_dump_json(indent=2),
        "",
        "Portfolio Snapshot:",
        context.portfolio.model_dump_json(indent=2),
    ]

    if context.decision_features is not None:
        sections.extend(
            [
                "",
                "Decision Feature Summary:",
                _render_decision_feature_summary(context),
            ]
        )

    if context.canonical_snapshot is not None:
        sections.extend(
            [
                "",
                "Canonical Analysis Snapshot Summary:",
                _render_canonical_snapshot_summary(context),
            ]
        )

    if context.market_session is not None:
        sections.extend(
            [
                "",
                "Market Session:",
                context.market_session.model_dump_json(indent=2),
            ]
        )

    if context.recent_runs:
        sections.extend(
            ["", "Recent Runs:", "\n".join(f"- {line}" for line in context.recent_runs)]
        )
    if context.memory_notes:
        sections.extend(
            [
                "",
                "Trade Memory:",
                "\n".join(f"- {line}" for line in context.memory_notes),
            ]
        )
    if context.retrieved_memories:
        sections.extend(
            [
                "",
                "Retrieved Similar Memories:",
                "\n".join(f"- {line}" for line in context.retrieved_memories),
            ]
        )
    if context.calibration is not None:
        sections.extend(
            [
                "",
                "Confidence Calibration:",
                context.calibration.model_dump_json(indent=2),
            ]
        )
    if context.shared_memory_bus:
        sections.extend(
            [
                "",
                "Shared Memory Bus:",
                "\n".join(
                    f"- {entry.role}: {entry.summary}"
                    for entry in context.shared_memory_bus
                ),
            ]
        )
    if context.tool_outputs:
        sections.extend(
            [
                "",
                "Tool Outputs:",
                "\n".join(f"- {line}" for line in context.tool_outputs),
            ]
        )
    if context.upstream_context:
        rendered = []
        for key, value in context.upstream_context.items():
            rendered.append(f"{key}:\n{value}")
        sections.extend(["", "Upstream Context:", "\n\n".join(rendered)])

    return "\n".join(sections).strip()
