import sys

from agentic_trader.cli import main
from agentic_trader.tui import run_main_menu


if __name__ == "__main__":
    if len(sys.argv) == 1:
        run_main_menu()
    else:
        main()
