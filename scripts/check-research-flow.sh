#!/usr/bin/env sh
set -eu

REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

if ! command -v uv >/dev/null 2>&1; then
	echo "uv is required for the research CrewAI Flow sidecar. Install uv before running this check." >&2
	exit 1
fi

cd "${REPO_ROOT}"
uv sync --locked --all-packages --all-extras --group dev
uv run --locked --package research-flow python -m compileall -q sidecars/research_flow/src
uv run --locked --package research-flow research-flow-check
printf '%s\n' '{"mode":"training","symbols":["AAPL"],"provider_outputs":[]}' | uv run --locked --package research-flow --no-sync research-flow-contract
uv run --locked --package research-flow python -c 'import sys; print(f"python={sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")'
