from __future__ import annotations

import argparse
from pathlib import Path


def parse_args(argv: list[str], *, default_artifact_root: Path) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the V1 paper desk rehearsal and collect QA evidence."
    )
    parser.add_argument("--symbols", default="AAPL,MSFT")
    parser.add_argument("--cycles", type=int, default=2)
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--lookback", default="180d")
    parser.add_argument("--proposal-symbol")
    parser.add_argument("--side", choices=["buy", "sell"], default="buy")
    parser.add_argument("--quantity", type=float, default=1.0)
    parser.add_argument("--reference-price", type=float, default=190.0)
    parser.add_argument("--confidence", type=float, default=0.72)
    parser.add_argument(
        "--thesis",
        default="V1 paper desk rehearsal proposal with explicit risk controls.",
    )
    parser.add_argument(
        "--invalidation-condition",
        default="Close if risk controls trigger or thesis invalidates.",
    )
    parser.add_argument(
        "--execution-backend",
        choices=["paper", "alpaca_paper"],
        default="paper",
    )
    parser.add_argument("--artifact-root", type=Path, default=default_artifact_root)
    parser.add_argument("--label")
    return parser.parse_args(argv)
