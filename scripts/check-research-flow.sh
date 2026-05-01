#!/usr/bin/env sh
set -eu

REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
SIDECAR_DIR="${REPO_ROOT}/sidecars/research_flow"

if ! command -v uv >/dev/null 2>&1; then
	echo "uv is required for the research CrewAI Flow sidecar. Install uv before running this check." >&2
	exit 1
fi

cd "${SIDECAR_DIR}"
uv sync --locked
uv run --locked python -m compileall -q src
uv run --locked research-flow-check
printf '%s\n' '{"mode":"training","symbols":["AAPL"],"provider_outputs":[]}' | uv run --locked --no-sync research-flow-contract
uv run --locked python -c 'import sys; print(f"python={sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")'
