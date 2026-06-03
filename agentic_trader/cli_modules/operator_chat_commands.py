from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

import typer
from rich.panel import Panel
from rich.table import Table

from agentic_trader.cli_modules.common import console
from agentic_trader.config import Settings
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import (
    ChatHistoryEntry,
    ChatPersona,
    InvestmentPreferences,
    OperatorInstruction,
)
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.ui_text import (
    HELP_CHAT_MESSAGE,
    HELP_CHAT_PERSONA,
    HELP_INSTRUCT_APPLY,
    HELP_INSTRUCT_MESSAGE,
    HELP_JSON,
    LABEL_FIELD,
    LABEL_MESSAGE,
    LABEL_PREFERENCE_UPDATE,
    LABEL_RATIONALE,
    LABEL_REQUIRES_CONFIRMATION,
    LABEL_SUMMARY,
    LABEL_UPDATE_PREFERENCES,
    LABEL_VALUE,
    TITLE_CHAT,
    TITLE_OPERATOR_INSTRUCTION,
    TITLE_UPDATED_PREFERENCES,
)


@dataclass(frozen=True)
class OperatorChatCommandDeps:
    settings_provider: Callable[[], Settings]
    ensure_ready: Callable[[Settings], object]
    emit_json: Callable[[object], None]
    open_db: Callable[..., TradingDatabase]
    llm_factory: Callable[[Settings], LocalLLM]
    chat_with_persona: Callable[..., str]
    append_chat_history: Callable[[Settings, ChatHistoryEntry], object]
    database_factory: Callable[[Settings], TradingDatabase]
    interpret_instruction: Callable[..., OperatorInstruction]
    apply_preference_update: Callable[..., InvestmentPreferences]


def register_operator_chat_commands(
    app: typer.Typer,
    deps: OperatorChatCommandDeps,
) -> None:
    _register_chat_command(app, deps)
    _register_instruct_command(app, deps)


def _register_chat_command(app: typer.Typer, deps: OperatorChatCommandDeps) -> None:
    @app.command()
    def chat(
        persona: ChatPersona = typer.Option("operator_liaison", help=HELP_CHAT_PERSONA),
        message: str | None = typer.Option(None, help=HELP_CHAT_MESSAGE),
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    ) -> None:
        """
        Send a message to a chosen operator persona and display or emit the persona's reply.

        If `message` is omitted an interactive prompt is shown. The interaction is recorded
        in persistent chat history. Output is printed as a terminal panel unless
        `json_output` is true, in which case a JSON payload containing `persona`,
        `message`, and `response` is emitted.
        """
        settings = deps.settings_provider()
        deps.ensure_ready(settings)
        db = deps.open_db(settings, read_only=True)
        try:
            prompt = message or typer.prompt(LABEL_MESSAGE)
            response = deps.chat_with_persona(
                llm=deps.llm_factory(settings),
                db=db,
                settings=settings,
                persona=persona,
                user_message=prompt,
            )
        finally:
            db.close()
        deps.append_chat_history(
            settings,
            ChatHistoryEntry(
                entry_id=f"chat-{uuid4().hex[:12]}",
                created_at=datetime.now(timezone.utc).isoformat(),
                persona=persona,
                user_message=prompt,
                response_text=response,
            ),
        )
        if json_output:
            deps.emit_json(
                {
                    "persona": persona,
                    "message": prompt,
                    "response": response,
                }
            )
            return
        console.print(
            Panel(
                response,
                title=TITLE_CHAT.format(persona=persona),
                border_style="cyan",
            )
        )


def _register_instruct_command(app: typer.Typer, deps: OperatorChatCommandDeps) -> None:
    @app.command()
    def instruct(
        message: str = typer.Option(..., help=HELP_INSTRUCT_MESSAGE),
        apply: bool = typer.Option(False, help=HELP_INSTRUCT_APPLY),
        json_output: bool = typer.Option(False, "--json", help=HELP_JSON),
    ) -> None:
        """
        Interpret a natural-language operator instruction and optionally persist a resulting preference update.
        """
        settings = deps.settings_provider()
        deps.ensure_ready(settings)
        db = deps.database_factory(settings)
        try:
            instruction = deps.interpret_instruction(
                llm=deps.llm_factory(settings),
                db=db,
                settings=settings,
                user_message=message,
                allow_fallback=True,
            )
            updated: InvestmentPreferences | None = None
            if apply and instruction.should_update_preferences:
                updated = deps.apply_preference_update(
                    db, instruction.preference_update
                )
            if json_output:
                deps.emit_json(
                    {
                        "instruction": instruction.model_dump(mode="json"),
                        "applied": updated is not None,
                        "updated_preferences": (
                            updated.model_dump(mode="json")
                            if updated is not None
                            else None
                        ),
                    }
                )
                return
            _render_instruction(instruction)
            if updated is not None:
                console.print(
                    Panel(
                        updated.model_dump_json(indent=2),
                        title=TITLE_UPDATED_PREFERENCES,
                        border_style="green",
                    )
                )
        finally:
            db.close()


def _render_instruction(instruction: OperatorInstruction) -> None:
    table = Table(title=TITLE_OPERATOR_INSTRUCTION)
    table.add_column(LABEL_FIELD)
    table.add_column(LABEL_VALUE)
    table.add_row(LABEL_SUMMARY, instruction.summary)
    table.add_row(LABEL_UPDATE_PREFERENCES, str(instruction.should_update_preferences))
    table.add_row(LABEL_REQUIRES_CONFIRMATION, str(instruction.requires_confirmation))
    table.add_row(LABEL_RATIONALE, instruction.rationale)
    table.add_row(
        LABEL_PREFERENCE_UPDATE,
        json.dumps(instruction.preference_update.model_dump(mode="json"), indent=2),
    )
    console.print(table)
