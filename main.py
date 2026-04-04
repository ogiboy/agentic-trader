import sys

from rich.console import Console
from rich.panel import Panel

from agentic_trader.cli import main

console = Console()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print(
            Panel("Control room closed cleanly.", title="Exit", border_style="blue")
        )
