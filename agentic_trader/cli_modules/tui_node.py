from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import typer
from rich.panel import Panel

from agentic_trader.cli_modules.common import console
from agentic_trader.tui import run_main_menu
from agentic_trader.ui_text import (
    MESSAGE_INSTALLING_TUI_DEPENDENCIES,
    MESSAGE_NODE_MISSING,
    MESSAGE_TUI_MISSING,
    TITLE_INSTALLING_TUI_DEPENDENCIES,
    TITLE_NODE_MISSING,
    TITLE_TUI_MISSING,
)

TUI_PACKAGE_NAME = "agentic-trader-tui"
type NodeCommandSet = tuple[list[str], list[str], Path, str]
ToolResolver = Callable[[str], str | None]


def resolve_tui_node_commands(
    tui_dir: Path,
    *,
    which: ToolResolver = shutil.which,
) -> NodeCommandSet | None:
    repo_root = tui_dir.parent
    pnpm = which("pnpm")
    if pnpm and (repo_root / "pnpm-workspace.yaml").exists():
        return (
            [pnpm, "install"],
            [pnpm, "--filter", TUI_PACKAGE_NAME, "run", "start"],
            repo_root,
            "pnpm workspace",
        )
    if pnpm and (tui_dir / "pnpm-lock.yaml").exists():
        return (
            [pnpm, "install"],
            [pnpm, "run", "start"],
            tui_dir,
            "pnpm",
        )

    npm = which("npm")
    if npm and (tui_dir / "package-lock.json").exists():
        return (
            [npm, "install"],
            [npm, "run", "start"],
            tui_dir,
            "npm",
        )
    if npm:
        return (
            [npm, "install", "--no-package-lock"],
            [npm, "run", "start"],
            tui_dir,
            "npm",
        )

    yarn = which("yarn")
    if yarn and (tui_dir / "yarn.lock").exists():
        return (
            [yarn, "install", "--frozen-lockfile"],
            [yarn, "start"],
            tui_dir,
            "yarn",
        )
    if yarn:
        return (
            [yarn, "install", "--no-lockfile"],
            [yarn, "start"],
            tui_dir,
            "yarn",
        )

    return None


def tui_dependencies_installed(tui_dir: Path, command_cwd: Path) -> bool:
    _ = command_cwd
    return (tui_dir / "node_modules").exists()


def register_tui_command(app: typer.Typer) -> None:
    @app.command("tui")
    def ink_tui() -> None:
        open_ink_tui()


def open_ink_tui() -> None:
    tui_dir = Path(__file__).resolve().parents[2] / "tui"
    if not tui_dir.exists():
        console.print(
            _render_health_panel(
                TITLE_TUI_MISSING,
                MESSAGE_TUI_MISSING,
                border_style="yellow",
            )
        )
        run_main_menu()
        return

    node_commands = resolve_tui_node_commands(tui_dir)
    if node_commands is None:
        console.print(
            _render_health_panel(
                TITLE_NODE_MISSING,
                MESSAGE_NODE_MISSING,
                border_style="yellow",
            )
        )
        run_main_menu()
        return
    install_command, start_command, command_cwd, package_manager = node_commands

    if not tui_dependencies_installed(tui_dir, command_cwd):
        console.print(
            _render_health_panel(
                TITLE_INSTALLING_TUI_DEPENDENCIES,
                MESSAGE_INSTALLING_TUI_DEPENDENCIES.format(
                    package_manager=package_manager
                ),
                border_style="yellow",
            )
        )
        subprocess.run(install_command, cwd=command_cwd, check=True)

    cli_exec = shutil.which("agentic-trader") or "agentic-trader"
    env = {
        **os.environ,
        "AGENTIC_TRADER_CLI": cli_exec,
        "AGENTIC_TRADER_PYTHON": sys.executable,
    }
    subprocess.run(start_command, cwd=command_cwd, check=True, env=env)


def _render_health_panel(status: str, body: str, *, border_style: str) -> Panel:
    return Panel(
        body,
        title=f"Agentic Trader // {status}",
        border_style=border_style,
    )
