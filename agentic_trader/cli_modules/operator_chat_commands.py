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
from agentic_trader.ui_text import t as ui_t


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
        persona: ChatPersona = typer.Option(
            "operator_liaison", help=ui_t("help.chat_persona")
        ),
        message: str | None = typer.Option(None, help=ui_t("help.chat_message")),
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
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
            prompt = message or typer.prompt(ui_t("label.message"))
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
                title=ui_t("title.chat").format(persona=persona),
                border_style="cyan",
            )
        )


def _register_instruct_command(app: typer.Typer, deps: OperatorChatCommandDeps) -> None:
    @app.command()
    def instruct(
        message: str = typer.Option(..., help=ui_t("help.instruct_message")),
        apply: bool = typer.Option(False, help=ui_t("help.instruct_apply")),
        json_output: bool = typer.Option(False, "--json", help=ui_t("help.json")),
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
                        title=ui_t("title.updated_preferences"),
                        border_style="green",
                    )
                )
        finally:
            db.close()


def _render_instruction(instruction: OperatorInstruction) -> None:
    table = Table(title=ui_t("title.operator_instruction"))
    table.add_column(ui_t("label.field"))
    table.add_column(ui_t("label.value"))
    table.add_row(ui_t("label.summary"), instruction.summary)
    table.add_row(
        ui_t("label.update_preferences"), str(instruction.should_update_preferences)
    )
    table.add_row(
        ui_t("label.requires_confirmation"), str(instruction.requires_confirmation)
    )
    table.add_row(ui_t("label.rationale"), instruction.rationale)
    table.add_row(
        ui_t("label.preference_update"),
        json.dumps(instruction.preference_update.model_dump(mode="json"), indent=2),
    )
    console.print(table)
