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
    """
    Prompt the user to choose which chat persona to use for the session.
    
    The prompt offers the personas: "operator_liaison", "regime_analyst", "strategy_selector", "risk_steward", and "portfolio_manager". The default selection is "operator_liaison".
    
    Returns:
        ChatPersona: The selected chat persona.
    """
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
    """
    Render the recent chat transcript for the given persona to the console.
    
    Displays a banner, an exit hint panel titled with the persona, and the last eight (role, message) pairs from `transcript` as individual panels. Roles equal to "operator" are styled with a bright blue border; all other roles use a green border.
    
    Parameters:
        persona (ChatPersona): The chat persona whose title is shown in the exit-hint panel.
        transcript (Sequence[tuple[str, str]]): Sequence of (role, message) pairs representing the conversation; only the last eight entries are rendered.
    """
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
    """
    Start an interactive operator chat session with a selected persona and maintain an in-memory transcript.
    
    Displays the chat UI, prompts the operator for messages, and appends each operator message and persona response to an in-memory transcript until the operator enters "/exit", "exit", or "quit" (case-insensitive, trimmed). The session uses the provided settings and trading database to generate persona responses.
    
    Parameters:
        settings (Settings): Application settings used to prepare and drive the local language model.
        db (TradingDatabase): Open trading database used as context for persona responses.
    """
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
    """
    Render an operator instruction as a formatted JSON panel in the console.
    
    Parameters:
        instruction (OperatorInstruction): The parsed operator instruction to display; it is shown as pretty-printed JSON inside a cyan-bordered panel titled with the localized "parsed operator instruction" label.
    """
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
    """
    Apply preference updates contained in an OperatorInstruction after asking the user for confirmation.
    
    If the instruction does not request preference updates the function returns without making changes. If the user confirms, applies the preference update to the provided TradingDatabase and displays the updated preferences as JSON in a green-bordered panel.
    
    Parameters:
        instruction (OperatorInstruction): Parsed operator instruction that may include a preference update and a flag indicating whether to apply it.
        db (TradingDatabase): Database instance to which preference updates will be applied.
    """
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
    """
    Prompt the operator for a free-form instruction, interpret it using the local LLM, render the parsed OperatorInstruction, and apply any confirmed preference updates to the trading database.
    
    Parameters:
        settings (Settings): Configuration and runtime settings used to initialize the local LLM.
        db (TradingDatabase): Database instance used to read context and persist confirmed preference updates.
    """
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
    """
    Display the operator desk menu and handle user-selected actions until the user chooses to go back.
    
    Shows a menu with options to open the operator chat, parse an operator instruction, or return. Selecting the chat attempts to open a read-only database and either enters the chat screen or displays an observer-mode panel if the DB is unavailable. Selecting instruction parsing attempts to open a writable database, displays an observer-mode panel on error, or enters the instruction screen on success. The function loops until the user selects the "back" action.
    
    Parameters:
        settings (Settings): Application settings used to open databases and configure UI.
    """
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
