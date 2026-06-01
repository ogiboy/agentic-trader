from __future__ import annotations

import json

import typer
from rich.console import Console

from agentic_trader.config import Settings
from agentic_trader.security import redact_sensitive_text
from agentic_trader.storage.db import TradingDatabase

console = Console()


def emit_json(payload: object) -> None:
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


def emit_json_error(error: Exception | str) -> None:
    typer.echo(
        json.dumps(
            {"error": redact_sensitive_text(error, max_length=240)},
            indent=2,
            sort_keys=True,
        )
    )


def open_db(settings: Settings, *, read_only: bool = False) -> TradingDatabase:
    return TradingDatabase(settings, read_only=read_only)
