from collections.abc import Sequence
from typing import cast

from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from agentic_trader.agents.operator_chat import (
    apply_preference_update,
    chat_with_persona,
    interpret_operator_instruction,
)
from agentic_trader.config import Settings
from agentic_trader.llm.client import LocalLLM
from agentic_trader.schemas import ChatPersona, OperatorInstruction
from agentic_trader.storage.db import TradingDatabase
from agentic_trader.tui_modules.common import banner, console, open_db
from agentic_trader.tui_modules.monitor_runtime import (
    observer_mode_panel,
    safe_open_read_db,
)
from agentic_trader.ui_text import t as ui_t
from agentic_trader.workflows.service import ensure_llm_ready


def select_chat_persona() -> ChatPersona:
    return cast(
        ChatPersona,
        Prompt.ask(
            ui_t("prompt.chat_persona"),
            choices=[
                "operator_liaison",
                "regime_analyst",
                "strategy_selector",
                "risk_steward",
                "portfolio_manager",
            ],
            default="operator_liaison",
        ),
    )


def render_chat_transcript(
    *, persona: ChatPersona, transcript: Sequence[tuple[str, str]]
) -> None:
    console.clear()
    console.print(banner())
    console.print(
        Panel(
            ui_t("message.chat_exit_hint"),
            title=ui_t("title.chat").format(persona=persona),
            border_style="cyan",
        )
    )
    for role, message in transcript[-8:]:
        border = "bright_blue" if role == "operator" else "green"
        console.print(Panel(message, title=role, border_style=border))


def chat_screen(settings: Settings, db: TradingDatabase) -> None:
    ensure_llm_ready(settings)
    llm = LocalLLM(settings)
    persona = select_chat_persona()
    transcript: list[tuple[str, str]] = []
    while True:
        render_chat_transcript(persona=persona, transcript=transcript)
        user_message = Prompt.ask(ui_t("prompt.you"))
        if user_message.strip().lower() in {"/exit", "exit", "quit"}:
            return
        transcript.append(("operator", user_message))
        response = chat_with_persona(
            llm=llm,
            db=db,
            settings=settings,
            persona=persona,
            user_message=user_message,
        )
        transcript.append((persona, response))


def render_instruction_result(instruction: OperatorInstruction) -> None:
    console.print(
        Panel(
            instruction.model_dump_json(indent=2),
            title=ui_t("title.parsed_operator_instruction"),
            border_style="cyan",
        )
    )


def apply_instruction_update_if_confirmed(
    instruction: OperatorInstruction, db: TradingDatabase
) -> None:
    if not instruction.should_update_preferences:
        return
    if not Confirm.ask(ui_t("prompt.apply_preference_update"), default=False):
        return

    updated = apply_preference_update(db, instruction.preference_update)
    console.print(
        Panel(
            updated.model_dump_json(indent=2),
            title=ui_t("title.updated_preferences"),
            border_style="green",
        )
    )


def instruction_screen(settings: Settings, db: TradingDatabase) -> None:
    ensure_llm_ready(settings)
    llm = LocalLLM(settings)
    message = Prompt.ask(ui_t("prompt.instruction"))
    instruction = interpret_operator_instruction(
        llm=llm,
        db=db,
        settings=settings,
        user_message=message,
        allow_fallback=True,
    )
    render_instruction_result(instruction)
    apply_instruction_update_if_confirmed(instruction, db)


def operator_menu(settings: Settings) -> None:
    while True:
        console.clear()
        console.print(banner())
        table = Table(title=ui_t("title.operator_desk"))
        table.add_column(ui_t("label.key"), style=ui_t("style.key_column"))
        table.add_column(ui_t("label.action"))
        table.add_row("1", ui_t("menu.action_open_operator_chat"))
        table.add_row("2", ui_t("menu.action_parse_operator_instruction"))
        table.add_row("3", ui_t("menu.action_back"))
        console.print(table)
        choice = Prompt.ask(
            ui_t("prompt.select_action"), choices=["1", "2", "3"], default="1"
        )
        if choice == "1":
            db = safe_open_read_db(settings)
            if db is None:
                console.print(
                    observer_mode_panel(ui_t("title.operator_chat_memory_context"))
                )
            else:
                try:
                    chat_screen(settings, db)
                finally:
                    db.close()
        elif choice == "2":
            try:
                db = open_db(settings, read_only=False)
            except Exception as exc:
                console.print(
                    observer_mode_panel(ui_t("title.instruction_application"), str(exc))
                )
                Prompt.ask(ui_t("prompt.continue"), default="")
                continue
            try:
                instruction_screen(settings, db)
            finally:
                db.close()
        else:
            return
