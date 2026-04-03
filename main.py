import sys

from rich.console import Console
from rich.panel import Panel

from agentic_trader.cli import main
from agentic_trader.tui import run_main_menu

console = Console()


if __name__ == "__main__":
    try:
        if len(sys.argv) == 1:
            run_main_menu()
        else:
            main()
    except KeyboardInterrupt:
        console.print(Panel("Control room closed cleanly.", title="Exit", border_style="blue"))
