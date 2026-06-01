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
from agentic_trader.tui_modules.monitor_sections import (
    observer_mode_panel,
    safe_open_read_db,
)
from agentic_trader.ui_text import (
    LABEL_ACTION,
    LABEL_KEY,
    MENU_ACTION_BACK,
    MENU_ACTION_OPEN_OPERATOR_CHAT,
    MENU_ACTION_PARSE_OPERATOR_INSTRUCTION,
    MESSAGE_CHAT_EXIT_HINT,
    PROMPT_APPLY_PREFERENCE_UPDATE,
    PROMPT_CHAT_PERSONA,
    PROMPT_CONTINUE,
    PROMPT_INSTRUCTION,
    PROMPT_SELECT_ACTION,
    PROMPT_YOU,
    STYLE_KEY_COLUMN,
    TITLE_CHAT,
    TITLE_INSTRUCTION_APPLICATION,
    TITLE_OPERATOR_CHAT_MEMORY_CONTEXT,
    TITLE_OPERATOR_DESK,
    TITLE_PARSED_OPERATOR_INSTRUCTION,
    TITLE_UPDATED_PREFERENCES,
)
from agentic_trader.workflows.service import ensure_llm_ready


def select_chat_persona() -> ChatPersona:
    return cast(
        ChatPersona,
        Prompt.ask(
            PROMPT_CHAT_PERSONA,
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
            MESSAGE_CHAT_EXIT_HINT,
            title=TITLE_CHAT.format(persona=persona),
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
        user_message = Prompt.ask(PROMPT_YOU)
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
            title=TITLE_PARSED_OPERATOR_INSTRUCTION,
            border_style="cyan",
        )
    )


def apply_instruction_update_if_confirmed(
    instruction: OperatorInstruction, db: TradingDatabase
) -> None:
    if not instruction.should_update_preferences:
        return
    if not Confirm.ask(PROMPT_APPLY_PREFERENCE_UPDATE, default=False):
        return

    updated = apply_preference_update(db, instruction.preference_update)
    console.print(
        Panel(
            updated.model_dump_json(indent=2),
            title=TITLE_UPDATED_PREFERENCES,
            border_style="green",
        )
    )


def instruction_screen(settings: Settings, db: TradingDatabase) -> None:
    ensure_llm_ready(settings)
    llm = LocalLLM(settings)
    message = Prompt.ask(PROMPT_INSTRUCTION)
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
        table = Table(title=TITLE_OPERATOR_DESK)
        table.add_column(LABEL_KEY, style=STYLE_KEY_COLUMN)
        table.add_column(LABEL_ACTION)
        table.add_row("1", MENU_ACTION_OPEN_OPERATOR_CHAT)
        table.add_row("2", MENU_ACTION_PARSE_OPERATOR_INSTRUCTION)
        table.add_row("3", MENU_ACTION_BACK)
        console.print(table)
        choice = Prompt.ask(PROMPT_SELECT_ACTION, choices=["1", "2", "3"], default="1")
        if choice == "1":
            db = safe_open_read_db(settings)
            if db is None:
                console.print(observer_mode_panel(TITLE_OPERATOR_CHAT_MEMORY_CONTEXT))
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
                    observer_mode_panel(TITLE_INSTRUCTION_APPLICATION, str(exc))
                )
                Prompt.ask(PROMPT_CONTINUE, default="")
                continue
            try:
                instruction_screen(settings, db)
            finally:
                db.close()
        else:
            return
