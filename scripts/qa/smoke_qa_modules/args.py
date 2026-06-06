from __future__ import annotations

import os
from argparse import ArgumentParser, Namespace
from collections.abc import Mapping, Sequence
from datetime import datetime

DEFAULT_SONAR_HOST_URL = "http://localhost:9000"
DEFAULT_SONAR_PROJECT_KEY = "agentic-trader"
DEFAULT_SONAR_ORGANIZATION = ""


def _run_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def parse_args(
    argv: Sequence[str] | None = None,
    *,
    env: Mapping[str, str] = os.environ,
) -> Namespace:
    parser = ArgumentParser(
        description="Run terminal smoke QA checks for Agentic Trader."
    )
    parser.add_argument(
        "--include-quality",
        action="store_true",
        help="Also run code-quality checks: ruff, pytest, and pyright when available.",
    )
    parser.add_argument(
        "--include-sonar",
        action="store_true",
        help="Also run pysonar. Reads SONAR_TOKEN or the macOS Keychain token.",
    )
    parser.add_argument(
        "--sonar-host-url",
        default=env.get("SONAR_HOST_URL", DEFAULT_SONAR_HOST_URL),
        help="SonarQube host URL for --include-sonar.",
    )
    parser.add_argument(
        "--sonar-project-key",
        default=env.get("SONAR_PROJECT_KEY", DEFAULT_SONAR_PROJECT_KEY),
        help="SonarQube project key for --include-sonar.",
    )
    parser.add_argument(
        "--sonar-organization",
        default=env.get("SONAR_ORGANIZATION", DEFAULT_SONAR_ORGANIZATION),
        help="Optional SonarCloud organization key for --include-sonar.",
    )
    parser.add_argument(
        "--sonar-branch-name",
        default=env.get("SONAR_BRANCH_NAME"),
        help=(
            "Optional SonarQube branch name for --include-sonar. Leave unset for "
            "local Community Build."
        ),
    )
    parser.add_argument(
        "--run-label",
        default=f"smoke-{_run_id()}",
        help="Artifact subdirectory name under .ai/qa/artifacts/.",
    )
    parser.add_argument(
        "--include-runtime-cycle",
        action="store_true",
        help=(
            "Run one isolated foreground orchestrator cycle. This is slower and "
            "requires live market data plus a healthy LLM."
        ),
    )
    parser.add_argument(
        "--runtime-symbol",
        default="BTC-USD",
        help="Symbol used by --include-runtime-cycle.",
    )
    parser.add_argument(
        "--runtime-interval",
        default="1d",
        help="Interval used by --include-runtime-cycle.",
    )
    parser.add_argument(
        "--runtime-lookback",
        default="180d",
        help="Lookback used by --include-runtime-cycle.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)
